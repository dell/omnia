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

import os
import re
import ipaddress
import subprocess
import yaml
import en_us_validation_msg
import config

def load_yaml_as_json(yaml_file, omnia_base_dir, project_name, logger, module):
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
        raise FileNotFoundError(error_message)
    except yaml.YAMLError as e:
        error_message = f"Error loading YAML: {e}"
        logger.error(error_message)
        module.fail_json(msg=error_message)
        raise Exception(error_message)
    
def create_error_msg(key, value, msg):
    return {"error_key": key, "error_value": value, "error_msg": msg}

def create_file_path(input_file_path, other_file):
    path_parts = input_file_path.split("/")
    path_parts[-1] = other_file
    final_path = ("/").join(path_parts)
    return final_path

def contains_software(softwares, name):
    return any(name in software["name"].lower() for software in softwares)

def check_mandatory_fields(mandatory_fields, data, errors):
    for field in mandatory_fields:
        if is_string_empty(data[field]):
            errors.append(create_error_msg(field, data[field], en_us_validation_msg.mandatory_field_fail_msg))
    
# Below functions used to deal with encrypted files (Check if a file is encrypted, if yes then get the vault password, decrypt file, load data, encrypt file again)
def is_file_encrypted(file_path):
    try:
        with open(file_path, 'r') as file:
            first_line = file.readline().strip()
            return first_line.startswith('$ANSIBLE_VAULT')
    except (IOError, OSError):
        return False
    
def process_encrypted_file(yaml_file, omnia_base_dir, project_name, logger, module):
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
            logger.error("Error loading YAML(%s)" % e)
            module.fail_json(msg="Error loading YAML(%s)" % (e))
    else:
        unable_to_decrypt_fail_msg = (f"Error occured when attempting to decrypt file. Please check that the assoicated vault file exists for {yaml_file}")
        logger.error(unable_to_decrypt_fail_msg)
        module.fail_json(unable_to_decrypt_fail_msg)

def run_subprocess(cmd):
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
    if value is None:
        return True
    if not isinstance(value, str):
        return False
    return len(value.strip()) < 1

def verify_path(file_path):
    return os.path.exists(file_path)

def validate_default_lease_time(default_lease_time):
    return 21600 <= int(default_lease_time) <= 31536000


def verify_iso_file(iso_file_path, provision_os, provision_os_version):
    if (".iso" not in iso_file_path):
        return en_us_validation_msg.iso_file_path_not_contain_iso_msg
    if not (
        provision_os.lower() in iso_file_path and provision_os_version in iso_file_path
    ):
        return en_us_validation_msg.iso_file_path_not_contain_os_msg(
            iso_file_path, provision_os, provision_os_version
        )
    if not (verify_path(iso_file_path)):
        return en_us_validation_msg.iso_file_path_fail_msg
    return ""


# validate timezone (input_tz: str, available_timezone_file_path: str) -> bool
def validate_timezone(input_tz, available_timezone_file_path):
    all_timezones = []
    with open(available_timezone_file_path, "r") as file:
        content = file.read()
        for line in content.splitlines():
            all_timezones.append(line)
    return input_tz in all_timezones


def is_valid_password(
    password,
):  # Checks if the password meets the specified requirements: Length of at least 8 characters. Does not contain '-', '\', "'", or '"'.
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
    if not (min_username_length <= len(username) < max_length):
        return False
    
    forbidden_characters = {"-", "\\", "'", '"'}
    if any(char in username for char in forbidden_characters):
        return False
    
    return True


# check_overlap(ip_list: list[dict[str, str]]) -> tuple[bool, list[tuple]]:
def check_overlap(ip_list):
    ranges = []
    overlaps = []

    # Convert IP ranges and CIDR to ipaddress objects
    for item in ip_list:
        if (item == ''):
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