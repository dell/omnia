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
Orchestrator — Host Synchronization Functions

Functions for syncing project code and input datasets to the target host.
"""

import os
from typing import Any, Dict

from omnia_auto import (
    load_test_config,
    get_module_root,
    sync_files,
    connection_params,
)
from ..vars.common_vars import (
    DOMAIN_NAME,
    INPUT_PATH_TEMPLATE,
    REPO_MANAGER_OUTPUT_TEMPLATE,
)


def sync_project_to_remote(_host) -> Dict[str, Any]:
    """Sync the local omnia project tree to clone_path on target.

    Copies the complete project from the local monorepo to the remote
    clone_path. This replaces git-clone when the code is already
    available locally.

    Source: <repo_root>/ (the omnia monorepo root)
    Dest:   <clone_path>/ on the target server
    """
    config = load_test_config()
    conn = connection_params()
    clone_path = config.get("clone_path", "/root/omnia")

    # Repo root: test/orchestrator/ -> test/ -> omnia/
    repo_root = os.path.dirname(os.path.dirname(get_module_root()))

    try:
        result = sync_files(
            mode=conn["mode"],
            src=repo_root,
            dest=clone_path,
            ip=conn.get("ip"),
            user=conn.get("user", "root"),
            auth_secret=conn.get("auth_secret"),
            ssh_opts=conn.get("ssh_opts", ""),
        )
        return result
    except Exception as exc:  # pylint: disable=broad-except
        return {
            "success": False,
            "details": "",
            "error": f"Sync failed: {exc}",
        }


def sync_orchestrator_input(host) -> Dict[str, Any]:
    """Sync orchestrator input files (dataset) to target.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success (bool), details (str), error (str).
    """
    config = load_test_config()
    conn = connection_params()
    dataset = config.get("dataset", "data_set_01")
    project = config.get("project_name", "project_default")
    module_root = get_module_root()

    local_input = f"{module_root}/datasets/{dataset}/input"
    remote_input = INPUT_PATH_TEMPLATE.format(project=project)

    try:
        result = sync_files(
            mode=conn["mode"],
            src=local_input,
            dest=remote_input,
            ip=conn.get("ip"),
            user=conn.get("user", "root"),
            auth_secret=conn.get("auth_secret"),
            ssh_opts=conn.get("ssh_opts", ""),
        )
        return result
    except Exception as exc:  # pylint: disable=broad-except
        return {
            "success": False,
            "details": "",
            "error": f"Input sync failed: {exc}",
        }


def sync_repo_manager_output(host) -> Dict[str, Any]:
    """Sync repo_manager output (repo_status.yml) to target.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success (bool), details (str), error (str).
    """
    config = load_test_config()
    conn = connection_params()
    dataset = config.get("dataset", "data_set_01")
    project = config.get("project_name", "project_default")
    module_root = get_module_root()

    local_output = f"{module_root}/datasets/{dataset}/repo_manager_output"
    remote_path = REPO_MANAGER_OUTPUT_TEMPLATE.format(project=project)
    # Sync directory containing repo_status.yml
    remote_dir = os.path.dirname(remote_path)

    try:
        result = sync_files(
            mode=conn["mode"],
            src=local_output,
            dest=remote_dir,
            ip=conn.get("ip"),
            user=conn.get("user", "root"),
            auth_secret=conn.get("auth_secret"),
            ssh_opts=conn.get("ssh_opts", ""),
        )
        return result
    except Exception as exc:  # pylint: disable=broad-except
        return {
            "success": False,
            "details": "",
            "error": f"Output sync failed: {exc}",
        }


def sync_image_build_manager_output(host) -> Dict[str, Any]:
    """Sync image_build_manager output (build_status.yml) to target.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success (bool), details (str), error (str).
    """
    config = load_test_config()
    conn = connection_params()
    dataset = config.get("dataset", "data_set_01")
    project = config.get("project_name", "project_default")
    module_root = get_module_root()

    local_output = f"{module_root}/datasets/{dataset}/image_build_manager_output"
    # Sync to /opt/omnia/image_build_manager/output/<project>/
    remote_dir = f"/opt/omnia/image_build_manager/output/{project}"

    try:
        result = sync_files(
            mode=conn["mode"],
            src=local_output,
            dest=remote_dir,
            ip=conn.get("ip"),
            user=conn.get("user", "root"),
            auth_secret=conn.get("auth_secret"),
            ssh_opts=conn.get("ssh_opts", ""),
        )
        return result
    except Exception as exc:  # pylint: disable=broad-except
        return {
            "success": False,
            "details": "",
            "error": f"Image build output sync failed: {exc}",
        }
