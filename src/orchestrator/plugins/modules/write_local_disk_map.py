#!/usr/bin/python
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
"""Write the approved disk map for local_storage entries (ER-ORCH-011 FR-2.5)."""

from __future__ import annotations

import csv
import json
import os
from typing import Any

import yaml
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.orchestrator_validation.validators.local_disk_map import (
    resolve_map_dir,
    write_approved_map,
)
from ansible.module_utils.orchestrator_validation.validators.pxe_mapping_validator import (
    BASE_HEADERS,
    CANONICAL_HEADERS,
    LEGACY_HEADERS,
    read_mapping,
    resolve_mapping_path,
)
from ansible.module_utils.orchestrator_validation.validators.storage_config_validator import (
    BUILTIN_FUNCTIONAL_GROUPS,
    _catalog_functional_groups,  # noqa: PLC2701
)

DOCUMENTATION = r'''
---
module: write_local_disk_map
short_description: Write the approved disk map for local_storage entries
version_added: "2.3.0"
description:
  - Reads storage_config.yml and the PXE mapping from input_project_dir.
  - Verifies that the nfs_k8s mount point is active on the OIM.
  - Builds one map row per (node, entry) pair from declared data only.
  - Writes disk-map.approved.json under <nfs_k8s mount_point>/kafka_disk_mapping/.
  - Skipped when no local_storage entry with purpose "kafka" is declared.
options:
  input_project_dir:
    description: Project input directory containing configuration files.
    required: true
    type: str
author:
  - Dell Omnia Team
'''

EXAMPLES = r'''
- name: Write local disk map after nfs_k8s is mounted
  omnia.orchestrator.write_local_disk_map:
    input_project_dir: "{{ orchestrator_data_path }}/input/{{ project_name }}"
  register: disk_map_result
  when: local_storage_kafka_declared | default(false) | bool
'''

RETURN = r'''
changed:
  description: Whether the map file was written or updated.
  returned: always
  type: bool
map_path:
  description: Absolute path of the written map file, empty when skipped.
  returned: always
  type: str
row_count:
  description: Number of rows written to the map.
  returned: always
  type: int
skipped:
  description: True when no kafka local_storage entry is declared.
  returned: always
  type: bool
msg:
  description: Human-readable result message.
  returned: always
  type: str
'''


def _load_yaml(path: str) -> Any:
    """Load a YAML file, returning None on any error."""
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as yaml_file:
            return yaml.safe_load(yaml_file)
    except (OSError, UnicodeError, yaml.YAMLError):
        return None


def _load_json(path: str) -> dict[str, Any] | None:
    """Load a JSON object file, returning None on any error."""
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as json_file:
            data = json.load(json_file)
        return data if isinstance(data, dict) else None
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None


def _has_kafka_entry(local_storage: list[Any]) -> bool:
    """Return True when at least one local_storage entry has purpose kafka."""
    return any(
        isinstance(entry, dict) and entry.get("purpose") == "kafka"
        for entry in local_storage
    )


def _build_node_groups(
    orchestrator_data: dict[str, Any],
    input_project_dir: str,
) -> dict[str, str]:
    """Return {admin_ip: functional_group_name} from the PXE mapping CSV.

    Returns an empty dict when the mapping file is absent or unreadable.
    """
    path = resolve_mapping_path(orchestrator_data, input_project_dir)
    if not os.path.isfile(path):
        return {}
    try:
        raw_header, header, rows = read_mapping(path)
    except (csv.Error, OSError, UnicodeError):
        return {}

    # Normalise header to canonical form
    if raw_header == list(BASE_HEADERS):
        header = list(BASE_HEADERS)
    elif raw_header == list(LEGACY_HEADERS):
        header = list(CANONICAL_HEADERS)
        rows = [(n, vals + [""]) for n, vals in rows]
    elif raw_header != list(CANONICAL_HEADERS):
        return {}
    if any(len(row) != len(header) for _, row in rows):
        return {}

    node_groups: dict[str, str] = {}
    for _, row_values in rows:
        mapped = dict(zip(header, row_values))
        admin_ip = mapped.get("ADMIN_IP", "").strip()
        fg_name = mapped.get("FUNCTIONAL_GROUP_NAME", "").strip()
        if admin_ip and fg_name:
            node_groups[admin_ip] = fg_name
    return node_groups


def _known_functional_groups(
    orchestrator_data: dict[str, Any],
    node_groups: dict[str, str],
) -> set[str]:
    """Return all known functional group names from built-ins, mapping, and catalog."""
    known = set(BUILTIN_FUNCTIONAL_GROUPS)
    known.update(node_groups.values())
    known.update(_catalog_functional_groups(orchestrator_data))
    return known


def _verify_mount(mount_point: str) -> str | None:
    """Return an error message when mount_point is not an active mount, else None."""
    if not os.path.isdir(mount_point):
        return (
            f"nfs_k8s mount point '{mount_point}' does not exist on the OIM. "
            "Ensure mount_config has run with mount_config_mode: oim-mount before "
            "this task."
        )
    # Check /proc/mounts to confirm the directory is a real mount, not just
    # a local directory created before the NFS share was mounted.
    try:
        with open("/proc/mounts", "r", encoding="utf-8") as mounts_file:
            mounted_points = {
                line.split()[1]
                for line in mounts_file
                if len(line.split()) >= 2
            }
    except (OSError, UnicodeError):
        # Cannot read /proc/mounts; skip the active-mount check.
        return None
    if mount_point not in mounted_points:
        return (
            f"nfs_k8s mount point '{mount_point}' exists as a directory but is "
            "not an active mount. Ensure mount_config has run with "
            "mount_config_mode: oim-mount before this task."
        )
    return None


def run_module() -> None:
    """Run the Ansible module entry point."""
    module = AnsibleModule(
        argument_spec={
            "input_project_dir": {"type": "str", "required": True},
        },
        supports_check_mode=False,
    )

    input_project_dir = os.path.realpath(module.params["input_project_dir"])

    # ── Load storage_config.yml ──────────────────────────────────────────────
    storage_path = os.path.join(input_project_dir, "storage_config.yml")
    storage_data = _load_yaml(storage_path)
    if not isinstance(storage_data, dict):
        module.fail_json(
            msg=f"Cannot read storage_config.yml from '{storage_path}'.",
            map_path="", row_count=0, skipped=False,
        )

    local_storage = storage_data.get("local_storage", [])
    if not isinstance(local_storage, list) or not _has_kafka_entry(local_storage):
        module.exit_json(
            changed=False,
            map_path="",
            row_count=0,
            skipped=True,
            msg="No local_storage entry with purpose 'kafka' declared; map not written.",
        )

    # ── Resolve the map directory from nfs_k8s mount ─────────────────────────
    try:
        map_dir = resolve_map_dir(storage_data)
    except ValueError as exc:
        module.fail_json(
            msg=str(exc),
            map_path="", row_count=0, skipped=False,
        )

    # strip the kafka_disk_mapping subdir to get the nfs_k8s mount point
    nfs_mount_point = os.path.dirname(map_dir)

    # ── Verify the mount is active ───────────────────────────────────────────
    mount_error = _verify_mount(nfs_mount_point)
    if mount_error:
        module.fail_json(
            msg=mount_error,
            map_path="", row_count=0, skipped=False,
        )

    # ── Load orchestrator_config.yml for PXE mapping path resolution ─────────
    orch_path = os.path.join(input_project_dir, "orchestrator_config.yml")
    orchestrator_data = _load_yaml(orch_path)
    if not isinstance(orchestrator_data, dict):
        orchestrator_data = {}

    # ── Build node→group mapping from PXE CSV ────────────────────────────────
    node_groups = _build_node_groups(orchestrator_data, input_project_dir)
    if not node_groups:
        module.fail_json(
            msg=(
                "PXE mapping file not found or unreadable in "
                f"'{input_project_dir}'. Cannot build the disk map without "
                "node-to-group assignments."
            ),
            map_path="", row_count=0, skipped=False,
        )

    known_fg = _known_functional_groups(orchestrator_data, node_groups)

    # ── Write the approved map ───────────────────────────────────────────────
    try:
        map_path = write_approved_map(map_dir, local_storage, node_groups, known_fg)
    except (ValueError, OSError) as exc:
        module.fail_json(
            msg=f"Failed to write disk map: {exc}",
            map_path="", row_count=0, skipped=False,
        )

    # Count rows written
    try:
        with open(map_path, "r", encoding="utf-8") as map_file:
            row_count = len(json.load(map_file).get("rows", []))
    except (OSError, json.JSONDecodeError):
        row_count = 0

    module.exit_json(
        changed=True,
        map_path=map_path,
        row_count=row_count,
        skipped=False,
        msg=(
            f"Disk map written to '{map_path}' with {row_count} row(s). "
            "Nodes read their own row during cloud-init and report in status files."
        ),
    )


def main() -> None:
    """Run the module entry point."""
    run_module()


if __name__ == "__main__":
    main()
