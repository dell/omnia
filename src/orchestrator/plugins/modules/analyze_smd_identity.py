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

"""Analyze desired PXE identities against live OpenCHAMI SMD interfaces."""

from __future__ import annotations

from collections import Counter
from typing import Any

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.smd_utils import interface_ips
from ansible.module_utils.smd_utils import is_node_interface
from ansible.module_utils.smd_utils import normalize_mac


DOCUMENTATION = r"""
---
module: analyze_smd_identity
short_description: Compare PXE node identities with live SMD interfaces
version_added: "2.3.0"
description:
  - Treats the current PXE mapping as the desired identity state.
  - Detects stale SMD interfaces that collide by admin IP or admin MAC.
  - Uses xname only to verify ownership of an IP/MAC-selected interface.
  - Can use a prior Omnia-managed identity manifest as additional safe anchors.
  - Validates that each desired admin IP has exactly one matching SMD interface.
author:
  - Dell Omnia Team
options:
  desired_nodes:
    description: PXE mapping rows containing ADMIN_IP and optional ADMIN_MAC/XNAME.
    required: true
    type: list
    elements: dict
  managed_nodes:
    description:
      - Previously managed PXE identities used only as safe IP/MAC cleanup anchors.
      - This permits removal of retired identities without selecting unrelated SMD records.
    required: false
    type: list
    elements: dict
    default: []
  interfaces:
    description: Objects returned by the SMD EthernetInterfaces API.
    required: true
    type: list
    elements: dict
  require_present:
    description: Report missing desired interfaces as validation errors.
    required: false
    type: bool
    default: true
"""

EXAMPLES = r"""
- name: Analyze live SMD identity state
  analyze_smd_identity:
    desired_nodes: "{{ mapping_nodes }}"
    managed_nodes: "{{ previous_managed_nodes | default([]) }}"
    interfaces: "{{ smd_interfaces.json }}"
    require_present: true
  register: smd_identity
"""

RETURN = r"""
errors:
  description: Identity validation errors.
  type: list
  elements: str
  returned: always
stale_interfaces:
  description: Live interfaces colliding with, but not matching, desired identities.
  type: list
  elements: dict
  returned: always
stale_macs:
  description: MAC addresses of stale interfaces.
  type: list
  elements: str
  returned: always
stale_xnames:
  description: Component IDs of stale interfaces.
  type: list
  elements: str
  returned: always
retired_xnames:
  description:
    - Previously managed XNAMEs that are absent from the desired mapping.
    - A still-live XNAME is included only when every interface carrying that
      XNAME is a Node interface authorized by the historical ADMIN_IP or
      ADMIN_MAC anchors.
  type: list
  elements: str
  returned: always
stale_interfaces_missing_id:
  description: Selected interfaces that cannot be safely deleted by interface ID.
  type: list
  elements: dict
  returned: always
stale_interface_ids:
  description: Authoritative SMD interface IDs selected for deletion.
  type: list
  elements: str
  returned: always
input_errors:
  description: Invalid or ambiguous desired and previously managed identities.
  type: list
  elements: str
  returned: always
identity_errors:
  description: Differences between desired identities and live SMD owners.
  type: list
  elements: str
  returned: always
ownership_errors:
  description:
    - Conflicts that cannot be safely reconciled from current or historical anchors.
    - These errors must block mutation.
  type: list
  elements: str
  returned: always
"""


def _duplicates(values: list[str]) -> list[str]:
    """Return sorted non-empty duplicate values."""
    counts = Counter(value for value in values if value)
    return sorted(value for value, count in counts.items() if count > 1)


def _normalized_desired(nodes: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Normalize fields used for identity comparison."""
    return [
        {
            "admin_ip": str(node.get("ADMIN_IP", "") or "").strip(),
            "admin_mac": normalize_mac(node.get("ADMIN_MAC", "")),
            "xname": str(node.get("XNAME", "") or "").strip(),
            "hostname": str(node.get("HOSTNAME", "") or "").strip(),
        }
        for node in nodes
    ]


def _desired_errors(desired: list[dict[str, str]]) -> list[str]:
    """Validate uniqueness and required fields in the desired identities."""
    errors = []
    for field in ("admin_ip", "admin_mac", "xname"):
        duplicates = _duplicates([node[field] for node in desired])
        if duplicates:
            errors.append(
                f"Desired PXE mapping contains duplicate {field}: {duplicates}"
            )
    missing_ips = [
        node["hostname"] or "<unknown>"
        for node in desired
        if not node["admin_ip"]
    ]
    if missing_ips:
        errors.append(f"Desired PXE nodes are missing ADMIN_IP: {missing_ips}")
    missing_xnames = [
        node["hostname"] or node["admin_ip"] or "<unknown>"
        for node in desired
        if not node["xname"]
    ]
    if missing_xnames:
        errors.append(f"Desired PXE nodes are missing XNAME: {missing_xnames}")
    return errors


def _managed_errors(managed: list[dict[str, str]]) -> list[str]:
    """Validate historical identities before they authorize deletion."""
    errors = []
    for field in ("admin_ip", "admin_mac", "xname"):
        duplicates = _duplicates([node[field] for node in managed])
        if duplicates:
            errors.append(
                f"Managed identity manifest contains duplicate {field}: "
                f"{duplicates}"
            )
    for index, node in enumerate(managed, start=1):
        label = node["hostname"] or node["xname"] or f"row {index}"
        if not node["admin_ip"] and not node["admin_mac"]:
            errors.append(
                f"Managed identity {label} has no ADMIN_IP or ADMIN_MAC anchor"
            )
        if not node["xname"]:
            errors.append(
                f"Managed identity {label} has no XNAME ownership verifier"
            )
    return errors


def _normalized_live(
    interfaces: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Normalize live SMD fields while retaining the original response."""
    return [
        {
            "raw": interface,
            "id": str(interface.get("ID", "") or "").strip(),
            "mac": normalize_mac(interface.get("MACAddress", "")),
            "xname": str(interface.get("ComponentID", "") or "").strip(),
            "ips": interface_ips(interface),
            "type": str(interface.get("Type", "") or "").strip(),
            "is_node": is_node_interface(interface),
        }
        for interface in interfaces
    ]


def _touches_anchor(node: dict[str, str], entry: dict[str, Any]) -> bool:
    """Return whether an IP or MAC anchor selects a live interface."""
    return bool(
        (node["admin_ip"] and node["admin_ip"] in entry["ips"])
        or (
            node["admin_mac"]
            and entry["mac"]
            and node["admin_mac"] == entry["mac"]
        )
    )


def _is_exact_owner(node: dict[str, str], entry: dict[str, Any]) -> bool:
    """Return whether a live interface is the complete desired owner."""
    return bool(
        node["admin_ip"]
        and node["admin_ip"] in entry["ips"]
        and (not node["admin_mac"] or node["admin_mac"] == entry["mac"])
        and (not node["xname"] or node["xname"] == entry["xname"])
    )


def _stale_interfaces(
    desired: list[dict[str, str]],
    managed: list[dict[str, str]],
    live: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Return safely stale interfaces and historical ownership conflicts."""
    node_live = [entry for entry in live if entry["is_node"]]
    selected_ids: set[int] = set()

    # The current desired state owns its declared IP/MAC namespace. Preserve a
    # single exact owner and retire only the conflicting records. If there is
    # no unique exact owner, retire every current-anchor collision so category
    # registration can recreate one authoritative record.
    for node in desired:
        matches = [entry for entry in node_live if _touches_anchor(node, entry)]
        exact_matches = [entry for entry in matches if _is_exact_owner(node, entry)]
        selected = [
            entry for entry in matches
            if len(exact_matches) != 1 or entry is not exact_matches[0]
        ]
        selected_ids.update(id(entry["raw"]) for entry in selected)

    ownership_errors = []
    exact_live_ids = {
        id(entry["raw"])
        for entry in node_live
        if any(_is_exact_owner(node, entry) for node in desired)
    }

    # Historical anchors authorize retirement only when the stored XNAME also
    # identifies the selected live record. An old IP/MAC reused by a different
    # SMD component is preserved and reported instead of being deleted.
    for entry in node_live:
        entry_id = id(entry["raw"])
        if entry_id in exact_live_ids or entry_id in selected_ids:
            continue
        anchors = [node for node in managed if _touches_anchor(node, entry)]
        if not anchors:
            continue
        verified = [
            node for node in anchors
            if node["xname"] and node["xname"] == entry["xname"]
        ]
        if verified:
            selected_ids.add(entry_id)
            continue
        expected_xnames = sorted({node["xname"] for node in anchors if node["xname"]})
        ownership_errors.append(
            "Historical ADMIN_IP/ADMIN_MAC anchor now belongs to SMD XNAME "
            f"{entry['xname'] or '<missing>'}; expected one of "
            f"{expected_xnames or ['<missing>']}. The record was preserved."
        )

    # Never mutate an explicitly non-Node EthernetInterface, even if it shares
    # an IP or MAC anchor with a managed node. Multiple interfaces may
    # legitimately share one ComponentID, so XNAME alone is not a collision.
    anchors = desired + managed
    for entry in (item for item in live if not item["is_node"]):
        if any(_touches_anchor(node, entry) for node in anchors):
            ownership_errors.append(
                f"SMD EthernetInterface {entry['id'] or '<missing ID>'} has "
                f"Type {entry['type'] or '<missing>'} and collides with a "
                "managed node identity. Only Node interfaces may be reconciled."
            )

    stale = [
        entry["raw"] for entry in node_live
        if id(entry["raw"]) in selected_ids
    ]
    return stale, list(dict.fromkeys(ownership_errors))


def _ownership_errors(
    desired: list[dict[str, str]],
    live: list[dict[str, Any]],
    require_present: bool,
) -> list[str]:
    """Validate unique IP ownership and optional MAC/XNAME equality."""
    errors = []
    for node in desired:
        ip_matches = [entry for entry in live if node["admin_ip"] in entry["ips"]]
        label = node["hostname"] or node["xname"] or node["admin_ip"]
        if not ip_matches:
            if require_present:
                errors.append(
                    f"{label}: ADMIN_IP {node['admin_ip']} has no SMD EthernetInterface"
                )
            continue
        if len(ip_matches) != 1:
            owners = [
                {
                    "id": entry["id"],
                    "mac": entry["mac"],
                    "xname": entry["xname"],
                }
                for entry in ip_matches
            ]
            errors.append(
                f"{label}: ADMIN_IP {node['admin_ip']} has {len(ip_matches)} "
                f"SMD EthernetInterfaces: {owners}"
            )
            continue
        actual = ip_matches[0]
        if node["admin_mac"] and actual["mac"] != node["admin_mac"]:
            errors.append(
                f"{label}: ADMIN_IP {node['admin_ip']} expected MAC "
                f"{node['admin_mac']}, found {actual['mac'] or '<missing>'}"
            )
        if node["xname"] and actual["xname"] != node["xname"]:
            errors.append(
                f"{label}: ADMIN_IP {node['admin_ip']} expected XNAME "
                f"{node['xname']}, found {actual['xname'] or '<missing>'}"
            )
    return errors


def _retirement_state(
    desired: list[dict[str, str]],
    managed: list[dict[str, str]],
    live: list[dict[str, Any]],
    stale: list[dict[str, Any]],
) -> tuple[list[str], list[str]]:
    """Resolve retired XNAMEs only when every live owner is historical."""
    desired_xnames = {node["xname"] for node in desired if node["xname"]}
    historical_xnames = {
        node["xname"] for node in managed
        if node["xname"] and node["xname"] not in desired_xnames
    }
    stale_object_ids = {id(interface) for interface in stale}
    retired = []
    errors = []

    for xname in sorted(historical_xnames):
        historical_owners = [
            node for node in managed if node["xname"] == xname
        ]
        live_for_xname = [
            entry for entry in live
            if entry["xname"] == xname
        ]
        unauthorized = [
            entry for entry in live_for_xname
            if (
                not entry["is_node"]
                or not any(
                    _touches_anchor(owner, entry)
                    for owner in historical_owners
                )
                or id(entry["raw"]) not in stale_object_ids
            )
        ]
        if unauthorized:
            owners = [
                {
                    "id": entry["id"] or "<missing>",
                    "type": entry["type"] or "<missing>",
                    "mac": entry["mac"] or "<missing>",
                    "ips": sorted(entry["ips"]),
                }
                for entry in unauthorized
            ]
            errors.append(
                f"Previously managed XNAME {xname} is absent from the desired "
                "mapping, but not every live interface carrying that XNAME "
                "is authorized by its historical ADMIN_IP or ADMIN_MAC "
                f"anchors: {owners}. The identity and all dependencies were "
                "preserved."
            )
            continue
        retired.append(xname)

    return retired, errors


def analyze_smd_identity(
    desired_nodes: list[dict[str, Any]],
    interfaces: list[dict[str, Any]],
    require_present: bool = True,
    managed_nodes: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return stale live interfaces and desired-state validation errors."""
    desired = _normalized_desired(desired_nodes)
    managed = _normalized_desired(managed_nodes or [])
    live = _normalized_live(interfaces)
    input_errors = _desired_errors(desired) + _managed_errors(managed)
    node_live = [entry for entry in live if entry["is_node"]]
    identity_errors = _ownership_errors(desired, node_live, require_present)
    stale, ownership_errors = _stale_interfaces(desired, managed, live)
    retired_xnames, retirement_errors = _retirement_state(
        desired, managed, live, stale
    )
    ownership_errors.extend(retirement_errors)
    ownership_errors = list(dict.fromkeys(ownership_errors))
    errors = input_errors + identity_errors + ownership_errors

    stale_macs = sorted(
        {normalize_mac(item.get("MACAddress", "")) for item in stale}
        - {""}
    )
    stale_xnames = sorted(
        {str(item.get("ComponentID", "") or "").strip() for item in stale}
        - {""}
    )
    stale_ids = sorted(
        {str(item.get("ID", "") or "").strip() for item in stale}
        - {""}
    )
    stale_interfaces_missing_id = [
        item for item in stale if not str(item.get("ID", "") or "").strip()
    ]
    return {
        "errors": errors,
        "input_errors": input_errors,
        "identity_errors": identity_errors,
        "ownership_errors": ownership_errors,
        "stale_interfaces": stale,
        "stale_interface_ids": stale_ids,
        "stale_interfaces_missing_id": stale_interfaces_missing_id,
        "stale_macs": stale_macs,
        "stale_xnames": stale_xnames,
        "retired_xnames": retired_xnames,
    }


def main() -> None:
    """Execute the Ansible module."""
    module = AnsibleModule(
        argument_spec={
            "desired_nodes": {"type": "list", "elements": "dict", "required": True},
            "interfaces": {"type": "list", "elements": "dict", "required": True},
            "require_present": {"type": "bool", "default": True},
            "managed_nodes": {
                "type": "list",
                "elements": "dict",
                "default": [],
            },
        },
        supports_check_mode=True,
    )
    result = analyze_smd_identity(
        module.params["desired_nodes"],
        module.params["interfaces"],
        module.params["require_present"],
        module.params["managed_nodes"],
    )
    module.exit_json(changed=False, **result)


if __name__ == "__main__":
    main()
