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
Utils Domain — Host Sync Functions.

Functions for syncing project files, input files, and credentials to target.
"""

import base64
import os
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
)

from ..vars.common_vars import (
    DOMAIN_NAME,
    MODULE_ROOT,
    MONOREPO_ROOT,
    SRC_INPUT_DIR,
    COLLECT_PXE_FILE,
    INSTALL_OS_CREDENTIALS_FILE,
    ENV_OMNIA_DATA_PATH,
    ENV_OMNIA_PROJECT_NAME,
)


def sync_project_to_remote(host) -> Dict[str, Any]:
    """Sync the entire omnia project to the remote target.

    Args:
        host: Testinfra host object.

    Returns:
        dict: {"success": bool, "details": str, "error": str}
    """
    config = load_test_config()
    clone_path = config.get("clone_path", "/root/omnia")

    try:
        result = sync_files(
            host=host,
            src=MONOREPO_ROOT,
            dest=clone_path,
            exclude=[
                ".git",
                "__pycache__",
                "*.pyc",
                ".venv",
                "reports",
                "test/*/datasets/data_set_*",
            ],
        )
        if result["success"]:
            return {
                "success": True,
                "details": f"Project synced to {clone_path}",
                "error": "",
            }
        return {
            "success": False,
            "details": "",
            "error": result.get("error", "Sync failed"),
        }
    except Exception as exc:
        return {
            "success": False,
            "details": "",
            "error": str(exc),
        }


def sync_utils_input(host) -> Dict[str, Any]:
    """Sync utils input files to target.

    Syncs from dataset directory (if set) or src/utils/input/ to target's
    input directory at $OMNIA_DATA_PATH/utils/input/$OMNIA_PROJECT_NAME/.

    Args:
        host: Testinfra host object.

    Returns:
        dict: {"success": bool, "details": str, "error": str}
    """
    config = load_test_config()
    dataset = config.get("dataset", "")
    conn = connection_params()

    # Determine source directory
    if dataset:
        src_dir = os.path.join(MODULE_ROOT, "datasets", dataset, "input")
    else:
        src_dir = SRC_INPUT_DIR

    if not os.path.isdir(src_dir):
        return {
            "success": False,
            "details": "",
            "error": f"Source input directory not found: {src_dir}",
        }

    try:
        # Resolve target path from environment
        dest_path = resolve_domain_input_path(
            host, DOMAIN_NAME, ENV_OMNIA_DATA_PATH, ENV_OMNIA_PROJECT_NAME
        )
        if not dest_path:
            return {
                "success": False,
                "details": "",
                "error": "Failed to resolve target input path",
            }

        # Ensure target directory exists
        ensure_remote_dir(host, dest_path)

        # Sync files
        result = sync_files(
            mode=conn["mode"], src=src_dir, dest=dest_path,
            ip=conn["ip"], user=conn["user"],
            password=conn["password"], ssh_opts=conn["ssh_opts"],
        )

        if result["success"]:
            return {
                "success": True,
                "details": f"Input files synced to {dest_path}",
                "error": "",
            }
        return {
            "success": False,
            "details": "",
            "error": result.get("error", "Sync failed"),
        }
    except Exception as exc:
        return {
            "success": False,
            "details": "",
            "error": str(exc),
        }

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

    # Resolve target input path
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


def get_utils_input_path(host) -> str:
    """Get the utils input path on target.

    Args:
        host: Testinfra host object.

    Returns:
        str: The input path or empty string on failure.
    """
    return resolve_domain_input_path(
        host, DOMAIN_NAME, ENV_OMNIA_DATA_PATH, ENV_OMNIA_PROJECT_NAME
    )


def get_utils_output_path(host) -> str:
    """Get the utils output path on target.

    Args:
        host: Testinfra host object.

    Returns:
        str: The output path or empty string on failure.
    """
    try:
        data_path = read_remote_env(host, ENV_OMNIA_DATA_PATH)
        project = read_remote_env(host, ENV_OMNIA_PROJECT_NAME)
        # Output is directly in the collect directory (timestamped subdirectories are handled separately)
        return f"{data_path}/{DOMAIN_NAME}/output/{project}/collect"
    except Exception:
        return ""
