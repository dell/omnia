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
from .boot_image_identity_provision_func import (
    _build_status_path,
    _match_build_entry,
    _parse_build_status_images,
)
from ._prepare_helpers import read_yaml_mapping


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
        for row in rows:
            fg = row.get("EXPECTED_FUNCTIONAL_GROUP", "")
            expected_arch, _os, _ver = parse_fg_identity(fg)
            if not expected_arch:
                # Cannot determine expected architecture from the FG name.
                outcomes[row["HOSTNAME"]] = (
                    False,
                    f"No architecture suffix in functional group name '{fg}'",
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
        fields.extend(group_fields(rows, outcomes))
        return runtime_result(
            not failed,
            summary,
            fields,
            "Architecture mismatch for: " + ", ".join(failed) if failed else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def _parse_os_release(output: str) -> tuple[str, str]:
    """Extract ``(os_id, version_id)`` from ``/etc/os-release`` grep output."""
    os_id = ""
    version_id = ""
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("ID="):
            os_id = line.partition("=")[2].strip().strip('"').lower()
        elif line.startswith("VERSION_ID="):
            version_id = line.partition("=")[2].strip().strip('"')
    return os_id, version_id


def _resolve_expected_os(
    fg_name: str,
    build_entries: list[dict[str, str]] | None,
) -> tuple[str | None, str | None, str | None]:
    """Resolve OS identity for a functional group.

    First tries the FG name itself.  If the FG name has no OS segment
    (e.g. ``slurm_node_x86_64``), falls back to the matched
    ``build_status.yml`` entry which carries the full versioned name
    (e.g. ``slurm_node_rhel_10_0_x86_64``).

    Returns ``(matched_source_name, os_id, os_version)`` or
    ``(None, None, None)`` when resolution fails.
    """
    _arch, os_id, os_ver = parse_fg_identity(fg_name)
    if os_id and os_ver:
        return fg_name, os_id, os_ver
    if build_entries is not None:
        matched = _match_build_entry(fg_name, build_entries)
        if matched:
            _arch2, os_id2, os_ver2 = parse_fg_identity(matched["group"])
            if os_id2 and os_ver2:
                return matched["group"], os_id2, os_ver2
    return None, None, None


def check_node_os_version(host):
    """Verify each node's live OS identity matches the expected image.

    The expected OS is resolved from ``build_status.yml`` — the PXE
    mapping functional group name (e.g. ``slurm_node_x86_64``) is
    matched to the corresponding build entry
    (e.g. ``slurm_node_rhel_10_0_x86_64``) using the same prefix +
    architecture matching used by the Orchestrator's ``validate_image.yml``.

    The live node's ``/etc/os-release`` is then compared against the
    OS identity extracted from the matched build entry.
    """
    summary = "Node OS version identity"
    try:
        context = load_runtime_context(host)
        rows = context["rows"]

        # Load build_status.yml — mandatory evidence for OS verification.
        build_entries: list[dict[str, str]] | None = None
        build_source = ""
        build_error = ""
        try:
            build_path = _build_status_path(host)
            build_status = read_yaml_mapping(host, build_path)
            if build_status.get("overall_status") == "success":
                build_entries, _arch_map = _parse_build_status_images(
                    build_status
                )
                build_source = build_path
            else:
                build_error = (
                    f"build_status.yml overall_status="
                    f"'{build_status.get('overall_status')}', "
                    f"expected 'success'"
                )
        except (OSError, TypeError, ValueError) as read_exc:
            build_error = f"build_status.yml unreadable: {read_exc}"

        if build_error:
            return runtime_result(
                False,
                summary,
                [("build_status.yml", build_error)],
                build_error,
            )

        # OS verification is mandatory — every mapped node must resolve.
        outcomes: dict[str, tuple[bool, str]] = {}
        for row in rows:
            fg = row.get("EXPECTED_FUNCTIONAL_GROUP", "")
            source_name, expected_os, expected_version = (
                _resolve_expected_os(fg, build_entries)
            )

            # If we cannot resolve expected OS for this node, fail.
            if not expected_os or not expected_version:
                outcomes[row["HOSTNAME"]] = (
                    False,
                    f"Cannot resolve expected OS from build_status.yml "
                    f"or functional group name '{fg}'",
                )
                continue

            # Probe the live node.
            result_cmd = remote_command(
                host, row, PXEBOOT_COMMANDS["os_release"]
            )
            if result_cmd.rc != 0:
                outcomes[row["HOSTNAME"]] = (
                    False,
                    "os-release probe failed "
                    "(SSH unreachable or command error)",
                )
                continue

            actual_os, actual_version = _parse_os_release(result_cmd.stdout)

            os_ok = actual_os == expected_os.lower()
            version_ok = actual_version == expected_version
            source_label = (
                f" via {source_name}" if source_name != fg else ""
            )
            if os_ok and version_ok:
                outcomes[row["HOSTNAME"]] = (
                    True,
                    f"{actual_os} {actual_version} "
                    f"(matched{source_label})",
                )
            else:
                parts = []
                if not os_ok:
                    parts.append(
                        f"OS: expected={expected_os}, "
                        f"actual={actual_os or 'unknown'}"
                    )
                if not version_ok:
                    parts.append(
                        f"version: expected={expected_version}, "
                        f"actual={actual_version or 'unknown'}"
                    )
                outcomes[row["HOSTNAME"]] = (
                    False,
                    f"MISMATCH{source_label}: " + "; ".join(parts),
                )

        failed = [
            name for name, outcome in outcomes.items() if not outcome[0]
        ]
        fields: list[tuple[str, object]] = [
            ("Mapped nodes", len(rows)),
        ]
        if build_source:
            fields.append(("OS source", build_source))
        fields.extend(group_fields(rows, outcomes))
        return runtime_result(
            not failed,
            summary,
            fields,
            "OS version mismatch for: " + ", ".join(failed)
            if failed
            else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)
