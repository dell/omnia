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
"""Utility functions for input validation in Omnia."""
# pylint: disable=import-error

import os
import ipaddress
import subprocess
import yaml

if os.getenv('UNIT_TESTING') == 'true':
    from input_validation.common_utils import config, en_us_validation_msg
else:
    from ansible.module_utils.input_validation.common_utils import ( # type: ignore
        config, en_us_validation_msg)


def load_yaml_as_json(yaml_file, omnia_base_dir, project_name, logger, module):
    """
    Load YAML file and return its contents as an object.

    Handles encrypted files by decrypting them first, then loading the content.
    Provides detailed error messages for YAML syntax errors.

    Args:
        yaml_file (str): Path to the YAML file to load
        omnia_base_dir (str): Base directory of the Omnia project
        project_name (str): Name of the project
        logger: Logger object for logging messages
        module: Ansible module object for error handling

    Returns:
        dict: The loaded YAML content as an object, or None if validation fails

    Raises:
        FileNotFoundError: If the specified file does not exist
    """
    try:
        if is_file_encrypted(yaml_file):
            data = process_encrypted_file(
                yaml_file, omnia_base_dir, project_name, logger, module)
            return data
        with open(yaml_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data
    except FileNotFoundError:
        error_message = f"File {yaml_file} not found"
        logger.error(error_message)
        module.fail_json(msg=error_message)
        raise FileNotFoundError(error_message) # pylint: disable=W0707
    except yaml.YAMLError as e:
        error_parts = []
        error_parts.append(
            f"Syntax error when loading YAML file '{yaml_file}'")

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


def create_error_msg(key, value, msg):
    """
    Create a standardized error message dictionary for validation errors.

    Args:
        key (str): The key or field name where the error occurred
        value (any): The invalid value that caused the error
        msg (str): The error message describing the validation failure

    Returns:
        dict: A dictionary containing the error key, value, and message
    """
    return {"error_key": key, "error_value": value, "error_msg": msg}


def create_file_path(input_file_path, other_file):
    """
    Create a new file path by replacing the filename in the input path with another filename.

    Args:
        input_file_path (str): The original file path
        other_file (str): The new filename to use

    Returns:
        str: A new file path with the same directory as input_file_path
          but with other_file as the filename
    """
    path_parts = input_file_path.split("/")
    path_parts[-1] = other_file
    final_path = ("/").join(path_parts)
    return final_path


def contains_software(softwares, name):
    """
    Check if a software with the given name exists in the list of software dictionaries.

    Args:
        softwares (list): List of dictionaries containing software information
        name (str): Name of the software to search for

    Returns:
        bool: True if the software name is found, False otherwise
    """
    return any(name in software["name"].lower() for software in softwares)


def check_mandatory_fields(mandatory_fields, data, errors):
    """
    Check if mandatory fields in the data dictionary have valid values.

    Validates that each field in the mandatory_fields list exists in the data dictionary
    and is not empty. Appends error messages to the errors list for any fields that fail validation.

    Args:
        mandatory_fields (list): List of field names that must be present and non-empty
        data (dict): Dictionary containing the data to validate
        errors (list): List to which error messages will be appended

    Returns:
        None: Errors are appended to the provided errors list
    """
    for field in mandatory_fields:
        if is_string_empty(data[field]):
            errors.append(
                create_error_msg(
                    field,
                    data[field],
                    en_us_validation_msg.MANDATORY_FIELD_FAIL_MSG))

# Below functions used to deal with encrypted files (Check if a file is
# encrypted, if yes then get the vault password, decrypt file, load data,
# encrypt file again)
def is_file_encrypted(file_path):
    """
    Check if a file is encrypted with Ansible Vault.

    Examines the first line of the file to determine if it starts with
    the Ansible Vault signature ('$ANSIBLE_VAULT').

    Args:
        file_path (str): Path to the file to check

    Returns:
        bool: True if the file is encrypted with Ansible Vault, False otherwise

    Raises:
        IOError, OSError: If there are issues accessing the file
    """
    try:
        with open(file_path, 'r', encoding="utf-8") as file:
            first_line = file.readline().strip()
            return first_line.startswith('$ANSIBLE_VAULT')
    except (IOError, OSError):
        return False


def process_encrypted_file(yaml_file, omnia_base_dir,
                           project_name, logger, module):
    """
    Process an encrypted YAML file by decrypting, loading, and re-encrypting it.

    Args:
        yaml_file (str): Path to the encrypted YAML file
        omnia_base_dir (str): Base directory of the Omnia project
        project_name (str): Name of the project
        logger: Logger object for logging messages
        module: Ansible module object for error handling

    Returns:
        dict: The loaded YAML content as a Python object

    Raises:
        FileNotFoundError: If the specified file does not exist
        yaml.YAMLError: If there are syntax errors in the YAML file
    """
    vault_password_file = config.get_vault_password(yaml_file)
    decrypted_file = decrypt_file(
        omnia_base_dir,
        project_name,
        yaml_file,
        vault_password_file)
    if decrypted_file:
        try:
            with open(yaml_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                encrypt_file(
                    omnia_base_dir,
                    project_name,
                    yaml_file,
                    vault_password_file)
                return data
        except FileNotFoundError:
            logger.error("File {%s} not found" % yaml_file)
            module.fail_json(msg="File {%s} not found" % (yaml_file))
        except yaml.YAMLError as e:
            logger.error(f"Error loading YAML({e})")
            module.fail_json(msg=f"Error loading YAML({e})")
    else:
        unable_to_decrypt_fail_msg = (
            f"Error occured when attempting to decrypt file. "
            f"Please check that the assoicated vault file exists for {yaml_file}")
        logger.error(unable_to_decrypt_fail_msg)
        module.fail_json(unable_to_decrypt_fail_msg)


def run_subprocess(cmd):
    """
    Execute a subprocess command and handle any errors.

    Args:
        cmd (list): Command to execute as a list of arguments

    Returns:
        bool: True if the command executed successfully, False otherwise
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


def encrypt_file(omnia_base_dir, project_name,
                 vault_file, vault_password_file):
    """
    Encrypt a file using Ansible Vault.

    Constructs the full path to the vault password file and uses it to encrypt
    the specified file with Ansible Vault.

    Args:
        omnia_base_dir (str): Base directory of the Omnia project
        project_name (str): Name of the project
        vault_file (str): Path to the file to encrypt
        vault_password_file (str): Path to the file containing the vault password

    Returns:
        bool: True if encryption was successful, False otherwise
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


def decrypt_file(omnia_base_dir, project_name,
                 vault_file, vault_password_file):
    """
    Decrypt a file using Ansible Vault.

    Constructs the full path to the vault password file and uses it to decrypt
    the specified file with Ansible Vault.

    Args:
        omnia_base_dir (str): Base directory of the Omnia project
        project_name (str): Name of the project
        vault_file (str): Path to the file to decrypt
        vault_password_file (str): Path to the file containing the vault password

    Returns:
        bool: True if decryption was successful, False otherwise
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
    Check if a value is None or an empty string.

    Args:
        value: The value to check, can be any type

    Returns:
        bool: True if the value is None or an empty string, False otherwise
    """
    if value is None:
        return True
    if not isinstance(value, str):
        return False
    return len(value.strip()) < 1


def verify_path(file_path):
    """
    Check if a file exists at the specified path.

    Args:
        file_path (str): Path to the file to check

    Returns:
        bool: True if the file exists, False otherwise
    """
    if not os.path.exists(file_path):
        return False
    return os.path.isfile(file_path)


def validate_default_lease_time(default_lease_time):
    """
    Validate that the default lease time is within the acceptable range.

    Args:
        default_lease_time (str or int): The default lease time to validate

    Returns:
        bool: True if the default lease time is between 21600 and 31536000
            (inclusive), False otherwise
    """
    return 21600 <= int(default_lease_time) <= 31536000


def verify_iso_file(iso_file_path, provision_os, provision_os_version):
    """
    Verify that an ISO file path is valid and contains the correct OS information.

    Checks that the file path has a .iso extension, contains the OS name and version
    in the filename, and that the file exists at the specified path.

    Args:
        iso_file_path (str): Path to the ISO file
        provision_os (str): Operating system name that should be in the filename
        provision_os_version (str): OS version that should be in the filename

    Returns:
        str: Empty string if validation passes, error message otherwise
    """
    if ".iso" not in iso_file_path:
        return en_us_validation_msg.ISO_FILE_PATH_NOT_CONTAIN_ISO_MSG

    iso_path_lower = iso_file_path.lower()
    os_name_matches = provision_os.lower() in iso_path_lower
    version_matches = provision_os_version in iso_path_lower

    if not (os_name_matches and version_matches):
        return en_us_validation_msg.iso_file_path_not_contain_os_msg(
            provision_os, provision_os_version
        )

    if not verify_path(iso_file_path):
        return en_us_validation_msg.ISO_FILE_PATH_FAIL_MSG

    return ""


def validate_timezone(input_tz, available_timezone_file_path):
    """
    Validate that the provided timezone exists in the available timezones list.

    Reads the available timezones from a file and checks if the input timezone
    is among them.

    Args:
        input_tz (str): The timezone to validate
        available_timezone_file_path (str): Path to the file containing valid timezones

    Returns:
        bool: True if the timezone is valid, False otherwise
    """
    all_timezones = []
    with open(available_timezone_file_path, "r", encoding="utf-8") as file:
        content = file.read()
        for line in content.splitlines():
            all_timezones.append(line)
    return input_tz in all_timezones


def is_valid_password(password, ):
    """
    Check if a password meets the specified security requirements.

    Validates that the password:
    - Is a string
    - Has a length between 8 and 30 characters (exclusive)
    - Does not contain any of the forbidden characters: '-', '\', "'", or '"'

    Args:
        password: The password to validate

    Returns:
        bool: True if the password meets all requirements, False otherwise
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


# check_overlap(ip_list: list[dict[str, str]]) -> tuple[bool, list[tuple]]:
def check_overlap(ip_list):
    """
    Check if any IP ranges in the provided list overlap with each other.

    Converts IP ranges (e.g., "192.168.1.1-192.168.1.10")
    to ipaddress objects and checks for overlaps between them.

    Args:
        ip_list (list): List of strings representing IP ranges or CIDR blocks

    Returns:
        tuple: A tuple containing:
            - bool: True if any overlaps exist, False otherwise
            - list: List of tuples containing pairs of overlapping networks
    """
    ranges = []
    overlaps = []

    # Convert IP ranges and CIDR to ipaddress objects
    for item in ip_list:
        if item == '':
            continue
        if "-" in item:
            start_ip, end_ip = item.split("-")
            start_ip = ipaddress.ip_address(start_ip)
            end_ip = ipaddress.ip_address(end_ip)
            # Convert IP range to a list of networks
            networks = list(
                ipaddress.summarize_address_range(
                    start_ip, end_ip))
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
        else:
            return False
    except ValueError:
        return False


def validate_netmask_bits(bits):
    """
    Validate that the netmask bits value is within the valid range for IPv4.

    Checks that the provided value can be converted to an integer and
    is between 1 and 32 (inclusive), which are the valid values for
    IPv4 netmask bits.

    Args:
        bits (str or int): The netmask bits value to validate

    Returns:
        bool: True if the netmask bits value is valid, False otherwise
    """
    try:
        bits_int = int(bits)
        if 1 <= bits_int <= 32:
            return True
        else:
            return False
    except (ValueError, TypeError):
        return False


def check_bmc_static_range_overlap(
        static_range, static_range_group_mapping) -> list:
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
    Check if an IP address is within a specified IP range.

    Args:
        ip_range (str): The IP range in format "start_ip-end_ip"
        ip (str): The IP address to check

    Returns:
        bool: True if the IP address is within the range, False otherwise
    """
    start_ip, end_ip = [ipaddress.IPv4Address(part.strip()) for part in ip_range.split('-')]
    target_ip = ipaddress.IPv4Address(ip)
    return start_ip <= target_ip <= end_ip

def is_ip_in_subnet(admin_oim_ip, netmask_bits, vip_address):
    """
    Check if an IP address is within a subnet defined by a reference IP and netmask.

    Args:
        admin_oim_ip (str): The reference IP address used to define the subnet
        netmask_bits (str or int): The netmask bits
        vip_address (str): The IP address to check

    Returns:
        bool: True if the IP address is within the subnet, False otherwise
    """
    # Create the subnet from the reference IP and netmask bits
    subnet = ipaddress.IPv4Network(f"{admin_oim_ip}/{netmask_bits}", strict=False)
    ip = ipaddress.IPv4Address(vip_address)
    return ip in subnet
