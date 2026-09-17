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
"""Build a side-effect-free metadata-service hostname reconciliation plan."""

from __future__ import annotations

from collections import Counter
from typing import Any

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.smd_utils import response_records


DOCUMENTATION = r"""
---
module: plan_smd_hostname
short_description: Plan metadata-service hostname reconciliation
version_added: "2.3.0"
description:
  - Classifies desired metadata hostnames as create, update, or unchanged.
  - Validates identity uniqueness and deletion/update identifiers.
  - Does not contact or mutate metadata-service.
options:
  desired_entries:
    description: Desired entries containing id and local-hostname.
    required: true
    type: list
    elements: dict
  instanceinfos:
    description: Metadata-service instanceinfos response.
    required: true
    type: raw
author:
  - Dell Omnia Team
"""

EXAMPLES = r"""
- name: Plan metadata hostname updates
  plan_smd_hostname:
    desired_entries: "{{ hostname_entries }}"
    instanceinfos: "{{ instanceinfos_response.json }}"
  register: hostname_plan
"""

RETURN = r"""
errors:
  description: Conditions that must block metadata mutation.
  type: list
  elements: str
  returned: always
create:
  description: Missing hostname identities to create.
  type: list
  elements: dict
  returned: always
update:
  description: Existing hostname identities to update by UID.
  type: list
  elements: dict
  returned: always
unchanged:
  description: XNAMEs already matching desired hostname state.
  type: list
  elements: str
  returned: always
"""


def _duplicates(values: list[str]) -> list[str]:
    """Return sorted non-empty duplicate values."""
    counts = Counter(value for value in values if value)
    return sorted(value for value, count in counts.items() if count > 1)


def plan_smd_hostname(
    desired_entries: list[dict[str, Any]], instanceinfos_response: Any
) -> dict[str, Any]:
    """Return deterministic create/update/no-op metadata operations."""
    errors: list[str] = []
    creates = []
    updates = []
    unchanged = []
    desired = [
        {
            "xname": str(entry.get("id", "") or "").strip(),
            "hostname": str(entry.get("local-hostname", "") or "").strip(),
        }
        for entry in desired_entries
    ]

    duplicate_xnames = _duplicates([entry["xname"] for entry in desired])
    if duplicate_xnames:
        errors.append(
            f"Desired metadata entries contain duplicate XNAMEs: {duplicate_xnames}"
        )
    for index, entry in enumerate(desired, start=1):
        if not entry["xname"]:
            errors.append(f"Desired metadata entry {index} has no XNAME")
        if not entry["hostname"]:
            errors.append(
                f"Desired metadata entry {entry['xname'] or index} has no hostname"
            )

    records, shape_error = response_records(
        instanceinfos_response, "InstanceInfos"
    )
    if shape_error:
        errors.append(f"metadata-service instanceinfos: {shape_error}")
        records = []

    if errors:
        return {
            "errors": list(dict.fromkeys(errors)),
            "create": [],
            "update": [],
            "unchanged": [],
        }

    for entry in desired:
        xname = entry["xname"]
        hostname = entry["hostname"]
        matches = []
        for index, record in enumerate(records, start=1):
            metadata = record.get("metadata", {})
            spec = record.get("spec", {})
            if not isinstance(metadata, dict) or not isinstance(spec, dict):
                errors.append(
                    f"Metadata instanceinfo record {index} has invalid "
                    "metadata or spec data"
                )
                continue
            if (
                str(metadata.get("name", "") or "").strip() == xname
                or str(spec.get("instance_id", "") or "").strip() == xname
            ):
                matches.append(record)

        if len(matches) > 1:
            errors.append(
                f"XNAME {xname} has {len(matches)} metadata-service records; "
                "expected at most one"
            )
            continue
        if not matches:
            creates.append({"xname": xname, "hostname": hostname})
            continue

        record = matches[0]
        metadata = record.get("metadata") or {}
        spec = record.get("spec") or {}
        metadata_name = str(metadata.get("name", "") or "").strip()
        instance_id = str(spec.get("instance_id", "") or "").strip()
        if metadata_name != xname or instance_id != xname:
            errors.append(
                f"XNAME {xname} has inconsistent metadata identity: "
                f"name={metadata_name or '<missing>'}, "
                f"instance_id={instance_id or '<missing>'}"
            )
            continue

        actual_hostname = str(spec.get("hostname", "") or "").strip()
        actual_local_hostname = str(
            spec.get("local_hostname", "") or ""
        ).strip()
        if actual_hostname == hostname and actual_local_hostname == hostname:
            unchanged.append(xname)
            continue

        uid = str(metadata.get("uid", "") or "").strip()
        if not uid:
            errors.append(
                f"XNAME {xname} requires a hostname update but has no metadata UID"
            )
            continue
        updates.append({"uid": uid, "xname": xname, "hostname": hostname})

    if errors:
        creates = []
        updates = []

    return {
        "errors": list(dict.fromkeys(errors)),
        "create": creates,
        "update": updates,
        "unchanged": unchanged,
    }


def main() -> None:
    """Execute the Ansible module."""
    module = AnsibleModule(
        argument_spec={
            "desired_entries": {
                "type": "list",
                "elements": "dict",
                "required": True,
            },
            "instanceinfos": {"type": "raw", "required": True},
        },
        supports_check_mode=True,
    )
    result = plan_smd_hostname(
        module.params["desired_entries"], module.params["instanceinfos"]
    )
    module.exit_json(changed=False, **result)


if __name__ == "__main__":
    main()
