# Copyright 2025 Dell Inc. or its subsidiaries. All Rights Reserved.
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
This module contains utility functions for input validation.
"""
import os
import ipaddress
import subprocess
import yaml
from ansible.module_utils.input_validation.common_utils import en_us_validation_msg
from ansible.module_utils.input_validation.common_utils import config

def load_yaml_as_json(yaml_file, omnia_base_dir, project_name, logger, module):
    """
    Loads a YAML file as JSON.

    Args:
        yaml_file (str): The path to the YAML file.
        omnia_base_dir (str): The base directory of the Omnia project.
        project_name (str): The name of the project.
        logger (Logger): A logger instance.
        module (AnsibleModule): An Ansible module instance.

    Returns:
        dict: The loaded YAML data as JSON.

    Raises:
        FileNotFoundError: If the YAML file is not found.
        yaml.YAMLError: If there is a syntax error in the YAML file.
    """
    try:
        if is_file_encrypted(yaml_file):
            data = process_encrypted_file(yaml_file, omnia_base_dir, project_name, logger, module)
            return data
        with open(yaml_file, "r") as f:
            data = yaml.safe_load(f)
            return data
    except FileNotFoundError:
        error_message = f"File {yaml_file} not found"
        logger.error(error_message)
        module.fail_json(msg=error_message)
    except yaml.YAMLError as e:
        error_parts = []
        error_parts.append(f"Syntax error when loading YAML file '{yaml_file}'")

        if hasattr(e, 'problem_mark'):
            error_parts.append(
                f"at line {e.problem_mark.line + 1}, column {e.problem_mark.column + 1}")
            if hasattr(e, 'problem'):
                error_parts.append(f"Problem: {e.problem}")
            if hasattr(e, 'context'):
                error_parts.append(f"Context: {e.context}")
        else:
            error_parts.append(str(e))

        error_context = " | ".join(error_parts)
        logger.error(error_context)
        # Instead of raising exception immediately, return None to indicate
        # validation failure, in case there are other validations to perform
        return None
    
def check_bmc_range_against_admin_network(bmc_range, admin_static_range, admin_dynamic_range, admin_ip):
    """
    Validates that the BMC static range does not overlap with:
    - Admin static range
    - Admin dynamic range
    - Primary OIM admin IP

    Args:
        bmc_range (str): BMC static range (start-end format)
        admin_static_range (str): Admin static range (start-end format)
        admin_dynamic_range (str): Admin dynamic range (start-end format)
        admin_ip (str): Primary OIM admin IP (single IP)

    Returns:
        list: A list of error strings if overlaps are found.
    """
    errors = []

    if not bmc_range or bmc_range in ["", "N/A"]:
        return errors  # Skip empty or N/A values

    # Check overlap with admin static and dynamic ranges
    for field_name, admin_range in [("admin static_range", admin_static_range), ("admin dynamic_range", admin_dynamic_range)]:
        if admin_range and admin_range not in ["", "N/A"]:
            has_overlap, _ = check_overlap([bmc_range, admin_range])
            if has_overlap:
                errors.append(f"BMC range {bmc_range} overlaps with {field_name}: {admin_range}")

    # Check containment of primary_oim_admin_ip
    if admin_ip and is_ip_within_range(bmc_range, admin_ip):
        errors.append(f"BMC range {bmc_range} contains primary_oim_admin_ip: {admin_ip}")

    return errors

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
    Creates a file path by replacing the last part of the input file path with another file name.

    Args:
        input_file_path (str): The input file path.
        other_file (str): The name of the other file.

    Returns:
        str: The new file path.
    """
    path_parts = input_file_path.split("/")
    path_parts[-1] = other_file
    final_path = ("/").join(path_parts)
    return final_path

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

    Returns:
        None
    """
    for field in mandatory_fields:
        if is_string_empty(data[field]):
            errors.append(
                create_error_msg(
                    field, data[field], en_us_validation_msg.MANDATORY_FIELD_FAIL_MSG
                )
            )

# Below functions used to deal with encrypted files
# (Check if a file is encrypted, if yes then get the vault password,
# decrypt file, load data, encrypt file again)
def is_file_encrypted(file_path):
    """
    Checks if a file is encrypted.

    Args:
        file_path (str): The path to the file.

    Returns:
        bool: True if the file is encrypted, False otherwise.
    """
    try:
        with open(file_path, 'r') as file:
            first_line = file.readline().strip()
            return first_line.startswith('$ANSIBLE_VAULT')
    except (IOError, OSError):
        return False

def process_encrypted_file(yaml_file, omnia_base_dir, project_name, logger, module):
    """
    Decrypts an encrypted file, loads the data, and encrypts the file again.

    Args:
        yaml_file (str): The path to the encrypted file.
        omnia_base_dir (str): The base directory of the Omnia project.
        project_name (str): The name of the project.
        logger (Logger): A logger instance.
        module (AnsibleModule): An Ansible module instance.

    Returns:
        dict: The loaded data from the encrypted file.
    """
    vault_password_file = config.get_vault_password(yaml_file)
    decrypted_file = decrypt_file(omnia_base_dir, project_name, yaml_file, vault_password_file)
    if decrypted_file:
        try:
            with open(yaml_file, "r") as f:
                data = yaml.safe_load(f)
                encrypt_file(omnia_base_dir, project_name, yaml_file, vault_password_file)
                return data
        except FileNotFoundError:
            logger.error("File {%s} not found" % yaml_file)
            module.fail_json(msg="File {%s} not found" % (yaml_file))
        except yaml.YAMLError as e:
            logger.error(f"Error loading YAML: {e}")
            module.fail_json(f"Error loading YAML: {e}")
    else:
        unable_to_decrypt_fail_msg = (
            f"Error occured when attempting to decrypt file. "
            f"Please check that the assoicated vault file exists for {yaml_file}")
        logger.error(unable_to_decrypt_fail_msg)
        module.fail_json(unable_to_decrypt_fail_msg)

def run_subprocess(cmd):
    """
    Runs a subprocess command and returns True if successful, False otherwise.

    Args:
        cmd (list): The command to run.

    Returns:
        bool: True if the command was successful, False otherwise.
    """
    try:
        subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False

def encrypt_file(omnia_base_dir, project_name, vault_file, vault_password_file):
    """
    Encrypts a file using Ansible Vault.

    Args:
        omnia_base_dir (str): The base directory of the Omnia project.
        project_name (str): The name of the project.
        vault_file (str): The path to the file to encrypt.
        vault_password_file (str): The path to the Ansible Vault password file.

    Returns:
        bool: True if the encryption was successful, False otherwise.
    """
    password_full_path = omnia_base_dir + project_name + "/" + vault_password_file
    cmd = [
        "ansible-vault",
        "encrypt",
        vault_file,
        "--vault-password-file",
        password_full_path,
    ]
    return run_subprocess(cmd)

def decrypt_file(omnia_base_dir, project_name, vault_file, vault_password_file):
    """
    Decrypts a file using Ansible Vault.

    Args:
        omnia_base_dir (str): The base directory of the Omnia project.
        project_name (str): The name of the project.
        vault_file (str): The path to the file to decrypt.
        vault_password_file (str): The path to the Ansible Vault password file.

    Returns:
        bool: True if the decryption was successful, False otherwise.
    """
    password_full_path = omnia_base_dir + project_name + "/" + vault_password_file
    cmd = [
        "ansible-vault",
        "decrypt",
        vault_file,
        "--vault-password-file",
        password_full_path,
    ]
    return run_subprocess(cmd)

# Below are common functions used in L2 validation (logical_validation.py)
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

def verify_path(file_path):
    """
    Verifies if a file exists at the given path.

    Args:
        file_path (str): The path to the file.

    Returns:
        bool: True if the file exists, False otherwise.
    """
    if not os.path.exists(file_path):
        return False
    return os.path.isfile(file_path)

def validate_default_lease_time(default_lease_time):
    """
    Validates the default lease time.

    Args:
        default_lease_time (int): The default lease time.

    Returns:
        bool: True if the default lease time is valid, False otherwise.
    """
    return 21600 <= int(default_lease_time) <= 31536000


def verify_iso_file(iso_file_path, provision_os, provision_os_version):
    """
    Verifies if the ISO file path is valid.

    Args:
        iso_file_path (str): The path to the ISO file.
        provision_os (str): The provision OS.
        provision_os_version (str): The provision OS version.

    Returns:
        str: An error message if the ISO file path is invalid, empty string otherwise.
    """
    if ".iso" not in iso_file_path:
        return en_us_validation_msg.ISO_FILE_PATH_NOT_CONTAIN_ISO_MSG

    iso_path_lower = iso_file_path.lower()
    os_name_matches = provision_os.lower() in iso_path_lower
    version_matches = provision_os_version in iso_path_lower

    if not (os_name_matches and version_matches):
        return en_us_validation_msg.iso_file_path_invalid_os_msg(
            iso_file_path, provision_os, provision_os_version
        )

    if not verify_path(iso_file_path):
        return en_us_validation_msg.ISO_FILE_PATH_FAIL_MSG

    return ""


# validate timezone (input_tz: str, available_timezone_file_path: str) -> bool
def validate_timezone(input_tz, available_timezone_file_path):
    """
    Validates the timezone.

    Args:
        input_tz (str): The input timezone.
        available_timezone_file_path (str): The path to the file containing available timezones.

    Returns:
        bool: True if the timezone is valid, False otherwise.
    """
    all_timezones = []
    with open(available_timezone_file_path, "r") as file:
        content = file.read()
        for line in content.splitlines():
            all_timezones.append(line)
    return input_tz in all_timezones


# Checks if the password meets the specified requirements:
# Length of at least 8 characters. Does not contain '-', '\', "'", or '"'.
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


# check_overlap(ip_list: list[dict[str, str]]) -> tuple[bool, list[tuple]]:
def check_overlap(ip_list):
    """
    Checks for IP range overlap.

    Args:
        ip_list (list): A list of IP ranges and CIDR.

    Returns:
        tuple: A tuple containing a boolean indicating if there is an overlap,
            and a list of overlapping IP ranges.
    """
    ranges = []
    overlaps = []

    # Convert IP ranges and CIDR to ipaddress objects
    for item in ip_list:
        if item in ('', 'N/A'):
            continue
        if "-" in item:
            start_ip, end_ip = item.split("-")
            start_ip = ipaddress.ip_address(start_ip)
            end_ip = ipaddress.ip_address(end_ip)
            # Convert IP range to a list of networks
            networks = list(ipaddress.summarize_address_range(start_ip, end_ip))
            ranges.extend(networks)
        else:
            ranges.append(ipaddress.ip_network(item, strict=False))

    # Check for overlaps using the overlaps() method
    for i in range(len(ranges)):
        for j in range(i + 1, len(ranges)):
            if ranges[i].overlaps(ranges[j]):
                overlaps.append((ranges[i], ranges[j]))

    return len(overlaps) > 0, overlaps

def key_value_exists(list_of_dicts, key, value) -> bool:
    """
    Check if a key-value pair exists in a list of dictionaries.

    Args:
        list_of_dicts (List[Dict[Any, Any]]): The list of dictionaries to search.
        key (Any): The key to search for.
        value (Any): The value to search for.

    Returns:
        bool: True if the key-value pair exists, False otherwise.
    """
    for dictionary in list_of_dicts:
        if dictionary.get(key) == value:
            return True
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

        if end_ip >= start_ip:
            return True
        return False
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
        if 1 <= bits_int <= 32:
            return True
        return False
    except (ValueError, TypeError):
        return False

def check_bmc_static_range_overlap(static_range, static_range_group_mapping) -> list:
    """
    Checks if the given static BMC range overlaps with any of the ranges in other groups.

    Args:
        static_range (str): The static BMC range to check for overlaps.
        static_range_group_mapping (Dict[str, str]):
            A dictionary mapping group names to their corresponding bmc static ranges.

    Returns:
        list: A list of group names that have overlapping ranges with the given static_range.
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

def check_port_overlap(port_ranges) -> bool:
    """
    Check if any of the port ranges in the given string overlap.

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

def is_range_within_netmask(ip_range, netmask_bits):
    """
    Check if a given IP range falls within the valid IP address range for a given netmask.

    Args:
        ip_range (str): The IP range in format "start_ip-end_ip"
            (e.g., "192.168.1.10-192.168.1.50").
        netmask_bits (int or str): The netmask bits (e.g., 20 for /20).

    Returns:
        bool: True if the IP range is valid for the given netmask, False otherwise.
    """
    try:
        # Parse the IP range
        start_ip, end_ip = ip_range.split('-')
        start_ip_obj = ipaddress.ip_address(start_ip)
        end_ip_obj = ipaddress.ip_address(end_ip)

        # Ensure start_ip <= end_ip
        if start_ip_obj > end_ip_obj:
            return False

        # Create network from start_ip with the given netmask
        network = ipaddress.ip_network(f"{start_ip}/{netmask_bits}", strict=False)

        # Get first and last usable addresses (excluding network and broadcast)
        first_usable = network.network_address + 1
        last_usable = network.broadcast_address - 1

        # Check if both start and end IPs are within the usable range
        return (first_usable <= start_ip_obj <= last_usable and
                first_usable <= end_ip_obj <= last_usable)
    except (ValueError, TypeError):
        return False

def is_ip_within_range(ip_range, ip):
    """
    Check if a given IP falls within a specified IP range.

    Args:
        ip_range (str): The IP range in format "start_ip-end_ip"
            (e.g., "192.168.1.10-192.168.1.50").
        ip (str): The IP address to check.

    Returns:
        bool: True if the IP is within the range, False otherwise.
    """
    start_ip, end_ip = [ipaddress.IPv4Address(part.strip()) for part in ip_range.split('-')]
    target_ip = ipaddress.IPv4Address(ip)
    return start_ip <= target_ip <= end_ip

def is_ip_in_subnet(admin_oim_ip, netmask_bits, vip_address):
    """
    Check if a given IP falls within the subnet defined by the admin OIM IP and netmask bits.

    Args:
        admin_oim_ip (str): The admin OIM IP address.
        netmask_bits (int or str): The netmask bits (e.g., 20 for /20).
        vip_address (str): The IP address to check.

    Returns:
        bool: True if the IP is within the subnet, False otherwise.
    """
    # Create the subnet from the reference IP and netmask bits
    subnet = ipaddress.IPv4Network(f"{admin_oim_ip}/{netmask_bits}", strict=False)
    ip = ipaddress.IPv4Address(vip_address)
    return ip in subnet

def flatten_sub_groups(sub_groups):
    """
    Flattens a list of sub-groups,
        where each sub-group can contain multiple groups separated by commas.

    Args:
        sub_groups (list): A list of sub-groups.

    Returns:
        list: A flattened list of individual groups.
    """
    result = []
    for group in sub_groups:
        result.extend(group.split(','))
    return result

def validate_cluster_items(cluster_items, json_file_path):
    """
    Validates the cluster items in a JSON file based on predefined type requirements.

    Args:
        cluster_items (list): A list of cluster items to validate.
        json_file_path (str): The path to the JSON file.

    Returns:
        tuple: A tuple containing two lists - one for successful validations and one for failures.
    """
    failures = []
    successes = []

    for item in cluster_items:
        item_type = item.get('type')
        required_fields = config.TYPE_REQUIREMENTS.get(item_type)

        if not required_fields:
            failures.append(f"Failed. Unknown type '{item_type}' in file '{json_file_path}'.")
            continue

        # Handle types with either/or fields (like tag/digest for image)
        if any(isinstance(field, list) for field in required_fields):
            # Separate flat and alternative fields
            flat_fields = [f for f in required_fields if isinstance(f, str)]
            alt_fields_groups = [f for f in required_fields if isinstance(f, list)]

            missing_flat = [f for f in flat_fields if f not in item]
            has_one_alt = any(any(alt in item for alt in group) for group in alt_fields_groups)

            if missing_flat or not has_one_alt:
                failures.append(
                    f"Failed. Missing required properties for '{item_type}' in file "
                    f"'{json_file_path}'.")
            else:
                successes.append(f"Success. Valid '{item_type}' item in file '{json_file_path}'.")
        else:
            missing_fields = [field for field in required_fields if field not in item]
            if missing_fields:
                failures.append(
                    f"Failed. Missing {missing_fields} for '{item_type}' in file "
                    f"'{json_file_path}'.")
            else:
                successes.append(f"Success. Valid '{item_type}' item in file '{json_file_path}'.")

    return successes, failures

def validate_softwaresubgroup_entries(
        software_name, json_path, json_data, validation_results, failures):
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
        #check for the key in software.json
        if software_name in json_data:
            validation_results.append((json_path, True))
            if 'cluster' in json_data[software_name]:
                cluster_items = json_data[software_name]['cluster']
                item_successes, item_failures = validate_cluster_items(cluster_items, json_path)
                if item_failures:
                    failures.append(f"{item_failures}")
            else:
                failures.append(
                    f"Failed. Invalid JSON format for: '{software_name}'"
                    f" in file '{json_path}'. Cluster property is missing")
        else:
            validation_results.append((json_path, False))
            failures.append(
                f"Failed. Invalid software name: '{software_name}' in file '{json_path}'.")

    except KeyError as e:
        failures.append(f"Failed. Missing key {str(e)} in file '{json_path}'.")
    except TypeError as e:
        failures.append(f"Failed. Type error in file '{json_path}': {str(e)}")
    except Exception as e:
        failures.append(f"Failed. Unexpected error in file '{json_path}': {str(e)}")

    return validation_results, failures
