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

# Regex for a valid GROUP_NAME in the PXE mapping (grp0-grp100 or SU[A-Z]?1-100).
GROUP_NAME_RE = re.compile(
    r"^(?:grp(?:[0-9]|[1-9][0-9]|100)|[Ss][Uu][A-Za-z]?(?:0*[1-9][0-9]?|100))$"
)

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
    admin_subnets:
        description: List of admin network CIDR entries. Each entry contains 'subnet' and 'netmask_bits'. The entry whose CIDR contains the constructed admin IP is selected (longest-prefix match).
        required: false
        type: list
        default: []
    ib_subnet:
        description: InfiniBand subnet (e.g. 192.168.2.0) used to derive IB_IP from BMC IP last two octets
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
    admin_subnets:
      - subnet: "172.16.107.0"
        netmask_bits: "24"
      - subnet: "172.16.108.0"
        netmask_bits: "24"
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
PARENT_TAG_SOURCE_GROUP = "service_kube_node_x86_64"

# Omnia-supported functional group names.
# Only servers whose OME static group matches one of these will be
# included in the PXE mapping file.
SUPPORTED_FUNCTIONAL_GROUPS = {
    "service_kube_control_plane_x86_64",
    "service_kube_node_x86_64",
    "login_node_x86_64",
    "login_node_aarch64",
    "login_compiler_node_x86_64",
    "login_compiler_node_aarch64",
    "slurm_control_node_x86_64",
    "slurm_node_x86_64",
    "slurm_node_aarch64",
    "os_x86_64",
    "os_aarch64",
}

# Roles that receive PARENT_SERVICE_TAG (set to a service_kube_node_x86_64
# service tag from the same Scalable Unit).
CHILD_ROLES_WITH_PARENT_TAG = {
    "slurm_node_aarch64",
    "slurm_node_x86_64",
}


def extract_su_from_hostname(bmc_hostname):
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


def _candidate_ip_from_network(bmc_ip, subnet_str):
    """Build a candidate IP using the first two octets of a network and the last two of the BMC IP."""
    bmc_octets = bmc_ip.split('.')
    subnet_octets = subnet_str.split('.')
    if len(bmc_octets) != 4 or len(subnet_octets) != 4:
        return ""
    return f"{subnet_octets[0]}.{subnet_octets[1]}.{bmc_octets[2]}.{bmc_octets[3]}"


def resolve_admin_ip(bmc_ip, admin_subnets):
    """
    Derive admin IP from a BMC IP using the best matching admin subnet CIDR.

    Each admin_subnet entry is a dict with 'subnet' (network address) and
    'netmask_bits'. The candidate admin IP is built from the first two octets
    of the admin subnet and the last two octets of the BMC IP. The candidate
    falling inside the most specific (longest prefix) matching CIDR wins.

    If no CIDR matches, an empty string is returned so the caller can detect a
    configuration mismatch.
    """
    if not bmc_ip or not admin_subnets:
        return ""

    bmc_octets = bmc_ip.split('.')
    if len(bmc_octets) != 4:
        return ""

    best_match = ""
    best_prefix = -1
    for entry in admin_subnets:
        subnet_str = entry.get("subnet", "") if isinstance(entry, dict) else str(entry)
        netmask_bits = entry.get("netmask_bits", "") if isinstance(entry, dict) else ""
        if not subnet_str or not netmask_bits:
            continue

        try:
            network = ipaddress.ip_network(f"{subnet_str}/{netmask_bits}", strict=False)
        except (ValueError, TypeError):
            continue

        candidate_str = _candidate_ip_from_network(bmc_ip, subnet_str)
        if not candidate_str:
            continue

        try:
            candidate = ipaddress.ip_address(candidate_str)
        except (ValueError, TypeError):
            continue

        if candidate in network and network.prefixlen > best_prefix:
            best_match = candidate_str
            best_prefix = network.prefixlen

    return best_match


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
        "admin_subnets": {"type": "list", "required": False, "default": []}
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
    admin_subnets = module.params['admin_subnets']

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
            admin_ip = resolve_admin_ip(bmc_ip, admin_subnets)
            ib_ip = calculate_ib_ip(ib_subnet, bmc_ip) if ib_nic_name else ""

            # Per-server optional values from inventory (Magellan) vs OME group (OME).
            # If the inventory source provides both, functional_group takes precedence for
            # FUNCTIONAL_GROUP_NAME and group_name for GROUP_NAME.
            server_functional_group = server.get('functional_group', '').strip()
            server_group_name = server.get('group_name', '').strip()

            # OME stores the static/functional group in 'group_name'. If a per-server
            # functional_group is absent and group_name is not a valid GROUP_NAME,
            # treat group_name as the functional group for backward compatibility.
            if not server_functional_group and not GROUP_NAME_RE.match(server_group_name):
                server_functional_group = server_group_name

            # Resolve the functional group: per-server value wins, then module default.
            resolved_functional_group = server_functional_group if server_functional_group else functional_group

            # Validate the functional group that will actually be written.
            if resolved_functional_group not in SUPPORTED_FUNCTIONAL_GROUPS:
                svc_tag = server.get('service_tag', 'unknown')
                module.warn(
                    f"Skipping device {svc_tag}: functional group '{resolved_functional_group}' "
                    f"is not a supported Omnia functional group. "
                    f"Supported groups: {', '.join(sorted(SUPPORTED_FUNCTIONAL_GROUPS))}"
                )
                continue

            # Derive GROUP_NAME. Prefer an explicit per-server group_name that matches
            # the valid GROUP_NAME format, then extract an SU from the BMC hostname,
            # then from the per-server functional group string, then fall back to the
            # module-level group_name default.
            if server_group_name and GROUP_NAME_RE.match(server_group_name):
                resolved_group_name = server_group_name
            else:
                su_name = extract_su_from_hostname(bmc_hostname)
                if not su_name:
                    su_name = extract_su_from_hostname(server_functional_group)
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
                "IB_NIC_NAME": ib_nic_name,
                "IB_IP": ib_ip
            }
            rows.append(row)

        # Build SU -> service_kube_node service tag map
        su_kube_node_map = {}
        for row in rows:
            if row["FUNCTIONAL_GROUP_NAME"] == PARENT_TAG_SOURCE_GROUP:
                su = row["GROUP_NAME"]
                if su and su not in su_kube_node_map:
                    su_kube_node_map[su] = row["SERVICE_TAG"]

        # Assign PARENT_SERVICE_TAG only to slurm_node roles,
        # using a service_kube_node_x86_64 service tag from the same GROUP_NAME
        for row in rows:
            if row["FUNCTIONAL_GROUP_NAME"] not in CHILD_ROLES_WITH_PARENT_TAG:
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
