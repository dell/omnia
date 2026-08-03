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
Testinfra host, configuration, and credential utilities.

Handles:
- Config YAML loading
- Credentials loading with Ansible Vault encryption
- Testinfra host connection (local or remote SSH)
- Local vs remote execution detection
- Remote environment variable reading
- Remote directory management
- Domain input path resolution
"""

import os
import subprocess
import tempfile
from typing import Dict, Any, Optional, Tuple

import yaml
import testinfra

from ..vars.common_vars import get_module_root, get_setting
from .formatting_func import log


# =============================================================================
# CONFIG LOADING
# =============================================================================

def _resolve_config_path(config_path: Optional[str] = None) -> str:
    """Resolve the config file path.

    Args:
        config_path: Explicit path.  When ``None``, built from
                     ``module_root`` + ``config_file`` setting.

    Raises:
        RuntimeError: If neither param nor setting is available.
    """
    if config_path:
        return config_path
    config_file = get_setting("config_file")
    if not config_file:
        raise RuntimeError(
            "config_file not configured. "
            "Pass config_path= or call configure(config_file=...)."
        )
    return os.path.join(get_module_root(), config_file)


def _resolve_credentials_paths(
    creds_path: Optional[str] = None,
    key_path: Optional[str] = None,
) -> Tuple[str, str]:
    """Resolve credentials file and key file paths.

    Args:
        creds_path: Explicit credentials file path.
        key_path: Explicit vault key file path.

    Raises:
        RuntimeError: If neither param nor setting is available.
    """
    root = get_module_root()
    if not creds_path:
        creds_file = get_setting("credentials_file")
        if not creds_file:
            raise RuntimeError(
                "credentials_file not configured. "
                "Pass creds_path= or call configure(credentials_file=...)."
            )
        creds_path = os.path.join(root, creds_file)
    if not key_path:
        key_file = get_setting("credentials_key")
        if not key_file:
            raise RuntimeError(
                "credentials_key not configured. "
                "Pass key_path= or call configure(credentials_key=...)."
            )
        key_path = os.path.join(root, key_file)
    return creds_path, key_path


def load_test_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load test configuration from a YAML file.

    Args:
        config_path: Explicit file path.  When ``None``, resolved
                     from ``configure(config_file=...)``.

    Returns:
        Dict containing the configuration, or empty dict if not found.
    """
    path = _resolve_config_path(config_path)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


# =============================================================================
# VAULT ENCRYPTION
# =============================================================================

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


def _decrypt_vault_file(config_path: str, key_path: str) -> Dict:
    """Decrypt ansible-vault encrypted file and return as dict."""
    try:
        result = subprocess.run(
            [
                "ansible-vault", "view", config_path,
                "--vault-password-file", key_path,
            ],
            capture_output=True, text=True, timeout=30, check=True,
        )
        return yaml.safe_load(result.stdout) or {}
    except subprocess.CalledProcessError as exc:
        raise ValueError(
            f"Failed to decrypt {config_path}: {exc.stderr}"
        ) from exc
    except FileNotFoundError:
        raise ValueError(
            "ansible-vault not found. Install ansible."
        ) from None


def _encrypt_vault_file(config_path: str, key_path: str) -> bool:
    """Encrypt file with ansible-vault."""
    try:
        subprocess.run(
            [
                "ansible-vault", "encrypt", config_path,
                "--vault-password-file", key_path,
            ],
            capture_output=True, text=True, timeout=30, check=True,
        )
        return True
    except subprocess.CalledProcessError as exc:
        raise ValueError(
            f"Failed to encrypt {config_path}: {exc.stderr}"
        ) from exc
    except FileNotFoundError:
        raise ValueError(
            "ansible-vault not found. Install ansible."
        ) from None


def load_test_credentials(
    creds_path: Optional[str] = None,
    key_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Load test credentials with automatic vault encryption.

    Args:
        creds_path: Explicit credentials file path.
        key_path: Explicit vault key file path.

    Behavior:
    - Encrypted + key exists: decrypt and return
    - Encrypted + key missing: raise error
    - Plain: read, create key, encrypt, return
    - Not found: return empty dict
    """
    creds_path, key_path = _resolve_credentials_paths(creds_path, key_path)

    if not os.path.exists(creds_path):
        return {}

    if _is_vault_encrypted(creds_path):
        if os.path.exists(key_path):
            return _decrypt_vault_file(creds_path, key_path)
        raise ValueError(
            f"Credentials encrypted but key not found: {key_path}"
        )

    with open(creds_path, "r", encoding="utf-8") as f:
        creds = yaml.safe_load(f) or {}

    if not os.path.exists(key_path):
        _create_vault_key(key_path)

    _encrypt_vault_file(creds_path, key_path)
    return creds


def encrypt_test_credentials(
    creds_path: Optional[str] = None,
    key_path: Optional[str] = None,
) -> bool:
    """Encrypt credentials file if not already encrypted.

    Args:
        creds_path: Explicit credentials file path.
        key_path: Explicit vault key file path.
    """
    creds_path, key_path = _resolve_credentials_paths(creds_path, key_path)

    if not os.path.exists(creds_path):
        return False
    if _is_vault_encrypted(creds_path):
        return True
    if not os.path.exists(key_path):
        _create_vault_key(key_path)

    _encrypt_vault_file(creds_path, key_path)
    return True


# =============================================================================
# LOCAL / REMOTE DETECTION
# =============================================================================

def _is_local_ip(ip: str) -> bool:
    """Check if IP belongs to this machine."""
    if ip in ("localhost", "127.0.0.1", ""):
        return True
    try:
        result = subprocess.run(
            ["hostname", "-I"],
            capture_output=True, text=True, timeout=5, check=False,
        )
        return ip in result.stdout.strip().split()
    except (OSError, subprocess.SubprocessError):
        return False


def is_local_execution() -> bool:
    """Determine if tests run locally on the target host.

    Returns True when:
    - oim_server_ip is empty/not set
    - oim_server_ip matches a local IP address
    """
    config = load_test_config()
    oim_ip = config.get("oim_server_ip", "")
    if not oim_ip:
        return True
    return _is_local_ip(str(oim_ip).strip())


# =============================================================================
# TESTINFRA HOST CONNECTION
# =============================================================================

def get_testinfra_host():
    """Get testinfra host connected to the target server.

    When oim_server_ip is empty or local, runs in local mode.
    When oim_server_ip is remote, connects via SSH.

    Returns:
        testinfra Host object.
    """
    config = load_test_config()
    credentials = load_test_credentials()
    oim_ip = str(config.get("oim_server_ip", "")).strip()

    # Local execution
    if not oim_ip or _is_local_ip(oim_ip):
        return testinfra.get_host("local://")

    # Remote — SSH
    ssh_user = config["oim_ssh_user"]
    ssh_port = config.get("oim_ssh_port", 22)
    ssh_password = credentials.get("oim_password", "")

    inventory_dir = os.path.join(
        tempfile.gettempdir(), "omnia_auto_testinfra"
    )
    os.makedirs(inventory_dir, exist_ok=True)
    inventory_path = os.path.join(inventory_dir, "inventory.ini")

    ssh_args = get_setting(
        "ssh_opts",
        "-o StrictHostKeyChecking=no "
        "-o UserKnownHostsFile=/dev/null "
        "-o LogLevel=ERROR",
    )

    with open(inventory_path, "w", encoding="utf-8") as f:
        f.write("[all]\n")
        f.write(
            f"target ansible_host={oim_ip} "
            f"ansible_user={ssh_user} "
            f"ansible_port={ssh_port} "
            f"ansible_ssh_pass={ssh_password} "
            f"ansible_connection=ssh "
            f"ansible_ssh_common_args='{ssh_args}'\n"
        )

    return testinfra.get_host(
        "ansible://target", ansible_inventory=inventory_path
    )


def run_on_host(host, cmd: str):
    """Run command on the target host (OIM server).

    Args:
        host: Testinfra host object
        cmd: Command to execute

    Returns:
        Result with stdout, stderr, rc attributes.
    """
    return host.run(cmd)


# =============================================================================
# MONOREPO HOST UTILITIES
# =============================================================================

_DEFAULT_ENV_FILE = "/etc/omnia/omnia.env"


def connection_params() -> dict:
    """Build mode / ip / user / password / ssh_opts from test config.

    Returns a dict ready to unpack into ``sync_files()`` or other
    functions that need SSH connection details::

        conn = connection_params()
        sync_files(mode=conn["mode"], ip=conn["ip"], ...)

    Returns:
        Dict with keys: mode, ip, user, password, ssh_opts.

    Raises:
        ValueError: If required config keys are missing for remote mode.
    """
    config = load_test_config()
    creds = load_test_credentials()
    local = is_local_execution()

    if not local:
        oim_ip = config.get("oim_server_ip", "").strip()
        if not oim_ip:
            raise ValueError(
                "oim_server_ip is required in test_config.yml "
                "for remote (SSH) execution"
            )
        oim_user = config.get("oim_ssh_user", "").strip()
        if not oim_user:
            raise ValueError(
                "oim_ssh_user is required in test_config.yml "
                "for remote (SSH) execution"
            )
    else:
        oim_ip = None
        oim_user = config.get("oim_ssh_user", "root")

    return {
        "mode": "local" if local else "ssh",
        "ip": oim_ip,
        "user": oim_user,
        "password": creds.get("oim_password") or None,
        "ssh_opts": get_setting(
            "ssh_opts",
            "-o StrictHostKeyChecking=no "
            "-o UserKnownHostsFile=/dev/null "
            "-o LogLevel=ERROR",
        ),
    }


def read_remote_env(
    host, var_name: str, env_file: str = None
) -> str:
    """Read an environment variable from the target host.

    Sources the env file before reading so that variables defined
    by setup scripts are available in non-login SSH sessions.

    Args:
        host: Testinfra host object.
        var_name: Environment variable name (e.g. ``OMNIA_DATA_PATH``).
        env_file: Path to the env file on the target host.
            Defaults to ``configure(env_file=...)`` or
            ``/etc/omnia/omnia.env``.

    Returns:
        The variable value, stripped.

    Raises:
        ValueError: If the variable is not set or empty on the target.
    """
    ef = env_file or get_setting("env_file", _DEFAULT_ENV_FILE)
    cmd = (
        f"test -f {ef} && set -a && . {ef} && set +a; "
        f"echo ${{{var_name}}}"
    )
    result = host.run(cmd)
    value = result.stdout.strip() if result.rc == 0 else ""
    if not value:
        raise ValueError(
            f"Environment variable '{var_name}' is not set on the "
            f"target host.  Ensure the environment has been set up "
            f"and {ef} contains {var_name}."
        )
    return value


def ensure_remote_dir(host, path: str) -> None:
    """Create a directory on the target if it does not exist.

    Args:
        host: Testinfra host object.
        path: Absolute path to create on the target.

    Raises:
        ValueError: If *path* is empty.
        RuntimeError: If ``mkdir -p`` fails.
    """
    if not path:
        raise ValueError("path is required for ensure_remote_dir")
    result = host.run(f"mkdir -p {path}")
    if result.rc != 0:
        raise RuntimeError(
            f"Failed to create remote directory '{path}': "
            f"{result.stderr.strip()}"
        )
    log(f"Ensured remote directory exists: {path}", "DEBUG")


def resolve_domain_input_path(
    host, domain: str, data_path_var: str, project_var: str
) -> str:
    """Build the remote input directory for a domain.

    Reads the given environment variables from the target and
    assembles ``<data_path>/<domain>/input/<project>/``.

    Args:
        host: Testinfra host object.
        domain: Domain name (e.g. ``image_build_manager``).
        data_path_var: Name of the env var holding the data path
            (e.g. ``OMNIA_DATA_PATH``).
        project_var: Name of the env var holding the project name
            (e.g. ``OMNIA_PROJECT_NAME``).

    Returns:
        Absolute path string on the target.

    Raises:
        ValueError: If *domain* is empty or either env var is unset.
    """
    if not domain:
        raise ValueError("domain is required for resolve_domain_input_path")
    data_path = read_remote_env(host, data_path_var)
    project = read_remote_env(host, project_var)
    remote_input = f"{data_path}/{domain}/input/{project}"
    log(f"Resolved remote input path: {remote_input}", "INFO")
    return remote_input
