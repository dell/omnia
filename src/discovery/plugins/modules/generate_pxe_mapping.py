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

"""Ansible module to generate PXE mapping file from discovered server inventory."""

import csv
import ipaddress
import os
import re

from ansible.module_utils.basic import AnsibleModule


def _sanitize_csv_value(value: str) -> str:
    """Prefix CSV values that could trigger formula injection in Excel.
    
    Excel interprets cells starting with =, +, -, @, tab, or carriage return
    as formulas. Prefixing with a single quote forces Excel to treat the cell
    as text, preventing formula injection.
    """
    if not value:
        return value
    if value[0] in ('=', '+', '-', '@', '\t', '\r'):
        return "'" + value
    return value

DOCUMENTATION = r'''
---
module: generate_pxe_mapping
short_description: Generate PXE mapping file from server inventory
description:
    - This module generates a PXE mapping CSV file from discovered server
      inventory data collected from OME.
options:
    servers:
        description: List of server dictionaries with inventory details
        required: true
        type: list
    output_file:
        description: Path to the output PXE mapping CSV file
        required: true
        type: str
    functional_group:
        description: Functional group name for all servers
        required: false
        type: str
        default: compute_node
    group_name:
        description: Group name for all servers
        required: false
        type: str
        default: grp0
    hostname_prefix:
        description: Prefix for generated hostnames
        required: false
        type: str
        default: nid
    hostname_start:
        description: Starting number for hostname generation
        required: false
        type: int
        default: 1
    hostname_padding:
        description: Number of digits for hostname padding (must be 3 for orchestrator NID support: nid000-nid999)
        required: false
        type: int
        default: 3
    ib_subnet:
        description: InfiniBand subnet (e.g. 192.168.2.0) used to derive IB_IP from BMC IP last two octets
        required: false
        type: str
        default: ""
    admin_subnet:
        description: Admin network subnet (e.g. 172.16.0.0) - first two octets combined with last two octets of iDRAC IP to derive ADMIN_IP
        required: false
        type: str
        default: ""
author:
    - Dell Inc.
'''

EXAMPLES = r'''
- name: Generate PXE mapping file
  generate_pxe_mapping:
    servers: "{{ discovered_servers }}"
    output_file: "/path/to/pxe_mapping_file.csv"
    functional_group: "compute_node"
    group_name: "grp0"
    hostname_prefix: "nid"
    hostname_start: 1
    hostname_padding: 3
    ib_subnet: "192.168.2.0"
'''

RETURN = r'''
file_path:
    description: Path to the generated PXE mapping file
    type: str
    returned: always
server_count:
    description: Number of servers written to the mapping file
    type: int
    returned: always
'''


DEFAULT_FUNCTIONAL_GROUP = "slurm_node_rhel_10_0_aarch64"
PARENT_TAG_SOURCE_PREFIX = "service_kube_node_"

# Supported functional group role prefixes.
# OME static group names must match one of these prefixes (followed by an
# optional OS version segment and an architecture suffix) to be included
# in the PXE mapping file.
# "fg_" is the flexible functional-group prefix (ER-ORCH-009). Flexible-group
# names (fg_<label>_<os>_<version>_<arch>) are accepted and preserved verbatim
# through the operator-reviewed mapping handoff; Discovery does not interpret
# them further.
SUPPORTED_ROLE_PREFIXES = (
    "service_kube_control_plane_",
    "service_kube_node_",
    "login_node_",
    "login_compiler_node_",
    "slurm_control_node_",
    "slurm_node_",
    "os_",
    "fg_",
)

SUPPORTED_ARCHITECTURES = ("x86_64", "aarch64")

# Pattern to detect architecture suffix (e.g. _x86_64 or _aarch64)
_ARCH_PATTERN = re.compile(r"_(?P<arch>x86_64|aarch64)$")

# Functional group pattern (Omnia 2.3):
# <any_prefix>_rhel_<major>_<minor>_<arch>
#
# This is the MANDATORY format for all functional groups in Omnia 2.3.
# - The prefix can be ANY string (e.g., slurm_node, os, sujal, custom_group)
# - The OS MUST be "rhel"
# - The OS version (major_minor) is REQUIRED
# - The architecture (x86_64 or aarch64) is REQUIRED
#
# Valid examples:
#   slurm_control_node_rhel_10_2_x86_64   OK
#   slurm_node_rhel_10_2_x86_64           OK
#   os_rhel_10_2_x86_64                   OK
#   sujal_rhel_10_0_x86_64                OK  (custom prefix allowed)
#   my_custom_group_rhel_9_4_aarch64      OK  (any prefix allowed)
#
# Invalid examples:
#   slurm_node_rocky_9_4_aarch64          INVALID (only rhel supported)
#   slurm_node_x86_64                     INVALID (missing _rhel_<version>_)
#   slurm_node                            INVALID (missing _rhel_<version>_<arch>)
#
# Pattern regex: ^.+_rhel_\d+_\d+_(x86_64|aarch64)$
_FUNCTIONAL_GROUP_PATTERN = re.compile(
    r'^(.+)_rhel_(\d+)_(\d+)_(x86_64|aarch64)$'
)

# Roles that receive PARENT_SERVICE_TAG (set to a service_kube_node
# service tag from the same Scalable Unit).
# Note: In Omnia 2.3, PARENT_SERVICE_TAG is optional for all groups.
CHILD_ROLE_PREFIXES = ("slurm_node_",)


def _is_supported_functional_group(group_name: str) -> bool:
    """Check if an OME group name matches a supported Omnia role pattern.

    In Omnia 2.3, functional groups MUST follow the pattern:
        <any_prefix>_rhel_<major>_<minor>_<arch>

    The prefix can be ANY string. The mandatory suffix is:
        _rhel_<major>_<minor>_(x86_64|aarch64)

    Valid examples:
        slurm_node_rhel_10_2_x86_64       OK
        os_rhel_10_2_x86_64               OK
        sujal_rhel_10_0_x86_64            OK (custom prefix)
        my_custom_group_rhel_9_4_aarch64  OK (any prefix)

    Invalid examples:
        slurm_node_x86_64                 INVALID (missing _rhel_<version>_)
        slurm_node_rocky_9_4_aarch64      INVALID (only rhel supported)

    Args:
        group_name: The functional group name to validate.

    Returns:
        True if the group name matches the pattern, False otherwise.
    """
    if not group_name:
        return False
    return bool(_FUNCTIONAL_GROUP_PATTERN.match(group_name))


def extract_su_from_hostname(bmc_hostname: str) -> str:
    """
    Extract Scalable Unit (SU) identifier from iDRAC/BMC hostname.
    Supported formats:
      idrac-SUA99R999OU30C2  ->  SUA99
      SU1R2OU1C5             ->  SU1
      idrac-JCGT033          ->  '' (service tag pattern, not an SU hostname)
    The lookahead (?=R\\d+) ensures only genuine SU hostnames match;
    service-tag-only hostnames like idrac-JCGT033 are ignored.
    Returns empty string when no SU pattern is found; caller defaults to grp0.
    """
    if not bmc_hostname:
        return ""
    match = re.search(r'(SU[A-Z]?\d+)(?=R\d+)', bmc_hostname, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return ""


def calculate_admin_ip(admin_subnet: str, bmc_ip: str) -> str:
    """
    Derive admin IP from admin_subnet and BMC IP.
    First two octets come from admin_subnet, last two from bmc_ip.
    Example: admin_subnet=172.16.0.0, bmc_ip=172.16.0.250 -> 172.16.0.250

    Returns an empty string when the inputs are missing or when the
    derived address is not a valid IPv4 address.
    """
    if not admin_subnet or not bmc_ip:
        return ""

    subnet_octets = admin_subnet.split('.')
    bmc_octets = bmc_ip.split('.')
    if len(subnet_octets) != 4 or len(bmc_octets) != 4:
        return ""

    candidate = f"{subnet_octets[0]}.{subnet_octets[1]}.{bmc_octets[2]}.{bmc_octets[3]}"

    # Validate that the derived value is a well-formed IPv4 address.
    # This prevents shell metacharacters or malformed data from propagating
    # into downstream consumers (e.g. /etc/hosts generation).
    try:
        ipaddress.IPv4Address(candidate)
    except (ipaddress.AddressValueError, ValueError):
        return ""

    return candidate


def calculate_ib_ip(ib_subnet: str, bmc_ip: str) -> str:
    """
    Derive IB IP from ib_subnet and the last two octets of bmc_ip.
    Example: ib_subnet=192.168.2.0, bmc_ip=10.5.3.45 -> 192.168.3.45

    Returns an empty string when the inputs are missing or when the
    derived address is not a valid IPv4 address.
    """
    if not ib_subnet or not bmc_ip:
        return ""

    subnet_octets = ib_subnet.split('.')
    bmc_octets = bmc_ip.split('.')
    if len(subnet_octets) != 4 or len(bmc_octets) != 4:
        return ""

    candidate = f"{subnet_octets[0]}.{subnet_octets[1]}.{bmc_octets[2]}.{bmc_octets[3]}"

    try:
        ipaddress.IPv4Address(candidate)
    except (ipaddress.AddressValueError, ValueError):
        return ""

    return candidate


def generate_hostname(prefix: str, number: int, padding: int) -> str:
    """Generate hostname with zero-padded number."""
    return f"{prefix}{str(number).zfill(padding)}"


def main() -> None:
    """Main function for the Ansible module."""
    module_args = {
        "servers": {"type": "list", "required": True},
        "output_file": {"type": "str", "required": True},
        "functional_group": {"type": "str", "required": False, "default": DEFAULT_FUNCTIONAL_GROUP},
        "group_name": {"type": "str", "required": False, "default": "grp0"},
        "hostname_prefix": {"type": "str", "required": False, "default": "nid"},
        "hostname_start": {"type": "int", "required": False, "default": 1},
        "hostname_padding": {"type": "int", "required": False, "default": 3},
        "ib_subnet": {"type": "str", "required": False, "default": ""},
        "admin_subnet": {"type": "str", "required": False, "default": ""},
    }

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    servers = module.params['servers']
    output_file = module.params['output_file']
    group_name = module.params['group_name']
    hostname_prefix = module.params['hostname_prefix']
    hostname_start = module.params['hostname_start']
    hostname_padding = module.params['hostname_padding']
    ib_subnet = module.params['ib_subnet']
    admin_subnet = module.params['admin_subnet']

    # CSV headers as specified
    headers = [
        "FUNCTIONAL_GROUP_NAME",
        "GROUP_NAME",
        "SERVICE_TAG",
        "PARENT_SERVICE_TAG",
        "HOSTNAME",
        "ADMIN_MAC",
        "ADMIN_IP",
        "BMC_MAC",
        "BMC_IP",
        "IB_NIC_NAME",
        "IB_IP"
    ]

    if module.check_mode:
        module.exit_json(changed=True, file_path=output_file, server_count=len(servers))

    try:
        # Ensure output directory exists
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, mode=0o755)

        # Generate PXE mapping rows
        rows = []
        for idx, server in enumerate(servers):
            hostname_num = hostname_start + idx
            hostname = generate_hostname(hostname_prefix, hostname_num, hostname_padding)
            bmc_ip = server.get('idrac_ip', '')
            bmc_hostname = server.get('idrac_hostname', '')
            ib_nic_name = server.get('ib_nic_name', '')
            admin_ip = calculate_admin_ip(admin_subnet, bmc_ip)
            ib_ip = calculate_ib_ip(ib_subnet, bmc_ip) if ib_nic_name else ""

            # Use group_name from OME if available, else fall back to module param default
            server_group = server.get('group_name', '').strip()

            # Servers with invalid OME groups fall back to default functional group
            # In Omnia 2.3, functional groups must follow: <prefix>_rhel_<major>_<minor>_<arch>
            if server_group and not _is_supported_functional_group(server_group):
                svc_tag = server.get('service_tag', 'unknown')
                module.warn(
                    f"Device {svc_tag}: OME static group '{server_group}' "
                    f"is not a valid Omnia 2.3 functional group. "
                    f"Required pattern: <prefix>_rhel_<major>_<minor>_(x86_64|aarch64). "
                    f"Adding to default functional group: {DEFAULT_FUNCTIONAL_GROUP}"
                )
                server_group = ""  # Clear to use default functional group

            # Use OME static group if valid, otherwise use fixed default
            # No catalog dependency - default is always slurm_node_rhel_10_0_aarch64
            resolved_functional_group = server_group if server_group else DEFAULT_FUNCTIONAL_GROUP

            # Derive GROUP_NAME: try SU from BMC hostname first,
            # then from OME group name, then fall back to module default (grp0)
            su_name = extract_su_from_hostname(bmc_hostname)
            if not su_name:
                su_name = extract_su_from_hostname(server_group)
            resolved_group_name = su_name if su_name else group_name

            row = {
                "FUNCTIONAL_GROUP_NAME": _sanitize_csv_value(resolved_functional_group),
                "GROUP_NAME": _sanitize_csv_value(resolved_group_name),
                "SERVICE_TAG": _sanitize_csv_value(server.get('service_tag', '')),
                "PARENT_SERVICE_TAG": "",
                "HOSTNAME": _sanitize_csv_value(hostname),
                "ADMIN_MAC": _sanitize_csv_value(server.get('first_nic_mac', '')),
                "ADMIN_IP": _sanitize_csv_value(admin_ip),
                "BMC_MAC": _sanitize_csv_value(server.get('idrac_mac', '')),
                "BMC_IP": _sanitize_csv_value(bmc_ip),
                "IB_NIC_NAME": _sanitize_csv_value(ib_nic_name),
                "IB_IP": _sanitize_csv_value(ib_ip)
            }
            rows.append(row)

        # Build SU -> service_kube_node service tag map
        su_kube_node_map = {}
        for row in rows:
            if row["FUNCTIONAL_GROUP_NAME"].startswith(PARENT_TAG_SOURCE_PREFIX):
                su = row["GROUP_NAME"]
                if su and su not in su_kube_node_map:
                    su_kube_node_map[su] = row["SERVICE_TAG"]

        # Assign PARENT_SERVICE_TAG only to slurm_node roles,
        # using a service_kube_node service tag from the same GROUP_NAME
        for row in rows:
            if not any(
                row["FUNCTIONAL_GROUP_NAME"].startswith(p)
                for p in CHILD_ROLE_PREFIXES
            ):
                continue
            su = row["GROUP_NAME"]
            if su in su_kube_node_map:
                row["PARENT_SERVICE_TAG"] = su_kube_node_map[su]

        # Write CSV file
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)

        module.exit_json(
            changed=True,
            file_path=output_file,
            server_count=len(rows),
            msg=f"Successfully generated PXE mapping file with {len(rows)} servers"
        )

    except Exception as e:  # pylint: disable=broad-except
        module.fail_json(msg=f"Error generating PXE mapping file: {str(e)}")


if __name__ == '__main__':
    main()
