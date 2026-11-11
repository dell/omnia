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
Discovery — Host Synchronization Functions

This module provides functions for syncing project code and input datasets
to the target host. It re-exports common functions from omnia_auto and
provides domain-specific synchronization for the discovery domain.

Functions:
    sync_project_to_remote: Sync the local omnia project tree to clone_path on target
    sync_discovery_input: Sync discovery input files (dataset) to target
"""

import os
from typing import Any, Dict

from omnia_auto import (
    connection_params,
    ensure_remote_dir,
    get_module_root,
    load_test_config,
    read_remote_env,
    resolve_domain_input_path,
    sync_files,
)
from ..vars.common_vars import (
    DOMAIN_NAME,
    ENV_OMNIA_DATA_PATH,
    ENV_DISCOVERY_DATA_PATH,
    ENV_OMNIA_PROJECT_NAME,
    SRC_INPUT_DIR,
)


def sync_project_to_remote(_host) -> Dict[str, Any]:
    """Sync the local omnia project tree to clone_path on target.

    This function copies the complete project from the local monorepo to the
    remote clone_path. This replaces git-clone when the code is already
    available locally.

    Args:
        _host: Testinfra host connection (unused, kept for interface compatibility).

    Returns:
        Dict[str, Any]: A dictionary with keys:
            - success (bool): Whether the sync operation succeeded
            - details (str): Details about the sync operation
            - error (str): Error message if the sync failed

    Source:
        <repo_root>/ (the omnia monorepo root)

    Destination:
        <clone_path>/ on the target server
    """
    config = load_test_config()
    oim_server_ip = config.get("oim_server_ip", "")
    clone_path = config.get("clone_path", "/root/omnia")

    # Repo root: test/discovery/ -> test/ -> omnia/
    repo_root = os.path.dirname(os.path.dirname(get_module_root()))

    try:
        if oim_server_ip:
            result = sync_files(
                mode="remote",
                src=repo_root,
                dest=clone_path,
                ip=oim_server_ip,
                user=config.get("oim_ssh_user", "root"),
                password=None,
            )
        else:
            result = sync_files(
                mode="local",
                src=repo_root,
                dest=clone_path,
            )
        return result
    except Exception as exc:  # pylint: disable=broad-except
        return {
            "success": False,
            "details": "",
            "error": f"Sync failed: {exc}",
        }


def sync_discovery_input(host) -> Dict[str, Any]:
    """Sync discovery input files (dataset) to target.

    This function synchronizes the discovery input files from the local dataset
    directory to the target host's input directory. It reads the target's
    environment variables to resolve the destination path dynamically.

    Args:
        host: Testinfra host connection for the target server.

    Returns:
        Dict[str, Any]: A dictionary with keys:
            - success (bool): Whether the sync operation succeeded
            - details (str): Details about the sync operation
            - error (str): Error message if the sync failed

    Notes:
        - The local input path is constructed as: <module_root>/datasets/<dataset>/input
        - The remote input path is resolved from target env vars:
          <DISCOVERY_DATA_PATH>/input/<project> or
          <OMNIA_DATA_PATH>/discovery/input/<project>
        - Uses sync_files from omnia_auto for the actual file transfer
    """
    config = load_test_config()
    dataset = config.get("dataset", "data_set_01")
    module_root = get_module_root()
    conn = connection_params()

    # Resolve local input directory from dataset or src/
    if dataset:
        local_input = f"{module_root}/datasets/{dataset}/input"
    else:
        local_input = SRC_INPUT_DIR

    # Resolve remote input path from target environment variables
    remote_input = resolve_domain_input_path(
        host,
        DOMAIN_NAME,
        ENV_OMNIA_DATA_PATH,
        ENV_OMNIA_PROJECT_NAME,
        domain_data_path_var=ENV_DISCOVERY_DATA_PATH,
    )
    ensure_remote_dir(host, remote_input)

    try:
        result = sync_files(
            mode=conn["mode"],
            src=local_input,
            dest=remote_input,
            ip=conn["ip"],
            user=conn["user"],
            port=conn["port"],
            auth_secret=conn["auth_secret"],
            ssh_opts=conn["ssh_opts"],
        )
    except Exception as exc:  # pylint: disable=broad-except
        return {
            "success": False,
            "details": "",
            "error": f"Input sync failed: {exc}",
        }

    if result["success"]:
        result["details"] = f"Synced {local_input} -> {remote_input}"
    return result
