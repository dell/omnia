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
# pylint: disable=too-many-arguments,import-error,no-name-in-module
# pylint: disable=too-many-locals,too-many-positional-arguments
"""
This module contains functions for validating VIP against PXE mapping file.
"""
import csv
import os
from ansible.module_utils.input_validation.common_utils import validation_utils

create_error_msg = validation_utils.create_error_msg


def extract_host_ips_from_pxe_mapping(pxe_mapping_file_path):
    """
    Extract all ADMIN_IP values from PXE mapping file.

    Parameters:
        pxe_mapping_file_path (str): Path to the PXE mapping file

    Returns:
        list: List of ADMIN_IP values (node admin IPs)
    """
    host_ips = []

    if not pxe_mapping_file_path or not os.path.isfile(pxe_mapping_file_path):
        return host_ips

    try:
        with open(pxe_mapping_file_path, "r", encoding="utf-8") as fh:
            raw_lines = fh.readlines()

        non_comment_lines = [
            ln for ln in raw_lines
            if ln.strip() and not ln.strip().startswith('#')
        ]
        reader = csv.DictReader(non_comment_lines)

        fieldname_map = {fn.strip().upper(): fn for fn in reader.fieldnames}
        admin_ip_col = fieldname_map.get("ADMIN_IP")

        if admin_ip_col:
            for row in reader:
                admin_ip_value = row.get(admin_ip_col, "").strip() \
                    if row.get(admin_ip_col) else ""
                if admin_ip_value and \
                        validation_utils.validate_ipv4(admin_ip_value):
                    host_ips.append(admin_ip_value)

    except (OSError, csv.Error):
        # If file can't be read, return empty list
        pass

    return host_ips


def validate_vip_vs_pxe_mapping_host_ips(
        errors, config_type, vip_address, pxe_mapping_file_path):
    """
    Validate that VIP doesn't conflict with any ADMIN_IP in PXE mapping file.

    Parameters:
        errors (list): List to append error messages
        config_type (str): Configuration type for error reporting
        vip_address (str): VIP address to validate
        pxe_mapping_file_path (str): Path to PXE mapping file
    """
    host_ips = extract_host_ips_from_pxe_mapping(pxe_mapping_file_path)

    for host_ip in host_ips:
        if vip_address == host_ip:
            errors.append(
                create_error_msg(
                    f"{config_type} virtual_ip_address",
                    vip_address,
                    "VIP cannot be the same as any ADMIN_IP in PXE "
                    f"mapping file. VIP {vip_address} conflicts with "
                    f"node ADMIN_IP {host_ip}. "
                    "Please use a different VIP address."
                )
            )
            break  # Only need to report once


def validate_all_host_ips_same_subnet_as_vip(
        errors, vip_address, pxe_mapping_file_path, admin_netmaskbits,
        additional_subnets=None, oim_admin_ip=None):
    """
    Validate that all ADMIN_IPs in PXE mapping are in a known subnet
    (primary admin subnet, VIP subnet, or any additional subnet).

    Parameters:
        errors (list): List to append error messages
        vip_address (str): VIP address to validate against
        pxe_mapping_file_path (str): Path to PXE mapping file
        admin_netmaskbits (str): Netmask bits for subnet validation
        additional_subnets (list, optional): List of additional subnet
            dicts with 'subnet' and 'netmask_bits' keys.
        oim_admin_ip (str, optional): Primary OIM admin IP address for
            checking the primary admin subnet.
    """
    host_ips = extract_host_ips_from_pxe_mapping(pxe_mapping_file_path)
    if additional_subnets is None:
        additional_subnets = []

    for host_ip in host_ips:
        # Check if host_ip is in the VIP subnet
        if validation_utils.is_ip_in_subnet(
                vip_address, admin_netmaskbits, host_ip):
            continue

        # Check if host_ip is in the primary admin subnet
        if oim_admin_ip and validation_utils.is_ip_in_subnet(
                oim_admin_ip, admin_netmaskbits, host_ip):
            continue

        # Check if host_ip is in any additional subnet
        in_additional = False
        for subnet_entry in additional_subnets:
            subnet_addr = subnet_entry.get("subnet", "")
            subnet_bits = subnet_entry.get("netmask_bits", "")
            if subnet_addr and subnet_bits:
                if validation_utils.is_ip_in_subnet(
                        subnet_addr, subnet_bits, host_ip):
                    in_additional = True
                    break

        if not in_additional:
            errors.append(
                create_error_msg(
                    "ADMIN_IP subnet consistency",
                    host_ip,
                    f"Node ADMIN_IP {host_ip} must be in the same "
                    f"subnet as VIP {vip_address} or in one of the "
                    "configured additional_subnets. "
                    "Please ensure all ADMIN_IPs in PXE mapping file "
                    "are in a known subnet."
                )
            )