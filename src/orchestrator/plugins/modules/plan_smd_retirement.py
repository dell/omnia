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
"""Build a deterministic, side-effect-free SMD dependency retirement plan."""

from __future__ import annotations

import re
from typing import Any

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.smd_utils import response_records


NODE_XNAME_PATTERN = re.compile(
    r"^(?P<bmc>x[0-9]+c[0-9]+s[0-9]+b[0-9]+)n[0-9]+$"
)
XNAME_CHILD_SUFFIX_PATTERN = re.compile(r"^(?:[a-z][0-9]+)+$")


DOCUMENTATION = r"""
---
module: plan_smd_retirement
short_description: Plan dependency cleanup for retired SMD node identities
version_added: "2.3.0"
description:
  - Converts live SMD and metadata-service responses into a deterministic plan.
  - Does not contact services, mutate records, or authorize identity ownership.
  - Fails closed through the returned errors when a response shape or deletion
    identifier is unsafe.
options:
  retired_xnames:
    description: Retired Node XNAMEs already authorized by identity analysis.
    required: true
    type: list
    elements: str
  groups:
    description: SMD groups API response, either a list or a Groups mapping.
    required: true
    type: raw
  instanceinfos:
    description: Metadata-service instanceinfos response.
    required: true
    type: raw
  redfish_endpoints:
    description: SMD RedfishEndpoints API response.
    required: true
    type: raw
  component_endpoints:
    description: SMD ComponentEndpoints API response.
    required: true
    type: raw
  ethernet_interfaces:
    description: SMD EthernetInterfaces API response.
    required: true
    type: raw
  state_components:
    description: SMD State Components API response.
    required: true
    type: raw
author:
  - Dell Omnia Team
"""

EXAMPLES = r"""
- name: Plan dependency retirement
  plan_smd_retirement:
    retired_xnames: "{{ retired_xnames }}"
    groups: "{{ groups_response.json }}"
    instanceinfos: "{{ instanceinfos_response.json }}"
    redfish_endpoints: "{{ redfish_response.json }}"
    component_endpoints: "{{ component_response.json }}"
    ethernet_interfaces: "{{ interfaces_response.json }}"
    state_components: "{{ state_response.json }}"
  register: retirement_plan
"""

RETURN = r"""
errors:
  description: Conditions that must block all retirement mutations.
  type: list
  elements: str
  returned: always
group_memberships:
  description: Group/XNAME pairs to remove.
  type: list
  elements: dict
  returned: always
metadata_identities:
  description: Metadata identities and UIDs to delete.
  type: list
  elements: dict
  returned: always
redfish_endpoint_ids:
  description: Existing retired RedfishEndpoint IDs.
  type: list
  elements: str
  returned: always
component_endpoint_ids:
  description:
    - Existing retired ComponentEndpoint IDs.
    - Includes descendant endpoints owned by a retired Redfish endpoint.
  type: list
  elements: str
  returned: always
ethernet_interface_ids:
  description:
    - EthernetInterface IDs belonging to fully authorized retired Node or BMC
      components.
  type: list
  elements: str
  returned: always
state_component_ids:
  description:
    - Existing retired State Component IDs.
    - Includes structurally valid descendants of an authorized retired BMC,
      even when their ComponentEndpoint record is already absent.
  type: list
  elements: str
  returned: always
retired_bmc_xnames:
  description: Derived BMC XNAMEs for the retired nodes.
  type: list
  elements: str
  returned: always
retired_component_xnames:
  description: Combined retired Node and BMC XNAMEs.
  type: list
  elements: str
  returned: always
"""


def _unique_strings(values: list[Any]) -> list[str]:
    """Return non-empty strings once, preserving their first occurrence."""
    return list(dict.fromkeys(
        str(value or "").strip() for value in values
        if str(value or "").strip()
    ))


def _records(
    response: Any,
    key: str,
    source: str,
    errors: list[str],
) -> list[dict[str, Any]]:
    """Normalize one response and attach a source-specific shape error."""
    records, error = response_records(response, key)
    if error:
        errors.append(f"{source}: {error}")
    return records


def _record_ids(
    records: list[dict[str, Any]],
    targets: set[str],
    source: str,
    errors: list[str],
) -> list[str]:
    """Select existing record IDs that belong to the authorized targets."""
    record_ids = []
    for index, record in enumerate(records, start=1):
        record_id = str(record.get("ID", "") or "").strip()
        if record_id not in targets:
            continue
        if not record_id:
            errors.append(f"{source} record {index} has no ID")
            continue
        record_ids.append(record_id)
    return sorted(set(record_ids))


def _component_endpoint_ids(
    records: list[dict[str, Any]],
    retired_components: set[str],
    retired_bmcs: set[str],
    errors: list[str],
) -> list[str]:
    """Select direct and Redfish-owned component endpoint IDs."""
    record_ids = []
    for index, record in enumerate(records, start=1):
        record_id = str(record.get("ID", "") or "").strip()
        redfish_id = str(record.get("RedfishEndpointID", "") or "").strip()
        if (
            record_id not in retired_components
            and redfish_id not in retired_bmcs
        ):
            continue
        if not record_id:
            errors.append(
                "SMD ComponentEndpoint record "
                f"{index} belongs to retired Redfish endpoint "
                f"{redfish_id or '<missing>'} but has no deletion ID"
            )
            continue
        record_ids.append(record_id)
    return sorted(set(record_ids))


def _ethernet_interface_ids(
    records: list[dict[str, Any]],
    retired_components: set[str],
    errors: list[str],
) -> list[str]:
    """Select interfaces whose exact component owner is fully retired."""
    record_ids = []
    for index, record in enumerate(records, start=1):
        component_id = str(record.get("ComponentID", "") or "").strip()
        if component_id not in retired_components:
            continue
        record_id = str(record.get("ID", "") or "").strip()
        if not record_id:
            errors.append(
                f"SMD EthernetInterface record {index} belongs to retired "
                f"component {component_id} but has no deletion ID"
            )
            continue
        record_ids.append(record_id)
    return sorted(set(record_ids))


def _state_component_ids(
    records: list[dict[str, Any]],
    direct_targets: set[str],
    retired_bmcs: set[str],
    errors: list[str],
) -> list[str]:
    """Select direct targets and valid XNAME descendants of retired BMCs."""
    record_ids = []
    for index, record in enumerate(records, start=1):
        record_id = str(record.get("ID", "") or "").strip()
        if not record_id:
            errors.append(
                f"SMD State Component record {index} has no ID; its ownership "
                "cannot be classified safely"
            )
            continue
        if record_id in direct_targets:
            record_ids.append(record_id)
            continue

        descendant_owners = []
        ambiguous_owners = []
        for bmc_xname in retired_bmcs:
            if not record_id.startswith(bmc_xname):
                continue
            suffix = record_id[len(bmc_xname):]
            if not suffix:
                continue
            # A numeric continuation is a similarly prefixed BMC ordinal
            # (for example b00 compared with retired b0), not a descendant.
            if suffix[0].isdigit():
                continue
            if XNAME_CHILD_SUFFIX_PATTERN.fullmatch(suffix):
                descendant_owners.append(bmc_xname)
            else:
                ambiguous_owners.append(bmc_xname)

        if len(descendant_owners) == 1 and not ambiguous_owners:
            record_ids.append(record_id)
            continue
        if descendant_owners or ambiguous_owners:
            errors.append(
                f"SMD State Component {record_id} has an ambiguous or malformed "
                "XNAME relationship to retired BMCs: valid owners="
                f"{sorted(descendant_owners)}, malformed-prefix owners="
                f"{sorted(ambiguous_owners)}"
            )

    return sorted(set(record_ids))


def plan_smd_retirement(
    retired_xnames: list[str],
    groups_response: Any,
    instanceinfos_response: Any,
    redfish_response: Any,
    component_response: Any,
    ethernet_response: Any,
    state_response: Any,
) -> dict[str, Any]:
    """Return the complete dependency plan for authorized retired XNAMEs."""
    errors: list[str] = []
    retired_nodes = _unique_strings(retired_xnames)
    retired_bmcs = []
    for xname in retired_nodes:
        node_match = NODE_XNAME_PATTERN.fullmatch(xname)
        if not node_match:
            errors.append(
                f"Retired identity {xname} is not a Node XNAME; "
                "its BMC dependencies cannot be derived safely"
            )
            continue
        retired_bmcs.append(node_match.group("bmc"))
    retired_bmcs = _unique_strings(retired_bmcs)
    retired_components = _unique_strings(retired_nodes + retired_bmcs)
    retired_node_set = set(retired_nodes)
    retired_bmc_set = set(retired_bmcs)
    retired_component_set = set(retired_components)

    groups = _records(groups_response, "Groups", "SMD groups", errors)
    instanceinfos = _records(
        instanceinfos_response,
        "InstanceInfos",
        "metadata-service instanceinfos",
        errors,
    )
    redfish_endpoints = _records(
        redfish_response,
        "RedfishEndpoints",
        "SMD RedfishEndpoints",
        errors,
    )
    component_endpoints = _records(
        component_response,
        "ComponentEndpoints",
        "SMD ComponentEndpoints",
        errors,
    )
    ethernet_interfaces = _records(
        ethernet_response,
        "EthernetInterfaces",
        "SMD EthernetInterfaces",
        errors,
    )
    state_components = _records(
        state_response,
        "Components",
        "SMD State Components",
        errors,
    )

    group_memberships = []
    for index, group in enumerate(groups, start=1):
        members = group.get("members", {})
        if not isinstance(members, dict):
            errors.append(f"SMD group record {index} has invalid members data")
            continue
        member_ids = members.get("ids") or []
        if not isinstance(member_ids, list):
            errors.append(
                f"SMD group record {index} has a non-list members.ids field"
            )
            continue
        matches = sorted(retired_node_set.intersection(
            str(value or "").strip() for value in member_ids
        ))
        if not matches:
            continue
        label = str(group.get("label", "") or "").strip()
        if not label:
            errors.append(
                f"SMD group containing retired identities {matches} has no label"
            )
            continue
        group_memberships.extend(
            {"group": label, "xname": xname} for xname in matches
        )

    metadata_identities = []
    for index, record in enumerate(instanceinfos, start=1):
        metadata = record.get("metadata", {})
        spec = record.get("spec", {})
        if not isinstance(metadata, dict) or not isinstance(spec, dict):
            errors.append(
                f"Metadata instanceinfo record {index} has invalid "
                "metadata or spec data"
            )
            continue
        metadata_name = str(metadata.get("name", "") or "").strip()
        instance_id = str(spec.get("instance_id", "") or "").strip()
        if (
            metadata_name not in retired_node_set
            and instance_id not in retired_node_set
        ):
            continue
        if (
            not metadata_name
            or not instance_id
            or metadata_name != instance_id
            or instance_id not in retired_node_set
        ):
            errors.append(
                "Retired metadata identity is inconsistent: metadata.name="
                f"{metadata_name or '<missing>'}, "
                f"spec.instance_id={instance_id or '<missing>'}"
            )
            continue
        uid = str(metadata.get("uid", "") or "").strip()
        if not uid:
            errors.append(
                "Retired metadata identity has no deletion UID: "
                f"{instance_id or metadata_name or '<unknown>'}"
            )
            continue
        metadata_identities.append({
            "uid": uid,
            "xname": instance_id,
        })

    component_endpoint_ids = _component_endpoint_ids(
        component_endpoints,
        retired_component_set,
        retired_bmc_set,
        errors,
    )
    state_targets = retired_component_set.union(component_endpoint_ids)

    result = {
        "errors": list(dict.fromkeys(errors)),
        "group_memberships": group_memberships,
        "metadata_identities": metadata_identities,
        "redfish_endpoint_ids": _record_ids(
            redfish_endpoints,
            retired_bmc_set,
            "SMD RedfishEndpoint",
            errors,
        ),
        "component_endpoint_ids": component_endpoint_ids,
        "ethernet_interface_ids": _ethernet_interface_ids(
            ethernet_interfaces,
            retired_component_set,
            errors,
        ),
        "state_component_ids": _state_component_ids(
            state_components,
            state_targets,
            retired_bmc_set,
            errors,
        ),
        "retired_bmc_xnames": retired_bmcs,
        "retired_component_xnames": retired_components,
    }
    result["errors"] = list(dict.fromkeys(errors))
    if result["errors"]:
        result.update({
            "group_memberships": [],
            "metadata_identities": [],
            "redfish_endpoint_ids": [],
            "component_endpoint_ids": [],
            "ethernet_interface_ids": [],
            "state_component_ids": [],
        })
    return result


def main() -> None:
    """Execute the Ansible module."""
    module = AnsibleModule(
        argument_spec={
            "retired_xnames": {
                "type": "list",
                "elements": "str",
                "required": True,
            },
            "groups": {"type": "raw", "required": True},
            "instanceinfos": {"type": "raw", "required": True},
            "redfish_endpoints": {"type": "raw", "required": True},
            "component_endpoints": {"type": "raw", "required": True},
            "ethernet_interfaces": {"type": "raw", "required": True},
            "state_components": {"type": "raw", "required": True},
        },
        supports_check_mode=True,
    )
    result = plan_smd_retirement(
        module.params["retired_xnames"],
        module.params["groups"],
        module.params["instanceinfos"],
        module.params["redfish_endpoints"],
        module.params["component_endpoints"],
        module.params["ethernet_interfaces"],
        module.params["state_components"],
    )
    module.exit_json(changed=False, **result)


if __name__ == "__main__":
    main()
