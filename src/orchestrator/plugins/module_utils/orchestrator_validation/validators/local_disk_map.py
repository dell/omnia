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
"""Approved disk map, pre-check and per-node status view (ER-ORCH-011 FR-2.5, FR-2.7)."""

from __future__ import annotations

import glob
import hashlib
import ipaddress
import json
import os
from datetime import datetime, timezone
from typing import Any

from ..messages import orchestrator_messages as msg

MAP_FILE_NAME = "disk-map.approved.json"
STATUS_FILE_PATTERN = "status-*.json"
NFS_MOUNT_NAME = "nfs_k8s"
MAP_SUBDIRECTORY = "kafka_disk_mapping"
MAX_RANGE_SIZE = 256


def is_disabled(override: Any) -> bool:
    """Return True for a node_overrides entry that sets ``enabled: false``."""
    return isinstance(override, dict) and override.get("enabled") is False


def parse_node_range(value: str) -> tuple[int, int] | None:
    """Parse a ``start_ip-end_ip`` node_overrides value.

    Args:
        value: The node_overrides ``node`` value.

    Returns:
        ``(start, end)`` as integers for a range, or None when the value names
        one node (contains no ``-``).

    Raises:
        ValueError: When the value contains ``-`` but is not a valid IPv4 range
            of at most MAX_RANGE_SIZE addresses with start <= end.
    """
    if "-" not in value:
        return None
    start_text, _, end_text = value.partition("-")
    try:
        start = ipaddress.IPv4Address(start_text.strip())
        end = ipaddress.IPv4Address(end_text.strip())
    except ipaddress.AddressValueError as exc:
        raise ValueError("start and end must be IPv4 addresses") from exc
    if int(start) > int(end):
        raise ValueError("start is after end")
    if int(end) - int(start) + 1 > MAX_RANGE_SIZE:
        raise ValueError(f"more than {MAX_RANGE_SIZE} addresses")
    return int(start), int(end)


def override_covers(override: dict[str, Any], node: str) -> bool:
    """Return True when a node_overrides entry (one IP or a range) covers node.

    A malformed range covers no node; the validator reports it.
    """
    value = str(override.get("node", ""))
    try:
        bounds = parse_node_range(value)
    except ValueError:
        return False
    if bounds is None:
        return value == node
    try:
        address = int(ipaddress.IPv4Address(node))
    except ipaddress.AddressValueError:
        return False
    return bounds[0] <= address <= bounds[1]


def resolve_map_dir(storage_data: dict[str, Any]) -> str:
    """Return the kafka_disk_mapping directory under the nfs_k8s mount point.

    Args:
        storage_data: Parsed storage_config.yml.

    Returns:
        Directory that holds the approved map and the per-node status files.

    Raises:
        ValueError: When no mount named nfs_k8s with a mount_point is declared.
    """
    mount = next(
        (
            entry
            for entry in storage_data.get("mounts", [])
            if isinstance(entry, dict) and entry.get("name") == NFS_MOUNT_NAME
        ),
        None,
    )
    if not mount or not mount.get("mount_point"):
        raise ValueError(
            f"storage_config.yml must declare mount '{NFS_MOUNT_NAME}' with a mount_point."
        )
    return os.path.join(mount["mount_point"], MAP_SUBDIRECTORY)


def _digest(rows: list[dict[str, Any]]) -> str:
    """Return the SHA-256 checksum of the approved map rows."""
    canonical = json.dumps(rows, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_map_rows(
    local_storage: list[dict[str, Any]],
    node_groups: dict[str, str],
    known_functional_groups: set[str],
) -> list[dict[str, Any]]:
    """Build approved map rows from declared local_storage data without probing nodes.

    For nodes with a node_overrides entry the declared disk_id is used directly.
    For selector-only nodes (no node_overrides) the disk_id is left empty; the
    node fills it at cloud-init time by matching the selector against its actual
    disks.

    A node covered by a node_overrides entry with ``enabled: false`` (one IP or
    a ``start_ip-end_ip`` range) gets a row with ``"enabled": false``; its
    cloud-init reports status ``disabled`` and changes no disk. Ranges are
    expanded here so each node still reads one concrete row.

    The map carries no row state. Each node reports the result in its own status
    file (FR-2.7).

    Args:
        local_storage: The local_storage list from storage_config.yml.
        node_groups: Mapping of admin IP to functional group name from the PXE
            mapping CSV, e.g. ``{"10.60.0.11": "service_kube_node_x86_64"}``.
        known_functional_groups: All known functional group names (built-in +
            catalog + mapping). Used to expand functional_group_prefix entries.

    Returns:
        List of map row dicts, one per (node, entry) combination.
    """
    rows: list[dict[str, Any]] = []

    for entry in local_storage:
        if not isinstance(entry, dict):
            continue

        name = entry.get("name", "")
        purpose = entry.get("purpose", "")
        disk_type = entry.get("disk_type", "boss")
        disk_identity = entry.get("disk_identity", "serial")
        model = entry.get("model")
        prefixes = entry.get("functional_group_prefix", [])

        # Expand prefixes to concrete functional group names
        entry_groups: set[str] = set()
        for prefix in prefixes:
            for grp in known_functional_groups:
                if grp.startswith(prefix):
                    entry_groups.add(grp)

        # Build an override index keyed by node name; disabled entries may be ranges
        override_index: dict[str, dict[str, Any]] = {}
        disabled_overrides: list[dict[str, Any]] = []
        for override in entry.get("node_overrides", []):
            if not isinstance(override, dict) or not override.get("node"):
                continue
            if is_disabled(override):
                disabled_overrides.append(override)
            else:
                override_index[str(override["node"])] = override

        # Nodes that belong to this entry's groups
        entry_nodes = [
            node
            for node, grp in node_groups.items()
            if grp in entry_groups
        ]

        for node in sorted(entry_nodes):
            if any(override_covers(item, node) for item in disabled_overrides):
                rows.append({
                    "node": node,
                    "entry": name,
                    "purpose": purpose,
                    "disk_id": "",
                    "disk_identity": disk_identity,
                    "disk_type": disk_type,
                    "model": model,
                    "enabled": False,
                })
                continue
            override = override_index.get(node)
            if override:
                row_disk_id = str(override.get("disk_id", ""))
                row_disk_identity = str(override.get("disk_identity", disk_identity))
                row_disk_type = str(override.get("disk_type", disk_type))
            else:
                # Selector-only: disk_id unknown until cloud-init runs on the node
                row_disk_id = ""
                row_disk_identity = disk_identity
                row_disk_type = disk_type

            rows.append({
                "node": node,
                "entry": name,
                "purpose": purpose,
                "disk_id": row_disk_id,
                "disk_identity": row_disk_identity,
                "disk_type": row_disk_type,
                "model": model,
            })

    return rows


def write_approved_map(
    data_dir: str,
    local_storage: list[dict[str, Any]],
    node_groups: dict[str, str],
    known_functional_groups: set[str],
) -> str:
    """Write the approved disk map built from declared local_storage data.

    The map contains one row per (node, entry) pair for every node that belongs
    to an entry's functional group. The map carries no row state.

    Args:
        data_dir: The kafka_disk_mapping directory on the nfs_k8s share.
        local_storage: The local_storage list from storage_config.yml.
        node_groups: Mapping of admin IP to functional group from the PXE CSV.
        known_functional_groups: All known functional group names.

    Returns:
        Path of the written map file.

    Raises:
        ValueError: When local_storage is empty or no rows can be built.
    """
    rows = build_map_rows(local_storage, node_groups, known_functional_groups)
    if not rows:
        raise ValueError(
            "No local_storage entries or no matching nodes found; map not written."
        )
    os.makedirs(data_dir, exist_ok=True)
    path = os.path.join(data_dir, MAP_FILE_NAME)
    with open(path, "w", encoding="utf-8") as map_file:
        json.dump(
            {"rows": rows, "checksum": _digest(rows)},
            map_file,
            indent=2,
            sort_keys=True,
        )
    return path


def load_node_rows(path: str, node: str) -> list[dict[str, Any]]:
    """Return the approved rows for one node after verifying the checksum.

    Args:
        path: Approved disk map file.
        node: Node reading its own rows.

    Returns:
        The node's rows, one per entry.

    Raises:
        ValueError: When the checksum does not match or the node has no row.
    """
    with open(path, "r", encoding="utf-8") as map_file:
        data = json.load(map_file)
    rows = data.get("rows", [])
    if data.get("checksum") != _digest(rows):
        raise ValueError(msg.map_checksum_mismatch_msg(path))
    node_rows = [row for row in rows if row.get("node") == node]
    if not node_rows:
        raise ValueError(msg.map_node_missing_msg(node, path))
    return node_rows


def write_node_status(
    data_dir: str,
    node: str,
    entry: str,
    purpose: str,
    result: str,
    reason: str,
    action: str,
) -> str:
    """Write the status file that only this node owns (FR-2.7).

    Args:
        data_dir: kafka_disk_mapping directory on the nfs_k8s share.
        node: Node writing its own status.
        entry: local_storage entry name.
        purpose: Entry purpose, ``etcd`` or ``kafka``.
        result: ``ok``, ``failed`` or ``disabled``.
        reason: Reason text, empty on success.
        action: Next operator action, empty on success.

    Returns:
        Path of the written status file.
    """
    record = {
        "node": node,
        "entry": entry,
        "purpose": purpose,
        "result": result,
        "reason": reason,
        "action": action,
        "updated": datetime.now(timezone.utc).isoformat(),
    }
    os.makedirs(data_dir, exist_ok=True)
    path = os.path.join(data_dir, f"status-{node}.json")
    with open(path, "w", encoding="utf-8") as status_file:
        json.dump(record, status_file, indent=2, sort_keys=True)
    return path


def read_status_view(data_dir: str) -> list[dict[str, Any]]:
    """Return every node's status record without modifying any file (FR-2.7).

    Args:
        data_dir: kafka_disk_mapping directory on the nfs_k8s share.

    Returns:
        Status records sorted by node name.
    """
    records = []
    for path in sorted(glob.glob(os.path.join(data_dir, STATUS_FILE_PATTERN))):
        with open(path, "r", encoding="utf-8") as status_file:
            records.append(json.load(status_file))
    return sorted(records, key=lambda record: str(record.get("node", "")))
