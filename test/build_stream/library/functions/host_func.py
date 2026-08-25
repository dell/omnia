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
Build Stream — Host Sync Functions.

Functions to sync project files and input configs
to the target host for test execution.
"""

from typing import Any, Dict

from omnia_auto import (
    load_test_config,
    sync_files,
    get_module_root,
)


def sync_project_to_remote(host) -> Dict[str, Any]:
    """Sync the monorepo project to the remote target host.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, details, error.
    """
    config = load_test_config()
    clone_path = config.get("clone_path", "/root/omnia")
    module_root = get_module_root()

    try:
        sync_files(
            mode="ssh",
            host=host,
            src=f"{module_root}/../../",
            dest=clone_path,
        )
        return {
            "success": True,
            "details": f"Project synced to {clone_path}",
            "error": "",
        }
    except (OSError, RuntimeError) as exc:
        return {
            "success": False,
            "details": "",
            "error": str(exc),
        }


def sync_build_stream_input(host) -> Dict[str, Any]:
    """Sync build_stream input files to the target host.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, details, error.
    """
    config = load_test_config()
    dataset = config.get("dataset", "")
    project = config.get("project_name", "project_default")
    module_root = get_module_root()

    if not dataset:
        return {
            "success": True,
            "skipped": True,
            "details": "No dataset configured, skipping input sync",
            "error": "",
        }

    src_path = f"{module_root}/datasets/{dataset}/input/"
    shared_path = config.get("shared_path", "/opt/omnia/build_stream")
    dest_path = f"{shared_path}/input/{project}/"

    try:
        sync_files(
            mode="ssh",
            host=host,
            src=src_path,
            dest=dest_path,
        )
        return {
            "success": True,
            "details": f"Input synced to {dest_path}",
            "error": "",
        }
    except (OSError, RuntimeError) as exc:
        return {
            "success": False,
            "details": "",
            "error": str(exc),
        }
