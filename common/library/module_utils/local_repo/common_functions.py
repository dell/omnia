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
import subprocess
import yaml
import toml
import stat
import string
import secrets

def load_yaml_file(path):
    """
    Load YAML from a given file path.

    Args:
        path (str): The path to the YAML file.

    Returns:
        dict: The loaded YAML data.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path, "r", encoding = "utf-8") as file:
        return yaml.safe_load(file)

def get_repo_list(config_file, repo_key):
    """
    Retrieve the list of repositories from config using a given key.

    Args:
        config_file (dict): The configuration file data.
        repo_key (str): The key to retrieve the repository list.

    Returns:
        list: The list of repositories.
    """
    return config_file.get(repo_key, [])

def is_file_exists(file_path):
    """
    Check if a file exists at the given path.

    Args:
        file_path (str): The path to the file.

    Returns:
        bool: True if the file exists, False otherwise.
    """
    return os.path.isfile(file_path)

def is_encrypted(file_path):
    """
    Check if a file encrypted at the given path.

    Args:
        file_path (str): The path to the file.

    Returns:
        bool: True if the file encrypted, False otherwise.
    """
    with open(file_path, 'r', encoding = 'utf-8') as f:
        first_line = f.readline()
    return "$ANSIBLE_VAULT" in first_line

def run_vault_command(command, file_path, vault_key):
    """
    Run ansible-vault command at the given path.

    Args:
        command (str): Command to execute
        file_path (str): The path to the file.
        vault_key (str): key string

    Returns:
        bool: True/False based on execute command.
    """
    cmd = [
        "ansible-vault",
        command,
        file_path,
        "--vault-password-file", vault_key
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check = True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()

def process_file(file_path, vault_key, mode):
    """
    Encrypt or decrypt a file using Ansible Vault.

    Args:
        file_path (str): The path to the file.
        vault_key (str): The path to the Ansible Vault key.
        mode (str): The mode of operation, either 'encrypt' or 'decrypt'.

    Returns:
        tuple: A tuple containing a boolean indicating whether the
        operation was successful and a message.
    """
    if not os.path.isfile(file_path):
        return False, f"File not found: {file_path}"

    currently_encrypted = is_encrypted(file_path)
    success = False
    message = ""

    if mode == 'encrypt':
        if currently_encrypted:
            success, message = True, f"Already encrypted: {file_path}"
        else:
            code, out, err = run_vault_command('encrypt', file_path, vault_key)
            if code == 0:
                success, message = True, f"Encrypted: {file_path}"
            else:
                message = f"Failed to encrypt {file_path}: {err}"

    elif mode == 'decrypt':
        if not currently_encrypted:
            success, message = True, f"Already decrypted: {file_path}"
        else:
            code, out, err = run_vault_command('decrypt', file_path, vault_key)
            if code == 0:
                success, message = True, f"Decrypted: {file_path}"
            else:
                message = f"Failed to decrypt {file_path}: {err}"
    else:
        message = f"Invalid mode for {file_path}"

    return success, message

def load_pulp_config(path):
    """
    Load Pulp CLI configuration from a TOML file.

    Args:
        path (str): Path to the Pulp CLI config file.

    Returns:
        dict: A dictionary containing the following keys:
            - username (str): Pulp username
            - password (str): Pulp password.
            - base_url (str): Base URL for Pulp API".
    """
    with open(path, "r", encoding = "utf-8") as f:
        config = toml.load(f)
    cli_config = config.get("cli", {})
    return {
        "username": cli_config.get("username", ""),
        "password": cli_config.get("password", ""),
        "base_url": cli_config.get("base_url", "")
    }

def generate_vault_key(key_path):
    """
    Generate a secure Ansible Vault key
    only if the file does not already exist.

    Args:
        key_path (str): The directory where the Vault key file should be saved.

    Returns:
        str: The full path to the key file, or None if failed.
    """
    if os.path.isfile(key_path):
        return key_path

    try:
        alphabet = string.ascii_letters + string.digits
        key = ''.join(secrets.choice(alphabet) for _ in range(32))

        with open(key_path, "w", encoding="utf-8") as f:
            f.write(key + "\n")

        os.chmod(key_path, stat.S_IRUSR | stat.S_IWUSR)
        return key_path

    except (OSError, IOError) as e:
        return None

def get_arch_from_sw_config(software_name, sw_config_data, roles_config_data):
    """
    For a given software, extract architecture list from software_config.json.
    If not found, fallback to arch defined in Groups in roles_config.yml.
    Parameters
       software_name: name of the software
       sw_config_data: json content of software_config.json
       roles_config_data: content of roles_config.yml

    Returns:
        dict: {software_name: [arch list]}
    """
    for software in sw_config_data.get("softwares", []):
        if software.get("name") == software_name:
            arch = software.get("arch")

            if arch is None:
                # if arch is not defined for given software, fallback to roles_config.yml
                return get_arch_from_roles_config(software_name, roles_config_data)

            if isinstance(arch, list) and arch:
                arch_list = [a.strip() for a in arch]
                return {software_name: arch_list}
            else:
                error_msg = f"'arch' field for '{software_name}' should not be an empty list"
                raise ValueError(error_msg)

def get_arch_from_roles_config(software_name, roles_config_data):
    """
    Extract architecture values under each group defined in roles_config.yml
    Parameters
       software_name: name of the software
       roles_config_data: content of roles_config.yml

    Returns:
        dict: {software_name: [archs]}
    """
    archs = []
    groups = roles_config_data.get("Groups", {})

    if not groups:
        error_msg = "No groups defined in roles_config.yml under 'Groups'"
        raise ValueError(error_msg)

    for group_name, group_data in groups.items():
        architecture = group_data.get("architecture")
        if architecture:
            archs.append(architecture.strip())
        else:
            error_msg = f"No architecture defined for group '{group_name}' in roles_config.yml"
            raise ValueError(error_msg)

    return {software_name: archs}

