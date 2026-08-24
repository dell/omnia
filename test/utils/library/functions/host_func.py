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
    SET_PXE_BOOT_CONFIG_FILE,
    SET_PXE_BOOT_INVENTORY_FILE,
    SET_PXE_BOOT_CREDENTIALS_FILE,
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


def sync_utils_credentials(host) -> Dict[str, Any]:
    """Sync utils credentials from test_creds.yml to target.

    Bridges credentials from test_creds.yml to the target's
    set_pxe_boot_credentials.yml file.

    Args:
        host: Testinfra host object.

    Returns:
        dict: {"success": bool, "details": str, "error": str}
    """
    try:
        creds = load_test_credentials()

        # Check if we have PXE boot credentials
        bmc_username = creds.get("bmc_username", "")
        bmc_password = creds.get("bmc_password", "")

        if not bmc_username and not bmc_password:
            return {
                "success": True,
                "details": "No BMC credentials in test_creds.yml, skipping sync",
                "error": "",
            }

        # Resolve target path
        dest_path = resolve_domain_input_path(
            host, DOMAIN_NAME, ENV_OMNIA_DATA_PATH, ENV_OMNIA_PROJECT_NAME
        )
        if not dest_path:
            return {
                "success": False,
                "details": "",
                "error": "Failed to resolve target input path",
            }

        # Create credentials YAML content
        creds_content = f"""---
# PXE Boot Credentials (synced from test_creds.yml)
bmc_username: "{bmc_username}"
bmc_password: "{bmc_password}"
"""

        # Write to target
        creds_file = os.path.join(dest_path, SET_PXE_BOOT_CREDENTIALS_FILE)
        cmd = f"cat > {creds_file} << 'EOF'\n{creds_content}EOF"
        result = host.run(cmd)

        if result.rc == 0:
            return {
                "success": True,
                "details": f"Credentials synced to {creds_file}",
                "error": "",
            }
        return {
            "success": False,
            "details": "",
            "error": f"Failed to write credentials: {result.stderr}",
        }
    except Exception as exc:
        return {
            "success": False,
            "details": "",
            "error": str(exc),
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
