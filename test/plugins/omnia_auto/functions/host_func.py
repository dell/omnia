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

import atexit
import os
import re
import shutil
import shlex
import subprocess
import tempfile
from typing import Any, Dict, List, Optional, Tuple

import yaml
import testinfra

from ..vars.common_vars import get_module_root, get_setting
from ..vars.credential_vars import VAULT_FILE_MODE
from .credential_func import (
    ensure_vault_key,
    is_vault_encrypted,
    read_all_fields,
    vault_encrypt,
)
from .formatting_func import log
from .process_security import (
    exclusive_sensitive_text,
)
from ._ssh_options import (
    parse_ssh_options,
    validate_ssh_destination,
    validate_ssh_port,
)


_TESTINFRA_INVENTORY_DIRS: List[str] = []
_ENV_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _require_yaml_mapping(value: Any, source: str) -> Dict[str, Any]:
    """Return a YAML mapping, rejecting ambiguous document roots."""
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"{source} must contain a YAML mapping")
    return value


@atexit.register
def _cleanup_testinfra_inventory_dirs() -> None:
    """Remove protected temporary inventories when the runner exits."""
    while _TESTINFRA_INVENTORY_DIRS:
        shutil.rmtree(
            _TESTINFRA_INVENTORY_DIRS.pop(), ignore_errors=True,
        )


def _write_testinfra_inventory(inventory: Dict[str, Any]) -> str:
    """Write an Ansible YAML inventory in a private temporary directory."""
    inventory_dir = tempfile.mkdtemp(prefix="omnia_auto_testinfra_")
    os.chmod(inventory_dir, 0o700)
    inventory_path = os.path.join(inventory_dir, "inventory.yml")
    try:
        with exclusive_sensitive_text(
            inventory_path, VAULT_FILE_MODE,
        ) as inv_fh:
            yaml.safe_dump(inventory, inv_fh, sort_keys=False)
    except (OSError, ValueError, yaml.YAMLError):
        shutil.rmtree(inventory_dir, ignore_errors=True)
        raise
    _TESTINFRA_INVENTORY_DIRS.append(inventory_dir)
    return inventory_path


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
        with open(path, "r", encoding="utf-8") as cfg_fh:
            return _require_yaml_mapping(
                yaml.safe_load(cfg_fh), path,
            )
    return {}


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

    if not os.path.lexists(creds_path):
        return {}

    result = read_all_fields(creds_path, key_path)
    if not result["success"]:
        raise ValueError(result["error"])
    credentials = _require_yaml_mapping(result["data"], creds_path)

    if not is_vault_encrypted(creds_path):
        ensure_vault_key(key_path)
        encryption = vault_encrypt(creds_path, key_path)
        if not encryption["success"]:
            raise ValueError(encryption["error"])
    return credentials


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

    if not os.path.lexists(creds_path):
        return False
    if is_vault_encrypted(creds_path):
        if not os.path.lexists(key_path):
            raise ValueError(
                f"Credentials encrypted but key not found: {key_path}"
            )
        return True
    ensure_vault_key(key_path)
    result = vault_encrypt(creds_path, key_path)
    if not result["success"]:
        raise ValueError(result["error"])
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
    oim_ip, ssh_user = validate_ssh_destination(
        oim_ip, config["oim_ssh_user"],
    )
    ssh_port = validate_ssh_port(config.get("oim_ssh_port", 22))
    ssh_auth = credentials.get("oim_password", "")

    ssh_args = get_setting(
        "ssh_opts",
        "-o StrictHostKeyChecking=accept-new "
        "-o LogLevel=ERROR",
    )
    ssh_args = shlex.join(parse_ssh_options(ssh_args))

    inventory_path = _write_testinfra_inventory({
        "all": {
            "hosts": {
                "target": {
                    "ansible_host": oim_ip,
                    "ansible_user": ssh_user,
                    "ansible_port": ssh_port,
                    "ansible_ssh_pass": ssh_auth,
                    "ansible_connection": "ssh",
                    "ansible_ssh_common_args": ssh_args,
                },
            },
        },
    })

    return testinfra.get_host(
        "ansible://target", ansible_inventory=inventory_path
    )


def run_on_host(host, cmd: str, *args: str):
    """Run command on the target host (OIM server).

    Args:
        host: Testinfra host object
        cmd: Command template to execute.
        *args: Values that Testinfra must shell-quote into ``%s`` placeholders.

    Returns:
        Result with stdout, stderr, rc attributes.
    """
    return host.run(cmd, *args)


def run_ssh_command(
    host,
    target: str,
    command: str,
    user: str = "root",
    connect_timeout: int = 10,
):
    """Run a passwordless SSH command from the current target host.

    This supports tests that connect to an execution host through testinfra
    and must then inspect a secondary node. Values derived from configuration
    are shell-quoted before the SSH command is passed to testinfra.

    Args:
        host: Current testinfra host object.
        target: Secondary host name or IP address.
        command: Command to execute on the secondary host.
        user: Secondary-host SSH user.
        connect_timeout: SSH connection timeout in seconds.

    Returns:
        Result with stdout, stderr, and rc attributes.

    Raises:
        ValueError: If a required value is empty or timeout is invalid.
    """
    target, user = validate_ssh_destination(target, user)
    if not isinstance(command, str) or not command.strip():
        raise ValueError("SSH command must be a non-empty string")
    if (
        not isinstance(connect_timeout, int)
        or isinstance(connect_timeout, bool)
        or connect_timeout <= 0
    ):
        raise ValueError("SSH connect_timeout must be a positive integer")

    ssh_options = get_setting(
        "ssh_opts",
        "-o StrictHostKeyChecking=accept-new "
        "-o LogLevel=ERROR",
    )
    option_parts = parse_ssh_options(ssh_options)
    command_parts = [
        "ssh",
        *option_parts,
        "-o",
        "BatchMode=yes",
        "-o",
        f"ConnectTimeout={connect_timeout}",
        "--",
        f"{user}@{target}",
        command,
    ]
    command_template = " ".join("%s" for _ in command_parts)
    return run_on_host(host, command_template, *command_parts)


# =============================================================================
# MONOREPO HOST UTILITIES
# =============================================================================

_DEFAULT_ENV_FILE = "/etc/omnia/omnia.env"


def connection_params() -> dict:
    """Build mode / ip / user / port / auth_secret / ssh_opts from config.

    Returns a dict ready to unpack into ``sync_files()`` or other
    functions that need SSH connection details::

        conn = connection_params()
        sync_files(mode=conn["mode"], ip=conn["ip"], ...)

    Returns:
        Dict with keys: mode, ip, user, port, auth_secret, ssh_opts.

    Raises:
        ValueError: If required config keys are missing for remote mode.
    """
    config = load_test_config()
    creds = load_test_credentials()
    local = is_local_execution()

    if not local:
        oim_ip = config.get("oim_server_ip", "")
        if not oim_ip:
            raise ValueError(
                "oim_server_ip is required in test_config.yml "
                "for remote (SSH) execution"
            )
        oim_user = config.get("oim_ssh_user", "")
        if not oim_user:
            raise ValueError(
                "oim_ssh_user is required in test_config.yml "
                "for remote (SSH) execution"
            )
    else:
        oim_ip = None
        oim_user = config.get("oim_ssh_user", "root")

    if not local:
        oim_ip, oim_user = validate_ssh_destination(oim_ip, oim_user)
        oim_port = validate_ssh_port(config.get("oim_ssh_port", 22))
    else:
        oim_port = 22

    oim_auth = creds.get("oim_password") or None
    return {
        "mode": "local" if local else "ssh",
        "ip": oim_ip,
        "user": oim_user,
        "port": oim_port,
        "auth_secret": oim_auth,
        "ssh_opts": get_setting(
            "ssh_opts",
            "-o StrictHostKeyChecking=accept-new "
            "-o LogLevel=ERROR",
        ),
    }


def read_remote_env(
    host,
    var_name: str,
    env_file: str = None,
    required: bool = True,
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
        required: Raise ``ValueError`` when the variable is unset or empty.
            Set to ``False`` only for optional environment variables.

    Returns:
        The variable value, stripped.

    Raises:
        ValueError: If input is invalid, or a required variable is unset.
    """
    if not isinstance(var_name, str) or not _ENV_NAME_RE.fullmatch(var_name):
        raise ValueError(
            "Environment variable name must contain only letters, digits, "
            "and underscores and must not begin with a digit"
        )
    if not isinstance(required, bool):
        raise ValueError("required must be a boolean")
    ef = env_file or get_setting("env_file", _DEFAULT_ENV_FILE)
    if not isinstance(ef, str) or not ef:
        raise ValueError("env_file must be a non-empty path")
    cmd = (
        "test -f %s && set -a && . %s && set +a && "
        f"printenv {var_name}"
    )
    result = host.run(cmd, ef, ef)
    value = result.stdout.strip() if result.rc == 0 else ""
    if not value and required:
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
    if not isinstance(path, str) or not path or "\x00" in path:
        raise ValueError("path must be a non-empty filesystem path")
    result = host.run("mkdir -p -- %s", path)
    if result.rc != 0:
        raise RuntimeError(
            f"Failed to create remote directory '{path}': "
            f"{result.stderr.strip()}"
        )
    log(f"Ensured remote directory exists: {path}", "DEBUG")


def read_remote_yaml(host, file_path: str) -> Dict[str, Any]:
    """Read and parse a YAML file from the target host.

    Args:
        host: Testinfra host object.
        file_path: Absolute path to the YAML file on the target.

    Returns:
        Parsed mapping. An empty YAML document returns an empty mapping.

    Raises:
        ValueError: If the path is empty or YAML is malformed/non-mapping.
        RuntimeError: If the remote file cannot be read.
    """
    if not isinstance(file_path, str) or not file_path:
        raise ValueError("file_path must be a non-empty path")
    result = host.run("cat -- %s", file_path)
    if result.rc != 0:
        error = result.stderr.strip() or "remote command failed"
        raise RuntimeError(
            f"Unable to read remote YAML file '{file_path}': {error}"
        )
    if not result.stdout.strip():
        return {}
    try:
        return _require_yaml_mapping(
            yaml.safe_load(result.stdout), file_path,
        )
    except yaml.YAMLError as exc:
        raise ValueError(
            f"Invalid YAML in remote file '{file_path}': {exc}"
        ) from exc


def read_yaml_key(data: Dict[str, Any], key_path: str, default=None):
    """Read a nested key from a dict using dot-separated path.

    Supports dict keys and list indices (integer path segments).

    Args:
        data: Parsed YAML dict.
        key_path: Dot-separated path (e.g. ``"telemetry_sources.powerscale.metrics_enabled"``).
        default: Value returned when the key is not found.

    Returns:
        The value at the key path, or *default*.

    Examples::

        read_yaml_key(cfg, "telemetry_sources.idrac.metrics_enabled")
        read_yaml_key(cfg, "telemetry_sinks.victoria_metrics")
        read_yaml_key(cfg, "isilonClusters.0.endpoint")
    """
    if not isinstance(data, dict):
        raise ValueError("data must be a mapping")
    if not isinstance(key_path, str) or not key_path:
        raise ValueError("key_path must be a non-empty string")
    current = data
    for part in key_path.split("."):
        if current is None:
            return default
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list):
            try:
                current = current[int(part)]
            except (ValueError, IndexError):
                return default
        else:
            return default
    return current if current is not None else default


def resolve_domain_data_path(
    host,
    domain: str,
    data_path_var: str,
    domain_data_path_var: str = None,
) -> str:
    """Resolve the remote data root for a domain.

    A non-empty domain-specific environment variable takes precedence. When
    it is unset or empty, the path is derived as ``<data_path>/<domain>``.

    Args:
        host: Testinfra host object.
        domain: Safe domain name (for example ``telemetry``).
        data_path_var: Name of the base data-path environment variable.
        domain_data_path_var: Optional name of a domain-specific data-path
            environment variable.

    Returns:
        The resolved domain data root without a trailing slash.

    Raises:
        ValueError: If input is invalid or no usable data path is available.
    """
    if not isinstance(domain, str) or not re.fullmatch(
        r"[A-Za-z][A-Za-z0-9_-]*", domain,
    ):
        raise ValueError("domain must be a safe non-empty identifier")

    domain_data_path = ""
    if domain_data_path_var is not None:
        domain_data_path = read_remote_env(
            host, domain_data_path_var, required=False,
        )

    if domain_data_path:
        resolved_path = domain_data_path.rstrip("/")
    else:
        data_path = read_remote_env(host, data_path_var).rstrip("/")
        resolved_path = f"{data_path}/{domain}"

    if not resolved_path.startswith("/"):
        raise ValueError("Resolved domain data path must be absolute")
    if resolved_path == "/":
        raise ValueError("Resolved domain data path must not be filesystem root")
    log(f"Resolved remote domain data path: {resolved_path}", "INFO")
    return resolved_path


def resolve_domain_input_path(
    host,
    domain: str,
    data_path_var: str,
    project_var: str,
    domain_data_path_var: str = None,
) -> str:
    """Build the remote input directory for a domain.

    Uses the optional domain-specific path when it is non-empty. Otherwise,
    assembles ``<data_path>/<domain>/input/<project>``.

    Args:
        host: Testinfra host object.
        domain: Domain name (e.g. ``image_build_manager``).
        data_path_var: Name of the env var holding the data path
            (e.g. ``OMNIA_DATA_PATH``).
        project_var: Name of the env var holding the project name
            (e.g. ``OMNIA_PROJECT_NAME``).
        domain_data_path_var: Optional name of the env var holding the
            complete domain data root (e.g. ``TELEMETRY_DATA_PATH``).

    Returns:
        Absolute path string on the target.

    Raises:
        ValueError: If input is invalid or a required env var is unset.
    """
    domain_data_path = resolve_domain_data_path(
        host,
        domain,
        data_path_var,
        domain_data_path_var,
    )
    project = read_remote_env(host, project_var)
    remote_input = f"{domain_data_path}/input/{project}"
    log(f"Resolved remote input path: {remote_input}", "INFO")
    return remote_input


# =========================================================================
# Ansible Inventory Parsing
# =========================================================================

def get_inventory_hosts(
    host,
    inventory_path: str,
    groups: List[str],
    prefix_match: bool = True,
) -> Dict[str, Any]:
    """Get hostnames from specific groups in an Ansible inventory file.

    Parses an Ansible YAML inventory file on the remote host and extracts
    hostnames from the specified groups.

    Args:
        host: Testinfra host object.
        inventory_path: Absolute path to the inventory YAML file.
        groups: List of group names to extract hosts from
            (e.g., ["slurm_control_node", "slurm_node"]).
        prefix_match: If True, match groups that start with the given name
            (e.g., "slurm_node" matches "slurm_node_x86_64"). Default True.

    Returns:
        Dict with keys:
            - success (bool): True if at least one host was found.
            - hostnames (list): All unique hostnames found.
            - by_group (dict): Mapping of matched group name to list of hostnames.
            - error (str): Error message if failed.

    Example::

        result = get_inventory_hosts(
            host,
            "/opt/omnia/telemetry/input/project/orchestrator.yml",
            ["slurm_control_node", "slurm_node"],
        )
        # result["hostnames"] = ["scontrol", "snode1", "snode2"]
        # result["by_group"] = {"slurm_control_node_x86_64": ["scontrol"], ...}
    """
    if not inventory_path:
        return {
            "success": False,
            "hostnames": [],
            "by_group": {},
            "error": "inventory_path is required",
        }

    if not groups:
        return {
            "success": False,
            "hostnames": [],
            "by_group": {},
            "error": "groups list is required",
        }

    # Read and parse the inventory YAML
    inv_data = read_remote_yaml(host, inventory_path)
    if not inv_data:
        return {
            "success": False,
            "hostnames": [],
            "by_group": {},
            "error": f"Failed to read inventory: {inventory_path}",
        }

    # Navigate to all.children in the inventory structure
    all_children = read_yaml_key(inv_data, "all.children", default={})
    if not all_children:
        return {
            "success": False,
            "hostnames": [],
            "by_group": {},
            "error": "No 'all.children' found in inventory",
        }

    by_group = {}
    all_hostnames = []

    for group_pattern in groups:
        # Find matching groups (exact or prefix match)
        matching_groups = []
        for inv_group in all_children.keys():
            if inv_group == group_pattern:
                matching_groups.append(inv_group)
            elif prefix_match and inv_group.startswith(group_pattern + "_"):
                matching_groups.append(inv_group)

        # Extract hosts from matching groups
        for matched_group in matching_groups:
            group_data = all_children[matched_group]
            if isinstance(group_data, dict):
                hosts = group_data.get("hosts", {})
                if isinstance(hosts, dict):
                    hostnames = list(hosts.keys())
                    by_group[matched_group] = hostnames
                    for hostname in hostnames:
                        if hostname not in all_hostnames:
                            all_hostnames.append(hostname)

    return {
        "success": len(all_hostnames) > 0,
        "hostnames": all_hostnames,
        "by_group": by_group,
        "error": "" if all_hostnames else f"No hosts found in groups: {groups}",
    }


def get_inventory_host_var(
    host,
    inventory_path: str,
    group: str,
    hostname: str,
    var_name: str,
    default=None,
):
    """Get a host variable from an Ansible inventory file.

    Args:
        host: Testinfra host object.
        inventory_path: Absolute path to the inventory YAML file.
        group: Group name where the host is defined.
        hostname: Name of the host.
        var_name: Variable name to retrieve (e.g., "ansible_host").
        default: Value to return if not found.

    Returns:
        The variable value or *default* if not found.

    Example::

        ip = get_inventory_host_var(
            host,
            "/opt/omnia/orchestrator.yml",
            "kube_vip_group",
            "kube-vip",
            "ansible_host",
        )
    """
    inv_data = read_remote_yaml(host, inventory_path)
    if not inv_data:
        return default

    key_path = f"all.children.{group}.hosts.{hostname}.{var_name}"
    return read_yaml_key(inv_data, key_path, default=default)
