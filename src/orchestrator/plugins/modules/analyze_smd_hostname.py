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

"""Validate desired node hostnames against SMD and metadata-service state."""

from __future__ import annotations

import re
from typing import Any

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.smd_utils import interface_ips
from ansible.module_utils.smd_utils import is_node_interface


HOSTNAME_PATTERN = re.compile(r"^[a-z](?:[a-z0-9-]{0,61}[a-z0-9])?$")


DOCUMENTATION = r"""
---
module: analyze_smd_hostname
short_description: Validate prepared OpenCHAMI hostname state
version_added: "2.3.0"
description:
  - Resolves each desired node through its administrative IP address.
  - Validates the SMD Interface 0 description and metadata-service hostname.
  - Does not contact a provisioned node or mutate OpenCHAMI state.
author:
  - Dell Omnia Team
options:
  desired_nodes:
    description: PXE mapping rows containing ADMIN_IP and HOSTNAME.
    required: true
    type: list
    elements: dict
  interfaces:
    description: Objects returned by the SMD EthernetInterfaces API.
    required: true
    type: list
    elements: dict
  instanceinfos:
    description: Objects returned by the metadata-service instanceinfos API.
    required: true
    type: list
    elements: dict
  domain_name:
    description: Domain appended to the desired short hostname.
    required: false
    type: str
    default: ''
"""

EXAMPLES = r"""
- name: Validate prepared hostname state
  analyze_smd_hostname:
    desired_nodes: "{{ mapping_nodes }}"
    interfaces: "{{ smd_interfaces.json }}"
    instanceinfos: "{{ metadata_instanceinfos.json }}"
    domain_name: "{{ domain_name }}"
  register: hostname_state
"""

RETURN = r"""
errors:
  description: Hostname-state validation errors.
  type: list
  elements: str
  returned: always
resolved_nodes:
  description: Desired nodes resolved to their live SMD component IDs.
  type: list
  elements: dict
  returned: always
"""


def _normalize_name(value: Any) -> str:
    """Trim a hostname or FQDN while preserving its configured value."""
    return str(value or "").strip()


def _expected_fqdn(hostname: str, domain_name: str) -> str:
    """Build the normalized hostname stored in metadata-service."""
    normalized_hostname = _normalize_name(hostname)
    normalized_domain = _normalize_name(domain_name)
    if not normalized_domain:
        return normalized_hostname
    return f"{normalized_hostname}.{normalized_domain}"


def _comparison_errors(
    label: str, comparisons: tuple[tuple[str, str, str], ...]
) -> list[str]:
    """Return errors for metadata fields that differ from desired state."""
    return [
        f"{label}: metadata {field} expected {expected}, "
        f"found {actual or '<missing>'}"
        for field, actual, expected in comparisons
        if actual != expected
    ]


def _metadata_errors(
    instanceinfos: list[dict[str, Any]],
    live_xname: str,
    label: str,
    expected_hostname: str,
) -> list[str]:
    """Return metadata identity and hostname errors for one desired node."""
    matches = [
        record
        for record in instanceinfos
        if (
            str((record.get("spec") or {}).get("instance_id", "") or "").strip()
            == live_xname
            or str((record.get("metadata") or {}).get("name", "") or "").strip()
            == live_xname
        )
    ]
    if len(matches) != 1:
        return [
            f"{label}: xname {live_xname} has {len(matches)} "
            "metadata-service instanceinfos; expected exactly one"
        ]

    metadata = matches[0].get("metadata") or {}
    metadata_spec = matches[0].get("spec") or {}
    return _comparison_errors(
        label,
        (
            ("name", str(metadata.get("name", "") or "").strip(), live_xname),
            (
                "instance_id",
                str(metadata_spec.get("instance_id", "") or "").strip(),
                live_xname,
            ),
            (
                "hostname",
                _normalize_name(metadata_spec.get("hostname", "")),
                expected_hostname,
            ),
            (
                "local_hostname",
                _normalize_name(metadata_spec.get("local_hostname", "")),
                expected_hostname,
            ),
        ),
    )


def _interface_state(
    interfaces: list[dict[str, Any]],
    admin_ip: str,
    hostname: str,
    desired_xname: str,
    label: str,
) -> tuple[str, list[str]]:
    """Resolve one desired node and validate its SMD hostname identity."""
    matches = [
        interface
        for interface in interfaces
        if is_node_interface(interface)
        and admin_ip in interface_ips(interface)
    ]
    if len(matches) != 1:
        return "", [
            f"{label}: ADMIN_IP {admin_ip} resolves to {len(matches)} "
            "SMD Node interfaces; expected exactly one"
        ]

    interface = matches[0]
    live_xname = str(interface.get("ComponentID", "") or "").strip()
    if not live_xname:
        return "", [
            f"{label}: SMD interface for ADMIN_IP {admin_ip} has no ComponentID"
        ]

    errors = []
    if desired_xname and desired_xname != live_xname:
        errors.append(
            f"{label}: expected SMD ComponentID {desired_xname}, found {live_xname}"
        )
    expected_description = f"Interface 0 for {hostname}"
    actual_description = str(interface.get("Description", "") or "").strip()
    if actual_description != expected_description:
        errors.append(
            f"{label}: expected SMD interface description "
            f"'{expected_description}', found '{actual_description or '<missing>'}'"
        )
    return live_xname, errors


def analyze_smd_hostname(
    desired_nodes: list[dict[str, Any]],
    interfaces: list[dict[str, Any]],
    instanceinfos: list[dict[str, Any]],
    domain_name: str = "",
) -> dict[str, Any]:
    """Return exact SMD and metadata hostname validation results."""
    errors: list[str] = []
    resolved_nodes: list[dict[str, str]] = []

    for node in desired_nodes:
        admin_ip = str(node.get("ADMIN_IP", "") or "").strip()
        hostname = _normalize_name(node.get("HOSTNAME", ""))
        desired_xname = str(node.get("XNAME", "") or "").strip()
        label = hostname or desired_xname or admin_ip or "<unknown>"

        if not admin_ip or not hostname:
            errors.append(
                f"{label}: ADMIN_IP and HOSTNAME are required for hostname validation"
            )
            continue
        if not HOSTNAME_PATTERN.fullmatch(hostname):
            errors.append(
                f"{label}: HOSTNAME must be a lowercase short hostname label"
            )
            continue

        live_xname, interface_errors = _interface_state(
            interfaces, admin_ip, hostname, desired_xname, label
        )
        errors.extend(interface_errors)
        if not live_xname:
            continue

        expected_hostname = _expected_fqdn(hostname, domain_name)
        errors.extend(
            _metadata_errors(
                instanceinfos,
                live_xname,
                label,
                expected_hostname,
            )
        )

        resolved_nodes.append(
            {
                "admin_ip": admin_ip,
                "hostname": hostname,
                "xname": live_xname,
            }
        )

    return {"errors": errors, "resolved_nodes": resolved_nodes}


def main() -> None:
    """Execute the Ansible module."""
    module = AnsibleModule(
        argument_spec={
            "desired_nodes": {"type": "list", "elements": "dict", "required": True},
            "interfaces": {"type": "list", "elements": "dict", "required": True},
            "instanceinfos": {"type": "list", "elements": "dict", "required": True},
            "domain_name": {"type": "str", "default": ""},
        },
        supports_check_mode=True,
    )
    result = analyze_smd_hostname(
        module.params["desired_nodes"],
        module.params["interfaces"],
        module.params["instanceinfos"],
        module.params["domain_name"],
    )
    module.exit_json(changed=False, **result)


if __name__ == "__main__":
    main()
