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
"""Plan and validate per-node OpenCHAMI SMD group membership."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.smd_utils import response_records


DOCUMENTATION = r"""
---
module: analyze_smd_group_membership
short_description: Plan and validate per-node SMD group membership
version_added: "2.3.0"
description:
  - Treats each mapping row's FUNCTIONAL_GROUP_NAME as authoritative for its XNAME.
  - Plans exact membership removals only for groups proven to be Omnia-owned.
  - Recognizes built-in unversioned and OS-versioned functional-group aliases.
  - Preserves unrelated operator groups that do not publish metadata-service data.
  - Reports ambiguous extra cloud-init-bearing groups instead of deleting them.
options:
  groups:
    description: SMD groups response, either a list or a Groups mapping.
    required: true
    type: raw
  desired_nodes:
    description: PXE mapping rows containing XNAME and FUNCTIONAL_GROUP_NAME.
    required: true
    type: list
    elements: dict
  metadata_groups:
    description: Metadata-service groups response.
    required: true
    type: raw
  target_xnames:
    description: Mapping XNAMEs evaluated by this operation; defaults to all rows.
    required: false
    type: list
    elements: str
    default: []
  managed_groups:
    description: Group labels proven Omnia-owned by durable prior state.
    required: false
    type: list
    elements: str
    default: []
  allowed_groups:
    description: Configured auxiliary group labels allowed with a primary group.
    required: false
    type: list
    elements: str
    default: []
  allowed_group_prefixes:
    description:
      - Omnia-reserved prefixes identifying per-functional-group auxiliary groups.
      - A configured prefixed group is allowed only when its suffix matches the
        expected group after primary-control-plane normalization.
      - Other groups in a reserved namespace are treated as stale Omnia groups.
    required: false
    type: list
    elements: str
    default: []
author:
  - Dell Omnia Team
"""

EXAMPLES = r"""
- name: Plan stale functional-group memberships
  analyze_smd_group_membership:
    groups: "{{ smd_groups.json }}"
    desired_nodes: "{{ mapping_nodes }}"
    metadata_groups: "{{ metadata_groups.json }}"
    target_xnames: "{{ category_xnames }}"
    managed_groups: "{{ historical_managed_groups }}"
    allowed_groups: [ssh, chrony, phone_home, additional_metadata_svc]
    allowed_group_prefixes: [additional_metadata_svc_]
  register: membership_plan
"""

RETURN = r"""
errors:
  description: Invalid input or API response conditions that block mutation.
  type: list
  elements: str
  returned: always
removals:
  description: Exact proven-safe group and XNAME membership pairs to delete.
  type: list
  elements: dict
  returned: always
conflicts:
  description: Unproven extra memberships that can contribute cloud-init data.
  type: list
  elements: dict
  returned: always
missing_memberships:
  description: Expected functional-group memberships absent from SMD.
  type: list
  elements: dict
  returned: always
missing_metadata_groups:
  description: Expected functional groups absent from metadata-service.
  type: list
  elements: str
  returned: always
empty_groups_after_removal:
  description: Proven stale groups that become empty after the planned removals.
  type: list
  elements: str
  returned: always
metadata_deletions:
  description: Metadata-service group names and UIDs safe to delete after empty checks.
  type: list
  elements: dict
  returned: always
target_metadata_deletions:
  description: Current functional-group metadata names and UIDs safe to refresh.
  type: list
  elements: dict
  returned: always
"""


_BUILT_IN_FUNCTIONAL_GROUP = re.compile(
    r"^(?P<role>service_kube_control_plane(?:_first)?|service_kube_node|"
    r"slurm_control_node|slurm_node|login_node|login_compiler_node|os)"
    r"(?:_(?P<os>rhel|rocky|ubuntu|sles)_"
    r"(?P<version>[0-9]+(?:_[0-9]+)*))?"
    r"_(?P<arch>x86_64|aarch64)$"
)

_PRIMARY_CONTROL_PLANE_PREFIX = "service_kube_control_plane_first_"
_CONTROL_PLANE_PREFIX = "service_kube_control_plane_"


def _strings(values: list[Any]) -> set[str]:
    """Return normalized, non-empty strings."""
    return {str(value or "").strip() for value in values if str(value or "").strip()}


def _duplicates(values: list[str]) -> list[str]:
    """Return sorted duplicate non-empty strings."""
    counts = Counter(value for value in values if value)
    return sorted(value for value, count in counts.items() if count > 1)


def _functional_group_identity(
    label: str,
) -> tuple[str, str | None, str | None, str] | None:
    """Return the role, OS, version, and architecture represented by a label."""
    match = _BUILT_IN_FUNCTIONAL_GROUP.fullmatch(label)
    if not match:
        return None
    return (
        match.group("role"),
        match.group("os"),
        match.group("version"),
        match.group("arch"),
    )


def _is_known_alias(label: str, expected: str) -> bool:
    """Return whether labels are an unversioned/versioned built-in pair."""
    label_identity = _functional_group_identity(label)
    expected_identity = _functional_group_identity(expected)
    if label == expected or label_identity is None or expected_identity is None:
        return False

    label_role, label_os, _, label_arch = label_identity
    expected_role, expected_os, _, expected_arch = expected_identity
    return bool(
        label_role == expected_role
        and label_arch == expected_arch
        and bool(label_os) != bool(expected_os)
    )


def _auxiliary_scope(expected: str) -> str:
    """Return the functional-group suffix used by auxiliary metadata groups."""
    if expected.startswith(_PRIMARY_CONTROL_PLANE_PREFIX):
        return expected.replace(
            _PRIMARY_CONTROL_PLANE_PREFIX,
            _CONTROL_PLANE_PREFIX,
            1,
        )
    return expected


def _metadata_group_index(response: Any) -> tuple[dict[str, str], list[str]]:
    """Extract metadata-service group names and UIDs and validate the response."""
    records, shape_error = response_records(response, "Groups")
    if shape_error:
        return {}, [f"metadata-service groups: {shape_error}"]

    errors = []
    names = []
    groups_by_name = {}
    for index, record in enumerate(records, start=1):
        metadata = record.get("metadata")
        if not isinstance(metadata, dict):
            errors.append(
                f"metadata-service group record {index} has invalid metadata"
            )
            continue
        name = str(metadata.get("name", "") or "").strip()
        if not name:
            errors.append(f"metadata-service group record {index} has no name")
            continue
        names.append(name)
        groups_by_name[name] = str(metadata.get("uid", "") or "").strip()
    duplicate_names = _duplicates(names)
    if duplicate_names:
        errors.append(
            "metadata-service contains duplicate group names: "
            f"{duplicate_names}"
        )
    return groups_by_name, errors


def _desired_group_map(
    desired_nodes: list[dict[str, Any]],
) -> tuple[dict[str, str], list[str]]:
    """Build and validate the authoritative XNAME-to-group mapping."""
    errors = []
    pairs = []
    for index, node in enumerate(desired_nodes, start=1):
        if not isinstance(node, dict):
            errors.append(f"Desired mapping row {index} is not an object")
            continue
        xname = str(node.get("XNAME", "") or "").strip()
        group = str(node.get("FUNCTIONAL_GROUP_NAME", "") or "").strip()
        if not xname:
            errors.append(f"Desired mapping row {index} has no XNAME")
        if not group:
            errors.append(
                f"Desired mapping row {index} ({xname or '<unknown>'}) has no "
                "FUNCTIONAL_GROUP_NAME"
            )
        if xname and group:
            pairs.append((xname, group))

    duplicate_xnames = _duplicates([xname for xname, _ in pairs])
    if duplicate_xnames:
        errors.append(f"Desired mapping contains duplicate XNAMEs: {duplicate_xnames}")
    return dict(pairs), errors


def _live_group_members(
    groups_response: Any,
) -> tuple[dict[str, set[str]], list[str]]:
    """Normalize and validate live SMD group membership."""
    groups, shape_error = response_records(groups_response, "Groups")
    if shape_error:
        return {}, [f"SMD groups: {shape_error}"]

    errors = []
    live_groups: dict[str, set[str]] = {}
    for index, group in enumerate(groups, start=1):
        label = str(group.get("label", "") or "").strip()
        members = group.get("members", {})
        if not label:
            errors.append(f"SMD group record {index} has no label")
            continue
        if label in live_groups:
            errors.append(f"SMD contains duplicate group label: {label}")
            continue
        if not isinstance(members, dict):
            errors.append(f"SMD group {label} has invalid members data")
            continue
        member_ids = members.get("ids") or []
        if not isinstance(member_ids, list):
            errors.append(f"SMD group {label} has a non-list members.ids field")
            continue
        live_groups[label] = _strings(member_ids)
    return live_groups, errors


def analyze_smd_group_membership(
    groups_response: Any,
    desired_nodes: list[dict[str, Any]],
    metadata_groups: Any,
    target_xnames: list[str] | None = None,
    managed_groups: list[str] | None = None,
    allowed_groups: list[str] | None = None,
    allowed_group_prefixes: list[str] | None = None,
) -> dict[str, Any]:
    """Return a fail-closed per-XNAME membership plan."""
    desired, desired_errors = _desired_group_map(desired_nodes)
    live_groups, group_errors = _live_group_members(groups_response)
    metadata_by_name, metadata_errors = _metadata_group_index(metadata_groups)
    metadata_names = set(metadata_by_name)
    errors = desired_errors + group_errors + metadata_errors

    targets = _strings(target_xnames or []) or set(desired)
    unknown_targets = sorted(targets.difference(desired))
    if unknown_targets:
        errors.append(
            f"Target XNAMEs are absent from the desired mapping: {unknown_targets}"
        )

    proven_groups = _strings(managed_groups or []) | set(desired.values())
    auxiliary_groups = _strings(allowed_groups or [])
    auxiliary_prefixes = tuple(sorted(_strings(allowed_group_prefixes or [])))

    removals = []
    conflicts = []
    missing_memberships = []
    preserved_operator_memberships = []
    planned_by_group: dict[str, set[str]] = {}

    for xname in sorted(targets.intersection(desired)):
        expected = desired[xname]
        actual_groups = {
            label for label, members in live_groups.items() if xname in members
        }
        if expected not in actual_groups:
            missing_memberships.append({"xname": xname, "expected_group": expected})

        for label in sorted(actual_groups.difference({expected})):
            auxiliary_scope = _auxiliary_scope(expected)
            is_scoped_auxiliary = any(
                label == f"{prefix}{auxiliary_scope}"
                for prefix in auxiliary_prefixes
            )
            if label in auxiliary_groups and (
                not label.startswith(auxiliary_prefixes)
                or is_scoped_auxiliary
            ):
                continue

            safely_managed = (
                label in proven_groups
                or label.startswith(auxiliary_prefixes)
                or _is_known_alias(label, expected)
            )
            if safely_managed:
                removal = {
                    "group": label,
                    "xname": xname,
                    "expected_group": expected,
                }
                removals.append(removal)
                planned_by_group.setdefault(label, set()).add(xname)
            elif label in metadata_names:
                conflicts.append(
                    {
                        "xname": xname,
                        "expected_group": expected,
                        "conflicting_group": label,
                    }
                )
            else:
                preserved_operator_memberships.append(
                    {"xname": xname, "group": label}
                )

    expected_metadata = {desired[xname] for xname in targets.intersection(desired)}
    missing_metadata_groups = sorted(expected_metadata.difference(metadata_names))
    current_expected_groups = set(desired.values())
    empty_groups_after_removal = sorted(
        label
        for label, removed_members in planned_by_group.items()
        if label not in current_expected_groups
        and not live_groups[label].difference(removed_members)
    )

    required_metadata_uids = set(empty_groups_after_removal) | expected_metadata
    for label in sorted(required_metadata_uids.intersection(metadata_names)):
        if metadata_by_name[label]:
            continue
        errors.append(
            "metadata-service group "
            f"{label} is required for reconciliation but has no metadata.uid"
        )

    metadata_deletions = [
        {"name": label, "uid": metadata_by_name[label]}
        for label in empty_groups_after_removal
        if metadata_by_name.get(label)
    ]
    target_metadata_deletions = [
        {"name": label, "uid": metadata_by_name[label]}
        for label in sorted(expected_metadata)
        if metadata_by_name.get(label)
    ]

    if errors:
        removals = []
        empty_groups_after_removal = []
        metadata_deletions = []
        target_metadata_deletions = []
    return {
        "errors": list(dict.fromkeys(errors)),
        "removals": removals,
        "conflicts": conflicts,
        "missing_memberships": missing_memberships,
        "missing_metadata_groups": missing_metadata_groups,
        "empty_groups_after_removal": empty_groups_after_removal,
        "metadata_deletions": metadata_deletions,
        "target_metadata_deletions": target_metadata_deletions,
        "preserved_operator_memberships": preserved_operator_memberships,
    }


def main() -> None:
    """Execute the Ansible module."""
    module = AnsibleModule(
        argument_spec={
            "groups": {"type": "raw", "required": True},
            "desired_nodes": {
                "type": "list",
                "elements": "dict",
                "required": True,
            },
            "metadata_groups": {"type": "raw", "required": True},
            "target_xnames": {
                "type": "list",
                "elements": "str",
                "default": [],
            },
            "managed_groups": {
                "type": "list",
                "elements": "str",
                "default": [],
            },
            "allowed_groups": {
                "type": "list",
                "elements": "str",
                "default": [],
            },
            "allowed_group_prefixes": {
                "type": "list",
                "elements": "str",
                "default": [],
            },
        },
        supports_check_mode=True,
    )
    result = analyze_smd_group_membership(
        module.params["groups"],
        module.params["desired_nodes"],
        module.params["metadata_groups"],
        module.params["target_xnames"],
        module.params["managed_groups"],
        module.params["allowed_groups"],
        module.params["allowed_group_prefixes"],
    )
    module.exit_json(changed=False, **result)


if __name__ == "__main__":
    main()
