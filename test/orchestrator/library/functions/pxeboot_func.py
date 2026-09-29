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

"""Node connectivity, cloud-init, architecture, and OS version checks."""

from ..vars.pxeboot_vars import (
    PXEBOOT_COMMANDS,
    PING_RETRIES,
    PING_RETRY_DELAY_SECONDS,
    SSH_RETRIES,
    SSH_RETRY_DELAY_SECONDS,
)
from ._pxeboot_helpers import (
    direct_cloud_init_probe,
    group_fields,
    hostname_ssh_probe,
    load_runtime_context,
    parse_fg_identity,
    ping_probe,
    remote_command,
    retry_nodes,
    runtime_exception,
    runtime_result,
    ssh_probe,
)


def check_node_ping(host):
    """Verify ICMP reachability for every mapped administrative address."""
    try:
        context = load_runtime_context(host)
        rows = context["rows"]
        outcomes = retry_nodes(
            rows,
            lambda row: ping_probe(host, row),
            PING_RETRIES,
            PING_RETRY_DELAY_SECONDS,
        )
        failed = [name for name, outcome in outcomes.items() if not outcome[0]]
        return runtime_result(
            not failed,
            "PXE node ICMP reachability",
            [("Mapped nodes", len(rows)), *group_fields(rows, outcomes)],
            "Unreachable nodes: " + ", ".join(failed) if failed else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception("PXE node ICMP reachability", exc)


def check_node_ssh(host):
    """Verify passwordless root SSH from the execution OIM to every node."""
    try:
        context = load_runtime_context(host)
        rows = context["rows"]
        outcomes = retry_nodes(
            rows,
            lambda row: ssh_probe(host, row),
            SSH_RETRIES,
            SSH_RETRY_DELAY_SECONDS,
        )
        failed = [name for name, outcome in outcomes.items() if not outcome[0]]
        return runtime_result(
            not failed,
            "OIM-to-node passwordless SSH",
            [("Mapped nodes", len(rows)), *group_fields(rows, outcomes)],
            "SSH failed for: " + ", ".join(failed) if failed else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception("OIM-to-node passwordless SSH", exc)


def check_node_hostname_ssh(host):
    """Verify OIM name resolution and passwordless SSH by mapped hostname."""
    summary = "OIM-to-node hostname resolution and SSH"
    try:
        context = load_runtime_context(host)
        rows = context["rows"]
        outcomes = {}
        for row in rows:
            outcomes[row["HOSTNAME"]] = hostname_ssh_probe(host, row)
        failed = [name for name, outcome in outcomes.items() if not outcome[0]]
        return runtime_result(
            not failed,
            summary,
            [("Mapped nodes", len(rows)), *group_fields(rows, outcomes)],
            "Hostname resolution or SSH failed for: " + ", ".join(failed)
            if failed
            else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def _report_nodes(report) -> dict[str, dict]:
    """Index well-formed PXE report rows by hostname."""
    nodes = report.get("nodes", [])
    if not isinstance(nodes, list):
        raise TypeError("pxeboot_status.yml nodes must be a list")
    indexed: dict[str, dict] = {}
    duplicates: set[str] = set()
    for node in nodes:
        if not isinstance(node, dict):
            raise TypeError("pxeboot_status.yml contains a malformed node entry")
        hostname = str(node.get("hostname") or "").strip()
        if not hostname:
            continue
        if hostname in indexed:
            duplicates.add(hostname)
        indexed[hostname] = node
    if duplicates:
        raise ValueError(
            "pxeboot_status.yml has duplicate hostnames: "
            + ", ".join(sorted(duplicates))
        )
    return indexed


def _cloud_init_state(host, row, report_node) -> tuple[bool, str]:
    """Validate direct cloud-init state and the current PXE report."""
    pxe = report_node.get("pxeboot", {})
    if not isinstance(pxe, dict) or pxe.get("status") != "success":
        return False, str(pxe.get("detail") or "PXE report is not successful")
    if pxe.get("verification_method") == "disabled":
        return False, "PXE node registration verification was disabled"

    return direct_cloud_init_probe(host, row)


def check_node_cloud_init(host):
    """Verify direct cloud-init state and correlate available PXE evidence.

    When ``pxeboot_status.yml`` is not available (e.g. the verify suite
    runs after provision but before a PXE boot lifecycle), every node is
    probed directly via SSH using the PXE mapping file as the source of
    truth for administrative addresses.
    """
    try:
        context = load_runtime_context(host)
        report = context["pxeboot_status"]
        rows = context["rows"]

        # Direct-probe path: no PXE status file available.
        if report is None:
            outcomes = {}
            for row in rows:
                ok, detail = direct_cloud_init_probe(host, row)
                outcomes[row["HOSTNAME"]] = (ok, detail)
            failed = [name for name, outcome in outcomes.items() if not outcome[0]]
            return runtime_result(
                not failed,
                "Fresh PXE boot and cloud-init",
                [
                    ("PXE run ID", "N/A (direct probe from mapping file)"),
                    ("Mapped nodes", len(rows)),
                    ("Verification mode", "direct SSH probe"),
                    *group_fields(rows, outcomes),
                ],
                "Cloud-init verification failed for: " + ", ".join(failed)
                if failed
                else "",
            )

        # Report-correlated path: PXE status file is available.
        if report.get("phase") != "pxeboot":
            raise ValueError("pxeboot_status.yml does not describe the PXE phase")
        if report.get("overall_status") != "success":
            raise ValueError("The latest PXE boot report is not successful")
        report_nodes = _report_nodes(report)
        outcomes = {}
        report_coverage = 0
        for row in rows:
            report_node = report_nodes.get(row["HOSTNAME"])
            if report_node is None:
                direct_ok, direct_detail = direct_cloud_init_probe(host, row)
                outcomes[row["HOSTNAME"]] = (
                    direct_ok,
                    direct_detail + " | not targeted by latest partial PXE run",
                )
                continue
            report_coverage += 1
            outcomes[row["HOSTNAME"]] = _cloud_init_state(
                host,
                row,
                report_node,
            )
        failed = [name for name, outcome in outcomes.items() if not outcome[0]]
        return runtime_result(
            not failed,
            "Fresh PXE boot and cloud-init",
            [
                ("PXE run ID", report.get("run_id", "unknown")),
                ("Mapped nodes", len(rows)),
                (
                    "Latest PXE report coverage",
                    f"{report_coverage}/{len(rows)}",
                ),
                *group_fields(rows, outcomes),
            ],
            "Cloud-init verification failed for: " + ", ".join(failed)
            if failed
            else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception("Fresh PXE boot and cloud-init", exc)


def check_node_architecture(host):
    """Verify each node's live architecture matches its functional group."""
    summary = "Node architecture identity"
    try:
        context = load_runtime_context(host)
        rows = context["rows"]
        outcomes: dict[str, tuple[bool, str]] = {}
        skipped_count = 0
        for row in rows:
            fg = row.get("EXPECTED_FUNCTIONAL_GROUP", "")
            expected_arch, _os, _ver = parse_fg_identity(fg)
            if not expected_arch:
                # Cannot determine expected architecture from the FG name.
                skipped_count += 1
                outcomes[row["HOSTNAME"]] = (
                    True,
                    f"skipped (no arch suffix in '{fg}')",
                )
                continue
            result_cmd = remote_command(
                host, row, PXEBOOT_COMMANDS["node_architecture"]
            )
            if result_cmd.rc != 0:
                outcomes[row["HOSTNAME"]] = (
                    False,
                    "uname -m failed (SSH unreachable or command error)",
                )
                continue
            actual_arch = result_cmd.stdout.strip()
            if actual_arch == expected_arch:
                outcomes[row["HOSTNAME"]] = (
                    True,
                    f"{actual_arch} (matched)",
                )
            else:
                outcomes[row["HOSTNAME"]] = (
                    False,
                    f"MISMATCH: expected={expected_arch}, actual={actual_arch}",
                )
        failed = [name for name, outcome in outcomes.items() if not outcome[0]]
        fields: list[tuple[str, object]] = [
            ("Mapped nodes", len(rows)),
        ]
        if skipped_count:
            fields.append(("Skipped (no arch in FG name)", skipped_count))
        fields.extend(group_fields(rows, outcomes))
        return runtime_result(
            not failed,
            summary,
            fields,
            "Architecture mismatch for: " + ", ".join(failed) if failed else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_node_os_version(host):
    """Verify each node's live OS identity matches its functional group.

    When the functional group name does not encode the OS version (e.g.
    ``slurm_node_x86_64`` instead of ``slurm_node_rhel_10_0_x86_64``),
    the node is reported as *skipped* rather than failed — the expected
    OS cannot be derived without the version segment.
    """
    summary = "Node OS version identity"
    try:
        context = load_runtime_context(host)
        rows = context["rows"]
        outcomes: dict[str, tuple[bool, str]] = {}
        skipped_count = 0
        for row in rows:
            fg = row.get("EXPECTED_FUNCTIONAL_GROUP", "")
            _arch, expected_os, expected_version = parse_fg_identity(fg)
            if not expected_os or not expected_version:
                skipped_count += 1
                outcomes[row["HOSTNAME"]] = (
                    True,
                    f"skipped (no OS version in '{fg}')",
                )
                continue
            result_cmd = remote_command(
                host, row, PXEBOOT_COMMANDS["os_release"]
            )
            if result_cmd.rc != 0:
                outcomes[row["HOSTNAME"]] = (
                    False,
                    "os-release probe failed (SSH unreachable or command error)",
                )
                continue
            # Parse ID= and VERSION_ID= from grep output.
            actual_os = ""
            actual_version = ""
            for line in result_cmd.stdout.splitlines():
                line = line.strip()
                if line.startswith("ID="):
                    actual_os = line.partition("=")[2].strip().strip('"').lower()
                elif line.startswith("VERSION_ID="):
                    actual_version = line.partition("=")[2].strip().strip('"')
            os_ok = actual_os == expected_os.lower()
            version_ok = actual_version == expected_version
            if os_ok and version_ok:
                outcomes[row["HOSTNAME"]] = (
                    True,
                    f"{actual_os} {actual_version} (matched)",
                )
            else:
                parts = []
                if not os_ok:
                    parts.append(
                        f"OS: expected={expected_os}, actual={actual_os or 'unknown'}"
                    )
                if not version_ok:
                    parts.append(
                        f"version: expected={expected_version}, "
                        f"actual={actual_version or 'unknown'}"
                    )
                outcomes[row["HOSTNAME"]] = (False, "MISMATCH: " + "; ".join(parts))
        failed = [name for name, outcome in outcomes.items() if not outcome[0]]
        fields: list[tuple[str, object]] = [
            ("Mapped nodes", len(rows)),
        ]
        if skipped_count:
            fields.append(("Skipped (no OS in FG name)", skipped_count))
        fields.extend(group_fields(rows, outcomes))
        return runtime_result(
            not failed,
            summary,
            fields,
            "OS version mismatch for: " + ", ".join(failed) if failed else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)
