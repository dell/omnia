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

"""Compare PXE identities with OpenCHAMI Boot Service node records."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.smd_utils import (
    interface_ips,
    is_node_interface,
    normalize_mac,
)

DOCUMENTATION = r"""
---
module: analyze_boot_service_identity
short_description: Compare PXE MACs with Boot Service node identities
version_added: "2.3.0"
description:
  - Matches Boot Service nodes to PXE mapping rows by XNAME.
  - Produces a targeted bootMac patch plan without mutating either service.
  - Exposes a stale Boot Service MAC as a historical SMD cleanup anchor only
    when its XNAME ownership is unambiguous.
options:
  desired_nodes:
    description: PXE mapping rows containing XNAME and ADMIN_MAC.
    required: true
    type: list
    elements: dict
  boot_nodes:
    description: Objects returned by the Boot Service nodes API.
    required: true
    type: list
    elements: dict
  interfaces:
    description: Objects returned by the SMD EthernetInterfaces API.
    required: true
    type: list
    elements: dict
  managed_nodes:
    description: Previously recorded Omnia-managed SMD identities.
    required: false
    type: list
    elements: dict
    default: []
  known_xnames:
    description:
      - XNAMEs in the complete current mapping when desired_nodes contains only
        the functional-group subset currently being registered.
      - These XNAMEs prevent another mapped node from being reported as a
        foreign owner; they are not analyzed or patched by this invocation.
    required: false
    type: list
    elements: str
    default: []
  require_present:
    description: Fail when a desired XNAME has no Boot Service node record.
    required: false
    type: bool
    default: true
author:
  - Dell Omnia Team
"""

EXAMPLES = r"""
- name: Plan Boot Service identity reconciliation
  analyze_boot_service_identity:
    desired_nodes: "{{ mapping_nodes }}"
    boot_nodes: "{{ boot_service_nodes.json }}"
    interfaces: "{{ smd_interfaces.json }}"
    managed_nodes: "{{ previous_managed_nodes | default([]) }}"
    known_xnames: "{{ complete_mapping_xnames | default([]) }}"
    require_present: false
  register: boot_identity
"""

RETURN = r"""
errors:
  description: All input and live identity errors.
  type: list
  elements: str
  returned: always
input_errors:
  description: Invalid or ambiguous desired inputs.
  type: list
  elements: str
  returned: always
identity_errors:
  description: Missing, duplicate, or unsafe Boot Service records.
  type: list
  elements: str
  returned: always
patch_plan:
  description: Unique Boot Service records whose bootMac must be corrected.
  type: list
  elements: dict
  returned: always
foreign_mac_owners:
  description:
    - Boot Service records whose bootMac is assigned by the desired mapping
      to a different XNAME while their own XNAME is absent from that mapping.
    - These records require explicit cleanup because a partial mapping cannot
      prove that the foreign record is safe to delete.
  type: list
  elements: dict
  returned: always
historical_nodes:
  description:
    - Stale Boot Service XNAME and bootMac pairs that may safely anchor SMD
      interface cleanup and are not already represented in managed_nodes.
  type: list
  elements: dict
  returned: always
superseded_managed_xnames:
  description:
    - Managed identities that already equal the desired mapping and may be
      replaced by a stale Boot Service MAC as the historical cleanup anchor.
  type: list
  elements: str
  returned: always
"""


_MAC_PATTERN = re.compile(r"^[0-9a-f]{2}(?::[0-9a-f]{2}){5}$")


def _duplicates(values: list[str]) -> list[str]:
    """Return sorted duplicate non-empty strings."""
    counts = Counter(value for value in values if value)
    return sorted(value for value, count in counts.items() if count > 1)


def _desired_node(node: dict[str, Any]) -> dict[str, str]:
    """Normalize the desired identity fields used by this module."""
    return {
        "xname": str(node.get("XNAME", "") or "").strip(),
        "admin_ip": str(node.get("ADMIN_IP", "") or "").strip(),
        "admin_mac": normalize_mac(node.get("ADMIN_MAC", "")),
        "hostname": str(node.get("HOSTNAME", "") or "").strip(),
    }


def _managed_node(node: dict[str, Any]) -> dict[str, str]:
    """Normalize an earlier Omnia-managed identity."""
    return {
        "xname": str(node.get("XNAME", "") or "").strip(),
        "admin_ip": str(node.get("ADMIN_IP", "") or "").strip(),
        "admin_mac": normalize_mac(node.get("ADMIN_MAC", "")),
    }


def _boot_node(node: dict[str, Any]) -> dict[str, str]:
    """Normalize a Boot Service resource while retaining its patch UID."""
    spec = node.get("spec") if isinstance(node.get("spec"), dict) else {}
    metadata = (
        node.get("metadata")
        if isinstance(node.get("metadata"), dict)
        else {}
    )
    return {
        "xname": str(spec.get("xname", "") or "").strip(),
        "boot_mac": normalize_mac(spec.get("bootMac", "")),
        "uid": str(metadata.get("uid", "") or "").strip(),
    }


def _smd_interface(interface: dict[str, Any]) -> dict[str, Any]:
    """Normalize an SMD interface for topology and ownership checks."""
    return {
        "id": str(interface.get("ID", "") or "").strip(),
        "xname": str(interface.get("ComponentID", "") or "").strip(),
        "mac": normalize_mac(interface.get("MACAddress", "")),
        "ips": interface_ips(interface),
        "is_node": is_node_interface(interface),
    }


def _same_managed_identity(
    desired: dict[str, str], managed: dict[str, str]
) -> bool:
    """Return whether a manifest row already represents desired state."""
    return bool(
        managed["xname"] == desired["xname"]
        and managed["admin_mac"] == desired["admin_mac"]
    )


def _managed_owns_interface(
    managed: dict[str, str], interface: dict[str, Any]
) -> bool:
    """Require XNAME plus a historical IP or MAC ownership anchor."""
    return bool(
        managed["xname"]
        and managed["xname"] == interface["xname"]
        and (
            (
                managed["admin_mac"]
                and managed["admin_mac"] == interface["mac"]
            )
            or (
                managed["admin_ip"]
                and managed["admin_ip"] in interface["ips"]
            )
        )
    )


def analyze_boot_service_identity(
    desired_nodes: list[dict[str, Any]],
    boot_nodes: list[dict[str, Any]],
    interfaces: list[dict[str, Any]],
    managed_nodes: list[dict[str, Any]] | None = None,
    known_xnames: list[str] | None = None,
    require_present: bool = True,
) -> dict[str, Any]:
    """Return an immutable, fail-closed Boot Service identity plan."""
    desired = [_desired_node(node) for node in desired_nodes]
    managed = [_managed_node(node) for node in (managed_nodes or [])]
    live = [_boot_node(node) for node in boot_nodes]
    smd_live = [
        _smd_interface(interface) for interface in interfaces
        if is_node_interface(interface)
    ]

    input_errors = []
    duplicate_xnames = _duplicates([node["xname"] for node in desired])
    duplicate_macs = _duplicates([node["admin_mac"] for node in desired])
    if duplicate_xnames:
        input_errors.append(
            f"Desired PXE mapping contains duplicate XNAME: {duplicate_xnames}"
        )
    if duplicate_macs:
        input_errors.append(
            "Desired PXE mapping contains duplicate ADMIN_MAC: "
            f"{duplicate_macs}"
        )

    for index, node in enumerate(desired, start=1):
        label = node["hostname"] or node["xname"] or f"row {index}"
        if not node["xname"]:
            input_errors.append(f"Desired PXE node {label} is missing XNAME")
        if not _MAC_PATTERN.fullmatch(node["admin_mac"]):
            input_errors.append(
                f"Desired PXE node {label} has invalid ADMIN_MAC "
                f"{node['admin_mac'] or '<missing>'}"
            )

    desired_xnames = {node["xname"] for node in desired if node["xname"]}
    authoritative_xnames = desired_xnames | {
        str(xname or "").strip() for xname in (known_xnames or []) if xname
    }
    live_for_desired = [node for node in live if node["xname"] in desired_xnames]
    duplicate_live_xnames = _duplicates(
        [node["xname"] for node in live_for_desired]
    )
    live_uid_counts = Counter(node["uid"] for node in live if node["uid"])

    identity_errors = []
    if duplicate_live_xnames:
        identity_errors.append(
            "Boot Service contains multiple node records for mapped XNAMEs: "
            f"{duplicate_live_xnames}"
        )
    patch_plan = []
    historical_nodes = []
    superseded_managed_xnames = []
    for node in desired:
        if not node["xname"]:
            continue
        matches = [entry for entry in live if entry["xname"] == node["xname"]]
        label = node["hostname"] or node["xname"]
        current = matches[0] if len(matches) == 1 else None
        managed_for_xname = [
            entry for entry in managed if entry["xname"] == node["xname"]
        ]
        historical_managed = [
            entry for entry in managed_for_xname
            if not _same_managed_identity(node, entry)
        ]
        smd_for_xname = [
            entry for entry in smd_live if entry["xname"] == node["xname"]
        ]
        manifest_stale = [
            entry for entry in smd_for_xname
            if entry["mac"] != node["admin_mac"]
            and any(
                _managed_owns_interface(managed_entry, entry)
                for managed_entry in historical_managed
            )
        ]
        manifest_stale_ids = {id(entry) for entry in manifest_stale}
        remaining_after_manifest = [
            entry for entry in smd_for_xname
            if id(entry) not in manifest_stale_ids
        ]

        topology_error = ""
        boot_history_may_anchor = False
        if len(smd_for_xname) > 1:
            if not (
                len(remaining_after_manifest) == 1
                and remaining_after_manifest[0]["mac"] == node["admin_mac"]
            ):
                topology_error = (
                    "multiple SMD Node interfaces exist and the durable "
                    "managed-identity manifest does not independently reduce "
                    "them to exactly the desired ADMIN_MAC"
                )
        elif len(smd_for_xname) == 1:
            only_interface = smd_for_xname[0]
            if (
                not remaining_after_manifest
                or only_interface["mac"] == node["admin_mac"]
            ):
                pass
            elif (
                current is not None
                and _MAC_PATTERN.fullmatch(current["boot_mac"])
                and only_interface["mac"] == current["boot_mac"]
            ):
                boot_history_may_anchor = True
            else:
                topology_error = (
                    "the sole SMD Node interface matches neither the desired "
                    "ADMIN_MAC nor an unambiguous historical bootMac"
                )

        if topology_error:
            topology = [
                {
                    "id": entry["id"] or "<missing>",
                    "mac": entry["mac"] or "<missing>",
                    "ips": sorted(entry["ips"]),
                }
                for entry in smd_for_xname
            ]
            identity_errors.append(
                f"{label}: refusing Boot Service/SMD reconciliation because "
                f"{topology_error}. Interfaces={topology}"
            )

        if not matches:
            if require_present:
                identity_errors.append(
                    f"{label}: Boot Service has no node for XNAME {node['xname']}"
                )
            continue
        if len(matches) != 1:
            continue

        if current["boot_mac"] == node["admin_mac"]:
            continue
        if not current["uid"]:
            identity_errors.append(
                f"{label}: Boot Service node {node['xname']} requires a bootMac "
                "update but has no metadata.uid"
            )
            continue
        if live_uid_counts[current["uid"]] > 1:
            identity_errors.append(
                f"{label}: Boot Service metadata.uid {current['uid']} is shared "
                "by multiple node records; refusing to use it as a PATCH target"
            )
            continue

        patch_plan.append(
            {
                "xname": node["xname"],
                "hostname": node["hostname"],
                "uid": current["uid"],
                "current_mac": current["boot_mac"],
                "desired_mac": node["admin_mac"],
            }
        )

        # Boot Service history is a cleanup anchor only when exactly one SMD
        # Node interface exists for the XNAME and it carries that bootMac.
        # With multiple interfaces, only the durable managed manifest may
        # prove which record is stale.
        if not boot_history_may_anchor:
            continue
        if any(
            entry["admin_mac"] == current["boot_mac"]
            for entry in managed_for_xname
        ):
            continue
        if managed_for_xname:
            if all(
                entry["admin_mac"] == node["admin_mac"]
                for entry in managed_for_xname
            ):
                # The manifest already describes today's desired mapping, so
                # it is redundant as a cleanup anchor. Temporarily replace it
                # with the older Boot Service identity during reconciliation.
                superseded_managed_xnames.append(node["xname"])
            else:
                identity_errors.append(
                    f"{label}: Boot Service historical MAC "
                    f"{current['boot_mac']} conflicts with the managed "
                    f"identity recorded for XNAME {node['xname']}; refusing "
                    "automatic SMD cleanup"
                )
                continue
        historical_nodes.append(
            {
                "XNAME": node["xname"],
                "ADMIN_MAC": current["boot_mac"],
                "ADMIN_IP": "",
                "HOSTNAME": node["hostname"],
            }
        )

    # HSM synchronization creates and updates Boot Service nodes but does not
    # prove that a node absent from today's mapping is safe to delete. Report
    # old-XNAME ownership of a desired MAC separately so provisioning and PXE
    # can fail closed without deleting a potentially operator-owned record.
    foreign_mac_owners_by_uid: dict[str, dict[str, str]] = {}
    for node in desired:
        for owner in live:
            if (
                owner["boot_mac"] != node["admin_mac"]
                or owner["xname"] == node["xname"]
                or owner["xname"] in authoritative_xnames
            ):
                continue
            owner_key = owner["uid"] or (
                f"{owner['xname']}|{owner['boot_mac']}"
            )
            foreign_mac_owners_by_uid[owner_key] = {
                "uid": owner["uid"],
                "xname": owner["xname"],
                "boot_mac": owner["boot_mac"],
                "desired_xname": node["xname"],
            }

    return {
        "errors": input_errors + identity_errors,
        "input_errors": input_errors,
        "identity_errors": identity_errors,
        "patch_plan": patch_plan,
        "foreign_mac_owners": [
            foreign_mac_owners_by_uid[key]
            for key in sorted(foreign_mac_owners_by_uid)
        ],
        "historical_nodes": historical_nodes,
        "superseded_managed_xnames": sorted(
            set(superseded_managed_xnames)
        ),
    }


def main() -> None:
    """Execute the Ansible module."""
    module = AnsibleModule(
        argument_spec={
            "desired_nodes": {
                "type": "list",
                "elements": "dict",
                "required": True,
            },
            "boot_nodes": {
                "type": "list",
                "elements": "dict",
                "required": True,
            },
            "interfaces": {
                "type": "list",
                "elements": "dict",
                "required": True,
            },
            "managed_nodes": {
                "type": "list",
                "elements": "dict",
                "default": [],
            },
            "known_xnames": {
                "type": "list",
                "elements": "str",
                "default": [],
            },
            "require_present": {"type": "bool", "default": True},
        },
        supports_check_mode=True,
    )
    result = analyze_boot_service_identity(
        module.params["desired_nodes"],
        module.params["boot_nodes"],
        module.params["interfaces"],
        module.params["managed_nodes"],
        module.params["known_xnames"],
        module.params["require_present"],
    )
    module.exit_json(changed=False, **result)


if __name__ == "__main__":
    main()
