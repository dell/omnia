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

"""Build a guarded SMD and Boot Service identity reconciliation plan."""

from __future__ import annotations

from collections import Counter
from typing import Any

from ansible.module_utils.basic import AnsibleModule


DOCUMENTATION = r"""
---
module: plan_pxe_identity_reconciliation
short_description: Plan identity repairs before PXE restart
version_added: "2.3.0"
description:
  - Uses the complete PXE mapping as the desired identity contract.
  - Selects stale SMD Node interfaces only for target XNAMEs.
  - Preserves BMC and other non-Node interfaces.
  - Refuses to modify an interface owned by another current mapping row.
  - Plans Boot Service bootMac updates for target nodes.
author:
  - Dell Omnia Team
options:
  target_nodes:
    type: list
    elements: dict
    required: true
  all_nodes:
    type: list
    elements: dict
    required: true
  interfaces:
    type: list
    elements: dict
    required: true
  boot_nodes:
    type: list
    elements: dict
    required: true
"""


def _normalize_mac(value: Any) -> str:
    """Return a lowercase colon-separated MAC address."""
    compact = str(value or "").strip().lower().replace("-", ":")
    if ":" not in compact and len(compact) == 12:
        compact = ":".join(
            compact[index:index + 2] for index in range(0, 12, 2)
        )
    return compact


def _interface_ips(interface: dict[str, Any]) -> set[str]:
    """Return IP addresses from an SMD EthernetInterface record."""
    addresses = set()
    for entry in interface.get("IPAddresses") or []:
        value = entry.get("IPAddress", "") if isinstance(entry, dict) else entry
        value = str(value or "").strip()
        if value:
            addresses.add(value)
    return addresses


def _normalize_nodes(nodes: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Normalize the mapping fields used by the planner."""
    return [
        {
            "xname": str(node.get("XNAME", "") or "").strip(),
            "admin_mac": _normalize_mac(node.get("ADMIN_MAC", "")),
            "admin_ip": str(node.get("ADMIN_IP", "") or "").strip(),
            "hostname": str(node.get("HOSTNAME", "") or "").strip(),
        }
        for node in nodes
    ]


def _duplicates(values: list[str]) -> list[str]:
    counts = Counter(value for value in values if value)
    return sorted(value for value, count in counts.items() if count > 1)


def _validate_mapping(nodes: list[dict[str, str]]) -> list[str]:
    errors = []
    for index, node in enumerate(nodes, start=1):
        label = node["hostname"] or f"row {index}"
        for field in ("admin_mac", "admin_ip"):
            if not node[field]:
                errors.append(f"{label}: missing {field}")
    for field in ("admin_mac", "admin_ip"):
        duplicate_values = _duplicates([node[field] for node in nodes])
        if duplicate_values:
            errors.append(
                f"PXE mapping contains duplicate {field}: {duplicate_values}"
            )
    return errors


def _is_node_interface(interface: dict[str, Any]) -> bool:
    return str(interface.get("Type", "") or "").strip().lower() in {"", "node"}


def _normalize_interfaces(
    interfaces: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            "raw": interface,
            "id": str(interface.get("ID", "") or "").strip(),
            "xname": str(interface.get("ComponentID", "") or "").strip(),
            "mac": _normalize_mac(interface.get("MACAddress", "")),
            "ips": _interface_ips(interface),
            "is_node": _is_node_interface(interface),
        }
        for interface in interfaces
    ]


def _normalize_boot_nodes(boot_nodes: list[dict[str, Any]]) -> list[dict[str, str]]:
    normalized = []
    for node in boot_nodes:
        metadata = node.get("metadata") or {}
        spec = node.get("spec") or {}
        normalized.append(
            {
                "uid": str(metadata.get("uid", "") or "").strip(),
                "xname": str(
                    spec.get("xname", "") or metadata.get("name", "") or ""
                ).strip(),
                "boot_mac": _normalize_mac(spec.get("bootMac", "")),
            }
        )
    return normalized


def build_plan(
    target_nodes: list[dict[str, Any]],
    all_nodes: list[dict[str, Any]],
    interfaces: list[dict[str, Any]],
    boot_nodes: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return guarded deletions and Boot Service updates for target nodes."""
    targets = _normalize_nodes(target_nodes)
    desired = _normalize_nodes(all_nodes)
    live = _normalize_interfaces(interfaces)
    boot = _normalize_boot_nodes(boot_nodes)
    errors = _validate_mapping(desired)

    desired_by_identity = {
        (node["admin_mac"], node["admin_ip"]): node for node in desired
    }
    target_by_identity = {
        (node["admin_mac"], node["admin_ip"]): node for node in targets
    }
    target_identities = [
        (node["admin_mac"], node["admin_ip"]) for node in targets
    ]
    missing_targets = sorted(
        set(target_identities) - set(desired_by_identity)
    )
    if missing_targets:
        errors.append(
            "Retry inventory contains MAC/IP identities absent from the full "
            f"mapping: {missing_targets}"
        )

    stale_ids: set[str] = set()
    boot_updates = []
    protected_macs = {node["admin_mac"] for node in desired if node["admin_mac"]}
    protected_ips = {node["admin_ip"] for node in desired if node["admin_ip"]}

    target_xnames = []
    for identity in target_identities:
        node = desired_by_identity.get(identity)
        if not node:
            continue
        target = target_by_identity[identity]
        exact = [
            entry for entry in live
            if entry["is_node"]
            and entry["mac"] == node["admin_mac"]
            and node["admin_ip"] in entry["ips"]
        ]
        if len(exact) != 1:
            label = node["hostname"] or node["admin_ip"]
            errors.append(
                f"{label}: expected exactly one SMD Node interface for "
                f"{node['admin_mac']} / {node['admin_ip']}, found {len(exact)}"
            )
            continue
        xname = exact[0]["xname"]
        if not xname:
            errors.append(
                f"{node['hostname'] or node['admin_ip']}: exact SMD interface "
                "has no ComponentID"
            )
            continue
        expected_xname = target["xname"] or node["xname"]
        if expected_xname and expected_xname != xname:
            errors.append(
                f"{node['hostname'] or node['admin_ip']}: inventory XNAME "
                f"{expected_xname} does not match SMD owner {xname}"
            )
            continue
        target_xnames.append(xname)
        node_interfaces = [
            entry for entry in live
            if entry["is_node"] and entry["xname"] == xname
        ]

        for entry in node_interfaces:
            if entry is exact[0]:
                continue
            owned_elsewhere = (
                entry["mac"] in (protected_macs - {node["admin_mac"]})
                or bool(entry["ips"] & (protected_ips - {node["admin_ip"]}))
            )
            if owned_elsewhere:
                errors.append(
                    f"{xname}: extra SMD interface {entry['id'] or '<missing ID>'} "
                    "is owned by another current PXE mapping row"
                )
            elif not entry["id"]:
                errors.append(
                    f"{xname}: extra SMD Node interface has no deletion ID"
                )
            else:
                stale_ids.add(entry["id"])

        boot_matches = [entry for entry in boot if entry["xname"] == xname]
        if len(boot_matches) != 1:
            errors.append(
                f"{xname}: expected exactly one Boot Service node, "
                f"found {len(boot_matches)}"
            )
            continue
        boot_node = boot_matches[0]
        if not boot_node["uid"]:
            errors.append(f"{xname}: Boot Service node has no UID")
        elif boot_node["boot_mac"] != node["admin_mac"]:
            boot_updates.append(
                {
                    "uid": boot_node["uid"],
                    "xname": xname,
                    "expected_mac": node["admin_mac"],
                    "observed_mac": boot_node["boot_mac"],
                }
            )

    return {
        "errors": list(dict.fromkeys(errors)),
        "stale_interface_ids": sorted(stale_ids),
        "boot_node_updates": boot_updates,
        "target_xnames": list(dict.fromkeys(target_xnames)),
    }


def main() -> None:
    module = AnsibleModule(
        argument_spec={
            "target_nodes": {"type": "list", "elements": "dict", "required": True},
            "all_nodes": {"type": "list", "elements": "dict", "required": True},
            "interfaces": {"type": "list", "elements": "dict", "required": True},
            "boot_nodes": {"type": "list", "elements": "dict", "required": True},
        },
        supports_check_mode=True,
    )
    result = build_plan(
        module.params["target_nodes"],
        module.params["all_nodes"],
        module.params["interfaces"],
        module.params["boot_nodes"],
    )
    module.exit_json(changed=False, **result)


if __name__ == "__main__":
    main()
