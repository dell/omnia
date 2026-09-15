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
Common utility functions for repo_manager operations.

This module provides:
- Vault encryption/decryption operations
- File permission management
- Configuration file handling
- Common validation and helper functions
"""

import os
import subprocess
import stat
import string
import secrets
import base64
import tomllib as toml
from pathlib import Path

import yaml

from ansible.module_utils.repo_manager.secure_path import open_secure_directory


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
    with open(path, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)






def is_encrypted(file_path):
    """
    Check if a file encrypted at the given path.

    Args:
        file_path (str): The path to the file.

    Returns:
        bool: True if the file encrypted, False otherwise.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
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
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
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
            code, _, err = run_vault_command('encrypt', file_path, vault_key)
            if code == 0:
                success, message = True, f"Encrypted: {file_path}"
            else:
                message = f"Failed to encrypt {file_path}: {err}"

    elif mode == 'decrypt':
        if not currently_encrypted:
            success, message = True, f"Already decrypted: {file_path}"
        else:
            code, _, err = run_vault_command('decrypt', file_path, vault_key)
            if code == 0:
                success, message = True, f"Decrypted: {file_path}"
            else:
                message = f"Failed to decrypt {file_path}: {err}"
    else:
        message = f"Invalid mode for {file_path}"

    return success, message


def load_vault_yaml(file_path, vault_key):
    """
    Load YAML from a file, decrypting it with ansible-vault when necessary.

    Args:
        file_path (str): The path to the YAML file.
        vault_key (str): The path to the Ansible Vault password file.

    Returns:
        dict: The loaded YAML data. Returns an empty dict if the file does not exist.
    """
    if not os.path.isfile(file_path):
        return {}

    if is_encrypted(file_path):
        env = os.environ.copy()
        env["ANSIBLE_VAULT_PASSWORD_FILE"] = vault_key
        result = subprocess.run(
            ["ansible-vault", "view", file_path],
            capture_output=True,
            text=True,
            check=True,
            env=env
        )
        return yaml.safe_load(result.stdout)

    return yaml.safe_load(Path(file_path).read_text(encoding="utf-8"))


def load_pulp_config(path):
    """
    Load Pulp CLI configuration from a TOML file.

    Args:
        path (str): Path to the Pulp CLI config file.

    Returns:
        dict: A dictionary containing the following keys:
            - username (str): Pulp username
            - password (str): Pulp password (Base64 encoded).
            - base_url (str): Base URL for Pulp API.
    """
    # Securely read file using pathlib
    content = Path(path).read_text(encoding="utf-8")
    config = toml.loads(content)

    cli_config = config.get("cli", {})

    password_plain = cli_config.get("password", "")
    # Encode password using Base64
    password_encoded = base64.b64encode(password_plain.encode()).decode()

    return {
        "username": cli_config.get("username", ""),
        "password": password_encoded,
        "base_url": cli_config.get("base_url", "")
    }


def _open_vault_key_directory(directory_path):
    """Open and validate the directory used for a certificate vault key."""
    directory_descriptor = open_secure_directory(directory_path)
    directory_status = os.fstat(directory_descriptor)
    if (
            not stat.S_ISDIR(directory_status.st_mode)
            or directory_status.st_uid != os.geteuid()
            or directory_status.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
    ):
        os.close(directory_descriptor)
        raise PermissionError("Certificate vault-key directory is not trusted")
    return directory_descriptor


def _open_or_create_vault_key(directory_descriptor, key_name):
    """Return the no-follow key descriptor and whether it was newly created."""
    if not hasattr(os, "O_NOFOLLOW"):
        raise OSError("Secure certificate vault-key creation is unavailable")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    flags |= getattr(os, "O_CLOEXEC", 0)
    try:
        return os.open(
            key_name,
            flags,
            stat.S_IRUSR | stat.S_IWUSR,
            dir_fd=directory_descriptor,
        ), True
    except FileExistsError:
        flags = os.O_RDONLY | os.O_NOFOLLOW
        flags |= getattr(os, "O_CLOEXEC", 0)
        return os.open(
            key_name, flags, dir_fd=directory_descriptor
        ), False


def _validate_vault_key_descriptor(key_descriptor):
    """Reject an existing key that is not a privately owned regular file."""
    key_status = os.fstat(key_descriptor)
    if (
            not stat.S_ISREG(key_status.st_mode)
            or key_status.st_uid != os.geteuid()
            or key_status.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
    ):
        raise PermissionError("Certificate vault key is not trusted")


def _write_new_vault_key(key_descriptor):
    """Write and synchronize a new random certificate vault key."""
    alphabet = string.ascii_letters + string.digits
    key = ''.join(secrets.choice(alphabet) for _ in range(32))
    key_data = memoryview((key + "\n").encode("ascii"))
    while key_data:
        written = os.write(key_descriptor, key_data)
        if written == 0:
            raise OSError("Unable to write certificate vault key")
        key_data = key_data[written:]
    os.fsync(key_descriptor)


def generate_vault_key(key_path):
    """Create or securely reuse the certificate Ansible Vault key."""
    directory_path = os.path.dirname(os.path.abspath(key_path))
    key_name = os.path.basename(key_path)
    if not key_name:
        return None

    directory_descriptor = None
    key_descriptor = None
    created = False
    try:
        directory_descriptor = _open_vault_key_directory(directory_path)
        key_descriptor, created = _open_or_create_vault_key(
            directory_descriptor, key_name
        )
        _validate_vault_key_descriptor(key_descriptor)
        os.fchmod(key_descriptor, stat.S_IRUSR | stat.S_IWUSR)
        if created:
            _write_new_vault_key(key_descriptor)
            os.fsync(directory_descriptor)
        return key_path

    except OSError:
        if created and directory_descriptor is not None:
            try:
                os.unlink(key_name, dir_fd=directory_descriptor)
            except OSError:
                pass
        return None
    finally:
        if key_descriptor is not None:
            os.close(key_descriptor)
        if directory_descriptor is not None:
            os.close(directory_descriptor)


def get_arch_from_sw_config(software_name, sw_config_data):
    """
    For a given software, extract architecture list from catalog configuration.
    Extracts architecture from functional layer names (e.g., slurm_control_node_rhel_10_0_x86_64).

    Parameters
       software_name: name of the software
       sw_config_data: catalog configuration data

    Returns:
        dict: {software_name: [arch list]}
    """
    # Extract architectures from functional layer names
    functionallayer = sw_config_data.get("functionallayer", [])
    archs = set()

    for layer in functionallayer:
        layer_name = layer.get("name", "")
        # Extract architecture from layer name (e.g., x86_64, aarch64)
        if "_x86_64" in layer_name:
            archs.add("x86_64")
        elif "_aarch64" in layer_name:
            archs.add("aarch64")

    if archs:
        return {software_name: list(archs)}

    # Fallback: check if software is defined in packages with architecture info
    packages = sw_config_data.get("packages", {})
    if software_name in packages:
        pkg = packages[software_name]
        sources = pkg.get("sources", [])
        pkg_archs = set()
        for source in sources:
            arch = source.get("architecture")
            if arch:
                pkg_archs.add(arch)
        if pkg_archs:
            return {software_name: list(pkg_archs)}

    raise ValueError(
        f"No architecture is defined for software '{software_name}' in the catalog"
    )


def get_arch_from_functional_groups_config(software_name, functional_groups_config_data):
    """Extract architecture values from legacy functional group configuration."""
    archs = []
    groups = functional_groups_config_data.get("Groups", {})

    if not groups:
        raise ValueError(
            "No groups defined in functional_groups_config.yml under 'Groups'"
        )

    for group_name, group_data in groups.items():
        architecture = group_data.get("architecture")
        if architecture:
            archs.append(architecture.strip())
        else:
            raise ValueError(
                f"No architecture defined for group '{group_name}' "
                "in functional_groups_config.yml"
            )

    return {software_name: archs}
