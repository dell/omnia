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
Testinfra host and configuration utilities for the main module.

Self-contained config loading, testinfra host connection, vault
encryption, and container exec helpers.
"""

import os
import subprocess
import tempfile
from typing import Dict, Any

import yaml
import testinfra

from ..vars.common_vars import (
    MODULE_ROOT,
    OMNIA_CORE_CONTAINER,
    TEST_CONFIG_FILE,
    TEST_CREDENTIALS_FILE,
    TEST_CREDENTIALS_KEY,
)


def get_module_root() -> str:
    """Get the module root directory (main/)."""
    return MODULE_ROOT


def _get_config_path() -> str:
    """Get the test_config.yml path."""
    return os.path.join(MODULE_ROOT, TEST_CONFIG_FILE)


def _get_credentials_paths() -> tuple:
    """Get credentials file and key file paths."""
    creds_path = os.path.join(MODULE_ROOT, TEST_CREDENTIALS_FILE)
    key_path = os.path.join(MODULE_ROOT, TEST_CREDENTIALS_KEY)
    return creds_path, key_path


def _is_vault_encrypted(file_path: str) -> bool:
    """Check if file is ansible-vault encrypted."""
    if not os.path.exists(file_path):
        return False
    with open(file_path, "r", encoding="utf-8") as f:
        first_line = f.readline().strip()
    return first_line.startswith("$ANSIBLE_VAULT")


def _create_vault_key(key_path: str) -> None:
    """Create a new vault key file with random 32-char password."""
    import secrets
    key = secrets.token_urlsafe(32)[:32]
    with open(key_path, "w", encoding="utf-8") as f:
        f.write(key)
    os.chmod(key_path, 0o600)


def _decrypt_vault_file(config_path: str, key_path: str) -> Dict[str, Any]:
    """Decrypt ansible-vault encrypted file and return as dict."""
    try:
        result = subprocess.run(
            ["ansible-vault", "view", config_path, "--vault-password-file", key_path],
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )
        return yaml.safe_load(result.stdout) or {}
    except subprocess.CalledProcessError as e:
        raise ValueError(f"Failed to decrypt {config_path}: {e.stderr}") from e
    except FileNotFoundError:
        raise ValueError("ansible-vault command not found. Install ansible.") from None


def _encrypt_vault_file(config_path: str, key_path: str) -> bool:
    """Encrypt file with ansible-vault."""
    try:
        subprocess.run(
            ["ansible-vault", "encrypt", config_path, "--vault-password-file", key_path],
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )
        return True
    except subprocess.CalledProcessError as e:
        raise ValueError(f"Failed to encrypt {config_path}: {e.stderr}") from e
    except FileNotFoundError:
        raise ValueError("ansible-vault command not found. Install ansible.") from None


def load_test_config() -> Dict[str, Any]:
    """Load test configuration from test_config.yml.

    Reads the module-level test_config.yml which contains non-sensitive
    settings like OIM server IP, SSH user/port, dataset selection,
    and report configuration.

    Returns:
        Dict containing the configuration.
    """
    config_path = _get_config_path()

    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    return {}


def load_test_credentials() -> Dict[str, Any]:
    """Load test credentials from test_creds.yml with automatic vault encryption.

    This file contains sensitive credentials (passwords) that are
    encrypted with Ansible Vault on first use.

    Behavior:
    - If file is encrypted and key exists: decrypt and return credentials
    - If file is encrypted and key missing: raise error
    - If file is plain: read data, create key if missing, encrypt file, return data
    - If file doesn't exist: return empty dict

    Returns:
        Dict containing the credentials.
    """
    creds_path, key_path = _get_credentials_paths()

    if not os.path.exists(creds_path):
        return {}

    if _is_vault_encrypted(creds_path):
        if os.path.exists(key_path):
            return _decrypt_vault_file(creds_path, key_path)
        else:
            raise ValueError(
                f"Credentials file is encrypted but key not found: {key_path}\n"
                f"Please ensure {TEST_CREDENTIALS_KEY} exists in module root."
            )
    else:
        with open(creds_path, "r", encoding="utf-8") as f:
            creds = yaml.safe_load(f) or {}

        if not os.path.exists(key_path):
            _create_vault_key(key_path)

        _encrypt_vault_file(creds_path, key_path)

        return creds


def encrypt_test_credentials() -> bool:
    """Encrypt test_creds.yml if not already encrypted.

    Creates vault key (.test_creds.key) if it doesn't exist.

    Returns:
        True if file is now encrypted, False if file doesn't exist.
    """
    creds_path, key_path = _get_credentials_paths()

    if not os.path.exists(creds_path):
        return False

    if _is_vault_encrypted(creds_path):
        return True

    if not os.path.exists(key_path):
        _create_vault_key(key_path)

    _encrypt_vault_file(creds_path, key_path)
    return True


def get_dataset_path() -> str:
    """Get the configured dataset path from test_config.yml.

    Datasets are stored under main/datasets/<dataset_name>/.
    The active dataset is selected via the ``dataset`` key in
    test_config.yml.

    Returns:
        Absolute path to the active dataset directory.
    """
    config = load_test_config()
    dataset = config.get("dataset", "nfs_external")
    return os.path.join(MODULE_ROOT, "datasets", dataset)


def _is_local_ip(ip: str) -> bool:
    """Check if IP belongs to this machine."""
    if ip in ["localhost", "127.0.0.1"]:
        return True
    try:
        result = subprocess.run(
            ["hostname", "-I"], capture_output=True, text=True, timeout=5, check=False
        )
        return ip in result.stdout.strip().split()
    except (OSError, subprocess.SubprocessError):
        return False


def is_local_execution() -> bool:
    """Determine if tests should run locally (on the OIM itself).

    Returns True when:
    - oim_ip is empty/not set (implies running on the OIM)
    - oim_ip matches a local IP address
    """
    config = load_test_config()
    oim_ip = config.get("oim_server_ip", "")
    if not oim_ip or oim_ip.strip() == "":
        return True
    return _is_local_ip(oim_ip.strip())


def get_testinfra_host() -> testinfra.host.Host:
    """Get testinfra host connected to OIM server.

    When oim_ip is empty or matches a local IP, runs in local mode
    (no SSH required — assumes tests are running on the OIM itself).
    When oim_ip is set to a remote IP, connects via SSH using sshpass.

    Returns:
        testinfra Host object.
    """
    config = load_test_config()
    credentials = load_test_credentials()
    oim_ip = config.get("oim_server_ip", "")

    # Local execution
    if not oim_ip or oim_ip.strip() == "" or _is_local_ip(oim_ip.strip()):
        return testinfra.get_host("local://")

    # Remote — SSH with IP from test_config.yml
    ssh_user = config.get("oim_ssh_user", "root")
    ssh_port = config.get("oim_ssh_port", 22)
    ssh_password = credentials.get("oim_password", "")

    inventory_dir = os.path.join(tempfile.gettempdir(), "omnia_testinfra")
    os.makedirs(inventory_dir, exist_ok=True)
    inventory_path = os.path.join(inventory_dir, "inventory.ini")

    with open(inventory_path, "w", encoding="utf-8") as f:
        f.write("[all]\n")
        f.write(f"oim_server ansible_host={oim_ip} ansible_user={ssh_user} ")
        f.write(f"ansible_port={ssh_port} ansible_ssh_pass={ssh_password} ")
        f.write("ansible_connection=ssh ")
        ssh_args = "-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
        f.write(f"ansible_ssh_common_args='{ssh_args}'\n")

    return testinfra.get_host("ansible://oim_server", ansible_inventory=inventory_path)


def run_on_oim(host, cmd: str):
    """Run command on OIM server.

    Args:
        host: Testinfra host connected to OIM server
        cmd: Command to execute

    Returns:
        Result with stdout, stderr, rc attributes.
    """
    return host.run(cmd)


def run_in_container(host, cmd: str, container: str = OMNIA_CORE_CONTAINER):
    """Run command inside a container on OIM server.

    Args:
        host: Testinfra host connected to OIM server
        cmd: Command to execute inside container
        container: Container name (default: omnia_core)

    Returns:
        Result with stdout, stderr, rc attributes.
    """
    container_cmd = f"podman exec {container} {cmd}"
    return host.run(container_cmd)
