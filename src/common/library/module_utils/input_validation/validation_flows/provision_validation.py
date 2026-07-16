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
# pylint: disable=import-error,too-many-arguments,unused-argument,too-many-locals,too-many-positional-arguments
"""
This module contains functions for validating provision configuration.
"""
import json
import os
import re
import itertools
import csv
import yaml
import ipaddress
from ansible.module_utils.input_validation.common_utils import validation_utils
from ansible.module_utils.input_validation.common_utils import config
from ansible.module_utils.input_validation.common_utils import en_us_validation_msg
from ansible.module_utils.input_validation.common_utils.validation_utils import is_ip_in_subnet
from ansible.module_utils.input_validation.validation_flows import common_validation

file_names = config.files
create_error_msg = validation_utils.create_error_msg
create_file_path = validation_utils.create_file_path

# Expected header columns (case-insensitive)
required_headers = [
    "FUNCTIONAL_GROUP_NAME",
    "GROUP_NAME",
    "SERVICE_TAG",
    "PARENT_SERVICE_TAG",
    "HOSTNAME",
    "ADMIN_MAC",
    "ADMIN_IP",
    "BMC_MAC",
    "BMC_IP"
]

def validate_functional_groups_separation(pxe_mapping_file_path):
    """
    Validates that groups are not shared between different functional groups in the mapping file.
    Args:
        pxe_mapping_file_path (str): Path to the PXE mapping file.
    Raises:
        ValueError: If groups are shared between different functional groups.
    """
    if not pxe_mapping_file_path or not os.path.isfile(pxe_mapping_file_path):
        raise ValueError(f"PXE mapping file not found: {pxe_mapping_file_path}")

    with open(pxe_mapping_file_path, "r", encoding="utf-8") as fh:
        raw_lines = fh.readlines()

    non_comment_lines = [ln for ln in raw_lines if ln.strip()]
    reader = csv.DictReader(non_comment_lines)

    fieldname_map = {fn.strip().upper(): fn for fn in reader.fieldnames}
    fg_col = fieldname_map.get("FUNCTIONAL_GROUP_NAME")
    group_col = fieldname_map.get("GROUP_NAME")

    if not fg_col or not group_col:
        raise ValueError("FUNCTIONAL_GROUP_NAME or GROUP_NAME column not found in PXE mapping file")

    fg_groups = {}
    errors = []

    for row in reader:
        fg_name = row.get(fg_col, "").strip() if row.get(fg_col) else ""
        group_name = row.get(group_col, "").strip() if row.get(group_col) else ""

        if fg_name and group_name:
            if fg_name not in fg_groups:
                fg_groups[fg_name] = set()
            fg_groups[fg_name].add(group_name)

    # Check for shared groups between different functional groups
    for fg_name1, fg_name2 in itertools.combinations(fg_groups.keys(), 2):
        shared = fg_groups[fg_name1] & fg_groups[fg_name2]
        if shared:
            group_str = ', '.join(shared)
            msg = f"Group is shared between {fg_name1} and {fg_name2} functional groups."
            errors.append(create_error_msg("functional_groups", group_str, msg))

    if errors:
        raise ValueError("PXE mapping file group separation validation errors: " + "; ".join([str(e) for e in errors]))

def validate_slurm_login_compiler_prefix(pxe_mapping_file_path):
    """Validate that slurm_node and login_compiler entries align on architecture suffix when both are present.

    - Functional group suffix must be either _x86_64 or _aarch64 (case-sensitive).
    - When both slurm_node* and login_compiler_node* are present, their suffixes must match.

    Raises ValueError with details if suffixes differ. Prefix differences are allowed.
    """

    if not pxe_mapping_file_path or not os.path.isfile(pxe_mapping_file_path):
        raise ValueError(f"PXE mapping file not found: {pxe_mapping_file_path}")

    with open(pxe_mapping_file_path, "r", encoding="utf-8") as fh:
        raw_lines = fh.readlines()

    non_comment_lines = [ln for ln in raw_lines if ln.strip()]
    reader = csv.DictReader(non_comment_lines)

    fieldname_map = {fn.strip().upper(): fn for fn in reader.fieldnames}
    fg_col = fieldname_map.get("FUNCTIONAL_GROUP_NAME")
    hostname_col = fieldname_map.get("HOSTNAME")

    if not fg_col or not hostname_col:
        raise ValueError("FUNCTIONAL_GROUP_NAME or HOSTNAME column not found in PXE mapping file")

    arch_map = {"slurm_node": [], "login_compiler_node": []}

    for row_idx, row in enumerate(reader, start=2):
        fg_name = row.get(fg_col, "").strip() if row.get(fg_col) else ""
        hostname = row.get(hostname_col, "").strip() if row.get(hostname_col) else ""
        if not fg_name or not hostname:
            continue

        fg_arch = None
        fg_base = fg_name
        for suffix in ("_x86_64", "_aarch64"):
            if fg_name.endswith(suffix):
                fg_arch = suffix.lstrip("_")
                fg_base = fg_name[: -len(suffix)]
                break

        if fg_base in arch_map and fg_arch:
            arch_map[fg_base].append((fg_arch, row_idx))

    if not arch_map["slurm_node"] or not arch_map["login_compiler_node"]:
        return

    slurm_arch, _ = arch_map["slurm_node"][0]
    login_arch, _ = arch_map["login_compiler_node"][0]
    if slurm_arch != login_arch:
        slurm_rows = [str(r[1]) for r in arch_map["slurm_node"]]
        login_rows = [str(r[1]) for r in arch_map["login_compiler_node"]]
        raise ValueError(
            "Architecture suffix mismatch between slurm_node and login_compiler_node. "
            f"slurm_node suffix '{slurm_arch}' vs "
            f"login_compiler_node suffix '{login_arch}' "
            "Ensure both use the same suffix (_x86_64 or _aarch64)."
        )

def validate_hostname_nid_format_when_dns_enabled(pxe_mapping_file_path, dns_enabled):
    """
    Validates that all hostnames in the PXE mapping file follow the NID format
    (e.g., nid001, nid00001) when dns_enabled is true.

    When DNS is enabled, CoreDNS handles hostname resolution and expects NID-format
    hostnames. Custom hostnames require /etc/hosts (dns_enabled=false).

    Args:
        pxe_mapping_file_path (str): Path to the PXE mapping file.
        dns_enabled (bool): Whether DNS is enabled in provision_config.yml.

    Raises:
        ValueError: If dns_enabled is true and any hostname does not match the NID format.
    """
    if not dns_enabled:
        return

    if not pxe_mapping_file_path or not os.path.isfile(pxe_mapping_file_path):
        raise ValueError(f"PXE mapping file not found: {pxe_mapping_file_path}")

    with open(pxe_mapping_file_path, "r", encoding="utf-8") as fh:
        raw_lines = fh.readlines()

    non_comment_lines = [ln for ln in raw_lines if ln.strip()]
    reader = csv.DictReader(non_comment_lines)

    fieldname_map = {fn.strip().upper(): fn for fn in reader.fieldnames}
    hostname_col = fieldname_map.get("HOSTNAME")

    if not hostname_col:
        return

    nid_re = re.compile(r"^nid\d+$")
    invalid_hostnames = []

    for row_idx, row in enumerate(reader, start=2):
        hostname = row.get(hostname_col, "").strip() if row.get(hostname_col) else ""
        if hostname and not nid_re.match(hostname):
            invalid_hostnames.append(f"'{hostname}' (row {row_idx})")

    if invalid_hostnames:
        raise ValueError(
            f"{en_us_validation_msg.DNS_ENABLED_NON_NID_HOSTNAME_MSG} "
            f"Invalid hostnames: {', '.join(invalid_hostnames)}"
        )


def validate_duplicate_hostnames_in_mapping_file(pxe_mapping_file_path):
    """
    Validates that HOSTNAME values in the mapping file are unique.
    Args:
        pxe_mapping_file_path (str): Path to the PXE mapping file.
    Raises:
        ValueError: If duplicate hostnames are found.
    """
    if not pxe_mapping_file_path or not os.path.isfile(pxe_mapping_file_path):
        raise ValueError(f"PXE mapping file not found: {pxe_mapping_file_path}")

    with open(pxe_mapping_file_path, "r", encoding="utf-8") as fh:
        raw_lines = fh.readlines()

    non_comment_lines = [ln for ln in raw_lines if ln.strip()]
    reader = csv.DictReader(non_comment_lines)

    fieldname_map = {fn.strip().upper(): fn for fn in reader.fieldnames}
    hostname_col = fieldname_map.get("HOSTNAME")

    if not hostname_col:
        raise ValueError("HOSTNAME column not found in PXE mapping file")

    hostnames = []
    duplicates = []

    for row_idx, row in enumerate(reader, start=2):
        hostname = row.get(hostname_col, "").strip() if row.get(hostname_col) else ""
        if hostname in hostnames:
            duplicates.append(f"'{hostname}' at CSV row {row_idx}")
        else:
            hostnames.append(hostname)

    if duplicates:
        raise ValueError(f"Duplicate HOSTNAME found in PXE mapping file: {'; '.join(duplicates)}")

def validate_duplicate_service_tags_in_mapping_file(pxe_mapping_file_path):
    """
    Validates that SERVICE_TAG values in the mapping file are unique.

    Args:
        pxe_mapping_file_path (str): Path to the PXE mapping file.

    Raises:
        ValueError: If duplicate service tags are found.
    """
    if not pxe_mapping_file_path or not os.path.isfile(pxe_mapping_file_path):
        raise ValueError(f"PXE mapping file not found: {pxe_mapping_file_path}")

    with open(pxe_mapping_file_path, "r", encoding="utf-8") as fh:
        raw_lines = fh.readlines()

    non_comment_lines = [ln for ln in raw_lines if ln.strip()]
    reader = csv.DictReader(non_comment_lines)

    fieldname_map = {fn.strip().upper(): fn for fn in reader.fieldnames}
    st_col = fieldname_map.get("SERVICE_TAG")

    if not st_col:
        raise ValueError("SERVICE_TAG column not found in PXE mapping file")

    service_tags = []
    duplicates = []

    for row_idx, row in enumerate(reader, start=2):
        st = row.get(st_col, "").strip() if row.get(st_col) else ""
        if st in service_tags:
            duplicates.append(f"'{st}' at CSV row {row_idx}")
        else:
            service_tags.append(st)

    if duplicates:
        raise ValueError(f"Duplicate SERVICE_TAG found in PXE mapping file: {'; '.join(duplicates)}")


def validate_duplicate_admin_ips_in_mapping_file(pxe_mapping_file_path):
    """Validates that ADMIN_IP values in the mapping file are unique."""
    if not pxe_mapping_file_path or not os.path.isfile(pxe_mapping_file_path):
        raise ValueError(f"PXE mapping file not found: {pxe_mapping_file_path}")

    with open(pxe_mapping_file_path, "r", encoding="utf-8") as fh:
        raw_lines = fh.readlines()

    non_comment_lines = [ln for ln in raw_lines if ln.strip()]
    reader = csv.DictReader(non_comment_lines)

    fieldname_map = {fn.strip().upper(): fn for fn in reader.fieldnames}
    admin_ip_col = fieldname_map.get("ADMIN_IP")
    hostname_col = fieldname_map.get("HOSTNAME")

    if not admin_ip_col:
        raise ValueError("ADMIN_IP column not found in PXE mapping file")

    seen_admin_ips = {}
    duplicates = []

    for row_idx, row in enumerate(reader, start=2):
        admin_ip = row.get(admin_ip_col, "").strip() if row.get(admin_ip_col) else ""
        hostname = ""
        if hostname_col:
            hostname = row.get(hostname_col, "").strip() if row.get(hostname_col) else ""

        if not admin_ip:
            continue

        if admin_ip in seen_admin_ips:
            first_row = seen_admin_ips[admin_ip]["row"]
            first_host = seen_admin_ips[admin_ip]["hostname"]
            dup_host = hostname or "<empty>"
            first_host_disp = first_host or "<empty>"
            duplicates.append(
                f"'{admin_ip}' at CSV rows {first_row} ({first_host_disp}) and {row_idx} ({dup_host})"
            )
            continue

        seen_admin_ips[admin_ip] = {"row": row_idx, "hostname": hostname}

    if duplicates:
        raise ValueError(f"Duplicate ADMIN_IP found in PXE mapping file: {'; '.join(duplicates)}")


def validate_duplicate_ib_ips_in_mapping_file(pxe_mapping_file_path):
    """Validates that IB_IP values in the mapping file are unique."""
    if not pxe_mapping_file_path or not os.path.isfile(pxe_mapping_file_path):
        raise ValueError(f"PXE mapping file not found: {pxe_mapping_file_path}")

    with open(pxe_mapping_file_path, "r", encoding="utf-8") as fh:
        raw_lines = fh.readlines()

    non_comment_lines = [ln for ln in raw_lines if ln.strip()]
    reader = csv.DictReader(non_comment_lines)

    fieldname_map = {fn.strip().upper(): fn for fn in reader.fieldnames}
    ib_ip_col = fieldname_map.get("IB_IP")
    hostname_col = fieldname_map.get("HOSTNAME")

    if not ib_ip_col:
        return

    seen_ib_ips = {}
    duplicates = []

    for row_idx, row in enumerate(reader, start=2):
        ib_ip = row.get(ib_ip_col, "").strip() if row.get(ib_ip_col) else ""
        hostname = ""
        if hostname_col:
            hostname = row.get(hostname_col, "").strip() if row.get(hostname_col) else ""

        if not ib_ip:
            continue

        if ib_ip in seen_ib_ips:
            first_row = seen_ib_ips[ib_ip]["row"]
            first_host = seen_ib_ips[ib_ip]["hostname"]
            dup_host = hostname or "<empty>"
            first_host_disp = first_host or "<empty>"
            duplicates.append(
                f"'{ib_ip}' at CSV rows {first_row} ({first_host_disp}) and {row_idx} ({dup_host})"
            )
            continue

        seen_ib_ips[ib_ip] = {"row": row_idx, "hostname": hostname}

    if duplicates:
        raise ValueError(f"Duplicate IB_IP found in PXE mapping file: {'; '.join(duplicates)}")


def validate_ib_nic_name_format_in_mapping_file(pxe_mapping_file_path):
    """Validates IB_NIC_NAME format structure in the mapping file.
    
    Validates that IB_NIC_NAME follows one of the supported formats:
    - 'InfiniBand.PCIe.Slot.X-Y' (slot X, port Y)
    - 'InfiniBand.Slot.X-Y' (slot X, port Y)  
    - 'NIC.InfiniBand.X-Y' (slot X, port Y)
    - 'InfiniBand.Single-Y' (single device, port Y)
    
    Only validates format structure, not specific slot/port ranges.
    """
    if not pxe_mapping_file_path or not os.path.isfile(pxe_mapping_file_path):
        raise ValueError(f"PXE mapping file not found: {pxe_mapping_file_path}")

    with open(pxe_mapping_file_path, "r", encoding="utf-8") as fh:
        raw_lines = fh.readlines()

    non_comment_lines = [ln for ln in raw_lines if ln.strip()]
    reader = csv.DictReader(non_comment_lines)

    fieldname_map = {fn.strip().upper(): fn for fn in reader.fieldnames}
    ib_nic_col = fieldname_map.get("IB_NIC_NAME")
    hostname_col = fieldname_map.get("HOSTNAME")

    if not ib_nic_col:
        return  # No IB_NIC_NAME column to validate

    # Supported IB_NIC_NAME format patterns (updated to support hexadecimal slots)
    slot_pattern = re.compile(r'^(InfiniBand\.PCIe\.Slot\.|InfiniBand\.Slot\.|NIC\.InfiniBand\.)([0-9a-fA-F]+)-([0-9]+)$')
    single_pattern = re.compile(r'^InfiniBand\.Single-([0-9]+)$')

    invalid_formats = []

    for row_idx, row in enumerate(reader, start=2):
        ib_nic_name = row.get(ib_nic_col, "").strip() if ib_nic_col and row.get(ib_nic_col) else ""
        hostname = ""
        if hostname_col:
            hostname = row.get(hostname_col, "").strip() if hostname_col and row.get(hostname_col) else ""

        # Skip empty IB_NIC_NAME (already handled by consistency validation)
        if not ib_nic_name:
            continue

        # Check if format matches supported patterns
        if slot_pattern.match(ib_nic_name):
            # Valid slot-based format
            continue
        elif single_pattern.match(ib_nic_name):
            # Valid single-device format
            continue
        else:
            # Invalid format
            hostname_disp = f" ({hostname})" if hostname else ""
            invalid_formats.append(f"'{ib_nic_name}' at CSV row {row_idx}{hostname_disp}")

    if invalid_formats:
        raise ValueError(
            f"Invalid IB_NIC_NAME format(s) found in PXE mapping file: {'; '.join(invalid_formats)}. "
            f"Supported formats are: "
            f"'InfiniBand.PCIe.Slot.X-Y', 'InfiniBand.Slot.X-Y', 'NIC.InfiniBand.X-Y', 'InfiniBand.Single-Y'. "
            f"Slot numbers support decimal (22) and hexadecimal (b5, a0, ff) formats. "
            f"Examples: 'InfiniBand.PCIe.Slot.22-1', 'InfiniBand.PCIe.Slot.b5-1', 'InfiniBand.Single-1'"
        )





def validate_group_parent_service_tag_consistency_in_mapping_file(pxe_mapping_file_path):
    """Validates that GROUP_NAME has a consistent PARENT_SERVICE_TAG across the mapping file."""
    if not pxe_mapping_file_path or not os.path.isfile(pxe_mapping_file_path):
        raise ValueError(f"PXE mapping file not found: {pxe_mapping_file_path}")

    with open(pxe_mapping_file_path, "r", encoding="utf-8") as fh:
        raw_lines = fh.readlines()

    non_comment_lines = [ln for ln in raw_lines if ln.strip()]
    reader = csv.DictReader(non_comment_lines)

    fieldname_map = {fn.strip().upper(): fn for fn in reader.fieldnames}
    group_col = fieldname_map.get("GROUP_NAME")
    parent_col = fieldname_map.get("PARENT_SERVICE_TAG")

    if not group_col or not parent_col:
        raise ValueError("GROUP_NAME or PARENT_SERVICE_TAG column not found in PXE mapping file")

    group_to_parent = {}
    errors = []

    for row_idx, row in enumerate(reader, start=2):
        group_name = row.get(group_col, "").strip() if row.get(group_col) else ""
        parent = row.get(parent_col, "").strip() if row.get(parent_col) else ""
        if not group_name:
            continue

        if group_name not in group_to_parent:
            group_to_parent[group_name] = {"parent": parent, "row": row_idx}
            continue

        prev_parent = group_to_parent[group_name]["parent"]
        if prev_parent != parent:
            errors.append(
                f"GROUP_NAME '{group_name}' is associated with different PARENT_SERVICE_TAG. "
                f"Found PARENT_SERVICE_TAG='{prev_parent}' at CSV row {group_to_parent[group_name]['row']} and "
                f"PARENT_SERVICE_TAG='{parent}' at CSV row {row_idx}. "
                f"Fix: Use exactly one PARENT_SERVICE_TAG value for same GROUP_NAME. "
            )

    if errors:
        raise ValueError(
            "PXE mapping file GROUP_NAME and PARENT_SERVICE_TAG consistency validation errors: "
            + "\n".join(errors)
        )

def validate_mapping_file_entries(mapping_file_path):
    """
    Validate CSV mapping file without pandas:
        - Mandatory columns (case-insensitive)
        - Non-null/empty values per required column
        - MAC addresses format (ADMIN_MAC, BMC_MAC)
        - Service tags (alphanumeric)
        - Parent service tag (alphanumeric or empty)
        - HOSTNAME format
        - GROUP_NAME format (grp0..grp100 or SU1..SU100)
        - FUNCTIONAL_GROUP_NAME format (alphanumeric and underscores)
        - ADMIN_IP and BMC_IP are valid IPv4 (BMC_IP may be empty)
    Raises:
        ValueError: If the mapping file format is invalid
    """
    if not mapping_file_path or not os.path.isfile(mapping_file_path):
        raise ValueError(f"PXE mapping file not found: {mapping_file_path}")

    with open(mapping_file_path, "r", encoding="utf-8") as fh:
        raw_lines = fh.readlines()

    # Remove blank lines only (preserve header and data). Comments are handled elsewhere.
    non_blank_lines = [ln for ln in raw_lines if ln.strip()]
    if not non_blank_lines:
        raise ValueError("Please provide details in mapping file.")

    reader = csv.DictReader(non_blank_lines)
    if not reader.fieldnames:
        raise ValueError("CSV header not found in mapping file.")

    # Map header names case-insensitively to original names
    fieldname_map = {fn.strip().upper(): fn for fn in reader.fieldnames}

    # Ensure required headers present
    for hdr in required_headers:
        if hdr not in fieldname_map:
            raise ValueError(f"Missing mandatory column: {hdr} in mapping file.")

    # Pre-compile regexes
    mac_re = re.compile(r"^([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}$")
    hostname_re = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?$")
    group_re = re.compile(r"^(?:grp(?:[0-9]|[1-9][0-9]|100)|[Ss][Uu][A-Za-z]?(?:0*[1-9][0-9]?|100))$")
    fg_re = re.compile(r"^[A-Za-z0-9_]+$")

    row_seen = False
    for row_idx, row in enumerate(reader, start=2):  # start=2 approximates CSV row number
        row_seen = True
        # Check presence and non-empty for all required headers
        for hdr in required_headers:
            col = fieldname_map[hdr]
            val = row.get(col)
            if val is None or str(val).strip() == "":
                if hdr == "PARENT_SERVICE_TAG":
                    # allow empty parent service tag; ensure None becomes empty string for later
                    #.strip() calls
                    if val is None:
                        row[fieldname_map[hdr]] = ""
                    continue
                raise ValueError(f"Null or empty value in column: {hdr} at CSV row {row_idx} in mapping file.")

        # Extract normalized values
        svc = row.get(fieldname_map["SERVICE_TAG"]).strip()
        parent = row.get(fieldname_map["PARENT_SERVICE_TAG"]).strip()
        hostname = row.get(fieldname_map["HOSTNAME"]).strip()
        admin_mac = row.get(fieldname_map["ADMIN_MAC"]).strip()
        bmc_mac = row.get(fieldname_map["BMC_MAC"]).strip()
        admin_ip = row.get(fieldname_map["ADMIN_IP"]).strip()
        bmc_ip = row.get(fieldname_map["BMC_IP"]).strip()
        group_name = row.get(fieldname_map["GROUP_NAME"]).strip()
        fg_name = row.get(fieldname_map["FUNCTIONAL_GROUP_NAME"]).strip()

        # Service tags: alphanumeric
        if not svc.isalnum():
            raise ValueError(f"Invalid SERVICE_TAG: '{svc}' at CSV row {row_idx} in mapping file. Must be alphanumeric.")

        # Parent service tag: allow empty, otherwise alphanumeric
        if parent and not parent.isalnum():
            raise ValueError(f"Invalid PARENT_SERVICE_TAG: '{parent}' at CSV row {row_idx} in mapping file. "
            "Must be alphanumeric or empty.")

        # MAC addresses
        if not mac_re.match(admin_mac):
            raise ValueError(f"Invalid ADMIN_MAC: '{admin_mac}' at CSV row {row_idx} in mapping file.")
        if not mac_re.match(bmc_mac):
            raise ValueError(f"Invalid BMC_MAC: '{bmc_mac}' at CSV row {row_idx} in mapping file.")

        # Hostname
        if not hostname_re.match(hostname):
            raise ValueError(f"Invalid HOSTNAME: '{hostname}' at CSV row {row_idx} in mapping file.")

        # GROUP_NAME format
        if not group_re.match(group_name):
            raise ValueError(f"Invalid GROUP_NAME: '{group_name}' at CSV row {row_idx} in mapping file. Must be grp0-grp100 or SU[A-Z]1-100 (e.g. SU1, SU01, SUA99).")

        # FUNCTIONAL_GROUP_NAME format
        if not fg_re.match(fg_name):
            raise ValueError(f"Invalid FUNCTIONAL_GROUP_NAME: '{fg_name}' at CSV row {row_idx} in mapping file. Must be alphanumeric with underscores.")

        # IP validations (ADMIN_IP required, BMC_IP optional)
        if not validation_utils.validate_ipv4(admin_ip):
            raise ValueError(f"Invalid ADMIN_IP: '{admin_ip}' at CSV row {row_idx} in mapping file.")
        if bmc_ip and not validation_utils.validate_ipv4(bmc_ip):
            raise ValueError(f"Invalid BMC_IP: '{bmc_ip}' at CSV row {row_idx} in mapping file.")

        ib_nic_col = fieldname_map.get("IB_NIC_NAME")
        ib_ip_col = fieldname_map.get("IB_IP")
        ib_nic_name = row.get(ib_nic_col, "").strip() if ib_nic_col and row.get(ib_nic_col) else ""
        ib_ip = row.get(ib_ip_col, "").strip() if ib_ip_col and row.get(ib_ip_col) else ""

        if bool(ib_nic_name) != bool(ib_ip):
            raise ValueError(
                f"IB_NIC_NAME and IB_IP must both be provided or both be empty at CSV row {row_idx} in mapping file."
            )

        if ib_ip and not validation_utils.validate_ipv4(ib_ip):
            raise ValueError(f"Invalid IB_IP: '{ib_ip}' at CSV row {row_idx} in mapping file.")

    if not row_seen:
        raise ValueError("Please provide details in mapping file.")

def validate_functional_groups_in_mapping_file(pxe_mapping_file_path):
    """
    Validates the PXE mapping file format.

    Args:
        pxe_mapping_file_path (str): Path to the PXE mapping file.

    Raises:
        ValueError: If the PXE mapping file format is invalid.
    """

    if not pxe_mapping_file_path or not os.path.isfile(pxe_mapping_file_path):
        raise ValueError(f"PXE mapping file not found: {pxe_mapping_file_path}")

    with open(pxe_mapping_file_path, "r", encoding="utf-8") as fh:
        raw_lines = fh.readlines()
    # Disallow any comment lines in the PXE mapping file
    comment_lines = [i + 1 for i, ln in enumerate(raw_lines) if ln.lstrip().startswith("#")]
    if comment_lines:
        raise ValueError(
            f"PXE mapping file must not contain comments. Comment lines found at: {', '.join(map(str, comment_lines))}"
        )

    # Remove blank lines only; after the check above there are no comment lines
    non_comment_lines = [ln for ln in raw_lines if ln.strip()]
    if not non_comment_lines:
        raise ValueError(f"PXE mapping file is empty: {pxe_mapping_file_path}")

    # Use csv.DictReader on the filtered lines
    reader = csv.DictReader(non_comment_lines)
    if not reader.fieldnames:
        raise ValueError(f"CSV header not found in PXE mapping file: {pxe_mapping_file_path}")

    # Normalize header names for case-insensitive matching
    fieldname_map = {fn.strip().upper(): fn for fn in reader.fieldnames}

    fg_col = fieldname_map.get("FUNCTIONAL_GROUP_NAME")
    if not fg_col:
        raise ValueError("FUNCTIONAL_GROUP_NAME column not found in PXE mapping file")

    invalid_entries = []
    # Iterate rows and validate FG names
    for row_idx, row in enumerate(reader, start=2):  # start=2 approximates line number of first data row
        raw_fg = row.get(fg_col, "")
        fg = raw_fg.strip() if raw_fg is not None else ""
        if not fg:
            invalid_entries.append(f"empty functional group name at CSV row {row_idx}")
        elif fg not in config.FUNCTIONAL_GROUP_LAYER_MAP.keys():
            invalid_entries.append(f"unrecognized functional group name '{fg}' at CSV row {row_idx}")

    if invalid_entries:
        raise ValueError("PXE mapping file functional group name validation errors: " + "; ".join(invalid_entries))

def validate_parent_service_tag_hierarchy(pxe_mapping_file_path):
    """
    Validates the parent service tag hierarchy in the PXE mapping file.
    
    Ensures that:
    - kube_control_plane and kube_node functional groups in slurm nodes have a parent_service_tag
    - Management nodes (login, compiler, control plane) do not have a parent_service_tag
    
    Args:
        pxe_mapping_file_path (str): Path to the PXE mapping file.
    
    Raises:
        ValueError: If the parent service tag hierarchy is invalid.
    """
    if not pxe_mapping_file_path or not os.path.isfile(pxe_mapping_file_path):
        raise ValueError(f"PXE mapping file not found: {pxe_mapping_file_path}")
    with open(pxe_mapping_file_path, "r", encoding="utf-8") as fh:
        raw_lines = fh.readlines()
    non_comment_lines = [ln for ln in raw_lines if ln.strip()]
    reader = csv.DictReader(non_comment_lines)
    fieldname_map = {fn.strip().upper(): fn for fn in reader.fieldnames}
    fg_col = fieldname_map.get("FUNCTIONAL_GROUP_NAME")
    parent_col = fieldname_map.get("PARENT_SERVICE_TAG")
    if not fg_col or not parent_col:
        raise ValueError("Required columns FUNCTIONAL_GROUP_NAME or PARENT_SERVICE_TAG not found")
    hierarchy_errors = []
    # Read all rows so we can pre-scan for a kube cluster and still iterate below
    rows = list(reader)

    # Detect if any row contains a kube control plane or kube node FG
    kube_cluster_present = any(
        ("kube_" in (row.get(fg_col) or "").strip().lower())
        for row in rows
    )
    kube_srv_tags = [row.get('SERVICE_TAG') for row in rows if 'kube_node' in row.get("FUNCTIONAL_GROUP_NAME")]
    # Replace reader with an iterator over the stored rows so the loop below can consume them
    reader_iter = iter(rows)
    for row_idx, row in enumerate(reader_iter, start=2):
        fg = row.get(fg_col, "").strip()
        parent = row.get(parent_col, "").strip() if row.get(parent_col) else ""
        # Get the layer for this functional group
        layer = config.FUNCTIONAL_GROUP_LAYER_MAP.get(fg)
        if layer == "management":
            # Management nodes should NOT have a parent
            if parent:
                hierarchy_errors.append(
                    f"Management node with functional group '{fg}' at CSV row {row_idx} "
                    f"should not have parent_service_tag, but found: '{parent}'"
                )
        elif layer == "compute" and kube_cluster_present and not fg.startswith("os_"):
            # Compute nodes (slurm_node) MUST have a parent
            # OS nodes are standalone compute nodes and do not require a parent
            if not parent:
                hierarchy_errors.append(
                    f"Compute node with functional group '{fg}' at CSV row {row_idx} "
                    f"must have a parent_service_tag configured"
                )
            elif parent not in kube_srv_tags:
                hierarchy_errors.append(
                    f"Compute node with functional group '{fg}' at CSV row {row_idx} "
                    f"must have a valid parent_service_tag configured as service_kube_node"
                )

    if hierarchy_errors:
        raise ValueError(
            "PXE mapping file parent service tag hierarchy validation errors: " +
            "; ".join(hierarchy_errors)
        )

# def validate_admin_ips_against_network_spec(pxe_mapping_file_path, network_spec_path):
#     """
#     Validates that ADMIN_IP addresses in the mapping file fall within the network ranges
#     defined in network_spec.yml.
#
#     Args:
#         pxe_mapping_file_path (str): Path to the PXE mapping file.
#         network_spec_path (str): Path to the network_spec.yml file.
#
#     Returns:
#         list: List of validation errors, empty if no errors found.
#     """
#     import ipaddress
#
#     errors = []
#
#     if not os.path.isfile(network_spec_path):
#         errors.append(
#             create_error_msg(
#                 "network_spec_path",
#                 network_spec_path,
#                 en_us_validation_msg.NETWORK_SPEC_FILE_NOT_FOUND_MSG
#             )
#         )
#         return errors
#
#     # Load network_spec.yml
#     with open(network_spec_path, "r", encoding="utf-8") as f:
#         network_spec = yaml.safe_load(f)
#
#     # Extract admin network configuration
#     admin_network_config = None
#     for network in network_spec.get("Networks", []):
#         if "admin_network" in network:
#             admin_network_config = network["admin_network"]
#             break
#
#     if not admin_network_config:
#         errors.append(
#             create_error_msg(
#                 "admin_network",
#                 network_spec_path,
#                 en_us_validation_msg.ADMIN_NETWORK_NOT_FOUND_MSG
#             )
#         )
#         return errors
#
#     # Get network parameters
#     primary_oim_admin_ip = admin_network_config.get("primary_oim_admin_ip", "")
#     netmask_bits = admin_network_config.get("netmask_bits", "")
#     dynamic_range = admin_network_config.get("dynamic_range", "")
#
#     if not primary_oim_admin_ip or not netmask_bits:
#         errors.append(
#             create_error_msg(
#                 "primary_oim_admin_ip/netmask_bits",
#                 network_spec_path,
#                 en_us_validation_msg.PRIMARY_ADMIN_IP_NETMASK_REQUIRED_MSG
#             )
#         )
#         return errors
#
#     # Calculate the network range
#     try:
#         network = ipaddress.IPv4Network(
#             f"{primary_oim_admin_ip}/{netmask_bits}", strict=False
#         )
#     except ValueError as e:
#         errors.append(
#             create_error_msg(
#                 "network_config",
#                 network_spec_path,
#                 f"{en_us_validation_msg.INVALID_NETWORK_CONFIG_MSG} Error: {e}"
#             )
#         )
#         return errors
#
#     # Parse dynamic range if provided
#     dynamic_ips = set()
#     if dynamic_range:
#         try:
#             range_parts = dynamic_range.split("-")
#             if len(range_parts) == 2:
#                 start_ip = ipaddress.IPv4Address(range_parts[0].strip())
#                 end_ip = ipaddress.IPv4Address(range_parts[1].strip())
#                 current_ip = start_ip
#                 while current_ip <= end_ip:
#                     dynamic_ips.add(str(current_ip))
#                     current_ip += 1
#         except ValueError as e:
#             errors.append(
#                 create_error_msg(
#                     "dynamic_range",
#                     network_spec_path,
#                     f"{en_us_validation_msg.INVALID_DYNAMIC_RANGE_FORMAT_MSG} Error: {e}"
#                 )
#             )
#             return errors
#
#     # Read and validate mapping file
#     with open(pxe_mapping_file_path, "r", encoding="utf-8") as fh:
#         raw_lines = fh.readlines()
#
#     non_comment_lines = [
#         ln for ln in raw_lines if ln.strip() and not ln.strip().startswith("#")
#     ]
#
#     if not non_comment_lines:
#         return errors  # Empty file, nothing to validate
#
#     reader = csv.DictReader(non_comment_lines)
#
#     # Map header names case-insensitively to original names
#     fieldname_map = {fn.strip().upper(): fn for fn in reader.fieldnames}
#     admin_ip_col = fieldname_map.get("ADMIN_IP")
#     hostname_col = fieldname_map.get("HOSTNAME")
#
#     if not admin_ip_col or not hostname_col:
#         errors.append(
#             create_error_msg(
#                 "pxe_mapping_file_headers",
#                 pxe_mapping_file_path,
#                 en_us_validation_msg.ADMIN_IP_HOSTNAME_COLUMN_MISSING_MSG
#             )
#         )
#         return errors
#
#     ip_validation_errors = []
#
#     for row_idx, row in enumerate(reader, start=2):
#         admin_ip = row.get(admin_ip_col, "").strip() if row.get(admin_ip_col) else ""
#         hostname = row.get(hostname_col, "").strip() if row.get(hostname_col) else ""
#
#         if not admin_ip:
#             continue
#
#         try:
#             ip_addr = ipaddress.IPv4Address(admin_ip)
#
#             # Check if IP is within the network range
#             if ip_addr not in network:
#                 error_detail = (
#                     f"Row {row_idx}: ADMIN_IP '{admin_ip}' (host: '{hostname}') "
#                     f"is outside the admin network range {network}"
#                 )
#                 ip_validation_errors.append(error_detail)
#             # Check if IP is in dynamic range (reserved for DHCP)
#             elif admin_ip in dynamic_ips:
#                 error_detail = (
#                     f"Row {row_idx}: ADMIN_IP '{admin_ip}' (host: '{hostname}') "
#                     f"is in the dynamic DHCP range ({dynamic_range})"
#                 )
#                 ip_validation_errors.append(error_detail)
#             # Check if IP conflicts with primary OIM admin IP
#             elif admin_ip == primary_oim_admin_ip:
#                 error_detail = (
#                     f"Row {row_idx}: ADMIN_IP '{admin_ip}' (host: '{hostname}') "
#                     f"conflicts with primary_oim_admin_ip"
#                 )
#                 ip_validation_errors.append(error_detail)
#         except ValueError:
#             pass
#
#     if ip_validation_errors:
#         # Add summary message first
#         summary_msg = (
#             f"ADMIN_IP validation failed for {len(ip_validation_errors)} node(s). "
#             f"Expected network range: {network}"
#         )
#         errors.append(
#             create_error_msg(
#                 "pxe_mapping_file_path",
#                 pxe_mapping_file_path,
#                 summary_msg
#             )
#         )
#         # Add each individual error as a separate entry
#         for ip_error in ip_validation_errors:
#             errors.append(
#                 create_error_msg(
#                     "pxe_mapping_file_path",
#                     pxe_mapping_file_path,
#                     ip_error
#                 )
#             )
#
#     return errors


def validate_pxe_admin_ips_subnet_consistency(
        errors, pxe_mapping_file_path, oim_admin_ip, admin_netmaskbits,
        additional_subnets=None):
    """
    Validate that every ADMIN_IP in the PXE mapping file belongs to a known
    subnet: either the primary admin subnet or one of the additional_subnets
    defined in network_spec.yml.

    Args:
        errors (list): List to append error messages to.
        pxe_mapping_file_path (str): Path to the PXE mapping CSV file.
        oim_admin_ip (str): Primary OIM admin IP address.
        admin_netmaskbits (str): Netmask bits for the primary admin subnet.
        additional_subnets (list, optional): List of additional subnet dicts
            with 'subnet' and 'netmask_bits' keys.
    """
    if additional_subnets is None:
        additional_subnets = []

    pxe_admin_ips = []
    try:
        with open(pxe_mapping_file_path, "r", encoding="utf-8") as fh:
            raw_lines = [ln for ln in fh.readlines()
                         if ln.strip() and not ln.strip().startswith('#')]
        reader = csv.DictReader(raw_lines)
        fieldname_map = {fn.strip().upper(): fn for fn in reader.fieldnames}
        admin_ip_col = fieldname_map.get("ADMIN_IP")
        if admin_ip_col:
            for row in reader:
                val = (row.get(admin_ip_col) or "").strip()
                if val and validation_utils.validate_ipv4(val):
                    pxe_admin_ips.append(val)
    except (OSError, csv.Error):
        return

    for host_ip in pxe_admin_ips:
        if is_ip_in_subnet(oim_admin_ip, admin_netmaskbits, host_ip):
            continue
        in_additional = any(
            is_ip_in_subnet(
                s.get("subnet", ""),
                s.get("netmask_bits", ""),
                host_ip
            )
            for s in additional_subnets
            if s.get("subnet") and s.get("netmask_bits")
        )
        if not in_additional:
            errors.append(
                create_error_msg(
                    f"{pxe_mapping_file_path}: ADMIN_IP subnet consistency",
                    host_ip,
                    f"Node ADMIN_IP {host_ip} does not belong to the primary "
                    f"admin subnet ({oim_admin_ip}/{admin_netmaskbits}) or any "
                    "subnet defined in network_spec.yml additional_subnets. "
                    "Please ensure all ADMIN_IPs in the PXE mapping file are "
                    "covered by a subnet in network_spec.yml."
                )
            )


def validate_aarch64_local_path_compatibility(pxe_mapping_file_path):
    """
    Validates that aarch64 nodes are not present when using local share path.
    
    Args:
        pxe_mapping_file_path (str): Path to the PXE mapping file.
        
    Raises:
        ValueError: If aarch64 nodes are found with local share path configuration.
    """
    # Check metadata file for omnia_share_option
    metadata_path = "/opt/omnia/.data/oim_metadata.yml"
    
    # Default to Local if metadata doesn't exist or omnia_Share_option is not set
    share_option = "Local"
    
    if os.path.isfile(metadata_path):
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = yaml.safe_load(f) or {}
                
            # Check omnia_share_option in metadata
            share_option = metadata.get("omnia_share_option", "Local")
        except Exception:
            # If there's an error reading metadata, assume Local
            pass
    
    # If share option is NFS, no need to check further
    if share_option.lower() == "nfs":
        return
    
    # Check for aarch64 nodes in PXE mapping file
    with open(pxe_mapping_file_path, "r", encoding="utf-8") as fh:
        raw_lines = fh.readlines()
    
    non_comment_lines = [ln for ln in raw_lines if ln.strip()]
    reader = csv.DictReader(non_comment_lines)
    
    fieldname_map = {fn.strip().upper(): fn for fn in reader.fieldnames}
    fg_col = fieldname_map.get("FUNCTIONAL_GROUP_NAME")
    
    if not fg_col:
        return
    
    aarch64_found = False
    for row in reader:
        fg_name = row.get(fg_col, "").strip() if row.get(fg_col) else ""
        if fg_name and "aarch64" in fg_name.lower():
            aarch64_found = True
            break
    
    if aarch64_found:
        raise ValueError(en_us_validation_msg.PXE_MAPPING_AARCH64_LOCAL_PATH_MSG)

def validate_functional_groups_software_consistency(pxe_mapping_file_path, software_config_json, logger):
    """
    Validates that functional groups in the PXE mapping file have corresponding
    software configured in software_config.json.
    
    This ensures that:
    - If service_kube_node_* or service_kube_control_plane_* functional groups exist
      in the mapping file, then 'service_k8s' must be in software_config.json
    - If slurm_control_node_* or slurm_node_* functional groups exist in the mapping file,
      then 'slurm_custom' must be in software_config.json
    
    Args:
        pxe_mapping_file_path (str): Path to the PXE mapping file.
        software_config_json (dict): Parsed software_config.json data.
        logger (Logger): Logger instance for logging messages.
        
    Raises:
        ValueError: If functional groups are defined without corresponding software.
    """
    if not pxe_mapping_file_path or not os.path.isfile(pxe_mapping_file_path):
        return
    
    # Read the mapping file to find functional groups
    with open(pxe_mapping_file_path, "r", encoding="utf-8") as fh:
        raw_lines = fh.readlines()
    
    non_comment_lines = [ln for ln in raw_lines if ln.strip()]
    if not non_comment_lines:
        return
    
    reader = csv.DictReader(non_comment_lines)
    fieldname_map = {fn.strip().upper(): fn for fn in reader.fieldnames}
    fg_col = fieldname_map.get("FUNCTIONAL_GROUP_NAME")
    
    if not fg_col:
        return
    
    # Track which functional groups are found
    has_service_k8s_fg = False
    has_slurm_fg = False
    
    for row in reader:
        fg_name = row.get(fg_col, "").strip() if row.get(fg_col) else ""
        if not fg_name:
            continue
        
        # Check for service k8s functional groups
        if fg_name.startswith('service_kube_node_') or fg_name.startswith('service_kube_control_plane_'):
            has_service_k8s_fg = True
            logger.info(f"Found service k8s functional group in mapping file: {fg_name}")
        
        # Check for slurm functional groups
        if fg_name.startswith('slurm_control_node_') or fg_name.startswith('slurm_node_'):
            has_slurm_fg = True
            logger.info(f"Found slurm functional group in mapping file: {fg_name}")
    
    # Get list of software names from software_config.json
    software_names = []
    if software_config_json and "softwares" in software_config_json:
        software_names = [sw.get("name", "") for sw in software_config_json.get("softwares", [])]
    
    logger.info(f"Software configured in software_config.json: {software_names}")
    
    # Validate service_k8s and slurm_custom, collecting all errors
    consistency_errors = []

    if has_service_k8s_fg and "service_k8s" not in software_names:
        logger.error("Service k8s functional groups found but service_k8s not in software_config.json")
        consistency_errors.append(en_us_validation_msg.SERVICE_K8S_FUNCTIONAL_GROUP_WITHOUT_SOFTWARE_MSG)

    if has_slurm_fg and "slurm_custom" not in software_names:
        logger.error("Slurm functional groups found but slurm_custom not in software_config.json")
        consistency_errors.append(en_us_validation_msg.SLURM_FUNCTIONAL_GROUP_WITHOUT_SOFTWARE_MSG)

    if consistency_errors:
        raise ValueError(" | ".join(consistency_errors))

    # Log success
    if has_service_k8s_fg and "service_k8s" in software_names:
        logger.info("✓ Service k8s functional groups validated: service_k8s found in software_config.json")
    if has_slurm_fg and "slurm_custom" in software_names:
        logger.info("✓ Slurm functional groups validated: slurm_custom found in software_config.json")

def _get_fg_names_from_mapping_file(pxe_mapping_file_path):
    """Extract unique functional group names from PXE mapping CSV.

    Args:
        pxe_mapping_file_path (str): Path to the PXE mapping CSV file.

    Returns:
        list: Sorted list of unique functional group names.
    """
    if not pxe_mapping_file_path or not os.path.isfile(pxe_mapping_file_path):
        return []
    with open(pxe_mapping_file_path, "r", encoding="utf-8") as fh:
        raw_lines = fh.readlines()
    non_comment_lines = [ln for ln in raw_lines if ln.strip()]
    reader = csv.DictReader(non_comment_lines)
    fieldname_map = {fn.strip().upper(): fn for fn in reader.fieldnames}
    fg_col = fieldname_map.get("FUNCTIONAL_GROUP_NAME")
    if not fg_col:
        return []
    fg_names = set()
    for row in reader:
        fg = row.get(fg_col, "").strip() if row.get(fg_col) else ""
        if fg:
            fg_names.add(fg)
    return sorted(fg_names)


def _validate_cloud_init_section(section_name, section_data):
    """Validate a single cloud-init section (common or per-FG).

    Returns:
        list: List of error dicts from create_error_msg.
    """
    errors = []
    key_prefix = f"additional_cloud_init.{section_name}"

    if not isinstance(section_data, dict):
        errors.append(create_error_msg(
            key_prefix, str(type(section_data).__name__),
            en_us_validation_msg.ADDITIONAL_CLOUD_INIT_SECTION_NOT_DICT_MSG,
        ))
        return errors

    prohibited_keys = ["bootcmd", "network", "network-config", "packages"]
    allowed_keys = ["write_files", "runcmd"]

    for key in section_data:
        if key in prohibited_keys:
            errors.append(create_error_msg(
                f"{key_prefix}.{key}", key,
                en_us_validation_msg.ADDITIONAL_CLOUD_INIT_PROHIBITED_KEY_MSG,
            ))
        elif key not in allowed_keys:
            errors.append(create_error_msg(
                f"{key_prefix}.{key}", key,
                en_us_validation_msg.ADDITIONAL_CLOUD_INIT_UNKNOWN_KEY_MSG,
            ))

    # write_files
    if "write_files" in section_data:
        wf = section_data["write_files"]
        if not isinstance(wf, list):
            errors.append(create_error_msg(
                f"{key_prefix}.write_files", str(type(wf).__name__),
                en_us_validation_msg.ADDITIONAL_CLOUD_INIT_WRITE_FILES_NOT_LIST_MSG,
            ))
        else:
            for idx, entry in enumerate(wf):
                if isinstance(entry, dict):
                    path_val = entry.get("path", "")
                    if not path_val or not str(path_val).strip():
                        errors.append(create_error_msg(
                            f"{key_prefix}.write_files[{idx}].path", "",
                            en_us_validation_msg.ADDITIONAL_CLOUD_INIT_WRITE_FILES_MISSING_PATH_MSG,
                        ))

    # runcmd
    if "runcmd" in section_data:
        rc = section_data["runcmd"]
        if not isinstance(rc, list):
            errors.append(create_error_msg(
                f"{key_prefix}.runcmd", str(type(rc).__name__),
                en_us_validation_msg.ADDITIONAL_CLOUD_INIT_RUNCMD_NOT_LIST_MSG,
            ))
        else:
            for idx, entry in enumerate(rc):
                if not isinstance(entry, str):
                    errors.append(create_error_msg(
                        f"{key_prefix}.runcmd[{idx}]", str(type(entry).__name__),
                        en_us_validation_msg.ADDITIONAL_CLOUD_INIT_RUNCMD_NOT_STRING_MSG,
                    ))

    return errors


def validate_additional_cloud_init_config(config_file_path, pxe_mapping_file_path):
    """Validate the additional cloud-init configuration file.

    Checks:
      - File exists and is valid YAML
      - Top-level keys are only 'common' and 'groups'
      - Per-section: no prohibited keys, only allowed keys, type checks
      - Group names match functional groups from pxe_mapping_file

    Args:
        config_file_path (str): Path to additional_cloud_init config file.
        pxe_mapping_file_path (str): Path to PXE mapping CSV for FG name validation.

    Returns:
        list: List of error dicts (empty if valid).
    """
    errors = []
    if not config_file_path or not config_file_path.strip():
        return errors

    config_file_path = config_file_path.strip()

    if not os.path.isfile(config_file_path):
        errors.append(create_error_msg(
            "additional_cloud_init_config_file", config_file_path,
            en_us_validation_msg.ADDITIONAL_CLOUD_INIT_FILE_NOT_FOUND_MSG,
        ))
        return errors

    try:
        with open(config_file_path, "r", encoding="utf-8") as fh:
            config_data = yaml.safe_load(fh)
    except yaml.YAMLError as exc:
        errors.append(create_error_msg(
            "additional_cloud_init_config_file", config_file_path,
            f"{en_us_validation_msg.ADDITIONAL_CLOUD_INIT_YAML_SYNTAX_MSG} {exc}",
        ))
        return errors

    if config_data is None:
        return errors

    if not isinstance(config_data, dict):
        errors.append(create_error_msg(
            "additional_cloud_init_config_file", str(type(config_data).__name__),
            en_us_validation_msg.ADDITIONAL_CLOUD_INIT_NOT_DICT_MSG,
        ))
        return errors

    top_level_keys = ["common", "groups"]
    for key in config_data:
        if key not in top_level_keys:
            errors.append(create_error_msg(
                f"additional_cloud_init.{key}", key,
                en_us_validation_msg.ADDITIONAL_CLOUD_INIT_UNKNOWN_TOP_KEY_MSG,
            ))

    common_data = config_data.get("common") or {}
    groups_data = config_data.get("groups") or {}

    if common_data:
        errors.extend(_validate_cloud_init_section("common", common_data))

    if groups_data:
        if not isinstance(groups_data, dict):
            errors.append(create_error_msg(
                "additional_cloud_init.groups", str(type(groups_data).__name__),
                en_us_validation_msg.ADDITIONAL_CLOUD_INIT_SECTION_NOT_DICT_MSG,
            ))
        else:
            valid_fg_names = _get_fg_names_from_mapping_file(pxe_mapping_file_path)
            for fg_name, section_data in groups_data.items():
                if valid_fg_names and fg_name not in valid_fg_names:
                    errors.append(create_error_msg(
                        f"additional_cloud_init.groups.{fg_name}", fg_name,
                        en_us_validation_msg.ADDITIONAL_CLOUD_INIT_INVALID_FG_MSG,
                    ))
                if section_data:
                    errors.extend(_validate_cloud_init_section(fg_name, section_data))

    return errors


def validate_provision_config(
    input_file_path, data, logger, module, omnia_base_dir, module_utils_base, project_name
):
    """
    Validates the provision configuration.

    Args:
        input_file_path (str): The path to the input file.
        data (dict): The data to be validated.
        logger (Logger): A logger instance.
        module (Module): A module instance.
        omnia_base_dir (str): The base directory of the Omnia configuration.
        module_utils_base (str): The base directory of the module utils.
        project_name (str): The name of the project.

    Returns:
        list: A list of errors encountered during validation.
    """
    errors = []
    software_config_file_path = create_file_path(input_file_path, file_names["software_config"])
    try:
        with open(software_config_file_path, "r", encoding="utf-8") as f:
            software_config_json = json.load(f)
    except json.JSONDecodeError as e:
        # Return error with correct filename using proper format
        return [create_error_msg("JSON syntax error", software_config_file_path, str(e))]

    # Call validate_software_config from common_validation
    software_errors = common_validation.validate_software_config(
        software_config_file_path,
        software_config_json,
        logger,
        module,
        omnia_base_dir,
        module_utils_base,
        project_name,
    )
    errors.extend(software_errors)

    # Validate language setting
    language = data.get("language", "")
    if not language:
        errors.append(
            create_error_msg("language", input_file_path, en_us_validation_msg.LANGUAGE_EMPTY_MSG)
        )
    elif "en_US.UTF-8" not in language:
        errors.append(
            create_error_msg("language", input_file_path, en_us_validation_msg.LANGUAGE_FAIL_MSG)
        )

    enable_build_stream = data.get("enable_build_stream", False)

    # Override from build_stream_config.yml if present
    try:
        build_stream_config_path = create_file_path(input_file_path, file_names["build_stream_config"])
        if os.path.isfile(build_stream_config_path):
            with open(build_stream_config_path, "r", encoding="utf-8") as bfh:
                bs_cfg = yaml.safe_load(bfh) or {}
                enable_build_stream = bs_cfg.get("enable_build_stream", enable_build_stream)
    except Exception:
        # If file missing or malformed, fall back to provided data value
        pass

    pxe_mapping_file_path = data.get("pxe_mapping_file_path", "")
    if pxe_mapping_file_path and validation_utils.verify_path(pxe_mapping_file_path):
        try:
            validate_mapping_file_entries(pxe_mapping_file_path)
            validate_functional_groups_in_mapping_file(pxe_mapping_file_path)
            validate_duplicate_service_tags_in_mapping_file(pxe_mapping_file_path)
            validate_duplicate_hostnames_in_mapping_file(pxe_mapping_file_path)
            validate_duplicate_admin_ips_in_mapping_file(pxe_mapping_file_path)
            validate_duplicate_ib_ips_in_mapping_file(pxe_mapping_file_path)
            validate_ib_nic_name_format_in_mapping_file(pxe_mapping_file_path)
            validate_group_parent_service_tag_consistency_in_mapping_file(pxe_mapping_file_path)
            validate_functional_groups_separation(pxe_mapping_file_path)
            validate_parent_service_tag_hierarchy(pxe_mapping_file_path)
            validate_slurm_login_compiler_prefix(pxe_mapping_file_path)
            validate_aarch64_local_path_compatibility(pxe_mapping_file_path)
            validate_functional_groups_software_consistency(pxe_mapping_file_path, software_config_json, logger)
            dns_enabled = data.get("dns_enabled", False)
            if isinstance(dns_enabled, str):
                dns_enabled = dns_enabled.lower() in ("true", "yes", "1")
            validate_hostname_nid_format_when_dns_enabled(pxe_mapping_file_path, bool(dns_enabled))

            # Validate ADMIN_IPs against network_spec.yml subnets (including additional_subnets)
            network_spec_path = create_file_path(input_file_path, file_names["network_spec"])
            if os.path.isfile(network_spec_path):
                try:
                    with open(network_spec_path, "r", encoding="utf-8") as f:
                        network_spec_json = yaml.safe_load(f)

                    # Extract admin network configuration
                    admin_netmaskbits = None
                    oim_admin_ip = None
                    additional_subnets = []

                    for network in (network_spec_json or {}).get("Networks", []):
                        if "admin_network" in network and isinstance(network["admin_network"], dict):
                            admin_net = network["admin_network"]
                            admin_netmaskbits = admin_net.get("netmask_bits")
                            oim_admin_ip = admin_net.get("primary_oim_admin_ip")
                            additional_subnets = admin_net.get("additional_subnets") or []
                            break

                    if admin_netmaskbits and oim_admin_ip:
                        validate_pxe_admin_ips_subnet_consistency(
                            errors, pxe_mapping_file_path,
                            oim_admin_ip, admin_netmaskbits,
                            additional_subnets
                        )
                except (yaml.YAMLError, IOError) as e:
                    errors.append(
                        create_error_msg(
                            "network_spec.yml",
                            network_spec_path,
                            f"Failed to load or parse network_spec.yml: {str(e)}"
                        )
                    )
        except ValueError as e:
            errors.append(
                create_error_msg(
                    "pxe_mapping_file_path",
                    pxe_mapping_file_path,
                    str(e),
                )
            )
    else:
        errors.append(
            create_error_msg(
                "pxe_mapping_file_path",
                pxe_mapping_file_path,
                en_us_validation_msg.PXE_MAPPING_FILE_PATH_FAIL_MSG,
            )
        )

    default_lease_time = data["default_lease_time"]
    if not validation_utils.validate_default_lease_time(default_lease_time):
        errors.append(
            create_error_msg(
                "default_lease_time",
                default_lease_time,
                en_us_validation_msg.DEFAULT_LEASE_TIME_FAIL_MSG,
            )
        )

    kernel_version_override = data.get("kernel_version_override", "")
    if kernel_version_override:
        if not re.match(r"^[0-9]+\.[0-9]+\.[0-9]+-.+$", kernel_version_override):
            errors.append(
                create_error_msg(
                    "kernel_version_override",
                    kernel_version_override,
                    en_us_validation_msg.KERNEL_VERSION_OVERRIDE_FAIL_MSG,
                )
            )

    # Validate additional cloud-init config file
    aci_path = data.get("additional_cloud_init_config_file", "")
    if aci_path:
        aci_errors = validate_additional_cloud_init_config(aci_path, pxe_mapping_file_path)
        errors.extend(aci_errors)

    return errors


def validate_orchestrator_config(
    input_file_path, data, logger, module, omnia_base_dir, module_utils_base, project_name
):
    """
    Validates the orchestrator configuration.
    Subset of validate_provision_config — skips software_config and build_stream
    validation since the orchestrator does not own those files.
    """
    errors = []

    # Validate language setting
    language = data.get("language", "")
    if not language:
        errors.append(
            create_error_msg("language", input_file_path, en_us_validation_msg.LANGUAGE_EMPTY_MSG)
        )
    elif "en_US.UTF-8" not in language:
        errors.append(
            create_error_msg("language", input_file_path, en_us_validation_msg.LANGUAGE_FAIL_MSG)
        )

    pxe_mapping_file_path = data.get("pxe_mapping_file_path", "")
    if pxe_mapping_file_path and validation_utils.verify_path(pxe_mapping_file_path):
        try:
            validate_mapping_file_entries(pxe_mapping_file_path)
            validate_functional_groups_in_mapping_file(pxe_mapping_file_path)
            validate_duplicate_service_tags_in_mapping_file(pxe_mapping_file_path)
            validate_duplicate_hostnames_in_mapping_file(pxe_mapping_file_path)
            validate_duplicate_admin_ips_in_mapping_file(pxe_mapping_file_path)
            validate_duplicate_ib_ips_in_mapping_file(pxe_mapping_file_path)
            validate_ib_nic_name_format_in_mapping_file(pxe_mapping_file_path)
            validate_group_parent_service_tag_consistency_in_mapping_file(pxe_mapping_file_path)
            validate_functional_groups_separation(pxe_mapping_file_path)
            validate_parent_service_tag_hierarchy(pxe_mapping_file_path)
            validate_slurm_login_compiler_prefix(pxe_mapping_file_path)
            validate_aarch64_local_path_compatibility(pxe_mapping_file_path)
            dns_enabled = data.get("dns_enabled", False)
            if isinstance(dns_enabled, str):
                dns_enabled = dns_enabled.lower() in ("true", "yes", "1")
            validate_hostname_nid_format_when_dns_enabled(pxe_mapping_file_path, bool(dns_enabled))

            # Validate ADMIN_IPs against network_spec.yml subnets
            network_spec_path = create_file_path(input_file_path, file_names["network_spec"])
            if os.path.isfile(network_spec_path):
                try:
                    with open(network_spec_path, "r", encoding="utf-8") as f:
                        network_spec_json = yaml.safe_load(f)

                    admin_netmaskbits = None
                    oim_admin_ip = None
                    additional_subnets = []

                    for network in (network_spec_json or {}).get("Networks", []):
                        if "admin_network" in network and isinstance(network["admin_network"], dict):
                            admin_net = network["admin_network"]
                            admin_netmaskbits = admin_net.get("netmask_bits")
                            oim_admin_ip = admin_net.get("primary_oim_admin_ip")
                            additional_subnets = admin_net.get("additional_subnets") or []
                            break

                    if admin_netmaskbits and oim_admin_ip:
                        validate_pxe_admin_ips_subnet_consistency(
                            errors, pxe_mapping_file_path,
                            oim_admin_ip, admin_netmaskbits,
                            additional_subnets
                        )
                except (yaml.YAMLError, IOError) as e:
                    errors.append(
                        create_error_msg(
                            "network_spec.yml",
                            network_spec_path,
                            f"Failed to load or parse network_spec.yml: {str(e)}"
                        )
                    )
        except ValueError as e:
            errors.append(
                create_error_msg(
                    "pxe_mapping_file_path",
                    pxe_mapping_file_path,
                    str(e),
                )
            )
    else:
        errors.append(
            create_error_msg(
                "pxe_mapping_file_path",
                pxe_mapping_file_path,
                en_us_validation_msg.PXE_MAPPING_FILE_PATH_FAIL_MSG,
            )
        )

    default_lease_time = data["default_lease_time"]
    if not validation_utils.validate_default_lease_time(default_lease_time):
        errors.append(
            create_error_msg(
                "default_lease_time",
                default_lease_time,
                en_us_validation_msg.DEFAULT_LEASE_TIME_FAIL_MSG,
            )
        )

    kernel_version_override = data.get("kernel_version_override", "")
    if kernel_version_override:
        if not re.match(r"^[0-9]+\.[0-9]+\.[0-9]+-.+$", kernel_version_override):
            errors.append(
                create_error_msg(
                    "kernel_version_override",
                    kernel_version_override,
                    en_us_validation_msg.KERNEL_VERSION_OVERRIDE_FAIL_MSG,
                )
            )

    # Validate additional cloud-init config file
    aci_path = data.get("additional_cloud_init_config_file", "")
    if aci_path:
        aci_errors = validate_additional_cloud_init_config(aci_path, pxe_mapping_file_path)
        errors.extend(aci_errors)

    return errors


def validate_network_spec(
    input_file_path, data, logger, module, omnia_base_dir, module_utils_base, project_name
):
    """
    Validates the network specification configuration.
    Args:
        input_file_path (str): Path to the input configuration file
        data (dict): The network specification data to validate
        logger (Logger): Logger instance for logging messages
        module (AnsibleModule): Ansible module instance
        omnia_base_dir (str): Base directory path for Omnia
        module_utils_base (str): Base path for module utilities
        project_name (str): Name of the project

    Returns:
        list: List of validation errors, empty if no errors found
    """
    errors = []

    if not data.get("Networks"):
        errors.append(
            create_error_msg("Networks", None, en_us_validation_msg.ADMIN_NETWORK_MISSING_MSG)
        )
        return errors

    # Extract admin and IB parameters for cross-validation
    admin_netmask_bits = None
    admin_primary_ip = None
    ib_netmask_bits = None
    ib_subnet = None
    ib_present = False

    for network in data["Networks"]:
        if "admin_network" in network and isinstance(network["admin_network"], dict):
            admin_net = network["admin_network"]
            admin_netmask_bits = admin_net.get("netmask_bits", admin_netmask_bits)
            admin_primary_ip = admin_net.get("primary_oim_admin_ip", admin_primary_ip)

        if "ib_network" in network and isinstance(network["ib_network"], dict):
            ib_net = network["ib_network"]
            # Consider IB network present only when config is non-empty
            if ib_net:
                ib_present = True
                ib_netmask_bits = ib_net.get("netmask_bits", ib_netmask_bits)
                ib_subnet = ib_net.get("subnet", ib_subnet)

    # If IB network is configured and both netmask bits are available, they must match
    if ib_present and ib_netmask_bits and admin_netmask_bits and ib_netmask_bits != admin_netmask_bits:
        errors.append(
            create_error_msg(
                "ib_network.netmask_bits",
                ib_netmask_bits,
                en_us_validation_msg.IB_NETMASK_BITS_MISMATCH_MSG,
            )
        )

    # If IB subnet and admin primary IP are available, ensure IB subnet is not in admin range
    if ib_present and ib_subnet and admin_primary_ip and admin_netmask_bits:
        try:
            admin_network = ipaddress.IPv4Network(f"{admin_primary_ip}/{admin_netmask_bits}", strict=False)
            ib_ip = ipaddress.IPv4Address(ib_subnet)
            if ib_ip in admin_network:
                errors.append(
                    create_error_msg(
                        "ib_network.subnet",
                        ib_subnet,
                        en_us_validation_msg.IB_SUBNET_IN_ADMIN_RANGE_MSG,
                    )
                )
        except ValueError:
            # If IPs/netmask are invalid, rely on existing validations to report issues
            pass

    for network in data["Networks"]:
        errors.extend(_validate_admin_network(network))

    # Validate additional_subnets if present
    for network in data["Networks"]:
        if "admin_network" in network and isinstance(network["admin_network"], dict):
            admin_net = network["admin_network"]
            additional = admin_net.get("additional_subnets", [])
            if additional:
                errors.extend(_validate_additional_subnets(
                    additional, admin_net
                ))

    return errors


def _validate_admin_network(network):
    """
    Validates the admin network configuration.

    Args:
        network (dict): Admin network configuration dictionary containing network settings

    Returns:
        list: List of validation errors for admin network, empty if no errors found

    Validates:
        - Netmask bits
        - Network gateway
        - Dynamic IP ranges
    """
    errors = []
    if "admin_network" not in network:
        return errors

    admin_net = network["admin_network"]
    primary_oim_admin_ip = admin_net.get("primary_oim_admin_ip", "")
    primary_oim_bmc_ip = admin_net.get("primary_oim_bmc_ip", "")
    dynamic_range = admin_net.get("dynamic_range", "")
    oim_nic_name = admin_net.get("oim_nic_name", "")
    netmask_bits = admin_net.get("netmask_bits", "")

    # Ensure admin NIC is up
    if oim_nic_name:
        if not validation_utils.is_interface_up(oim_nic_name):
            errors.append(
                create_error_msg(
                    "admin_network.oim_nic_name",
                    oim_nic_name,
                    en_us_validation_msg.ADMIN_NIC_DOWN_MSG.format(nic=oim_nic_name),
                )
            )

    # Validate netmask_bits
    if "netmask_bits" in admin_net:
        netmask = admin_net["netmask_bits"]
        if not validation_utils.validate_netmask_bits(netmask):
            errors.append(
                create_error_msg(
                    "admin_network.netmask_bits",
                    netmask,
                    en_us_validation_msg.NETMASK_BITS_FAIL_MSG,
                )
            )

    # Validate IP ranges
    if "dynamic_range" in admin_net:
        errors.extend(
            _validate_ip_ranges(
                admin_net["dynamic_range"], "admin_network", netmask
            )
        )

        # Ensure dynamic_range is inside the admin subnet (primary_oim_admin_ip/netmask_bits)
        if not validation_utils.is_range_within_subnet(admin_net["dynamic_range"], primary_oim_admin_ip, netmask):
            errors.append(
                create_error_msg(
                    "admin_network.dynamic_range",
                    admin_net["dynamic_range"],
                    en_us_validation_msg.RANGE_NETMASK_BOUNDARY_FAIL_MSG,
                )
            )

    # Validate admin_network.router (mandatory, must be a valid IPv4 address)
    router = admin_net.get("router", "")
    if not router or not validation_utils.validate_ipv4(router):
        errors.append(
            create_error_msg(
                "admin_network.router",
                router,
                en_us_validation_msg.ADMIN_ROUTER_INVALID_MSG,
            )
        )

    #  Admin and BMC IP should not be the same
    errors.extend(validate_admin_bmc_ip_not_same(primary_oim_admin_ip, primary_oim_bmc_ip))

    # Both should be valid IPv4 addresses (BMC IP is optional)
    errors.extend(validate_admin_bmc_ip_valid(primary_oim_admin_ip, primary_oim_bmc_ip))

    # Neither should be in the dynamic_range
    errors.extend(validate_admin_bmc_ip_not_in_dynamic_range(primary_oim_admin_ip, primary_oim_bmc_ip, dynamic_range))

    # Ensure primary_oim_admin_ip matches actual NIC IP and netmask
    # Ensure primary_oim_admin_ip matches actual NIC IP and netmask
    if oim_nic_name and primary_oim_admin_ip and netmask_bits:
        nic_ips = validation_utils.get_interface_ips_and_netmasks(oim_nic_name)  # returns list of (ip, netmask_bits)

        # Check if any IP/netmask pair matches
        match_found = any(
            ip == primary_oim_admin_ip and nm == netmask_bits
            for ip, nm in nic_ips
        )

        if not match_found:
            errors.append(
                create_error_msg(
                    "primary_oim_admin_ip",
                    primary_oim_admin_ip,
                    f"{en_us_validation_msg.PRIMARY_ADMIN_IP_INTERFACE_MISMATCH_MSG}: "
                    f"IP/netmask on {oim_nic_name} is {nic_ips}, "
                    f"but network_spec has {primary_oim_admin_ip}/{netmask_bits}."
                )
            )

    return errors

def validate_admin_bmc_ip_not_same(primary_oim_admin_ip, primary_oim_bmc_ip):
    """
    Validates that primary_oim_admin_ip and primary_oim_bmc_ip are not the same.
    """
    errors = []
    if primary_oim_admin_ip and primary_oim_bmc_ip and primary_oim_admin_ip == primary_oim_bmc_ip:
        errors.append(
            create_error_msg(
                "primary_oim_admin_ip",
                primary_oim_admin_ip,
                en_us_validation_msg.PRIMARY_ADMIN_BMC_IP_SAME_MSG
            )
        )
    return errors

def validate_admin_bmc_ip_valid(primary_oim_admin_ip, primary_oim_bmc_ip):
    """
    Validates that both primary_oim_admin_ip and primary_oim_bmc_ip are valid IPv4 addresses.
    """
    errors = []
    if primary_oim_admin_ip and not validation_utils.validate_ipv4(primary_oim_admin_ip):
        errors.append(
            create_error_msg(
                "primary_oim_admin_ip",
                primary_oim_admin_ip,
                en_us_validation_msg.PRIMARY_ADMIN_IP_INVALID_MSG
            )
        )
    if primary_oim_bmc_ip and not validation_utils.validate_ipv4(primary_oim_bmc_ip):
        errors.append(
            create_error_msg(
                "primary_oim_bmc_ip",
                primary_oim_bmc_ip,
                en_us_validation_msg.PRIMARY_BMC_IP_INVALID_MSG
            )
        )
    return errors

def validate_admin_bmc_ip_not_in_dynamic_range(
        primary_oim_admin_ip, primary_oim_bmc_ip, dynamic_range
):
    """
    Validates that neither primary_oim_admin_ip nor primary_oim_bmc_ip are
    within the dynamic_range.
    """
    errors = []
    if dynamic_range:
        if primary_oim_admin_ip and validation_utils.is_ip_within_range(
                dynamic_range, primary_oim_admin_ip
        ):
            errors.append(
                create_error_msg(
                    "primary_oim_admin_ip",
                    primary_oim_admin_ip,
                    en_us_validation_msg.PRIMARY_ADMIN_IP_IN_DYNAMIC_RANGE_MSG
                )
            )
        if primary_oim_bmc_ip and validation_utils.is_ip_within_range(
                dynamic_range, primary_oim_bmc_ip
        ):
            errors.append(
                create_error_msg(
                    "primary_oim_bmc_ip",
                    primary_oim_bmc_ip,
                    en_us_validation_msg.PRIMARY_BMC_IP_IN_DYNAMIC_RANGE_MSG
                )
            )
    return errors

def _validate_ip_ranges(dynamic_range, network_type, netmask_bits):
    """
    Validates a dynamic IP range for a given network type and netmask.

    Args:
        dynamic_range (str): IP range for dynamic addresses (format: "start_ip-end_ip")
        network_type (str): Type of network being validated ("admin_network")
        netmask_bits (str): The netmask bits value to validate IP ranges against

    Returns:
        list: List of validation errors for IP ranges, empty if no errors found

    Validates:
        - Dynamic IP range format.
        - Dynamic IP range is within valid netmask boundaries.
    """
    errors = []

    if not validation_utils.validate_ipv4_range(dynamic_range):
        errors.append(
            create_error_msg(
                f"{network_type}.dynamic_range",
                dynamic_range,
                en_us_validation_msg.RANGE_IP_CHECK_FAIL_MSG,
            )
        )

    return errors


def _validate_additional_subnets(additional_subnets, admin_net):
    """
    Validates additional_subnets entries for multi-subnet / multi-RAC DHCP support.

    Checks:
        - Each subnet/netmask_bits forms a valid CIDR network.
        - Router IP is a valid IPv4 address within the subnet.
        - dynamic_range is valid and falls within the subnet.
        - Additional subnets do not overlap with the admin network.
        - Additional subnets do not overlap with each other.
        - dynamic_ranges do not overlap with admin dynamic_range or each other.

    Args:
        additional_subnets (list): List of additional subnet dicts.
        admin_net (dict): The admin_network configuration dict.

    Returns:
        list: Validation error messages.
    """
    errors = []
    admin_ip = admin_net.get("primary_oim_admin_ip", "")
    admin_netmask = admin_net.get("netmask_bits", "")
    admin_dynamic = admin_net.get("dynamic_range", "")

    # Build admin network object for overlap checks
    try:
        admin_network_obj = ipaddress.IPv4Network(
            f"{admin_ip}/{admin_netmask}", strict=False
        )
    except (ValueError, TypeError):
        admin_network_obj = None

    seen_networks = []
    all_ranges = []

    # Collect admin dynamic_range for overlap checking
    if admin_dynamic and "-" in admin_dynamic:
        all_ranges.append(("admin_network.dynamic_range", admin_dynamic))

    for idx, entry in enumerate(additional_subnets):
        prefix = f"additional_subnets[{idx}]"
        subnet_str = entry.get("subnet", "")
        netmask_bits = entry.get("netmask_bits", "")
        router = entry.get("router", "")
        dynamic_range = entry.get("dynamic_range", "")

        # Validate netmask_bits
        if not validation_utils.validate_netmask_bits(netmask_bits):
            errors.append(
                create_error_msg(
                    f"{prefix}.netmask_bits",
                    netmask_bits,
                    en_us_validation_msg.NETMASK_BITS_FAIL_MSG,
                )
            )
            continue

        # Build subnet network object
        try:
            subnet_network = ipaddress.IPv4Network(
                f"{subnet_str}/{netmask_bits}", strict=False
            )
        except (ValueError, TypeError):
            errors.append(
                create_error_msg(
                    f"{prefix}.subnet",
                    subnet_str,
                    "Invalid subnet address.",
                )
            )
            continue

        # Validate router is within subnet
        try:
            router_ip = ipaddress.IPv4Address(router)
            if router_ip not in subnet_network:
                errors.append(
                    create_error_msg(
                        f"{prefix}.router",
                        router,
                        en_us_validation_msg.ADDITIONAL_SUBNET_ROUTER_NOT_IN_SUBNET_MSG,
                    )
                )
        except (ValueError, TypeError):
            errors.append(
                create_error_msg(
                    f"{prefix}.router",
                    router,
                    en_us_validation_msg.ADDITIONAL_SUBNET_ROUTER_INVALID_MSG,
                )
            )

        # Validate dynamic_range format
        if not validation_utils.validate_ipv4_range(dynamic_range):
            errors.append(
                create_error_msg(
                    f"{prefix}.dynamic_range",
                    dynamic_range,
                    en_us_validation_msg.RANGE_IP_CHECK_FAIL_MSG,
                )
            )
        else:
            # Validate dynamic_range is within subnet
            if not validation_utils.is_range_within_subnet(
                dynamic_range, subnet_str, netmask_bits
            ):
                errors.append(
                    create_error_msg(
                        f"{prefix}.dynamic_range",
                        dynamic_range,
                        en_us_validation_msg.ADDITIONAL_SUBNET_RANGE_OUTSIDE_MSG,
                    )
                )

        # Check overlap with admin network
        if admin_network_obj:
            if subnet_network.overlaps(admin_network_obj):
                errors.append(
                    create_error_msg(
                        f"{prefix}.subnet",
                        str(subnet_network),
                        en_us_validation_msg.ADDITIONAL_SUBNET_OVERLAP_ADMIN_MSG,
                    )
                )

        # Check overlap with previously seen additional subnets
        for prev_idx, prev_net in seen_networks:
            if subnet_network.overlaps(prev_net):
                errors.append(
                    create_error_msg(
                        f"{prefix}.subnet",
                        str(subnet_network),
                        (
                            f"{en_us_validation_msg.ADDITIONAL_SUBNET_OVERLAP_EACH_OTHER_MSG}"
                            f" Overlaps with additional_subnets[{prev_idx}]."
                        ),
                    )
                )

        seen_networks.append((idx, subnet_network))

        # Collect dynamic_range for cross-range overlap checks
        if dynamic_range and "-" in dynamic_range:
            all_ranges.append((f"{prefix}.dynamic_range", dynamic_range))

    # Cross-check all dynamic ranges for overlap
    for i in range(len(all_ranges)):
        for j in range(i + 1, len(all_ranges)):
            name_i, range_i = all_ranges[i]
            name_j, range_j = all_ranges[j]
            if _ranges_overlap(range_i, range_j):
                errors.append(
                    create_error_msg(
                        name_j,
                        range_j,
                        (
                            f"dynamic_range overlaps with {name_i}. "
                            "DHCP pools must not overlap."
                        ),
                    )
                )

    return errors


def _ranges_overlap(range_a, range_b):
    """Check if two IP ranges in 'start-end' format overlap.

    Args:
        range_a (str): First range, e.g. '10.0.0.1-10.0.0.50'.
        range_b (str): Second range.

    Returns:
        bool: True if the ranges overlap, False otherwise.
    """
    try:
        a_parts = range_a.split("-")
        b_parts = range_b.split("-")
        if len(a_parts) != 2 or len(b_parts) != 2:
            return False
        a_start = ipaddress.IPv4Address(a_parts[0].strip())
        a_end = ipaddress.IPv4Address(a_parts[1].strip())
        b_start = ipaddress.IPv4Address(b_parts[0].strip())
        b_end = ipaddress.IPv4Address(b_parts[1].strip())
        return a_start <= b_end and b_start <= a_end
    except (ValueError, TypeError):
        return False



def validate_dns_config(data):
    """
    Validates dns_config input parameters.

    dns_config.yml only contains dns_enabled (boolean).
    The cluster domain is read from OIM metadata (domain_name).

    Args:
        data (dict): The dns_config dict from dns_config.yml.

    Returns:
        list: Validation error messages (currently empty; schema
        validation handles the dns_enabled type check).
    """
    return []
