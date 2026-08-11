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

from typing import Any, Dict

from omnia_auto import (
    load_test_config,
    get_module_root,
    sync_files,
    clone_repo,
)
from ..vars.common_vars import (
    DOMAIN_NAME,
    INPUT_PATH_TEMPLATE,
    REPO_MANAGER_OUTPUT_TEMPLATE,
)


def sync_project_to_remote(host) -> Dict[str, Any]:
    """Clone or sync the Omnia repo to the remote target.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success (bool), details (str), error (str).
    """
    config = load_test_config()
    clone_path = config.get("clone_path", "/root/omnia")
    try:
        result = clone_repo(host, target_path=clone_path)
        return result
    except Exception as exc:  # pylint: disable=broad-except
        return {
            "success": False,
            "details": "",
            "error": f"Clone failed: {exc}",
        }


def sync_orchestrator_input(host) -> Dict[str, Any]:
    """Sync orchestrator input files (dataset) to target.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success (bool), details (str), error (str).
    """
    config = load_test_config()
    dataset = config.get("dataset", "data_set_01")
    project = config.get("project_name", "project_default")
    module_root = get_module_root()

    local_input = f"{module_root}/datasets/{dataset}/input"
    remote_input = INPUT_PATH_TEMPLATE.format(project=project)

    try:
        result = sync_files(
            host,
            local_path=local_input,
            remote_path=remote_input,
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
    dataset = config.get("dataset", "data_set_01")
    project = config.get("project_name", "project_default")
    module_root = get_module_root()

    local_output = f"{module_root}/datasets/{dataset}/repo_manager_output"
    remote_path = REPO_MANAGER_OUTPUT_TEMPLATE.format(project=project)
    # Sync directory containing repo_status.yml
    import os
    remote_dir = os.path.dirname(remote_path)

    try:
        result = sync_files(
            host,
            local_path=local_output,
            remote_path=remote_dir,
        )
        return result
    except Exception as exc:  # pylint: disable=broad-except
        return {
            "success": False,
            "details": "",
            "error": f"Output sync failed: {exc}",
        }
