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
import os
import re
from ansible.module_utils.basic import AnsibleModule

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
        description: Number of digits for hostname padding
        required: false
        type: int
        default: 5
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
    hostname_padding: 5
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


DEFAULT_FUNCTIONAL_GROUP = "slurm_node_aarch64"
SERVICE_CONTROL_PLANE_GROUP = "service_kube_control_plane_x86_64"


def extract_su_from_hostname(bmc_hostname):
    """
    Extract Scalable Unit (SU) identifier from iDRAC/BMC hostname.
    Supported formats:
      idrac-SUA99R999OU30C2  ->  SUA99
      SU1R2OU1C5             ->  SU1
      idrac-JCGT033          ->  '' (service tag pattern, not an SU hostname)
    The lookahead (?=R\d+) ensures only genuine SU hostnames match;
    service-tag-only hostnames like idrac-JCGT033 are ignored.
    Returns empty string when no SU pattern is found; caller defaults to grp0.
    """
    if not bmc_hostname:
        return ""
    match = re.search(r'(SU[A-Z]?\d+)(?=R\d+)', bmc_hostname, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return ""


def calculate_admin_ip(admin_subnet, bmc_ip):
    """
    Derive admin IP from admin_subnet and BMC IP.
    First two octets come from admin_subnet, last two from bmc_ip.
    Example: admin_subnet=172.16.0.0, bmc_ip=172.16.0.250 -> 172.16.0.250
    """
    if not admin_subnet or not bmc_ip:
        return ""

    subnet_octets = admin_subnet.split('.')
    bmc_octets = bmc_ip.split('.')
    if len(subnet_octets) != 4 or len(bmc_octets) != 4:
        return ""

    return f"{subnet_octets[0]}.{subnet_octets[1]}.{bmc_octets[2]}.{bmc_octets[3]}"


def calculate_ib_ip(ib_subnet, bmc_ip):
    """
    Derive IB IP from ib_subnet and the last two octets of bmc_ip.
    Example: ib_subnet=192.168.2.0, bmc_ip=10.5.3.45 -> 192.168.3.45
    """
    if not ib_subnet or not bmc_ip:
        return ""

    subnet_octets = ib_subnet.split('.')
    bmc_octets = bmc_ip.split('.')
    if len(subnet_octets) != 4 or len(bmc_octets) != 4:
        return ""

    return f"{subnet_octets[0]}.{subnet_octets[1]}.{bmc_octets[2]}.{bmc_octets[3]}"


def generate_hostname(prefix, number, padding):
    """Generate hostname with zero-padded number."""
    return f"{prefix}{str(number).zfill(padding)}"


def main():
    """Main function for the Ansible module."""
    module_args = {
        "servers": {"type": "list", "required": True},
        "output_file": {"type": "str", "required": True},
        "functional_group": {"type": "str", "required": False, "default": DEFAULT_FUNCTIONAL_GROUP},
        "group_name": {"type": "str", "required": False, "default": "grp0"},
        "hostname_prefix": {"type": "str", "required": False, "default": "nid"},
        "hostname_start": {"type": "int", "required": False, "default": 1},
        "hostname_padding": {"type": "int", "required": False, "default": 5},
        "ib_subnet": {"type": "str", "required": False, "default": ""},
        "admin_subnet": {"type": "str", "required": False, "default": ""}
    }

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    servers = module.params['servers']
    output_file = module.params['output_file']
    functional_group = module.params['functional_group']
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
        "IB_MAC",
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
            ib_mac = server.get('ib_nic_mac', '')
            admin_ip = calculate_admin_ip(admin_subnet, bmc_ip)
            ib_ip = calculate_ib_ip(ib_subnet, bmc_ip) if ib_mac else ""

            # Use group_name from OME if available, else fall back to module param default
            server_group = server.get('group_name', '').strip()
            resolved_functional_group = server_group if server_group else functional_group

            # Derive GROUP_NAME from SU extracted from BMC hostname
            su_name = extract_su_from_hostname(bmc_hostname)
            resolved_group_name = su_name if su_name else group_name

            row = {
                "FUNCTIONAL_GROUP_NAME": resolved_functional_group,
                "GROUP_NAME": resolved_group_name,
                "SERVICE_TAG": server.get('service_tag', ''),
                "PARENT_SERVICE_TAG": "",
                "HOSTNAME": hostname,
                "ADMIN_MAC": server.get('first_nic_mac', ''),
                "ADMIN_IP": admin_ip,
                "BMC_MAC": server.get('idrac_mac', ''),
                "BMC_IP": bmc_ip,
                "IB_MAC": ib_mac,
                "IB_IP": ib_ip
            }
            rows.append(row)

        # Build SU -> control plane service tag map
        su_control_plane_map = {}
        for row in rows:
            if row["FUNCTIONAL_GROUP_NAME"] == SERVICE_CONTROL_PLANE_GROUP:
                su = row["GROUP_NAME"]
                if su and su not in su_control_plane_map:
                    su_control_plane_map[su] = row["SERVICE_TAG"]

        # Assign PARENT_SERVICE_TAG from control plane node of the same SU
        for row in rows:
            su = row["GROUP_NAME"]
            if su in su_control_plane_map:
                row["PARENT_SERVICE_TAG"] = su_control_plane_map[su]

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
