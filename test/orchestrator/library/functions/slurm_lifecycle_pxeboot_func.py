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

"""Slurm node remove/add lifecycle verification.

Exercises the standard Slurm node removal and re-addition lifecycle by
modifying the PXE mapping file, running provision, and verifying that
the owned state (SMD, Boot Service, Metadata Service, Slurm membership)
reflects the expected inventory change.

Only existing ``slurm_node_*`` entries from the PXE mapping can be used.
New nodes that are not already present in the PXE mapping cannot be added
through this test.  The test removes existing nodes and then adds the same
nodes back.
"""

import csv
import io
import os
import re
from typing import Any

from omnia_auto import load_test_config, run_on_host

from ..vars.pxeboot_vars import PXEBOOT_COMMANDS, SLURM_COMPUTE_PREFIX
from ._pxeboot_helpers import (
    remote_command,
    runtime_exception,
    runtime_result,
)
from ._provision_helpers import (
    api_json,
    group_members,
    interface_ips,
    load_context,
    normalise_mac,
    resource_list,
)
from ._workload_helpers import slurm_context as _slurm_context
from .project_func import resolve_target_input_project_path

# Backup filename stored alongside the test reports.
_BACKUP_FILENAME = "pxe_mapping_file.csv.backup"

# Functional group prefix for Slurm compute nodes.
_SLURM_NODE_PREFIX = "slurm_node_"


def _result(
    success: bool,
    summary: str,
    fields: list[tuple[str, object]],
    error: str = "",
    *,
    skipped: bool = False,
) -> dict[str, Any]:
    return {
        "success": success,
        "skipped": skipped,
        "details": {"summary": summary, "fields": fields},
        "error": error,
    }


def _skip(summary: str, reason: str) -> dict[str, Any]:
    """Return a skip result when the test is not applicable."""
    return _result(True, summary, [("Reason", reason)], skipped=True)


def _backup_dir() -> str:
    """Return the report directory used to store the PXE mapping backup."""
    config = load_test_config()
    return str(config.get("report_path", "/opt/omnia/reports"))


def _backup_path() -> str:
    return os.path.join(_backup_dir(), _BACKUP_FILENAME)


def _mapping_path(host) -> str:
    """Resolve the active PXE mapping file path on the target."""
    from ._provision_helpers import _mapping_path as _resolve
    input_dir = resolve_target_input_project_path(host)
    return _resolve(host, input_dir)


def _read_mapping_lines(host, path: str) -> tuple[str, list[str]]:
    """Return the raw header line and all data lines from the mapping."""
    source = host.file(path)
    if not source.is_file:
        raise ValueError(f"PXE mapping file is missing: {path}")
    raw_lines = source.content_string.splitlines()
    header = ""
    data_lines: list[str] = []
    for line in raw_lines:
        stripped = line.strip()
        if not stripped or re.match(r"^\s*#", stripped):
            continue
        if not header:
            header = line
        else:
            data_lines.append(line)
    if not header:
        raise ValueError("PXE mapping file has no header row")
    return header, data_lines


def _parse_rows(header: str, data_lines: list[str]) -> list[dict[str, str]]:
    """Parse CSV rows from a header and data lines."""
    text = header + "\n" + "\n".join(data_lines) + "\n"
    reader = csv.DictReader(io.StringIO(text))
    rows = []
    for row in reader:
        clean = {
            str(k).strip(): str(v or "").strip()
            for k, v in row.items()
            if k is not None
        }
        rows.append(clean)
    return rows


def _resolve_target_nodes(
    host,
    mapping_path: str,
) -> tuple[list[str], list[dict[str, str]], str] | None:
    """Determine which nodes to remove.

    Returns:
        ``(admin_ips, all_rows, header_line)`` when target nodes are
        identified, or ``None`` when the test should be skipped because
        no ``slurm_node_*`` rows exist and the user did not provide
        explicit IPs.

    Raises:
        ValueError: When the user supplied explicit IPs that are invalid
        (not in mapping or not slurm_node roles).
    """
    config = load_test_config()
    configured = str(config.get("slurm_lifecycle_remove_add_nodes", "")).strip()
    header, data_lines = _read_mapping_lines(host, mapping_path)
    all_rows = _parse_rows(header, data_lines)

    if not all_rows:
        raise ValueError("PXE mapping contains no node rows")

    # Identify slurm_node rows by FUNCTIONAL_GROUP_NAME prefix.
    slurm_node_rows = [
        row for row in all_rows
        if row.get("FUNCTIONAL_GROUP_NAME", "").startswith(_SLURM_NODE_PREFIX)
    ]

    if configured:
        # User provided specific Admin IPs — validation failures are errors.
        requested_ips = [
            ip.strip() for ip in configured.split(",") if ip.strip()
        ]
        mapping_ips = {row["ADMIN_IP"] for row in all_rows}
        slurm_node_ips = {row["ADMIN_IP"] for row in slurm_node_rows}

        missing = [ip for ip in requested_ips if ip not in mapping_ips]
        if missing:
            raise ValueError(
                "Requested Admin IPs not found in PXE mapping: "
                + ", ".join(missing)
            )
        non_slurm = [ip for ip in requested_ips if ip not in slurm_node_ips]
        if non_slurm:
            raise ValueError(
                "Requested Admin IPs are not slurm_node_* roles: "
                + ", ".join(non_slurm)
                + ". Only existing slurm_node entries can be removed and re-added"
            )
        return requested_ips, all_rows, header

    # Default: remove the last slurm_node entry.  Skip when none exist.
    if not slurm_node_rows:
        return None

    last_node = slurm_node_rows[-1]
    return [last_node["ADMIN_IP"]], all_rows, header


def _write_mapping(host, path: str, header: str, rows: list[dict[str, str]]) -> None:
    """Write the mapping file back with the given rows."""
    if not rows:
        raise ValueError("Cannot write an empty PXE mapping")
    fieldnames = [h.strip() for h in header.split(",")]
    output = io.StringIO()
    writer = csv.DictWriter(
        output, fieldnames=fieldnames, extrasaction="ignore"
    )
    writer.writeheader()
    writer.writerows(rows)
    content = output.getvalue()
    # Write via shell to handle remote/local transparently.
    escaped = content.replace("'", "'\\''")
    result = run_on_host(host, f"cat > {path} << 'OMNIA_EOF'\n{escaped}OMNIA_EOF")
    if result.rc != 0:
        raise RuntimeError(f"Failed to write PXE mapping: {result.stderr}")


def backup_pxe_mapping(host) -> str:
    """Backup the current PXE mapping file.  Overwrites any existing backup."""
    source = _mapping_path(host)
    dest = _backup_path()
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    # Read from target and write locally.
    content = host.file(source).content_string
    with open(dest, "w", encoding="utf-8") as fh:
        fh.write(content)
    return dest


def restore_pxe_mapping(host) -> None:
    """Restore the PXE mapping from the backup file."""
    dest = _mapping_path(host)
    source = _backup_path()
    if not os.path.isfile(source):
        raise FileNotFoundError(f"PXE mapping backup not found: {source}")
    with open(source, encoding="utf-8") as fh:
        content = fh.read()
    escaped = content.replace("'", "'\\''")
    result = run_on_host(host, f"cat > {dest} << 'OMNIA_EOF'\n{escaped}OMNIA_EOF")
    if result.rc != 0:
        raise RuntimeError(f"Failed to restore PXE mapping: {result.stderr}")


def _verify_node_absent_smd(host, removed_ips: list[str]) -> list[str]:
    """Verify removed nodes are absent from SMD interfaces."""
    errors = []
    try:
        interfaces = resource_list(api_json(host, "ethernet"))
        for ip in removed_ips:
            matches = [
                iface for iface in interfaces if ip in interface_ips(iface)
            ]
            if matches:
                errors.append(f"SMD still has interface for {ip}")
    except Exception as exc:
        errors.append(f"SMD interface check failed: {exc}")
    return errors


def _verify_node_absent_boot_configs(
    host, removed_macs: list[str]
) -> list[str]:
    """Verify removed nodes are absent from Boot Service configurations."""
    errors = []
    try:
        configurations = resource_list(api_json(host, "boot_configurations"))
        for config in configurations:
            spec = config.get("spec")
            if not isinstance(spec, dict):
                continue
            macs = spec.get("mac_addresses") or []
            for mac in removed_macs:
                if normalise_mac(mac) in {normalise_mac(m) for m in macs}:
                    name = config.get("metadata", {}).get("name", "unknown")
                    errors.append(
                        f"Boot config '{name}' still references removed MAC {mac}"
                    )
    except Exception as exc:
        errors.append(f"Boot config check failed: {exc}")
    return errors


def _verify_node_absent_metadata(
    host, removed_ips: list[str]
) -> list[str]:
    """Verify removed nodes are absent from Metadata Service instances."""
    errors = []
    try:
        instances = resource_list(api_json(host, "instance_infos"))
        # Instance IDs are XNAMEs.  Resolve removed IPs to XNAMEs first.
        interfaces = resource_list(api_json(host, "ethernet"))
        removed_xnames = set()
        for iface in interfaces:
            for ip in removed_ips:
                if ip in interface_ips(iface):
                    xname = str(iface.get("ComponentID") or "").strip()
                    if xname:
                        removed_xnames.add(xname)
        for item in instances:
            spec = item.get("spec")
            if not isinstance(spec, dict):
                continue
            instance_id = str(spec.get("instance_id") or "").strip()
            if instance_id in removed_xnames:
                errors.append(
                    f"Metadata instance still references removed node {instance_id}"
                )
    except Exception as exc:
        errors.append(f"Metadata instance check failed: {exc}")
    return errors


def _verify_node_absent_slurm(
    host, removed_hostnames: list[str]
) -> list[str]:
    """Verify removed nodes are absent from Slurm membership (sinfo)."""
    errors = []
    try:
        _runtime, rows, control, _config = _slurm_context(host)
        if control is None:
            return ["Slurm control node not available"]
        result = remote_command(host, control, PXEBOOT_COMMANDS["slurm_nodes"])
        if result.rc != 0:
            return ["scontrol show nodes failed"]
        for hostname in removed_hostnames:
            if f"NodeName={hostname} " in result.stdout:
                errors.append(f"sinfo still shows removed node {hostname}")
    except Exception as exc:
        errors.append(f"Slurm membership check failed: {exc}")
    return errors


def _verify_node_present_slurm(
    host, expected_hostnames: list[str]
) -> list[str]:
    """Verify re-added nodes are present in Slurm membership."""
    errors = []
    try:
        _runtime, rows, control, _config = _slurm_context(host)
        if control is None:
            return ["Slurm control node not available"]
        result = remote_command(host, control, PXEBOOT_COMMANDS["slurm_nodes"])
        if result.rc != 0:
            return ["scontrol show nodes failed"]
        for hostname in expected_hostnames:
            if f"NodeName={hostname} " not in result.stdout:
                errors.append(f"sinfo does not show re-added node {hostname}")
    except Exception as exc:
        errors.append(f"Slurm membership check failed: {exc}")
    return errors


def _verify_node_present_smd(host, expected_ips: list[str]) -> list[str]:
    """Verify re-added nodes are present in SMD interfaces."""
    errors = []
    try:
        interfaces = resource_list(api_json(host, "ethernet"))
        for ip in expected_ips:
            matches = [
                iface for iface in interfaces if ip in interface_ips(iface)
            ]
            if not matches:
                errors.append(f"SMD missing interface for re-added {ip}")
    except Exception as exc:
        errors.append(f"SMD interface check failed: {exc}")
    return errors


def check_slurm_node_remove(host) -> dict[str, Any]:
    """Remove Slurm compute node(s), run provision, verify removal."""
    summary = "Slurm node removal lifecycle"
    try:
        mapping_path = _mapping_path(host)
        resolved = _resolve_target_nodes(host, mapping_path)
        if resolved is None:
            return _skip(summary, "No slurm_node entries in PXE mapping")
        remove_ips, all_rows, header = resolved

        removed_rows = [row for row in all_rows if row["ADMIN_IP"] in remove_ips]
        removed_hostnames = [row["HOSTNAME"] for row in removed_rows]
        removed_macs = [row["ADMIN_MAC"] for row in removed_rows]
        remaining_rows = [
            row for row in all_rows if row["ADMIN_IP"] not in remove_ips
        ]

        fields: list[tuple[str, object]] = [
            ("Nodes to remove", ", ".join(removed_hostnames)),
            ("Admin IPs", ", ".join(remove_ips)),
            ("Remaining nodes", len(remaining_rows)),
        ]

        # Step 1: Backup.
        backup = backup_pxe_mapping(host)
        fields.append(("Backup", backup))

        # Step 2: Remove rows and write back.
        _write_mapping(host, mapping_path, header, remaining_rows)
        fields.append(("Mapping updated", "removed target nodes"))

        # Step 3: Run provision.
        from . import run_playbook

        provision_result = run_playbook(tag="provision")
        fields.append(("Provision rc", provision_result["rc"]))
        fields.append((
            "Provision duration",
            f"{provision_result.get('duration', 0):.1f}s",
        ))
        if not provision_result["success"]:
            return _result(
                False,
                summary,
                fields,
                f"Provision failed after node removal (rc={provision_result['rc']})",
            )

        # Step 4: Verify removal.
        removal_errors: list[str] = []
        smd_errors = _verify_node_absent_smd(host, remove_ips)
        removal_errors.extend(smd_errors)
        fields.append((
            "SMD interfaces",
            "passed" if not smd_errors else "; ".join(smd_errors),
        ))

        boot_errors = _verify_node_absent_boot_configs(host, removed_macs)
        removal_errors.extend(boot_errors)
        fields.append((
            "Boot configs",
            "passed" if not boot_errors else "; ".join(boot_errors),
        ))

        meta_errors = _verify_node_absent_metadata(host, remove_ips)
        removal_errors.extend(meta_errors)
        fields.append((
            "Metadata instances",
            "passed" if not meta_errors else "; ".join(meta_errors),
        ))

        slurm_errors = _verify_node_absent_slurm(host, removed_hostnames)
        removal_errors.extend(slurm_errors)
        fields.append((
            "Slurm membership",
            "passed" if not slurm_errors else "; ".join(slurm_errors),
        ))

        # Verify remaining nodes still healthy.
        remaining_hostnames = [row["HOSTNAME"] for row in remaining_rows
                               if row.get("FUNCTIONAL_GROUP_NAME", "")
                               .startswith(_SLURM_NODE_PREFIX)]
        if remaining_hostnames:
            healthy_errors = _verify_node_present_slurm(
                host, remaining_hostnames
            )
            removal_errors.extend(healthy_errors)
            fields.append((
                "Remaining nodes healthy",
                "passed" if not healthy_errors else "; ".join(healthy_errors),
            ))

        return _result(
            not removal_errors,
            summary,
            fields,
            "; ".join(removal_errors),
        )
    except ValueError as exc:
        return _result(False, summary, [], str(exc))
    except Exception as exc:
        return runtime_exception(summary, exc)


def check_slurm_node_add(host) -> dict[str, Any]:
    """Restore removed Slurm compute node(s), run provision, verify addition."""
    summary = "Slurm node re-addition lifecycle"
    try:
        backup = _backup_path()
        if not os.path.isfile(backup):
            return _skip(
                summary,
                "No PXE mapping backup found; remove test was skipped "
                "or has not run yet",
            )

        # Read backup to identify which nodes are being re-added.
        with open(backup, encoding="utf-8") as fh:
            backup_content = fh.read()
        backup_header, backup_data = _read_mapping_lines_from_string(
            backup_content
        )
        backup_rows = _parse_rows(backup_header, backup_data)

        mapping_path = _mapping_path(host)
        current_header, current_data = _read_mapping_lines(host, mapping_path)
        current_rows = _parse_rows(current_header, current_data)

        current_ips = {row["ADMIN_IP"] for row in current_rows}
        readded_rows = [
            row for row in backup_rows if row["ADMIN_IP"] not in current_ips
        ]
        readded_hostnames = [row["HOSTNAME"] for row in readded_rows]
        readded_ips = [row["ADMIN_IP"] for row in readded_rows]

        fields: list[tuple[str, object]] = [
            ("Nodes to re-add", ", ".join(readded_hostnames) or "none"),
            ("Admin IPs", ", ".join(readded_ips) or "none"),
        ]

        # Step 1: Restore PXE mapping from backup.
        restore_pxe_mapping(host)
        fields.append(("Mapping restored", "from backup"))

        # Step 2: Run provision.
        from . import run_playbook

        provision_result = run_playbook(tag="provision")
        fields.append(("Provision rc", provision_result["rc"]))
        fields.append((
            "Provision duration",
            f"{provision_result.get('duration', 0):.1f}s",
        ))
        if not provision_result["success"]:
            return _result(
                False,
                summary,
                fields,
                f"Provision failed after node re-addition "
                f"(rc={provision_result['rc']})",
            )

        # Step 3: Verify re-addition — re-added node present in owned state.
        addition_errors: list[str] = []

        smd_errors = _verify_node_present_smd(host, readded_ips)
        addition_errors.extend(smd_errors)
        fields.append((
            "SMD interfaces",
            "passed" if not smd_errors else "; ".join(smd_errors),
        ))

        slurm_errors = _verify_node_present_slurm(host, readded_hostnames)
        addition_errors.extend(slurm_errors)
        fields.append((
            "Slurm membership",
            "passed" if not slurm_errors else "; ".join(slurm_errors),
        ))

        # Step 4: Full pxeboot verification — all existing checks on ALL nodes.
        # These functions read the restored PXE mapping and verify every node.
        from .pxeboot_func import (
            check_node_ping,
            check_node_ssh,
            check_node_hostname_ssh,
            check_node_cloud_init,
        )
        from .smd_provision_func import check_smd_identity, check_smd_groups
        from .boot_service_provision_func import (
            check_boot_configurations,
            check_boot_nodes,
        )
        from .metadata_service_provision_func import (
            check_metadata_groups,
            check_metadata_instances,
        )
        from .slurm_pxeboot_func import (
            check_slurm_membership,
            check_slurm_scheduler,
            check_slurm_services,
            check_slurm_cross_node_ssh,
        )
        from .slurm_configuration_pxeboot_func import (
            check_slurm_configless_mode,
        )

        full_checks = [
            ("Connectivity — ping", check_node_ping),
            ("Connectivity — SSH", check_node_ssh),
            ("Connectivity — hostname SSH", check_node_hostname_ssh),
            ("Cloud-init", check_node_cloud_init),
            ("SMD identity", check_smd_identity),
            ("SMD groups", check_smd_groups),
            ("Boot configurations", check_boot_configurations),
            ("Boot nodes", check_boot_nodes),
            ("Metadata groups", check_metadata_groups),
            ("Metadata instances", check_metadata_instances),
            ("Slurm membership (full)", check_slurm_membership),
            ("Slurm scheduler", check_slurm_scheduler),
            ("Slurm services", check_slurm_services),
            ("Slurm cross-node SSH", check_slurm_cross_node_ssh),
            ("Slurm configless mode", check_slurm_configless_mode),
        ]
        for label, checker in full_checks:
            check_result = checker(host)
            if check_result.get("skipped"):
                fields.append((label, "skipped"))
            elif check_result.get("success"):
                fields.append((label, "passed"))
            else:
                addition_errors.append(
                    f"{label}: {check_result.get('error', 'failed')}"
                )
                fields.append((label, check_result.get("error", "failed")))

        return _result(
            not addition_errors,
            summary,
            fields,
            "; ".join(addition_errors),
        )
    except Exception as exc:
        return runtime_exception(summary, exc)


def _read_mapping_lines_from_string(
    content: str,
) -> tuple[str, list[str]]:
    """Parse header and data lines from a string (for backup file reading)."""
    header = ""
    data_lines: list[str] = []
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or re.match(r"^\s*#", stripped):
            continue
        if not header:
            header = line
        else:
            data_lines.append(line)
    if not header:
        raise ValueError("Backup PXE mapping has no header row")
    return header, data_lines
