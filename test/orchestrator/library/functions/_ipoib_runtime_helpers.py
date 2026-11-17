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

"""Live IPoIB state, peer-mesh, and product-classifier helpers.

Shared by the ER-ORCH-005 resilience (TC-FVT-016/020/025/026) and PowerVault
coexistence (TC-FVT-024) post-boot checks.
"""

import importlib.util
import ipaddress
import re
import shlex
import time
from functools import lru_cache
from pathlib import Path
from typing import Any

from ..vars.ipoib_vars import (
    ADDRESS_VERIFIER_PATH,
    IB_MODE_FAMILIES,
    IB_MODE_IPV4_ONLY,
    IB_MODE_IPV6_ONLY,
    IPOIB_COMMANDS,
    IPOIB_KERNEL_MODULES,
    IPOIB_MIN_MTU,
    IPOIB_PING_ATTEMPTS,
    IPOIB_RESILIENCE_COMMANDS,
    PING_TIMEOUT_SECONDS,
    SAFE_IFACE,
    UNHEALTHY_IPV6_FLAGS,
)
from ..vars.pxeboot_vars import SLURM_COMPUTE_PREFIX
from ._ipoib_helpers import canonical_ip
from ._pxeboot_helpers import remote_command, remote_json, report_poll_progress


def families_for(mode: str) -> tuple[int, ...]:
    """Return the IP families IPoIB must carry for *mode*."""
    return IB_MODE_FAMILIES.get(mode, IB_MODE_FAMILIES[IB_MODE_IPV4_ONLY])


def is_compute(node: dict[str, Any]) -> bool:
    """Return whether an IPoIB node is a mapped Slurm compute node."""
    return str(node["row"].get("EXPECTED_FUNCTIONAL_GROUP", "")).startswith(
        SLURM_COMPUTE_PREFIX
    )


def hostname(node: dict[str, Any]) -> str:
    """Return the mapped hostname of an IPoIB node."""
    return node["row"]["HOSTNAME"]


def address(node: dict[str, Any], family: int) -> str:
    """Return the approved IB address of *node* for *family*."""
    return node["ipv6"] if family == 6 else node["ipv4"]


def _interface_with(payload: Any, addresses: set[str]) -> dict[str, Any] | None:
    for iface in payload if isinstance(payload, list) else []:
        for info in iface.get("addr_info", []) if isinstance(iface, dict) else []:
            if isinstance(info, dict) and canonical_ip(info.get("local")) in addresses:
                return iface
    return None


def ib_interface(host, node) -> tuple[dict[str, Any] | None, str]:
    """Return the interface carrying any approved IB address and its name."""
    payload = remote_json(host, node["row"], IPOIB_COMMANDS["ip_addresses"])
    iface = _interface_with(payload, {node["ipv6"], node["ipv4"]} - {""})
    name = str(iface.get("ifname", "")) if iface else ""
    if name and not SAFE_IFACE.fullmatch(name):
        raise ValueError(f"{hostname(node)} reported an unsafe interface name")
    return iface, name


def interface_addresses(iface: dict[str, Any] | None, family: int) -> set[str]:
    """Return global addresses of *family* configured on *iface*."""
    wanted = "inet6" if family == 6 else "inet"
    return {
        canonical_ip(info.get("local"))
        for info in (iface or {}).get("addr_info", [])
        if info.get("family") == wanted and info.get("scope") == "global"
    }


def ib_state(host, node, mode: str) -> dict[str, Any]:
    """Return the full operational IPoIB state of one node.

    Checks the approved address(es) and prefix, DAD flags, link and RDMA state,
    MTU, OFED, and the IPoIB kernel modules.
    """
    iface, name = ib_interface(host, node)
    if iface is None:
        return {
            "ok": False,
            "name": "",
            "problems": ["no interface carries an approved IB address"],
            "details": [("Interface", "missing")],
        }
    infos = {
        canonical_ip(info.get("local")): info for info in iface.get("addr_info", [])
    }
    problems = []
    for family in families_for(mode):
        expected = address(node, family)
        info = infos.get(expected) if expected else None
        if not expected:
            problems.append(f"no approved IPv{family} allocation")
        elif info is None:
            problems.append(f"IPv{family} {expected} missing")
        elif family == 6:
            if node["prefix6"] and info.get("prefixlen") != node["prefix6"]:
                problems.append(f"prefix /{info.get('prefixlen')} != /{node['prefix6']}")
            problems.extend(f"flag {flag}" for flag in UNHEALTHY_IPV6_FLAGS if info.get(flag))
    operstate = str(iface.get("operstate", "")).upper()
    mtu = int(iface.get("mtu", 0) or 0)
    if operstate != "UP":
        problems.append(f"netdev {operstate or 'unknown'}")
    if mtu < IPOIB_MIN_MTU:
        problems.append(f"MTU {mtu} < {IPOIB_MIN_MTU}")
    netdev = remote_command(host, node["row"], IPOIB_RESILIENCE_COMMANDS["netdev_map"])
    rdma_up = bool(re.search(rf"==>\s+{re.escape(name)}\s+\(Up\)", netdev.stdout))
    if not rdma_up:
        problems.append("RDMA link not Up")
    ofed = remote_command(host, node["row"], IPOIB_RESILIENCE_COMMANDS["ofed"])
    if ofed.rc != 0:
        problems.append("OFED not present")
    lsmod = remote_command(host, node["row"], IPOIB_RESILIENCE_COMMANDS["lsmod"])
    loaded = {line.split()[0] for line in lsmod.stdout.splitlines() if line.split()}
    missing = [module for module in IPOIB_KERNEL_MODULES if module not in loaded]
    if missing:
        problems.append("modules missing: " + ", ".join(missing))
    addresses = ", ".join(
        f"{address(node, family)}" for family in families_for(mode) if address(node, family)
    )
    return {
        "ok": not problems,
        "name": name,
        "problems": problems,
        "details": [
            ("Interface", name),
            ("Approved addresses", addresses or "none"),
            ("Link", f"netdev={operstate} | RDMA={'Up' if rdma_up else 'Down'}"),
            ("MTU", mtu),
            ("OFED", "present" if ofed.rc == 0 else "missing"),
            ("Kernel modules", "loaded" if not missing else "missing " + ", ".join(missing)),
            ("Result", "operational" if not problems else "; ".join(problems)),
        ],
    }


def wait_for_ib_state(host, node, mode, timeout_seconds, poll_seconds):
    """Poll until *node* reports an operational IPoIB state or times out."""
    started = time.monotonic()
    attempt = 0
    state: dict[str, Any] = {"ok": False, "name": "", "problems": ["not checked"], "details": []}
    while time.monotonic() - started < timeout_seconds:
        attempt += 1
        try:
            state = ib_state(host, node, mode)
        except (OSError, RuntimeError, ValueError) as exc:
            state = {"ok": False, "name": "", "problems": [str(exc)[:200]], "details": []}
        if state["ok"]:
            return state
        report_poll_progress(
            f"{hostname(node)} IPoIB recovery", attempt, started, timeout_seconds,
            "; ".join(state["problems"]),
        )
        time.sleep(poll_seconds)
    return state


def interface_names(host, nodes) -> dict[str, str]:
    """Return hostname -> IB interface name for every reachable node."""
    names = {}
    for node in nodes:
        try:
            names[hostname(node)] = ib_interface(host, node)[1]
        except (OSError, RuntimeError, ValueError):
            names[hostname(node)] = ""
    return names


def ping_over_ib(host, source, name: str, target: str, family: int) -> bool:
    """Ping *target* from *source* through IB interface *name* with retries."""
    if not name or not target:
        return False
    command = IPOIB_COMMANDS["ping_from_iface"] % (
        family, PING_TIMEOUT_SECONDS, shlex.quote(name), shlex.quote(target)
    )
    return any(
        remote_command(host, source["row"], command).rc == 0
        for _attempt in range(IPOIB_PING_ATTEMPTS)
    )


def mesh_failures(host, pairs, families, names) -> list[str]:
    """Return 'src->dst IPvN' labels for every unreachable directed IB pair."""
    failures = []
    for source, target in pairs:
        for family in families:
            if not ping_over_ib(
                host, source, names.get(hostname(source), ""), address(target, family), family
            ):
                failures.append(f"{hostname(source)}->{hostname(target)} IPv{family}")
    return failures


def full_mesh(nodes) -> list[tuple[dict, dict]]:
    """Return every ordered pair of distinct nodes."""
    return [(a, b) for a in nodes for b in nodes if a is not b]


def route_device(host, row, destination: str) -> str:
    """Return the egress device the kernel selects for *destination*."""
    lookup = remote_json(
        host, row, IPOIB_RESILIENCE_COMMANDS["route_get"] % shlex.quote(destination)
    )
    entry = lookup[0] if isinstance(lookup, list) and lookup else {}
    return str(entry.get("dev", ""))


def routes_covering(host, row, name: str, destination: str) -> list[str]:
    """Return IB-interface routes that would capture *destination*."""
    target = ipaddress.ip_address(destination)
    captured = []
    for family in (4, 6):
        routes = remote_json(
            host, row, IPOIB_RESILIENCE_COMMANDS["routes_dev"] % (family, shlex.quote(name))
        )
        for route in routes if isinstance(routes, list) else []:
            dst = str(route.get("dst", ""))
            if dst == "default":
                captured.append(f"default (IPv{family})")
                continue
            try:
                network = ipaddress.ip_network(dst, strict=False)
            except ValueError:
                continue
            if network.version == target.version and target in network:
                captured.append(dst)
    return captured


def allocation_records(node, mode: str) -> list[dict[str, str]]:
    """Return product allocation records for *node* under *mode*."""
    records = []
    if mode != IB_MODE_IPV6_ONLY and node["ipv4"]:
        records.append({"address": node["ipv4"], "address_family": "ipv4"})
    if mode != IB_MODE_IPV4_ONLY and node["ipv6"]:
        records.append({"address": node["ipv6"], "address_family": "ipv6"})
    return records


@lru_cache(maxsize=1)
def address_verifier():
    """Load the shipped ER-ORCH-005 address verifier from the source tree."""
    repository = Path(__file__).resolve().parents[4]
    path = repository.joinpath(*ADDRESS_VERIFIER_PATH)
    if not path.is_file():
        raise FileNotFoundError(f"Product address verifier not found: {path}")
    spec = importlib.util.spec_from_file_location("omnia_fvt_address_verifier", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _enum_value(value) -> str:
    return str(getattr(value, "value", value) or "")


def classify_live(host, node, name: str, peer, records) -> dict[str, Any]:
    """Classify the live interface state with the product verifier.

    Collects the same inputs as ``verify_ib_ipv6_state`` (address list, routes,
    privacy sysctl, on-link peer ping) and runs ``verify_interface``.
    """
    verifier = address_verifier()
    row = node["row"]
    quoted = shlex.quote(name)
    addr = remote_command(host, row, IPOIB_RESILIENCE_COMMANDS["ipv6_addr_dev"] % quoted)
    routes = remote_command(host, row, IPOIB_RESILIENCE_COMMANDS["ipv6_route_dev"] % quoted)
    sysctl = remote_command(host, row, IPOIB_RESILIENCE_COMMANDS["use_tempaddr"] % quoted)
    ping_output, ping_rc = "", 0
    if peer is not None and peer["ipv6"]:
        ping = remote_command(
            host, row,
            verifier.build_peer_check_command(peer["ipv6"], name, count=3, timeout=5),
        )
        ping_output, ping_rc = ping.stdout, ping.rc
    result = verifier.verify_interface(
        node_id=hostname(node),
        interface_id=name,
        records=records,
        ip_addr_output=addr.stdout,
        ip_route_output=routes.stdout,
        sysctl_output=sysctl.stdout,
        ping_output=ping_output,
        ping_rc=ping_rc,
    )
    health = result["health"]
    return {
        "node_id": result.get("node_id", ""),
        "interface_id": result.get("interface_id", ""),
        "mode": result.get("mode", ""),
        "status": _enum_value(health.get("status")),
        "stage": _enum_value(health.get("stage")),
        "errors": [str(error) for error in health.get("errors", [])],
        "corrective_action": str(health.get("corrective_action") or ""),
        "health": health,
    }


def wait_for_status(host, node, name, peer, records, expected, timeout, poll):
    """Poll the product classification until it reports *expected*."""
    started = time.monotonic()
    attempt = 0
    verdict: dict[str, Any] = {"status": "unknown", "errors": []}
    while time.monotonic() - started < timeout:
        attempt += 1
        verdict = classify_live(host, node, name, peer, records)
        if verdict["status"] == expected:
            return True, verdict
        report_poll_progress(
            f"{hostname(node)} IPoIB {expected}", attempt, started, timeout,
            f"status={verdict['status']}",
        )
        time.sleep(poll)
    return False, verdict


def verdict_fields(label: str, verdict: dict[str, Any]) -> list[tuple[str, object]]:
    """Render one product classification as report fields."""
    return [
        (f"{label} status", verdict.get("status") or "none"),
        (f"{label} stage", verdict.get("stage") or "none"),
        (f"{label} errors", "; ".join(verdict.get("errors", [])) or "none"),
        (f"{label} corrective action", verdict.get("corrective_action") or "none"),
    ]
