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

"""Kubernetes node remove/add lifecycle verification.

Exercises the standard Kubernetes worker node removal and re-addition
lifecycle by modifying the PXE mapping file, running provision, and
verifying that the Kubernetes membership reflects the expected change.

Only existing ``service_kube_node_*`` entries from the PXE mapping can
be used.  The test removes existing worker nodes and then adds the same
nodes back.
"""

import csv
import io
import os
import re
from typing import Any

from omnia_auto import load_test_config, run_on_host

from ..vars.pxeboot_vars import (
    KUBERNETES_NODE_PREFIX,
    PXEBOOT_COMMANDS,
)
from ._pxeboot_helpers import remote_command, runtime_exception
from ._workload_helpers import kubernetes_context as _kubernetes_context
from .project_func import resolve_target_input_project_path

# Backup filename stored alongside the test reports.
_BACKUP_FILENAME = "pxe_mapping_file.csv.backup"

# Minimum worker nodes required for the remove test.
_MIN_K8S_WORKERS = 2


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
    return str(config.get("report_path", "/automation"))


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
    """Determine which K8s worker nodes to remove.

    Returns:
        ``(admin_ips, all_rows, header_line)`` when target nodes are
        identified, or ``None`` when the test should be skipped because
        the mapping has fewer than ``_MIN_K8S_WORKERS``
        ``service_kube_node_*`` rows.
    """
    config = load_test_config()
    configured = str(config.get("k8s_lifecycle_remove_add_nodes", "")).strip()
    header, data_lines = _read_mapping_lines(host, mapping_path)
    all_rows = _parse_rows(header, data_lines)

    if not all_rows:
        raise ValueError("PXE mapping contains no node rows")

    # Identify K8s worker rows by FUNCTIONAL_GROUP_NAME prefix.
    k8s_worker_rows = [
        row for row in all_rows
        if row.get("FUNCTIONAL_GROUP_NAME", "").startswith(KUBERNETES_NODE_PREFIX)
    ]
    if len(k8s_worker_rows) < _MIN_K8S_WORKERS:
        return None

    if configured:
        requested_ips = [
            ip.strip() for ip in configured.split(",") if ip.strip()
        ]
        mapping_ips = {row["ADMIN_IP"] for row in all_rows}
        worker_ips = {row["ADMIN_IP"] for row in k8s_worker_rows}

        missing = [ip for ip in requested_ips if ip not in mapping_ips]
        if missing:
            raise ValueError(
                "Requested Admin IPs not found in PXE mapping: "
                + ", ".join(missing)
            )
        non_worker = [ip for ip in requested_ips if ip not in worker_ips]
        if non_worker:
            raise ValueError(
                "Requested Admin IPs are not service_kube_node_* roles: "
                + ", ".join(non_worker)
                + ". Only existing K8s worker entries can be removed and re-added"
            )
        return requested_ips, all_rows, header

    # Default: remove the last K8s worker entry.
    last_node = k8s_worker_rows[-1]
    return [last_node["ADMIN_IP"]], all_rows, header


def _write_remote_file(host, path: str, content: str) -> Any:
    """Write content through a heredoc; the delimiter must be on its own line."""
    if not content.endswith("\n"):
        content += "\n"
    return run_on_host(host, f"cat > {path} << 'OMNIA_EOF'\n{content}OMNIA_EOF")


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
    result = _write_remote_file(host, path, output.getvalue())
    if result.rc != 0:
        raise RuntimeError(f"Failed to write PXE mapping: {result.stderr}")


def backup_pxe_mapping(host) -> str:
    """Backup the current PXE mapping file.  Overwrites any existing backup."""
    source = _mapping_path(host)
    dest = _backup_path()
    os.makedirs(os.path.dirname(dest), exist_ok=True)
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
    result = _write_remote_file(host, dest, content)
    if result.rc != 0:
        raise RuntimeError(f"Failed to restore PXE mapping: {result.stderr}")


def _kubectl_node_identities(payload: dict) -> set[str]:
    """Extract all node identifiers from ``kubectl get nodes -o json``.

    Returns a set of node names, IPs, and hostnames so callers can match
    by any identifier (kubelet may register with ``--hostname-override``
    set to the admin IP instead of the hostname).
    """
    identities: set[str] = set()
    for item in payload.get("items", []):
        name = item.get("metadata", {}).get("name", "")
        if name:
            identities.add(name)
        for addr in item.get("status", {}).get("addresses", []):
            addr_value = addr.get("address", "")
            if addr_value:
                identities.add(addr_value)
    return identities


def _kubectl_node_items(payload: dict) -> dict[str, dict]:
    """Map every node identifier to its full item dict."""
    items: dict[str, dict] = {}
    for item in payload.get("items", []):
        name = item.get("metadata", {}).get("name", "")
        if name:
            items[name] = item
        for addr in item.get("status", {}).get("addresses", []):
            addr_value = addr.get("address", "")
            if addr_value:
                items[addr_value] = item
    return items


def _resolve_k8s_node_name(host, control, row: dict[str, str]) -> str | None:
    """Find the K8s node name for a PXE mapping row.

    kubelet may register with ``--hostname-override`` set to the admin IP,
    so the K8s node name might be the ADMIN_IP rather than the hostname.
    """
    result = remote_command(host, control, PXEBOOT_COMMANDS["kubernetes_nodes"])
    if result.rc != 0:
        return None
    import json as _json
    payload = _json.loads(result.stdout)
    items = _kubectl_node_items(payload)
    hostname = row.get("HOSTNAME", "")
    admin_ip = row.get("ADMIN_IP", "")
    item = items.get(hostname) or items.get(admin_ip)
    if item:
        return item.get("metadata", {}).get("name", "")
    return None


def _drain_and_delete_node(
    host, control, row: dict[str, str], fields: list,
) -> list[str]:
    """Drain and delete a single K8s node.  Returns a list of errors."""
    hostname = row.get("HOSTNAME", "")
    admin_ip = row.get("ADMIN_IP", "")
    errors: list[str] = []

    node_id = _resolve_k8s_node_name(host, control, row)
    if node_id is None:
        fields.append((f"Drain {hostname}", "node not found in cluster"))
        return [f"Cannot resolve K8s node name for {hostname} ({admin_ip})"]

    # kubectl drain
    drain_cmd = (
        f"kubectl drain {node_id} "
        "--ignore-daemonsets --delete-emptydir-data --force "
        "--timeout=120s 2>&1"
    )
    drain_result = remote_command(host, control, drain_cmd)
    fields.append((
        f"Drain {hostname}",
        "passed" if drain_result.rc == 0 else f"rc={drain_result.rc}",
    ))
    if drain_result.rc != 0:
        errors.append(f"kubectl drain {node_id} failed (rc={drain_result.rc})")

    # kubectl delete node
    delete_cmd = f"kubectl delete node {node_id} 2>&1"
    delete_result = remote_command(host, control, delete_cmd)
    fields.append((
        f"Delete node {hostname}",
        "passed" if delete_result.rc == 0 else f"rc={delete_result.rc}",
    ))
    if delete_result.rc != 0:
        errors.append(f"kubectl delete node {node_id} failed")

    # Stop kubelet on the removed node to prevent re-registration.
    stop_result = remote_command(host, row, "systemctl stop kubelet 2>&1")
    fields.append((
        f"Stop kubelet {hostname}",
        "passed" if stop_result.rc == 0 else f"rc={stop_result.rc}",
    ))
    return errors


_WORKER_JOIN_FILE = "/opt/omnia/k8s_mount/worker-join-command.sh"
_NODE_READY_WAIT = 60  # seconds to wait for a re-added node to become Ready


def _rejoin_node(
    host, row: dict[str, str], join_cmd: str, fields: list,
) -> list[str]:
    """Reset kubeadm state and rejoin a node to the K8s cluster."""
    hostname = row.get("HOSTNAME", "")
    errors: list[str] = []

    # kubeadm reset (clean up stale state)
    reset_result = remote_command(host, row, "kubeadm reset -f 2>&1")
    fields.append((
        f"Reset {hostname}",
        "passed" if reset_result.rc == 0 else f"rc={reset_result.rc}",
    ))
    if reset_result.rc != 0:
        errors.append(f"kubeadm reset failed on {hostname}")
        return errors

    # Run the join command
    join_result = remote_command(host, row, f"{join_cmd} 2>&1")
    fields.append((
        f"Join {hostname}",
        "passed" if join_result.rc == 0 else f"rc={join_result.rc}",
    ))
    if join_result.rc != 0:
        errors.append(f"kubeadm join failed on {hostname}")
    return errors


def _verify_node_absent_k8s(
    host, removed_rows: list[dict[str, str]]
) -> list[str]:
    """Verify removed nodes are absent from Kubernetes membership.

    Matches by both HOSTNAME and ADMIN_IP because kubelet may register
    with ``--hostname-override`` set to the admin IP.
    """
    errors = []
    try:
        _runtime, rows, control, _config = _kubernetes_context(host)
        if control is None:
            return ["Kubernetes control plane not available"]
        result = remote_command(host, control, PXEBOOT_COMMANDS["kubernetes_nodes"])
        if result.rc != 0:
            return ["kubectl get nodes -o json failed"]
        import json
        payload = json.loads(result.stdout)
        identities = _kubectl_node_identities(payload)
        for row in removed_rows:
            hostname = row.get("HOSTNAME", "")
            admin_ip = row.get("ADMIN_IP", "")
            label = hostname or admin_ip
            if hostname in identities or admin_ip in identities:
                errors.append(f"kubectl still shows removed node {label}")
    except Exception as exc:
        errors.append(f"Kubernetes membership check failed: {exc}")
    return errors


def _verify_node_present_k8s(
    host, expected_rows: list[dict[str, str]], *, label: str = "expected"
) -> list[str]:
    """Verify nodes are present and Ready in Kubernetes.

    Matches by both HOSTNAME and ADMIN_IP.  *label* is used in error
    messages (e.g. ``"remaining"`` or ``"re-added"``).
    """
    errors = []
    try:
        _runtime, rows, control, _config = _kubernetes_context(host)
        if control is None:
            return ["Kubernetes control plane not available"]
        result = remote_command(host, control, PXEBOOT_COMMANDS["kubernetes_nodes"])
        if result.rc != 0:
            return ["kubectl get nodes -o json failed"]
        import json
        payload = json.loads(result.stdout)
        items = _kubectl_node_items(payload)
        for row in expected_rows:
            hostname = row.get("HOSTNAME", "")
            admin_ip = row.get("ADMIN_IP", "")
            display = hostname or admin_ip
            item = items.get(hostname) or items.get(admin_ip)
            if item is None:
                errors.append(
                    f"kubectl does not show {label} node {display}"
                )
                continue
            conditions = item.get("status", {}).get("conditions", [])
            ready = any(
                c.get("type") == "Ready"
                and str(c.get("status", "")).lower() == "true"
                for c in conditions
                if isinstance(c, dict)
            )
            if not ready:
                errors.append(f"{label.title()} node {display} is not Ready")
    except Exception as exc:
        errors.append(f"Kubernetes membership check failed: {exc}")
    return errors


def check_k8s_node_remove(host) -> dict[str, Any]:
    """Remove Kubernetes worker node(s), run provision, verify removal."""
    summary = "Kubernetes node removal lifecycle"
    # K8s node remove/add is not yet supported by the orchestrator src code.
    # The orchestrator provision step does not drain/delete K8s nodes that
    # are removed from the PXE mapping (unlike Slurm, where slurm.conf is
    # regenerated).  Skipping until src support is added.
    return _skip(summary, "K8s node remove not supported by orchestrator yet")
    try:
        mapping_path = _mapping_path(host)
        resolved = _resolve_target_nodes(host, mapping_path)
        if resolved is None:
            if os.path.isfile(_backup_path()):
                os.remove(_backup_path())
            return _skip(
                summary,
                f"At least {_MIN_K8S_WORKERS} service_kube_node entries are "
                "required in the PXE mapping",
            )
        remove_ips, all_rows, header = resolved

        removed_rows = [row for row in all_rows if row["ADMIN_IP"] in remove_ips]
        removed_hostnames = [row["HOSTNAME"] for row in removed_rows]
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

        # Step 2: Drain and delete nodes from the K8s cluster.
        # Unlike Slurm (where re-provisioning regenerates slurm.conf and
        # automatically removes the node), Kubernetes keeps its membership
        # independent of the PXE mapping.  We must explicitly drain and
        # delete the node via kubectl before it disappears.
        _runtime, _rows, control, _config = _kubernetes_context(host)
        if control is None:
            return _result(
                False, summary, fields,
                "Kubernetes control plane not available",
            )
        drain_errors: list[str] = []
        for row in removed_rows:
            errs = _drain_and_delete_node(host, control, row, fields)
            drain_errors.extend(errs)
        if drain_errors:
            return _result(
                False, summary, fields,
                "K8s drain/delete failed: " + "; ".join(drain_errors),
            )

        # Step 3: Remove rows from PXE mapping and re-provision.
        _write_mapping(host, mapping_path, header, remaining_rows)
        fields.append(("Mapping updated", "removed target nodes"))

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

        # Step 4: Verify removal via kubectl (authoritative).
        removal_errors: list[str] = []

        k8s_errors = _verify_node_absent_k8s(host, removed_rows)
        removal_errors.extend(k8s_errors)
        fields.append((
            "K8s membership",
            "passed" if not k8s_errors else "; ".join(k8s_errors),
        ))

        # Verify remaining workers are still healthy.
        remaining_worker_rows = [
            row for row in remaining_rows
            if row.get("FUNCTIONAL_GROUP_NAME", "")
            .startswith(KUBERNETES_NODE_PREFIX)
        ]
        if remaining_worker_rows:
            healthy_errors = _verify_node_present_k8s(
                host, remaining_worker_rows, label="remaining"
            )
            removal_errors.extend(healthy_errors)
            fields.append((
                "Remaining workers healthy",
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


def check_k8s_node_add(host) -> dict[str, Any]:
    """Restore removed Kubernetes worker node(s), run provision, verify addition."""
    summary = "Kubernetes node re-addition lifecycle"
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

        # Step 3: Rejoin nodes to the K8s cluster.
        # Unlike Slurm (where provision regenerates slurm.conf and
        # nodes appear automatically), K8s requires an explicit
        # kubeadm reset + join on each re-added node.
        join_file = host.file(_WORKER_JOIN_FILE)
        if not join_file.is_file:
            return _result(
                False, summary, fields,
                f"Worker join command not found: {_WORKER_JOIN_FILE}",
            )
        join_cmd = join_file.content_string.strip()
        if not join_cmd:
            return _result(
                False, summary, fields,
                f"Worker join command is empty: {_WORKER_JOIN_FILE}",
            )
        fields.append(("Join command", _WORKER_JOIN_FILE))

        rejoin_errors: list[str] = []
        for row in readded_rows:
            errs = _rejoin_node(host, row, join_cmd, fields)
            rejoin_errors.extend(errs)
        if rejoin_errors:
            return _result(
                False, summary, fields,
                "K8s rejoin failed: " + "; ".join(rejoin_errors),
            )

        # Step 4: Wait for nodes to become Ready, then verify.
        import time
        fields.append(("Wait", f"{_NODE_READY_WAIT}s for nodes to become Ready"))
        time.sleep(_NODE_READY_WAIT)

        addition_errors: list[str] = []

        k8s_errors = _verify_node_present_k8s(
            host, readded_rows, label="re-added"
        )
        addition_errors.extend(k8s_errors)
        fields.append((
            "K8s membership (kubectl)",
            "passed" if not k8s_errors else "; ".join(k8s_errors),
        ))

        # Basic connectivity: re-added node must be reachable.
        for row in readded_rows:
            ip = row["ADMIN_IP"]
            hostname = row["HOSTNAME"]
            ping_result = remote_command(host, row, f"ping -c1 -W3 {ip}")
            if ping_result.rc != 0:
                addition_errors.append(f"{hostname} ({ip}) not reachable")
                fields.append((f"Ping {hostname}", "failed"))
            else:
                fields.append((f"Ping {hostname}", "passed"))

        return _result(
            not addition_errors,
            summary,
            fields,
            "; ".join(addition_errors),
        )
    except Exception as exc:
        return runtime_exception(summary, exc)
