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

"""Kubernetes version and local-etcd runtime contracts after PXE boot."""

import json
import os
import re
from collections.abc import Mapping
from typing import Any

from ..vars.pxeboot_vars import PXEBOOT_COMMANDS
from ._pxeboot_helpers import (
    group_fields,
    remote_command,
    remote_json,
    runtime_exception,
    runtime_result,
)
from ._workload_helpers import (
    kubernetes_context as _context,
)
from ._workload_helpers import (
    optional_skip as _skip,
)


def _major_minor(value: str) -> str:
    match = re.search(r"(?:^|[^0-9])(\d+)\.(\d+)(?:\D|$)", value)
    return f"{match.group(1)}.{match.group(2)}" if match else ""


def _version_tuple(value: str) -> tuple[int, int] | None:
    major_minor = _major_minor(value)
    if not major_minor:
        return None
    major, minor = major_minor.split(".", 1)
    return int(major), int(minor)


def _within_minor_skew(
    candidate: tuple[int, int] | None,
    server: tuple[int, int] | None,
    *,
    older: int,
    newer: int,
) -> bool:
    if candidate is None or server is None or candidate[0] != server[0]:
        return False
    delta = candidate[1] - server[1]
    return -older <= delta <= newer


def check_kubernetes_version_compatibility(host):
    """Verify kubectl, server, kubeadm, kubelet, and CRI-O version alignment."""
    summary = "Kubernetes component version compatibility"
    try:
        _runtime, rows, control, _config = _context(host)
        if not rows:
            return _skip(summary, "No Kubernetes nodes are mapped")

        version_result = remote_command(
            host,
            control,
            PXEBOOT_COMMANDS["kubernetes_client_version"],
        )
        if version_result.rc != 0:
            raise RuntimeError("kubectl could not read client and server versions")
        try:
            version_payload = json.loads(version_result.stdout)
        except json.JSONDecodeError as exc:
            raise ValueError("kubectl version returned invalid JSON") from exc

        client = _major_minor(
            str(version_payload.get("clientVersion", {}).get("gitVersion", ""))
        )
        server = _major_minor(
            str(version_payload.get("serverVersion", {}).get("gitVersion", ""))
        )
        client_version = _version_tuple(client)
        server_version = _version_tuple(server)
        client_ok = _within_minor_skew(
            client_version,
            server_version,
            older=1,
            newer=1,
        )
        outcomes: dict[str, dict[str, object]] = {}
        for row in rows:
            kubeadm_result = remote_command(
                host, row, PXEBOOT_COMMANDS["kubeadm_version"]
            )
            crio_result = remote_command(host, row, PXEBOOT_COMMANDS["crio_version"])
            kubelet_result = remote_command(
                host, row, PXEBOOT_COMMANDS["kubelet_version"]
            )
            kubeadm = _major_minor(kubeadm_result.stdout)
            crio = _major_minor(crio_result.stdout)
            kubelet = _major_minor(kubelet_result.stdout)
            kubeadm_version = _version_tuple(kubeadm)
            crio_version = _version_tuple(crio)
            kubelet_version = _version_tuple(kubelet)
            node_ok = (
                kubeadm_result.rc == 0
                and crio_result.rc == 0
                and kubelet_result.rc == 0
                and bool(kubeadm)
                and bool(crio)
                and bool(kubelet)
                and kubeadm_version == server_version
                and crio_version == server_version
                and _within_minor_skew(
                    kubelet_version,
                    server_version,
                    older=3,
                    newer=0,
                )
            )
            outcomes[row["HOSTNAME"]] = {
                "ok": node_ok,
                "kubeadm": kubeadm or "unknown",
                "kubelet": kubelet or "unknown",
                "crio": crio or "unknown",
            }
        compatible = bool(client and server) and client_ok
        failed = [name for name, outcome in outcomes.items() if not outcome["ok"]]
        fields: list[tuple[str, object]] = [
            ("kubectl client", f"{'✓' if client_ok else '✗'} {client or 'unknown'}"),
            ("Kubernetes server", server or "unknown"),
            ("Version skew", "✓ supported" if client_ok else "✗ unsupported"),
        ]
        grouped: dict[str, list[dict[str, str]]] = {}
        for row in rows:
            grouped.setdefault(row["EXPECTED_FUNCTIONAL_GROUP"], []).append(row)
        for group_name, group_rows in sorted(grouped.items()):
            passed = sum(outcomes[row["HOSTNAME"]]["ok"] for row in group_rows)
            fields.append(
                ("Functional group", f"[{group_name}] ({passed}/{len(group_rows)})")
            )
            for row in group_rows:
                outcome = outcomes[row["HOSTNAME"]]
                icon = "✓" if outcome["ok"] else "✗"
                fields.extend(
                    [
                        (f"  {row['HOSTNAME']}", f"{icon} {row['ADMIN_IP']}"),
                        ("    kubeadm", f"{icon} {outcome['kubeadm']}"),
                        ("    kubelet", f"{icon} {outcome['kubelet']}"),
                        ("    CRI-O", f"{icon} {outcome['crio']}"),
                    ]
                )
        return runtime_result(
            compatible and not failed,
            summary,
            fields,
            "Kubernetes, kubeadm, or CRI-O versions are incompatible"
            if not compatible or failed
            else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def _flatten_devices(devices: Any) -> list[dict[str, Any]]:
    flattened: list[dict[str, Any]] = []
    for device in devices if isinstance(devices, list) else []:
        if not isinstance(device, dict):
            continue
        flattened.append(device)
        flattened.extend(_flatten_devices(device.get("children", [])))
    return flattened


def _mountpoint_matches(device: Mapping[str, Any], path: str) -> bool:
    mountpoints = device.get("mountpoints")
    if isinstance(mountpoints, list):
        return path in mountpoints
    return device.get("mountpoint") == path


def _parent_disk(
    selected: Mapping[str, Any],
    by_name: Mapping[str, Mapping[str, Any]],
) -> Mapping[str, Any]:
    current = selected
    visited: set[str] = set()
    while str(current.get("pkname") or ""):
        parent_name = str(current.get("pkname"))
        if parent_name in visited or parent_name not in by_name:
            break
        visited.add(parent_name)
        current = by_name[parent_name]
    return current


def _root_disk_name(root_source: str, by_name: Mapping[str, Mapping[str, Any]]) -> str:
    name = os.path.basename(root_source.strip())
    current = by_name.get(name, {})
    visited: set[str] = set()
    while str(current.get("pkname") or ""):
        parent_name = str(current.get("pkname"))
        if parent_name in visited:
            break
        visited.add(parent_name)
        name = parent_name
        current = by_name.get(parent_name, {})
    return name


def _local_etcd_node_state(host, row) -> tuple[bool, str]:
    mount_payload = remote_json(host, row, PXEBOOT_COMMANDS["etcd_mount"])
    filesystems = (
        mount_payload.get("filesystems", []) if isinstance(mount_payload, dict) else []
    )
    if len(filesystems) != 1:
        return False, f"mount records={len(filesystems)}"
    mount = filesystems[0]
    mount_source = str(mount.get("source") or "")
    mount_type = str(mount.get("fstype") or "").lower()

    block_payload = remote_json(host, row, PXEBOOT_COMMANDS["etcd_block_devices"])
    devices = _flatten_devices(block_payload.get("blockdevices", []))
    by_name = {
        str(device.get("name")): device
        for device in devices
        if str(device.get("name") or "")
    }
    selected = next(
        (device for device in devices if _mountpoint_matches(device, "/var/lib/etcd")),
        {},
    )
    selected_disk = _parent_disk(selected, by_name) if selected else {}
    selected_disk_name = str(selected_disk.get("name") or "")

    root = remote_command(host, row, PXEBOOT_COMMANDS["etcd_root_source"])
    root_disk_name = _root_disk_name(root.stdout, by_name) if root.rc == 0 else ""
    fstab = remote_command(host, row, PXEBOOT_COMMANDS["etcd_fstab"])
    fstab_lines = [line.strip() for line in fstab.stdout.splitlines() if line.strip()]
    permissions = remote_command(host, row, PXEBOOT_COMMANDS["etcd_permissions"])
    manifest = remote_command(host, row, PXEBOOT_COMMANDS["etcd_manifest_data_dir"])
    log_time = remote_command(host, row, PXEBOOT_COMMANDS["etcd_boot_log"])
    boot_time = remote_command(host, row, PXEBOOT_COMMANDS["node_boot_time"])

    uuid = str(selected.get("uuid") or "")
    label = str(selected.get("label") or "")
    fstype = str(selected.get("fstype") or "").lower()
    expected_fstab_source = f"UUID={uuid}" if uuid else ""
    fstab_ok = (
        fstab.rc == 0
        and len(fstab_lines) == 1
        and fstab_lines[0].startswith(expected_fstab_source + "|")
        and "|/var/lib/etcd|ext4|" in fstab_lines[0]
    )
    boss_disks = [
        device
        for device in devices
        if str(device.get("type")) == "disk"
        and str(device.get("name") or "") != root_disk_name
        and "boss" in str(device.get("model") or "").lower()
    ]
    boss_ok = not boss_disks or "boss" in str(selected_disk.get("model") or "").lower()
    media_ok = str(selected_disk.get("type") or "") == "disk" and str(
        selected_disk.get("rota")
    ) in {"0", "1", "False", "True"}
    log_current = (
        log_time.rc == 0
        and boot_time.rc == 0
        and log_time.stdout.strip().isdigit()
        and boot_time.stdout.strip().isdigit()
        and int(log_time.stdout.strip()) >= int(boot_time.stdout.strip())
    )
    ok = all(
        (
            bool(mount_source),
            mount_type == "ext4",
            bool(selected),
            fstype == "ext4",
            label == "etcd_data",
            bool(uuid),
            selected_disk_name != root_disk_name,
            fstab_ok,
            permissions.rc == 0 and permissions.stdout.strip() == "etcd|etcd|700",
            manifest.rc == 0,
            boss_ok,
            media_ok,
            log_current,
        )
    )
    media = (
        "NVMe"
        if str(selected_disk.get("tran") or "") == "nvme"
        else ("HDD" if str(selected_disk.get("rota")) in {"1", "True"} else "SSD")
    )
    detail = (
        f"source={mount_source or 'missing'} | disk={selected_disk_name or 'missing'} "
        f"({media}) | fs={fstype or 'missing'} | label={label or 'missing'} | "
        f"UUID={'present' if uuid else 'missing'} | fstab={'valid' if fstab_ok else 'invalid'} | "
        f"permissions={permissions.stdout.strip() or 'invalid'} | "
        f"boot-script={'current' if log_current else 'stale/missing'}"
    )
    return ok, detail


def check_kubernetes_local_etcd_integrity(host):
    """Verify local-etcd disk selection, filesystem, mount, and boot persistence."""
    summary = "Kubernetes local-etcd storage integrity"
    try:
        _runtime, rows, _control, config = _context(host)
        if not rows or not bool(config.get("etcd_on_local_disk", False)):
            return _skip(summary, "etcd_on_local_disk is disabled")
        control_rows = [
            row for row in rows if "control_plane" in row["EXPECTED_FUNCTIONAL_GROUP"]
        ]
        outcomes = {
            row["HOSTNAME"]: _local_etcd_node_state(host, row) for row in control_rows
        }
        failures = [name for name, outcome in outcomes.items() if not outcome[0]]
        return runtime_result(
            bool(control_rows) and not failures,
            summary,
            group_fields(control_rows, outcomes),
            "Invalid local-etcd storage on: " + ", ".join(failures)
            if failures
            else (
                "No Kubernetes control-plane nodes are mapped"
                if not control_rows
                else ""
            ),
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)
