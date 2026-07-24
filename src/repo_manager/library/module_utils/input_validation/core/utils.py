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
"""
Common utility functions for input validation.

This module provides generic utility functions used across validators:
- Error message creation
- Path manipulation
- IP address validation
- Password validation
- Range checking
"""
import ipaddress
import subprocess

from ansible.module_utils.input_validation.core.config import TYPE_REQUIREMENTS

# =============================================================================
# ERROR MESSAGE UTILITIES
# =============================================================================


def create_error_msg(key, value, msg):
    """
    Creates an error message dictionary.

    Args:
        key (str): The key of the error.
        value (str): The value of the error.
        msg (str): The error message.

    Returns:
        dict: The error message dictionary.
    """
    return {"error_key": key, "error_value": value, "error_msg": msg}


def create_file_path(input_file_path, other_file):
    """
    Creates a file path by replacing the last part of the input file path.

    Args:
        input_file_path (str): The input file path.
        other_file (str): The name of the other file.

    Returns:
        str: The new file path.
    """
    path_parts = input_file_path.split("/")
    path_parts[-1] = other_file
    return "/".join(path_parts)


# =============================================================================
# STRING UTILITIES
# =============================================================================

def is_string_empty(value):
    """
    Checks if a string is empty.

    Args:
        value (str): The string to check.

    Returns:
        bool: True if the string is empty, False otherwise.
    """
    if value is None:
        return True
    if not isinstance(value, str):
        return False
    return len(value.strip()) < 1


def flatten_sub_groups(sub_groups):
    """
    Flattens a list of sub-groups.

    Args:
        sub_groups (list): A list of sub-groups.

    Returns:
        list: A flattened list of individual groups.
    """
    result = []
    for group in sub_groups:
        result.extend(group.split(','))
    return result


def extract_arch_from_fg(fg_name):
    """
    Extracts the architecture suffix from a functional group name.

    Args:
        fg_name (str): The functional group name.

    Returns:
        str or None: The architecture suffix if found, otherwise None.
    """
    valid_arches = {"x86_64", "aarch64"}
    for arch in valid_arches:
        if fg_name.endswith(f"_{arch}"):
            return arch
    return None


# =============================================================================
# IP ADDRESS UTILITIES
# =============================================================================

def validate_ipv4(ip: str) -> bool:
    """
    Validates if the given IP is a valid IPv4 address.

    Args:
        ip (str): The given IP address to be validated.

    Returns:
        bool: True if valid IPv4 address, False otherwise.
    """
    try:
        ipaddress.IPv4Address(ip)
        return True
    except ipaddress.AddressValueError:
        return False


def validate_ipv4_range(ip_range) -> bool:
    """
    Validates if the given IP range is a valid IPv4 range.

    Args:
        ip_range (str): The IP range to be validated.

    Returns:
        bool: True if the IP range is valid, False otherwise.
    """
    try:
        start, end = ip_range.split('-')
        start_ip = ipaddress.IPv4Address(start)
        end_ip = ipaddress.IPv4Address(end)
        return end_ip >= start_ip
    except ValueError:
        return False


def validate_netmask_bits(bits):
    """
    Validates if the given netmask bits are within the valid range.

    Args:
        bits (str): The netmask bits to be validated.

    Returns:
        bool: True if the netmask bits are valid, False otherwise.
    """
    try:
        bits_int = int(bits)
        return 1 <= bits_int <= 32
    except (ValueError, TypeError):
        return False


def is_range_within_subnet(ip_range, reference_ip, netmask_bits):
    """
    Validates that the given IP range falls within the subnet.

    Args:
        ip_range (str): IP range in "start_ip-end_ip" format.
        reference_ip (str): A reference IP in the subnet.
        netmask_bits (str or int): The CIDR prefix length.

    Returns:
        bool: True if both IPs are within the subnet, False otherwise.
    """
    try:
        network = ipaddress.IPv4Network(f"{reference_ip}/{netmask_bits}", strict=False)
        parts = ip_range.split("-")
        if len(parts) != 2:
            return False
        start_ip = ipaddress.IPv4Address(parts[0].strip())
        end_ip = ipaddress.IPv4Address(parts[1].strip())
        return start_ip in network and end_ip in network
    except (ValueError, TypeError):
        return False


def is_ip_within_range(ip_range, ip):
    """
    Check if a given IP falls within a specified IP range.

    Args:
        ip_range (str): The IP range in format "start_ip-end_ip".
        ip (str): The IP address to check.

    Returns:
        bool: True if the IP is within the range, False otherwise.
    """
    start_ip, end_ip = [ipaddress.IPv4Address(part.strip()) for part in ip_range.split('-')]
    target_ip = ipaddress.IPv4Address(ip)
    return start_ip <= target_ip <= end_ip


def is_ip_in_subnet(admin_oim_ip, netmask_bits, vip_address):
    """
    Check if a given IP falls within the subnet.

    Args:
        admin_oim_ip (str): The admin OIM IP address.
        netmask_bits (int or str): The netmask bits.
        vip_address (str): The IP address to check.

    Returns:
        bool: True if the IP is within the subnet, False otherwise.
    """
    subnet = ipaddress.IPv4Network(f"{admin_oim_ip}/{netmask_bits}", strict=False)
    ip = ipaddress.IPv4Address(vip_address)
    return ip in subnet


def check_overlap(ip_list):
    """
    Checks for IP range overlap.

    Args:
        ip_list (list): A list of IP ranges and CIDR.

    Returns:
        tuple: A tuple containing a boolean indicating overlap and list of overlapping ranges.
    """
    ranges = []
    overlaps = []

    for item in ip_list:
        if item in ('', 'N/A'):
            continue
        if "-" in item:
            start_ip, end_ip = item.split("-")
            start_ip = ipaddress.ip_address(start_ip)
            end_ip = ipaddress.ip_address(end_ip)
            networks = list(ipaddress.summarize_address_range(start_ip, end_ip))
            ranges.extend(networks)
        else:
            ranges.append(ipaddress.ip_network(item, strict=False))

    for i in range(len(ranges)):
        for j in range(i + 1, len(ranges)):
            if ranges[i].overlaps(ranges[j]):
                overlaps.append((ranges[i], ranges[j]))

    return len(overlaps) > 0, overlaps


def get_interface_ips_and_netmasks(interface):
    """
    Returns all IPv4 addresses and their netmask bits for an interface.

    Args:
        interface (str): Interface name (e.g., "eno3").

    Returns:
        list of tuples: [(ip, netmask_bits), ...]
    """
    results = []
    try:
        result = subprocess.run(
            ["ip", "-4", "addr", "show", interface],
            capture_output=True, text=True, check=True
        )
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("inet "):
                ip_with_mask = line.split()[1]
                ip_interface = ipaddress.ip_interface(ip_with_mask)
                results.append((str(ip_interface.ip), str(ip_interface.network.prefixlen)))
        return results
    except Exception:
        return []


def is_interface_up(interface: str) -> bool:
    """
    Return True if the interface link state is UP.

    Args:
        interface (str): Interface name.

    Returns:
        bool: True if interface is up, False otherwise.
    """
    try:
        with open(f"/sys/class/net/{interface}/operstate", "r", encoding="utf-8") as f:
            return f.read().strip() == "up"
    except Exception:
        return False


# =============================================================================
# PASSWORD VALIDATION
# =============================================================================

def is_valid_password(password):
    """
    Validates the password.

    Args:
        password (str): The password to validate.

    Returns:
        bool: True if the password is valid, False otherwise.
    """
    if not isinstance(password, str):
        return False
    if len(password) <= 8 or len(password) >= 30:
        return False
    invalid_chars = ["-", "\\", "'", '"']
    for char in invalid_chars:
        if char in password:
            return False
    return True


def validate_username(username, min_username_length, max_length):
    """
    Validates the username.

    Args:
        username (str): The username to validate.
        min_username_length (int): The minimum length of the username.
        max_length (int): The maximum length of the username.

    Returns:
        bool: True if the username is valid, False otherwise.
    """
    if not (min_username_length <= len(username) < max_length):
        return False
    forbidden_characters = {"-", "\\", "'", '"'}
    if any(char in username for char in forbidden_characters):
        return False
    return True


def validate_default_lease_time(default_lease_time):
    """
    Validates the default lease time.

    Args:
        default_lease_time (int): The default lease time.

    Returns:
        bool: True if the default lease time is valid, False otherwise.
    """
    return 21600 <= int(default_lease_time) <= 31536000


# =============================================================================
# PORT VALIDATION
# =============================================================================

def check_port_overlap(port_ranges) -> bool:
    """
    Check if any of the port ranges overlap.

    Args:
        port_ranges (str): A string of port ranges separated by commas.

    Returns:
        bool: True if any of the port ranges overlap, False otherwise.
    """
    ports = set()
    for port_range in port_ranges.split(','):
        if '-' in port_range:
            start, end = map(int, port_range.split('-'))
            for port in range(start, end + 1):
                if port in ports:
                    return True
                ports.add(port)
        else:
            if ':' not in port_range and port_range.isdigit():
                port = int(port_range)
            else:
                port = port_range
            if port in ports:
                return True
            ports.add(port)
    return False


def check_port_ranges(port_ranges) -> bool:
    """
    Check if any of the port ranges are invalid.

    Args:
        port_ranges (str): A string of port ranges separated by commas.

    Returns:
        bool: False if any of the port ranges are invalid, True otherwise.
    """
    for port_range in port_ranges.split(','):
        if '-' in port_range:
            start, end = map(int, port_range.split('-'))
            if start > end:
                return False
    return True


# =============================================================================
# DATA VALIDATION UTILITIES
# =============================================================================

def key_value_exists(list_of_dicts, key, value) -> bool:
    """
    Check if a key-value pair exists in a list of dictionaries.

    Args:
        list_of_dicts (list): The list of dictionaries to search.
        key: The key to search for.
        value: The value to search for.

    Returns:
        bool: True if the key-value pair exists, False otherwise.
    """
    for dictionary in list_of_dicts:
        if dictionary.get(key) == value:
            return True
    return False


def contains_software(softwares, name):
    """
    Checks if a software is present in the list of softwares.

    Args:
        softwares (list): The list of softwares.
        name (str): The name of the software to check.

    Returns:
        bool: True if the software is present, False otherwise.
    """
    return any(name in software["name"].lower() for software in softwares)


def check_mandatory_fields(mandatory_fields, data, errors):
    """
    Checks if all mandatory fields are present in the data.

    Args:
        mandatory_fields (list): The list of mandatory fields.
        data (dict): The data to check.
        errors (list): The list of errors.
    """
    from ansible.module_utils.input_validation.messages.common_messages import MANDATORY_FIELD_FAIL_MSG
    for field in mandatory_fields:
        if is_string_empty(data.get(field)):
            errors.append(create_error_msg(field, data.get(field), MANDATORY_FIELD_FAIL_MSG))


def check_bmc_static_range_overlap(static_range, static_range_group_mapping) -> list:
    """
    Checks if the given static BMC range overlaps with any ranges in other groups.

    Args:
        static_range (str): The static BMC range to check.
        static_range_group_mapping (dict): A dictionary mapping group names to ranges.

    Returns:
        list: A list of group names that have overlapping ranges.
    """
    grp_overlaps = []
    ip_ranges = [static_range]
    for grp, grp_static_range in static_range_group_mapping.items():
        ip_ranges.append(grp_static_range)
        overlap_exists, _ = check_overlap(ip_ranges)
        if overlap_exists:
            grp_overlaps.append(grp)
        ip_ranges.pop()
    return grp_overlaps


# =============================================================================
# CLUSTER ITEM VALIDATION
# =============================================================================

def validate_cluster_items(cluster_items, json_file_path):
    """
    Validates the cluster items in a JSON file based on predefined type requirements.

    Args:
        cluster_items (list): A list of cluster items to validate.
        json_file_path (str): The path to the JSON file.

    Returns:
        tuple: A tuple containing two lists - successes and failures.
    """
    failures = []
    successes = []

    is_additional_packages = json_file_path.endswith('additional_packages.json')
    allowed_types_for_additional = {'rpm', 'image'}

    for item in cluster_items:
        item_type = item.get('type')

        if is_additional_packages and item_type not in allowed_types_for_additional:
            failures.append(
                f"Failed. Type '{item_type}' is not allowed in '{json_file_path}'. "
                f"Only 'rpm' and 'image' types are permitted in this file.")
            continue

        required_fields = TYPE_REQUIREMENTS.get(item_type)

        if not required_fields:
            failures.append(f"Failed. Unknown type '{item_type}' in file '{json_file_path}'.")
            continue

        if any(isinstance(field, list) for field in required_fields):
            flat_fields = [f for f in required_fields if isinstance(f, str)]
            alt_fields_groups = [f for f in required_fields if isinstance(f, list)]

            missing_flat = [f for f in flat_fields if f not in item]
            has_one_alt = any(any(alt in item for alt in group) for group in alt_fields_groups)

            if missing_flat or not has_one_alt:
                failures.append(
                    f"Failed. Missing required properties for '{item_type}' in file '{json_file_path}'.")
            else:
                successes.append(f"Success. Valid '{item_type}' item in file '{json_file_path}'.")
        else:
            missing_fields = [field for field in required_fields if field not in item]
            if missing_fields:
                failures.append(
                    f"Failed. Missing {missing_fields} for '{item_type}' in file '{json_file_path}'.")
            else:
                successes.append(f"Success. Valid '{item_type}' item in file '{json_file_path}'.")

    return successes, failures


def validate_softwaresubgroup_entries(software_name, json_path, json_data, validation_results, failures):
    """
    Validates the entries for a specific software subgroup in a JSON file.

    Args:
        software_name (str): The name of the software.
        json_path (str): The path to the JSON file.
        json_data (dict): The JSON data.
        validation_results (list): A list to store the validation results.
        failures (list): A list to store the failure messages.

    Returns:
        tuple: A tuple containing the updated validation results and failures.
    """
    try:
        if software_name in json_data:
            validation_results.append((json_path, True))
            if 'cluster' in json_data[software_name]:
                cluster_items = json_data[software_name]['cluster']
                item_successes, item_failures = validate_cluster_items(cluster_items, json_path)
                if item_failures:
                    failures.extend(item_failures)
            else:
                failures.append(
                    f"Failed. Invalid JSON format for: '{software_name}' in file '{json_path}'. "
                    f"Cluster property is missing")
        else:
            validation_results.append((json_path, False))
            failures.append(f"Failed. Invalid software name: '{software_name}' in file '{json_path}'.")

    except KeyError as e:
        failures.append(f"Failed. Missing key {str(e)} in file '{json_path}'.")
    except TypeError as e:
        failures.append(f"Failed. Type error in file '{json_path}': {str(e)}")
    except Exception as e:
        failures.append(f"Failed. Unexpected error in file '{json_path}': {str(e)}")

    return validation_results, failures
