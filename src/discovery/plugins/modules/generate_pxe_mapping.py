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
        description: InfiniBand IPv4 subnet (e.g. 192.168.2.0) used to derive IB_IPV4 from BMC IP last two octets
        required: false
        type: str
        default: ""
    ipv6_subnet:
        description: InfiniBand IPv6 subnet (e.g. fd00:1b::) used to derive IB_IPV6 from BMC IP last two octets
        required: false
        type: str
        default: ""
    admin_subnet:
        description: Admin network subnet (e.g. 172.16.0.0) - first two octets combined with last two octets of iDRAC IP to derive ADMIN_IP
        required: false
        type: str
        default: ""
    os_type:
        description: Target OS type used to inject OS identity into unversioned functional groups
        required: false
        type: str
        default: "rhel"
    os_version:
        description: Target OS version used to inject OS identity into unversioned functional groups
        required: false
        type: str
        default: "10_0"
    omit_invalid_groups:
        description: Whether to omit servers with invalid functional group names instead of falling back
        required: false
        type: bool
        default: false
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
    ipv6_subnet: "fd00:1b::"
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
rejected_servers:
    description: List of servers whose OME groups were invalid, with truthful rejection evidence
    type: list
    returned: always
omitted_servers:
    description: List of servers omitted from output due to invalid functional group when omit_invalid_groups is true
    type: list
    returned: always
'''


DEFAULT_FUNCTIONAL_GROUP = "slurm_node_rhel_10_0_aarch64"
PARENT_TAG_SOURCE_PREFIX = "service_kube_node_"

# Supported architectures in functional group names
SUPPORTED_ARCHITECTURES = ("x86_64", "aarch64")

# Pattern to detect architecture suffix (e.g. _x86_64 or _aarch64)
_ARCH_PATTERN = re.compile(r"_(?P<arch>x86_64|aarch64)$")

PREDEFINED_ROLE_PREFIXES = (
    "service_kube_",
    "slurm_",
    "login_node_",
    "login_compiler_node_",
    "os_",
)
FLEXIBLE_ROLE_PREFIX = "fg_"

KNOWN_OTHER_ARCHS = {
    "ppc64le",
    "ppc64",
    "arm",
    "arm64",
    "aarch32",
    "riscv64",
    "riscv",
    "i386",
    "i686",
    "x86",
    "s390x",
    "noarch",
}

# Versioned flexible group pattern: fg_<label>_<os>_<version>_<arch>
_FLEXIBLE_GROUP_VERSIONED_PATTERN = re.compile(
    r"^fg_(?P<label>[a-zA-Z0-9_-]+)_(?P<os>[a-z]+)_"
    r"(?P<version>[0-9]+(?:_[0-9]+)*)_(?P<arch>x86_64|aarch64)$"
)

# Unversioned flexible group pattern: fg_<label>_<arch>
_FLEXIBLE_GROUP_UNVERSIONED_PATTERN = re.compile(
    r"^fg_(?P<label>[a-zA-Z0-9_-]+)_(?P<arch>x86_64|aarch64)$"
)

# Predefined role versioned pattern
_PREDEFINED_GROUP_VERSIONED_PATTERN = re.compile(
    r"^(?P<role>[a-zA-Z0-9_-]+)_(?P<os>rhel|rocky|ubuntu|sles)_"
    r"(?P<version>[0-9]+(?:_[0-9]+)*)_(?P<arch>x86_64|aarch64)$"
)

# Predefined role unversioned pattern
_PREDEFINED_GROUP_UNVERSIONED_PATTERN = re.compile(
    r"^(?P<role>[a-zA-Z0-9_-]+)_(?P<arch>x86_64|aarch64)$"
)

# Roles that receive PARENT_SERVICE_TAG (set to a service_kube_node
# service tag from the same Scalable Unit).
# Note: In Omnia 2.3, PARENT_SERVICE_TAG is optional for all groups.
CHILD_ROLE_PREFIXES = ("slurm_node_",)


def resolve_functional_group(
    group_name: str,
    os_type: str = "rhel",
    os_version: str = "10_0",
) -> tuple[bool, str, str]:
    """Validate and resolve functional group identity.

    Supports:
    - Predefined groups (e.g. slurm_node_rhel_10_2_x86_64 or unversioned slurm_node_x86_64)
    - Flexible groups with mandatory 'fg_' prefix:
      - Already versioned: fg_<label>_<os>_<version>_<arch> (preserved as-is)
      - Unversioned: fg_<label>_<arch> (injects os_type and os_version)
    - Rejects invalid prefixes (non-predefined groups without 'fg_' prefix)
    - Rejects invalid or missing architecture suffixes (must be x86_64 or aarch64)

    Args:
        group_name: OME group name candidate.
        os_type: Target OS type (e.g. 'rhel').
        os_version: Target OS version (e.g. '10_0' or '10.0').

    Returns:
        Tuple of (is_valid, resolved_group_name, error_reason).
    """
    if not group_name:
        return False, "", "Functional group name is empty"

    os_type = (os_type or "rhel").strip().lower()
    os_version = (os_version or "10_0").strip().replace(".", "_")

    # 1. Flexible functional group (mandatory 'fg_' prefix)
    if group_name.startswith(FLEXIBLE_ROLE_PREFIX):
        # Check if already versioned: fg_<label>_<os>_<version>_<arch>
        match_versioned = _FLEXIBLE_GROUP_VERSIONED_PATTERN.match(group_name)
        if match_versioned:
            return True, group_name, ""

        # Check if unversioned: fg_<label>_<arch>
        match_unversioned = _FLEXIBLE_GROUP_UNVERSIONED_PATTERN.match(group_name)
        if match_unversioned:
            arch = match_unversioned.group("arch")
            label = match_unversioned.group("label")
            resolved = f"fg_{label}_{os_type}_{os_version}_{arch}"
            return True, resolved, ""

        # Failed both patterns: inspect reason for failure
        tokens = group_name.split("_")
        last_token = tokens[-1].lower() if tokens else ""
        if last_token in KNOWN_OTHER_ARCHS:
            return (
                False,
                "",
                f"Unsupported architecture suffix '{tokens[-1]}' in flexible group '{group_name}'; "
                f"must be one of {list(SUPPORTED_ARCHITECTURES)}",
            )
        return (
            False,
            "",
            f"Flexible group '{group_name}' is missing required architecture suffix; "
            f"must end with '_x86_64' or '_aarch64'",
        )

    # 2. Predefined functional group
    if any(group_name.startswith(p) for p in PREDEFINED_ROLE_PREFIXES):
        match_pre_ver = _PREDEFINED_GROUP_VERSIONED_PATTERN.match(group_name)
        if match_pre_ver:
            return True, group_name, ""

        match_pre_unver = _PREDEFINED_GROUP_UNVERSIONED_PATTERN.match(group_name)
        if match_pre_unver:
            arch = match_pre_unver.group("arch")
            role = match_pre_unver.group("role")
            resolved = f"{role}_{os_type}_{os_version}_{arch}"
            return True, resolved, ""

        tokens = group_name.split("_")
        last_token = tokens[-1].lower() if tokens else ""
        if last_token in KNOWN_OTHER_ARCHS:
            return (
                False,
                "",
                f"Unsupported architecture suffix '{tokens[-1]}' "
                f"in predefined group '{group_name}'",
            )
        return (
            False,
            "",
            f"Predefined group '{group_name}' is missing required architecture suffix",
        )

    # 3. Not predefined and does not have fg_ prefix
    return (
        False,
        "",
        f"Group '{group_name}' is missing mandatory 'fg_' prefix for flexible functional groups",
    )


def _is_supported_functional_group(group_name: str) -> bool:
    """Check if an OME group name matches a supported Omnia role pattern.

    In Omnia 2.3, functional groups MUST follow:
    - Predefined role: <predefined_prefix>_<os>_<version>_<arch>
    - Flexible role: fg_<label>_<os>_<version>_<arch>

    Args:
        group_name: The functional group name to validate.

    Returns:
        True if the group name matches a valid versioned pattern, False otherwise.
    """
    if not group_name:
        return False
    is_valid, resolved, _ = resolve_functional_group(group_name)
    return is_valid and resolved == group_name


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


def calculate_ib_ipv6(ipv6_subnet: str, bmc_ip: str) -> str:
    """
    Derive IB IPv6 from ipv6_subnet and the last two octets of bmc_ip.
    Example: ipv6_subnet=fd00:1b::, bmc_ip=10.5.3.45 -> fd00:1b::3:2d

    The host portion is formed by combining the third BMC octet as the
    penultimate 16-bit group and the fourth octet as the last group,
    then adding to the prefix address.

    Returns an empty string when the inputs are missing or when the
    derived address is not a valid IPv6 address.
    """
    if not ipv6_subnet or not bmc_ip:
        return ""

    bmc_octets = bmc_ip.split('.')
    if len(bmc_octets) != 4:
        return ""

    try:
        prefix_addr = ipaddress.IPv6Address(ipv6_subnet)
    except (ipaddress.AddressValueError, ValueError):
        return ""

    try:
        host_part = int(bmc_octets[2]) * 256 + int(bmc_octets[3])
        candidate = prefix_addr + host_part
        return str(candidate)
    except (ValueError, ipaddress.AddressValueError):
        return ""


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
        "ipv6_subnet": {"type": "str", "required": False, "default": ""},
        "admin_subnet": {"type": "str", "required": False, "default": ""},
        "os_type": {"type": "str", "required": False, "default": "rhel"},
        "os_version": {"type": "str", "required": False, "default": "10_0"},
        "omit_invalid_groups": {"type": "bool", "required": False, "default": False},
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
    ipv6_subnet = module.params['ipv6_subnet']
    admin_subnet = module.params['admin_subnet']
    os_type = module.params['os_type'] or "rhel"
    os_version = module.params['os_version'] or "10_0"
    omit_invalid_groups = module.params['omit_invalid_groups']

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
        "IB_IPV4",
        "IB_IPV6"
    ]

    if module.check_mode:
        module.exit_json(
            changed=True,
            file_path=output_file,
            server_count=len(servers),
            rejected_servers=[],
            omitted_servers=[],
        )

    try:
        # Ensure output directory exists
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, mode=0o755)

        # Generate PXE mapping rows
        rows = []
        rejected_servers = []
        omitted_servers = []
        for idx, server in enumerate(servers):
            hostname_num = hostname_start + idx
            hostname = generate_hostname(hostname_prefix, hostname_num, hostname_padding)
            bmc_ip = server.get('idrac_ip', '')
            bmc_hostname = server.get('idrac_hostname', '')
            ib_nic_name = server.get('ib_nic_name', '')
            admin_ip = calculate_admin_ip(admin_subnet, bmc_ip)
            ib_ipv4 = calculate_ib_ip(ib_subnet, bmc_ip) if ib_nic_name else ""
            ib_ipv6 = calculate_ib_ipv6(ipv6_subnet, bmc_ip) if ib_nic_name else ""

            server_group = server.get('group_name', '').strip()
            fallback_fg = functional_group or DEFAULT_FUNCTIONAL_GROUP

            if server_group:
                is_valid, resolved_group, error_reason = resolve_functional_group(
                    server_group, os_type=os_type, os_version=os_version
                )
                if not is_valid:
                    svc_tag = server.get('service_tag', 'unknown')
                    module.warn(
                        f"Device {svc_tag}: OME static group '{server_group}' "
                        f"is not a valid functional group ({error_reason}). "
                        f"Adding to default functional group: {fallback_fg}"
                    )
                    rejection_entry = {
                        "service_tag": svc_tag,
                        "group_name": server_group,
                        "reason": error_reason,
                    }
                    rejected_servers.append(rejection_entry)
                    if omit_invalid_groups:
                        omitted_servers.append(rejection_entry)
                        continue
                    resolved_functional_group = fallback_fg
                else:
                    resolved_functional_group = resolved_group
            else:
                resolved_functional_group = fallback_fg

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
                "IB_IPV4": _sanitize_csv_value(ib_ipv4),
                "IB_IPV6": _sanitize_csv_value(ib_ipv6)
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

        # Write CSV file with secure permissions (0640: owner rw, group r, no other).
        # The file contains sensitive node inventory data (MAC addresses, BMC IPs,
        # IB addresses, service tags) and must not be world-readable.
        # Use fchmod after open so the mode is enforced even when the file
        # already exists (O_CREAT mode is only applied on creation).
        fd = os.open(output_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o640)
        try:
            os.fchmod(fd, 0o640)
        except Exception:
            os.close(fd)
            raise
        with os.fdopen(fd, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)

        module.exit_json(
            changed=True,
            file_path=output_file,
            server_count=len(rows),
            rejected_servers=rejected_servers,
            omitted_servers=omitted_servers,
            msg=f"Successfully generated PXE mapping file with {len(rows)} servers"
        )

    except Exception as e:  # pylint: disable=broad-except
        module.fail_json(msg=f"Error generating PXE mapping file: {str(e)}")


if __name__ == '__main__':
    main()
