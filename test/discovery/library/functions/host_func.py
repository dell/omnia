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

Functions for syncing project code and input datasets to the target host.
Re-exports common functions from omnia_auto.
"""

import os
from typing import Any, Dict

from omnia_auto import (
    load_test_config,
    get_module_root,
    sync_files,
)
from ..vars.common_vars import DOMAIN_NAME, INPUT_PATH_TEMPLATE


def sync_project_to_remote(_host) -> Dict[str, Any]:
    """Sync the local omnia project tree to clone_path on target.

    Copies the complete project from the local monorepo to the remote
    clone_path. This replaces git-clone when the code is already
    available locally.

    Source: <repo_root>/ (the omnia monorepo root)
    Dest:   <clone_path>/ on the target server
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

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success (bool), details (str), error (str).
    """
    config = load_test_config()
    dataset = config.get("dataset", "data_set_01")
    project = config.get("project_name", "project_default")
    module_root = get_module_root()
    oim_server_ip = config.get("oim_server_ip", "")

    local_input = f"{module_root}/datasets/{dataset}/input"
    remote_input = INPUT_PATH_TEMPLATE.format(project=project)

    try:
        if oim_server_ip:
            result = sync_files(
                mode="remote",
                src=local_input,
                dest=remote_input,
                ip=oim_server_ip,
                user=config.get("oim_ssh_user", "root"),
                password=None,
            )
        else:
            result = sync_files(
                mode="local",
                src=local_input,
                dest=remote_input,
            )
        return result
    except Exception as exc:  # pylint: disable=broad-except
        return {
            "success": False,
            "details": "",
            "error": f"Input sync failed: {exc}",
        }
