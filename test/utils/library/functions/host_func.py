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
Utils Domain — Module-specific host utilities (monorepo).

Reads module config and passes ALL params to omnia_auto's
``sync_files()``.  No logic in the package — only in this consumer.

Monorepo changes vs multi-repo:
- Input path resolved from target env vars (OMNIA_DATA_PATH, OMNIA_PROJECT_NAME)
- sync_project_to_remote() copies local project code to target clone_path
- No separate config.yml sync (env vars replace it)

Common functions are re-exported from omnia_auto so existing
callers keep working.
"""

import base64
import os
import shutil
import tempfile
from typing import Dict, Any

from omnia_auto import (
    load_test_config,
    load_test_credentials,
    sync_files,
    read_remote_env,
    ensure_remote_dir,
    resolve_domain_input_path,
    is_local_execution,
    connection_params,
    log,
)

from ..vars.common_vars import (
    DOMAIN_NAME,
    MODULE_ROOT,
    MONOREPO_ROOT,
    SRC_INPUT_DIR,
    COLLECT_PXE_FILE,
    INSTALL_OS_CREDENTIALS_FILE,
    BACKUP_OIM_LOGS_CONFIG_FILE,
    ENV_OMNIA_DATA_PATH,
    ENV_OMNIA_PROJECT_NAME,
)

# =============================================================================
# CREDENTIAL EXCLUSION PATTERNS
# =============================================================================
CREDENTIALS_FILE_NAME = "test_creds.yml"
CREDENTIALS_KEY_NAME = ".test_creds.key"

_DOMAIN_CREDENTIAL_PATTERNS = (
    CREDENTIALS_FILE_NAME,
    f"{CREDENTIALS_FILE_NAME}.*",
    CREDENTIALS_KEY_NAME,
    f"{CREDENTIALS_KEY_NAME}.*",
    INSTALL_OS_CREDENTIALS_FILE,
    f"{INSTALL_OS_CREDENTIALS_FILE}.*",
)
_input_sync_ignore = shutil.ignore_patterns(*_DOMAIN_CREDENTIAL_PATTERNS)


# =============================================================================
# SECURITY AND STAGING HELPERS
# =============================================================================

def _link_or_copy(source: str, destination: str) -> str:
    """Hard-link staged files when possible, otherwise copy them."""
    try:
        os.link(source, destination, follow_symlinks=False)
        return destination
    except OSError:
        return shutil.copy2(source, destination, follow_symlinks=False)


def _resolve_dataset_subdir(
    config: Dict[str, Any], subdirectory: str, fallback: str
) -> str:
    """Resolve one dataset subdirectory without allowing path traversal."""
    dataset = config.get("dataset", "")
    if not dataset:
        return fallback
    if not isinstance(dataset, str):
        raise ValueError("dataset must be a directory name string")
    if (
        dataset in {".", "..", "generator"}
        or os.path.isabs(dataset)
        or os.path.basename(dataset) != dataset
        or "\x00" in dataset
    ):
        raise ValueError(f"Unsafe dataset name: {dataset!r}")

    datasets_root = os.path.realpath(os.path.join(MODULE_ROOT, "datasets"))
    dataset_path = os.path.join(datasets_root, dataset)
    if os.path.islink(dataset_path):
        raise ValueError(f"Dataset symlinks are not allowed: {dataset}")
    resolved_dataset = os.path.realpath(dataset_path)
    if os.path.dirname(resolved_dataset) != datasets_root:
        raise ValueError(f"Dataset escapes datasets directory: {dataset!r}")

    subdir_path = os.path.join(resolved_dataset, subdirectory)
    if os.path.islink(subdir_path):
        raise ValueError(
            f"Dataset subdirectory symlinks are not allowed: {dataset}/{subdirectory}"
        )
    resolved_subdir = os.path.realpath(subdir_path)
    if os.path.commonpath((resolved_dataset, resolved_subdir)) != resolved_dataset:
        raise ValueError(
            f"Dataset subdirectory escapes its dataset: {dataset}/{subdirectory}"
        )
    return resolved_subdir


def _reject_symlinks(directory: str) -> None:
    """Reject nested links before copying an input tree into staging."""
    for current_dir, directory_names, file_names in os.walk(directory):
        for entry_name in directory_names + file_names:
            if os.path.islink(os.path.join(current_dir, entry_name)):
                raise OSError(
                    f"Refusing to sync symlink from dataset: "
                    f"{os.path.join(current_dir, entry_name)}"
                )


def _resolve_input_dir(config: Dict[str, Any]) -> str:
    """Resolve local input directory from dataset or src/."""
    return _resolve_dataset_subdir(config, "input", SRC_INPUT_DIR)


# =============================================================================
# PROJECT AND INPUT SYNC
# =============================================================================

# =============================================================================
# CREDENTIAL FILE PATTERNS TO EXCLUDE FROM SYNC
# =============================================================================

_CREDENTIAL_PATTERNS = (
    "install_os_credentials.yml",
    "install_os_credentials.yml.*",
    ".install_os_credentials.key",
    ".install_os_credentials.key.*",
)
_input_sync_ignore = shutil.ignore_patterns(*_CREDENTIAL_PATTERNS)
_project_sync_ignore = shutil.ignore_patterns(
    ".git",
    ".agents",
    ".codex",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "*.pyc",
    ".venv",
    "venv",
    "active-venv",
    "test_creds.yml",
    "test_creds.yml.*",
    ".test_creds.key",
    ".test_creds.key.*",
    *_CREDENTIAL_PATTERNS,
)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _link_or_copy(source: str, destination: str) -> str:
    """Hard-link staged project files when possible, otherwise copy them."""
    try:
        os.link(source, destination, follow_symlinks=False)
        return destination
    except OSError:
        return shutil.copy2(
            source, destination, follow_symlinks=False
        )


def _resolve_dataset_subdir(
    config: Dict[str, Any], subdirectory: str, fallback: str
) -> str:
    """Resolve one dataset subdirectory without allowing path traversal."""
    dataset = config.get("dataset", "")
    if not dataset:
        return fallback
    if not isinstance(dataset, str):
        raise ValueError("dataset must be a directory name string")
    if (
        dataset in {".", "..", "generator"}
        or os.path.isabs(dataset)
        or os.path.basename(dataset) != dataset
        or "\x00" in dataset
    ):
        raise ValueError(f"Unsafe dataset name: {dataset!r}")

    datasets_root = os.path.realpath(os.path.join(MODULE_ROOT, "datasets"))
    dataset_path = os.path.join(datasets_root, dataset)
    if os.path.islink(dataset_path):
        raise ValueError(f"Dataset symlinks are not allowed: {dataset}")
    resolved_dataset = os.path.realpath(dataset_path)
    if os.path.dirname(resolved_dataset) != datasets_root:
        raise ValueError(f"Dataset escapes datasets directory: {dataset!r}")

    subdir_path = os.path.join(resolved_dataset, subdirectory)
    if os.path.islink(subdir_path):
        raise ValueError(
            f"Dataset subdirectory symlinks are not allowed: {dataset}/{subdirectory}"
        )
    resolved_subdir = os.path.realpath(subdir_path)
    if os.path.commonpath((resolved_dataset, resolved_subdir)) != resolved_dataset:
        raise ValueError(
            f"Dataset subdirectory escapes its dataset: {dataset}/{subdirectory}"
        )
    return resolved_subdir


def _reject_symlinks(directory: str) -> None:
    """Reject nested links before copying an input tree into staging."""
    for current_dir, directory_names, file_names in os.walk(directory):
        for entry_name in directory_names + file_names:
            if os.path.islink(os.path.join(current_dir, entry_name)):
                raise OSError(
                    f"Refusing to sync symlink from dataset: "
                    f"{os.path.join(current_dir, entry_name)}"
                )


def _resolve_remote_clone_path(config: Dict[str, Any]) -> str:
    """Return the validated, normalized remote project destination."""
    raw_clone_path = config.get("clone_path")
    if not isinstance(raw_clone_path, str) or not raw_clone_path.strip():
        raise ValueError(
            "clone_path must be set in test_config.yml for remote execution"
        )
    clone_path = raw_clone_path.strip()
    if not os.path.isabs(clone_path):
        raise ValueError(
            f"clone_path must be absolute for remote execution: {clone_path}"
        )
    return os.path.normpath(clone_path)


def _resolve_input_dir(config):
    """Resolve local input directory from dataset or src/."""
    return _resolve_dataset_subdir(config, "input", SRC_INPUT_DIR)


# =============================================================================
# PROJECT SYNC
# =============================================================================

def sync_project_to_remote(host) -> Dict[str, Any]:
    """Sync the local omnia project tree to clone_path on target.

    Copies a filtered working tree from the local monorepo to the remote
    ``clone_path``, using the same rsync/SSH checks as other sync functions.
    Local credential files, vault keys, VCS metadata, virtual environments,
    and caches are excluded.

    Source: ``<repo_root>/`` (the omnia monorepo root)
    Dest:   ``<clone_path>/`` on the target server
    """
    config = load_test_config()
    conn = connection_params()
    clone_path = _resolve_remote_clone_path(config)

    try:
        with tempfile.TemporaryDirectory(
            prefix="omnia_utils_project_"
        ) as staging_dir:
            staged_project = os.path.join(staging_dir, "omnia")
            shutil.copytree(
                MONOREPO_ROOT,
                staged_project,
                symlinks=True,
                ignore=_project_sync_ignore,
                copy_function=_link_or_copy,
            )
            result = sync_files(
                mode=conn["mode"],
                src=staged_project,
                dest=clone_path,
                ip=conn["ip"],
                user=conn["user"],
                auth_secret=conn["auth_secret"],
                ssh_opts=conn["ssh_opts"],
            )
    except OSError as exc:
        return {
            "success": False,
            "details": "",
            "error": f"Failed to stage project for sync: {exc}",
        }

    if result["success"]:
        result["details"] = (
            f"Synced filtered project {MONOREPO_ROOT} -> {clone_path} "
            "(local credentials and caches excluded)"
        )
    return result


# =============================================================================
# INPUT SYNC
# =============================================================================

def sync_utils_input(host, config: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Push utils input files from local source to target.

    Uses secure staging with:
    - Path traversal protection via _resolve_dataset_subdir()
    - Symlink rejection via _reject_symlinks()
    - Credential exclusion via ignore patterns
    - Temporary staging directory for safe file operations

    Reads ``OMNIA_DATA_PATH`` and ``OMNIA_PROJECT_NAME`` from the target
    server's environment to resolve the correct destination::

        <OMNIA_DATA_PATH>/utils/input/<OMNIA_PROJECT_NAME>/

    Source: src/utils/input/ (default) or
            datasets/<dataset>/input/ (when dataset is set).

    Any credential artifacts are deliberately excluded.

    Args:
        host: Testinfra host object.
    """
    if config is None:
        config = load_test_config()
    conn = connection_params()

    local_input = _resolve_input_dir(config)
    remote_input = resolve_domain_input_path(
        host, DOMAIN_NAME, ENV_OMNIA_DATA_PATH, ENV_OMNIA_PROJECT_NAME,
    )
    ensure_remote_dir(host, remote_input)

    try:
        _reject_symlinks(local_input)
        with tempfile.TemporaryDirectory(
            prefix="omnia_utils_input_"
        ) as staging_dir:
            staged_input = os.path.join(staging_dir, "input")
            shutil.copytree(
                local_input,
                staged_input,
                ignore=_input_sync_ignore,
            )

            # Sync staged files to target
            result = sync_files(
                mode=conn["mode"],
                src=staged_input,
                dest=remote_input,
                ip=conn["ip"],
                user=conn["user"],
                auth_secret=conn.get("auth_secret", conn.get("password", "")),
                ssh_opts=conn["ssh_opts"],
            )

        if result["success"]:
            result["details"] = (
                f"Input files synced to {remote_input} (credentials excluded)"
            )
        return result
    except OSError as exc:
        return {
            "success": False,
            "details": "",
            "error": f"Failed to stage utils input: {exc}",
        }
    except Exception as exc:
        return {
            "success": False,
            "details": "",
            "error": str(exc),
        }


# =============================================================================
# CREDENTIAL SYNC
# =============================================================================

def sync_install_os_credentials(host) -> Dict[str, Any]:
    """Sync install_os credentials from test_creds.yml to target.

    Bridges credentials from test_creds.yml to the target's
    install_os_credentials.yml file matching manual playbook execution.

    Flow:
        1. Load test_creds.yml (decrypted via load_test_credentials).
        2. Extract bmc_username, bmc_password, os_root_password.
        3. If any field has a non-empty value:
           - Write plaintext credentials file
           - The playbook role collect_install_os_credentials will handle encryption

    This follows the image builder pattern: plaintext sync, playbook handles encryption.

    Args:
        host: Testinfra host object.

    Returns:
        dict: {"success": bool, "details": str, "error": str}
    """
    try:
        creds = load_test_credentials()
    except (ValueError, OSError) as exc:
        return {
            "success": False,
            "details": "",
            "error": f"Cannot load test_creds.yml: {exc}",
        }

    # Extract install_os credential fields
    bmc_username = creds.get("bmc_username", "")
    bmc_password = creds.get("bmc_password", "")
    os_root_password = creds.get("os_root_password", "")

    # Check if any credential fields have values
    has_values = bool(bmc_username and bmc_password and os_root_password)
    if not has_values:
        return {
            "success": True,
            "details": (
                "No install_os credentials in test_creds.yml — skipping sync. "
                "The collect_install_os_credentials role will prompt interactively "
                "for mandatory fields (bmc_username, bmc_password, os_root_password). "
                "To set credentials non-interactively, run: "
                "bash setup_env.sh --set-domain-creds"
            ),
            "error": "",
        }

    # Use resolve_domain_input_path to get target path from env vars
    dest_path = resolve_domain_input_path(
        host, DOMAIN_NAME, ENV_OMNIA_DATA_PATH, ENV_OMNIA_PROJECT_NAME
    )
    if not dest_path:
        return {
            "success": False,
            "details": "",
            "error": "Failed to resolve target input path",
        }

    # File paths
    creds_file = os.path.join(dest_path, INSTALL_OS_CREDENTIALS_FILE)

    # Step 1: Ensure target directory exists
    mkdir_cmd = f"mkdir -p {dest_path}"
    mkdir_result = host.run(mkdir_cmd)
    if mkdir_result.rc != 0:
        return {
            "success": False,
            "details": "",
            "error": f"Failed to create directory: {mkdir_result.stderr}",
        }

    # Step 2: Write plaintext credentials file (playbook will encrypt)
    yaml_content = f"""---
# OS Installation credentials (BMC/iDRAC + OS root password)
bmc_username: "{bmc_username}"
bmc_password: "{bmc_password}"
os_root_password: "{os_root_password}"
"""
    b64 = base64.b64encode(yaml_content.encode("utf-8")).decode("ascii")

    # Step 3: Write plaintext credentials file
    write_cmd = f"echo '{b64}' | base64 -d > {creds_file}"
    write_result = host.run(write_cmd)
    if write_result.rc != 0:
        return {
            "success": False,
            "details": "",
            "error": f"Failed to write credentials file: {write_result.stderr}",
        }

    # Step 4: Set credentials file permissions (0600)
    chmod_creds_cmd = f"chmod 600 {creds_file}"
    chmod_creds_result = host.run(chmod_creds_cmd)
    if chmod_creds_result.rc != 0:
        return {
            "success": False,
            "details": "",
            "error": f"Failed to set credentials file permissions: {chmod_creds_result.stderr}",
        }

    return {
        "success": True,
        "details": (
            f"Install OS credentials synced (plaintext) to {creds_file} "
            f"[bmc_username=set, bmc_password=set, os_root_password=set]. "
            f"The playbook role will handle encryption."
        ),
        "error": "",
    }


# =============================================================================
# PATH RESOLUTION (uses target env vars)
# =============================================================================

def get_utils_input_path(host) -> str:
    """Get the utils input path on target.

    Reads OMNIA_DATA_PATH and OMNIA_PROJECT_NAME from the target's
    environment to resolve the input path.

    Args:
        host: Testinfra host object.

    Returns:
        str: The input path or empty string on failure.
    """
    try:
        return resolve_domain_input_path(
            host, DOMAIN_NAME, ENV_OMNIA_DATA_PATH, ENV_OMNIA_PROJECT_NAME
        )
    except Exception:
        return ""


def get_utils_output_path(host) -> str:
    """Get the utils output path on target.

    Reads OMNIA_DATA_PATH and OMNIA_PROJECT_NAME from the target's
    environment to resolve the output path.

    Args:
        host: Testinfra host object.

    Returns:
        str: The output path or empty string on failure.
    """
    try:
        data_path = read_remote_env(host, ENV_OMNIA_DATA_PATH)
        project = read_remote_env(host, ENV_OMNIA_PROJECT_NAME)
        # Output is directly in the collect directory
        return f"{data_path}/{DOMAIN_NAME}/output/{project}/collect"
    except Exception:
        return ""


def get_backup_oim_logs_output_path(host) -> str:
    """Get the default OIM log backup output path on target.

    Reads OMNIA_DATA_PATH and OMNIA_PROJECT_NAME from the target's
    environment to resolve the default backup_oim_logs workspace
    (used when OMNIA_BACKUP_PATH is not set).

    Args:
        host: Testinfra host object.

    Returns:
        str: The default backup workspace path or empty string on failure.
    """
    try:
        data_path = read_remote_env(host, ENV_OMNIA_DATA_PATH)
        project = read_remote_env(host, ENV_OMNIA_PROJECT_NAME)
        return f"{data_path}/{DOMAIN_NAME}/output/{project}/backup_oim_logs"
    except Exception:
        return ""


def get_backup_oim_logs_config_path(host) -> str:
    """Get the backup_oim_logs_config.yml path on target.

    Args:
        host: Testinfra host object.

    Returns:
        str: The config file path or empty string on failure.
    """
    try:
        input_path = get_utils_input_path(host)
        return f"{input_path}/{BACKUP_OIM_LOGS_CONFIG_FILE}"
    except Exception:
        return ""
