# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""TC-FVT-023 extension: Slurm communication path IPv6 verification.

Captures live Slurm TCP traffic with tcpdump during a 2-node job and
classifies every flow by protocol family, interface, and Slurm port to
verify that controller-to-compute and srun-to-compute traffic uses IPoIB
IPv6 rather than admin Ethernet IPv4.
"""

import os
import re
import shlex
import time
from typing import Any

from ..vars.ipoib_vars import (
    IPOIB_COMM_CAPTURE_TIMEOUT,
    IPOIB_COMM_JOB_SLEEP,
    IPOIB_COMM_PATH_COMMANDS,
    IPOIB_COMM_SETTLE_SECONDS,
    IPOIB_COMM_V4_PCAP,
    IPOIB_COMM_V6_PCAP,
    IPOIB_SLURM_PORT_SLURMCTLD,
    IPOIB_SLURM_PORT_SLURMD,
    IPOIB_SLURM_SRUN_PORT_RANGE,
    IPV6_MODES,
    NETWORK_SPEC_FILE,
)
from ..vars.pxeboot_vars import SLURM_COMPUTE_PREFIX, SLURM_CONTROL_PREFIX
from ._ipoib_helpers import canonical_ip, ib_addr_mode, ib_network_block, row_address
from ._prepare_helpers import read_yaml_mapping
from ._provision_helpers import load_context
from ._pxeboot_helpers import remote_command, runtime_exception, runtime_result
from ._workload_helpers import optional_skip
from .project_func import resolve_target_input_project_path

_ERRORS = (OSError, RuntimeError, TypeError, ValueError, KeyError)

# Regex to parse tcpdump text output lines.
# Matches: "timestamp iface In/Out IP/IP6 src.port > dst.port: ..."
_TCPDUMP_LINE = re.compile(
    r"^\S+\s+(\S+)\s+\S+\s+(IP6?)\s+"
    r"(\S+?)\.(\d+)\s+>\s+"
    r"(\S+?)\.(\d+):"
)


def _parse_tcpdump(output: str) -> list[dict[str, Any]]:
    """Parse tcpdump text output into structured flow records."""
    flows = []
    for line in output.splitlines():
        match = _TCPDUMP_LINE.match(line)
        if not match:
            continue
        iface, family_str, src_ip, src_port, dst_ip, dst_port = match.groups()
        flows.append({
            "interface": iface,
            "family": "ipv6" if family_str == "IP6" else "ipv4",
            "src_ip": src_ip,
            "src_port": int(src_port),
            "dst_ip": dst_ip,
            "dst_port": int(dst_port),
        })
    return flows


def _classify_port(port: int) -> str:
    """Classify a Slurm port into a service name."""
    if port == IPOIB_SLURM_PORT_SLURMCTLD:
        return "slurmctld"
    if port == IPOIB_SLURM_PORT_SLURMD:
        return "slurmd"
    lo, hi = IPOIB_SLURM_SRUN_PORT_RANGE
    if lo <= port <= hi:
        return "srun"
    return "other"


def _classify_flows(flows, ib_addresses, admin_addresses):
    """Classify flows into directional categories with protocol family."""
    categories = {
        "controller_to_compute": {"ipv4": 0, "ipv6": 0, "ib_iface": 0, "eth_iface": 0},
        "compute_to_controller": {"ipv4": 0, "ipv6": 0, "ib_iface": 0, "eth_iface": 0},
        "srun_traffic": {"ipv4": 0, "ipv6": 0, "ib_iface": 0, "eth_iface": 0},
        "other": {"ipv4": 0, "ipv6": 0, "ib_iface": 0, "eth_iface": 0},
    }

    all_ib = set(ib_addresses.values())
    all_admin = set(admin_addresses.values())
    ib_iface_names = {"ibp", "ib"}  # IB interface name prefixes

    for flow in flows:
        dst_service = _classify_port(flow["dst_port"])
        is_ib_iface = any(flow["interface"].startswith(p) for p in ib_iface_names)

        if dst_service == "slurmctld":
            cat = "compute_to_controller"
        elif dst_service == "slurmd":
            # Check if source is an IB address (controller/srun pushing to compute)
            if flow["src_ip"] in all_ib or flow["src_ip"] in all_admin:
                cat = "controller_to_compute"
            else:
                cat = "controller_to_compute"
        elif dst_service == "srun":
            cat = "srun_traffic"
        else:
            cat = "other"

        categories[cat][flow["family"]] += 1
        if is_ib_iface:
            categories[cat]["ib_iface"] += 1
        else:
            categories[cat]["eth_iface"] += 1

    return categories


def _ipoib_nodes(host):
    """Return (mode, all_nodes, compute_nodes, controller) with IB address info."""
    context = load_context(host)
    input_dir = resolve_target_input_project_path(host)
    block = ib_network_block(
        read_yaml_mapping(host, os.path.join(input_dir, NETWORK_SPEC_FILE))
    )
    all_nodes = []
    compute_nodes = []
    controller = None
    for row in context["rows"]:
        if not str(row.get("IB_NIC_NAME") or "").strip():
            continue
        group = str(row.get("EXPECTED_FUNCTIONAL_GROUP", ""))
        node = {
            "row": row,
            "ipv4": canonical_ip(row_address(row, 4)),
            "ipv6": canonical_ip(row_address(row, 6)),
            "hostname": row["HOSTNAME"],
            "group": group,
        }
        all_nodes.append(node)
        if group.startswith(SLURM_COMPUTE_PREFIX):
            compute_nodes.append(node)
        elif group.startswith(SLURM_CONTROL_PREFIX):
            controller = node
    return ib_addr_mode(block), all_nodes, compute_nodes, controller


def check_ipoib_slurm_comm_path(host) -> dict[str, Any]:
    """TC-FVT-023 ext: verify Slurm job traffic uses IPoIB IPv6.

    1. Select two compute nodes with IB IPv6 addresses.
    2. Start tcpdump on one compute node (split IPv4/IPv6 captures).
    3. Submit a 2-node srun job from the controller.
    4. Parse captured packets and classify by direction and family.
    5. Assert controller-to-compute and srun traffic is IPv6 over IB.
    """
    summary = "Slurm IPoIB communication path"
    try:
        mode, all_nodes, compute_nodes, controller = _ipoib_nodes(host)
        fields: list[tuple[str, object]] = [
            ("Controller", controller["hostname"] if controller else "none"),
        ]
        if mode not in IPV6_MODES:
            return optional_skip(
                summary, f"ib_addr_mode is {mode}; IPv6 not selected"
            )
        if controller is None:
            return optional_skip(summary, "No Slurm controller with IB_NIC_NAME is present")
        ipv6_compute = [n for n in compute_nodes if n["ipv6"]]
        if len(ipv6_compute) < 2:
            return optional_skip(
                summary,
                "At least 2 compute nodes with IB IPv6 addresses required"
            )

        # Pick two compute nodes for the job and capture
        capture_node = ipv6_compute[0]
        peer_node = ipv6_compute[1]
        cap_host = capture_node["hostname"]
        peer_host = peer_node["hostname"]
        cap_row = capture_node["row"]
        control_row = controller["row"]

        fields.extend([
            ("Capture node", cap_host),
            ("Peer node", peer_host),
            ("IB addr (capture)", capture_node["ipv6"]),
            ("IB addr (peer)", peer_node["ipv6"]),
        ])

        # Build address maps for classification
        ib_addresses = {n["hostname"]: n["ipv6"] for n in all_nodes if n["ipv6"]}
        admin_addresses = {
            n["hostname"]: str(n["row"].get("ADMIN_IP", "")).strip()
            for n in all_nodes
        }

        # Step 1: Check tcpdump is available
        check = remote_command(
            host, cap_row, IPOIB_COMM_PATH_COMMANDS["tcpdump_check"]
        )
        if check.rc != 0:
            return optional_skip(
                summary, f"tcpdump not installed on {cap_host}"
            )

        v4_pcap = IPOIB_COMM_V4_PCAP
        v6_pcap = IPOIB_COMM_V6_PCAP
        timeout_s = str(IPOIB_COMM_CAPTURE_TIMEOUT)

        # Step 2: Start tcpdump on capture node
        start_cmd = IPOIB_COMM_PATH_COMMANDS["tcpdump_start"] % (
            shlex.quote(v4_pcap), shlex.quote(v6_pcap),
            timeout_s, shlex.quote(v4_pcap),
            timeout_s, shlex.quote(v6_pcap),
        )
        start = remote_command(host, cap_row, start_cmd)
        if "started" not in start.stdout:
            fields.append(("tcpdump start", "FAILED"))
            return runtime_result(
                False, summary, fields,
                f"Failed to start tcpdump on {cap_host}"
            )
        fields.append(("tcpdump", "capturing"))

        # Step 3: Wait for tcpdump to settle then run a 2-node job from the controller
        time.sleep(IPOIB_COMM_SETTLE_SECONDS)
        job_cmd = IPOIB_COMM_PATH_COMMANDS["srun_2node"] % (
            shlex.quote(cap_host), shlex.quote(peer_host),
            str(IPOIB_COMM_JOB_SLEEP),
        )
        job = remote_command(host, control_row, job_cmd)
        job_ok = job.rc == 0
        fields.append(("Job result", "PASS" if job_ok else f"FAIL rc={job.rc}"))
        if not job_ok:
            # Cleanup pcap files
            remote_command(
                host, cap_row,
                IPOIB_COMM_PATH_COMMANDS["tcpdump_cleanup"] % (
                    shlex.quote(v4_pcap), shlex.quote(v6_pcap)
                ),
            )
            return runtime_result(
                False, summary, fields,
                f"srun job failed on {cap_host},{peer_host}: {job.stderr[:200]}"
            )

        # Step 4: Wait for tcpdump to finish and read captures
        time.sleep(IPOIB_COMM_CAPTURE_TIMEOUT - IPOIB_COMM_JOB_SLEEP)
        v4_out = remote_command(
            host, cap_row,
            IPOIB_COMM_PATH_COMMANDS["tcpdump_read"] % shlex.quote(v4_pcap),
        )
        v6_out = remote_command(
            host, cap_row,
            IPOIB_COMM_PATH_COMMANDS["tcpdump_read"] % shlex.quote(v6_pcap),
        )
        v4_flows = _parse_tcpdump(v4_out.stdout)
        v6_flows = _parse_tcpdump(v6_out.stdout)
        all_flows = v4_flows + v6_flows

        fields.append(("IPv4 packets", len(v4_flows)))
        fields.append(("IPv6 packets", len(v6_flows)))

        # Step 5: Classify flows
        categories = _classify_flows(all_flows, ib_addresses, admin_addresses)
        failures = []

        # Controller -> compute (port 6818): must be IPv6 over IB
        c2c = categories["controller_to_compute"]
        fields.append((
            "Controller->compute",
            f"{c2c['ipv6']} IPv6 / {c2c['ipv4']} IPv4 "
            f"(IB: {c2c['ib_iface']}, Eth: {c2c['eth_iface']})"
        ))
        if c2c["ipv6"] == 0 and c2c["ipv4"] == 0:
            fields.append(("  Warning", "No controller->compute packets captured"))
        elif c2c["ipv4"] > 0 and c2c["ib_iface"] == 0:
            failures.append(
                f"Controller->compute: {c2c['ipv4']} IPv4 packets "
                f"(expected IPv6 over IB)"
            )

        # Compute -> controller (port 6817): known limitation, IPv4
        c2s = categories["compute_to_controller"]
        fields.append((
            "Compute->controller",
            f"{c2s['ipv6']} IPv6 / {c2s['ipv4']} IPv4 "
            f"(IB: {c2s['ib_iface']}, Eth: {c2s['eth_iface']})"
        ))
        if c2s["ipv4"] > 0 and c2s["ipv6"] == 0:
            fields.append((
                "  Info",
                "Known limitation (BR-18602): compute->controller "
                "uses IPv4 because SlurmctldHost has no AAAA record"
            ))

        # srun traffic (ports 60001-63000): must be IPv6 over IB
        srun = categories["srun_traffic"]
        fields.append((
            "srun I/O",
            f"{srun['ipv6']} IPv6 / {srun['ipv4']} IPv4 "
            f"(IB: {srun['ib_iface']}, Eth: {srun['eth_iface']})"
        ))
        if srun["ipv4"] > 0 and srun["ib_iface"] == 0:
            failures.append(
                f"srun I/O: {srun['ipv4']} IPv4 packets "
                f"(expected IPv6 over IB)"
            )

        # Cross-check: no IPv4 Slurm packets on the IB interface
        v4_on_ib = sum(
            1 for f in v4_flows
            if any(f["interface"].startswith(p) for p in ("ibp", "ib"))
        )
        fields.append(("IPv4 on IB interface", v4_on_ib))
        if v4_on_ib > 0:
            failures.append(
                f"{v4_on_ib} IPv4 Slurm packet(s) traversed the IB interface"
            )

        # Cross-check: no IPv6 Slurm packets on the Ethernet interface
        v6_on_eth = sum(
            1 for f in v6_flows
            if not any(f["interface"].startswith(p) for p in ("ibp", "ib"))
        )
        fields.append(("IPv6 on Ethernet", v6_on_eth))
        if v6_on_eth > 0:
            fields.append((
                "  Info",
                "IPv6 packets on Ethernet may indicate loopback or "
                "admin-network IPv6 (not necessarily a failure)"
            ))

        # Cleanup pcap files
        remote_command(
            host, cap_row,
            IPOIB_COMM_PATH_COMMANDS["tcpdump_cleanup"] % (
                shlex.quote(v4_pcap), shlex.quote(v6_pcap)
            ),
        )

        error = "; ".join(failures) if failures else ""
        return runtime_result(not failures, summary, fields, error)

    except _ERRORS as exc:
        return runtime_exception(summary, exc)
