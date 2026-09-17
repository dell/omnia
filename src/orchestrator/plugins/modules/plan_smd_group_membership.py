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
"""Build a side-effect-free plan for stale Omnia-owned SMD memberships."""

from __future__ import annotations

from typing import Any

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.smd_utils import response_records


DOCUMENTATION = r"""
---
module: plan_smd_group_membership
short_description: Plan stale Omnia-owned SMD group membership removal
version_added: "2.3.0"
description:
  - Selects target XNAME memberships only from groups proven to be managed by Omnia.
  - Preserves target and common groups supplied as protected groups.
  - Validates the complete groups response before returning any mutation plan.
options:
  groups:
    description: SMD groups response, either a list or a Groups mapping.
    required: true
    type: raw
  target_xnames:
    description: Current category XNAMEs whose stale memberships are evaluated.
    required: true
    type: list
    elements: str
  managed_groups:
    description: Group labels authorized as Omnia-managed by current or prior state.
    required: true
    type: list
    elements: str
  protected_groups:
    description: Group labels that must not be modified during this operation.
    required: false
    type: list
    elements: str
    default: []
author:
  - Dell Omnia Team
"""

EXAMPLES = r"""
- name: Plan stale functional-group memberships
  plan_smd_group_membership:
    groups: "{{ smd_groups.json }}"
    target_xnames: "{{ category_xnames }}"
    managed_groups: "{{ omnia_managed_groups }}"
    protected_groups: "{{ target_groups + common_groups }}"
  register: membership_plan
"""

RETURN = r"""
errors:
  description: Invalid response conditions that block every mutation.
  type: list
  elements: str
  returned: always
removals:
  description: Exact group and XNAME membership pairs to delete.
  type: list
  elements: dict
  returned: always
"""


def _strings(values: list[Any]) -> set[str]:
    """Return normalized, non-empty strings."""
    return {str(value or "").strip() for value in values if str(value or "").strip()}


def plan_smd_group_membership(
    groups_response: Any,
    target_xnames: list[str],
    managed_groups: list[str],
    protected_groups: list[str] | None = None,
) -> dict[str, Any]:
    """Return exact stale memberships, failing closed on malformed input."""
    errors: list[str] = []
    groups, shape_error = response_records(groups_response, "Groups")
    if shape_error:
        errors.append(f"SMD groups: {shape_error}")
        groups = []

    targets = _strings(target_xnames)
    managed = _strings(managed_groups)
    protected = _strings(protected_groups or [])
    removals = []

    for index, group in enumerate(groups, start=1):
        label = str(group.get("label", "") or "").strip()
        members = group.get("members", {})
        if not label:
            errors.append(f"SMD group record {index} has no label")
            continue
        if not isinstance(members, dict):
            errors.append(f"SMD group {label} has invalid members data")
            continue
        member_ids = members.get("ids") or []
        if not isinstance(member_ids, list):
            errors.append(f"SMD group {label} has a non-list members.ids field")
            continue
        if label not in managed or label in protected:
            continue
        removals.extend(
            {"group": label, "xname": xname}
            for xname in sorted(targets.intersection(_strings(member_ids)))
        )

    if errors:
        removals = []
    return {
        "errors": list(dict.fromkeys(errors)),
        "removals": removals,
    }


def main() -> None:
    """Execute the Ansible module."""
    module = AnsibleModule(
        argument_spec={
            "groups": {"type": "raw", "required": True},
            "target_xnames": {
                "type": "list",
                "elements": "str",
                "required": True,
            },
            "managed_groups": {
                "type": "list",
                "elements": "str",
                "required": True,
            },
            "protected_groups": {
                "type": "list",
                "elements": "str",
                "default": [],
            },
        },
        supports_check_mode=True,
    )
    result = plan_smd_group_membership(
        module.params["groups"],
        module.params["target_xnames"],
        module.params["managed_groups"],
        module.params["protected_groups"],
    )
    module.exit_json(changed=False, **result)


if __name__ == "__main__":
    main()
