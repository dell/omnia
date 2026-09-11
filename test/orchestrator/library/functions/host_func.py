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
import shutil
import tempfile
from typing import Any, Dict

from omnia_auto import (
    connection_params,
    load_test_config,
    get_module_root,
    sync_files,
)
from ..vars.common_vars import (
    DATASET_NAME_PATTERN,
    DATASETS_DIR,
    IMAGE_BUILD_MANAGER_OUTPUT_TEMPLATE,
    INPUT_PATH_TEMPLATE,
    REPO_MANAGER_OUTPUT_TEMPLATE,
    SRC_IMAGE_BUILD_OUTPUT_DIR,
    SRC_INPUT_DIR,
    SRC_REPO_OUTPUT_DIR,
)


def _resolve_dataset_subdir(config, subdirectory, fallback):
    """Resolve a dataset subdirectory without permitting path traversal."""
    dataset = config.get("dataset", "")
    if not dataset:
        return os.path.realpath(fallback)
    if (
        not isinstance(dataset, str)
        or not DATASET_NAME_PATTERN.fullmatch(dataset)
        or dataset in {".", "..", "generator"}
    ):
        raise ValueError(f"Unsafe dataset name: {dataset!r}")

    datasets_root = os.path.realpath(DATASETS_DIR)
    dataset_path = os.path.join(datasets_root, dataset)
    if os.path.islink(dataset_path):
        raise ValueError(f"Dataset symlinks are not allowed: {dataset}")
    resolved_dataset = os.path.realpath(dataset_path)
    if os.path.dirname(resolved_dataset) != datasets_root:
        raise ValueError(f"Dataset escapes datasets directory: {dataset!r}")

    subdir_path = os.path.join(resolved_dataset, subdirectory)
    if os.path.islink(subdir_path):
        raise ValueError(
            f"Dataset subdirectory symlinks are not allowed: "
            f"{dataset}/{subdirectory}"
        )
    resolved_subdir = os.path.realpath(subdir_path)
    if os.path.commonpath((resolved_dataset, resolved_subdir)) != resolved_dataset:
        raise ValueError(
            f"Dataset subdirectory escapes its dataset: "
            f"{dataset}/{subdirectory}"
        )
    return resolved_subdir


def _reject_symlinks(directory):
    """Reject links in a dataset tree before staging it for synchronization."""
    for current_dir, directory_names, file_names in os.walk(directory):
        for entry_name in directory_names + file_names:
            path = os.path.join(current_dir, entry_name)
            if os.path.islink(path):
                raise OSError(f"Refusing to synchronize dataset symlink: {path}")


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
            ip=conn["ip"],
            user=conn["user"],
            port=conn["port"],
            auth_secret=conn["auth_secret"],
            ssh_opts=conn["ssh_opts"],
        )
        return result
    except (OSError, RuntimeError, ValueError) as exc:
        return {
            "success": False,
            "details": "",
            "error": f"Sync failed: {exc}",
        }


def sync_orchestrator_input(_host, config=None) -> Dict[str, Any]:
    """Sync orchestrator input files (dataset) to target.

    Args:
        _host: Reserved testinfra host connection for API compatibility.
        config: Optional already-resolved test configuration.

    Returns:
        Dict with keys: success (bool), details (str), error (str).
    """
    config = config or load_test_config()
    project = config.get("project_name", "project_default")
    conn = connection_params()

    local_input = _resolve_dataset_subdir(config, "input", SRC_INPUT_DIR)
    remote_input = INPUT_PATH_TEMPLATE.format(project=project)

    try:
        _reject_symlinks(local_input)
        with tempfile.TemporaryDirectory(
            prefix="omnia_orchestrator_input_"
        ) as root:
            staged_input = os.path.join(root, "input")
            shutil.copytree(SRC_INPUT_DIR, staged_input)
            if os.path.realpath(local_input) != os.path.realpath(SRC_INPUT_DIR):
                shutil.copytree(local_input, staged_input, dirs_exist_ok=True)
            return sync_files(
                mode=conn["mode"],
                src=staged_input,
                dest=remote_input,
                ip=conn["ip"],
                user=conn["user"],
                port=conn["port"],
                auth_secret=conn["auth_secret"],
                ssh_opts=conn["ssh_opts"],
            )
    except (OSError, RuntimeError, ValueError) as exc:
        return {
            "success": False,
            "details": "",
            "error": f"Input sync failed: {exc}",
        }


def sync_repo_manager_output(_host, config=None) -> Dict[str, Any]:
    """Sync repo_manager output (repo_status.yml) to target.

    Args:
        _host: Reserved testinfra host connection for API compatibility.

    Returns:
        Dict with keys: success (bool), details (str), error (str).
    """
    config = config or load_test_config()
    project = config.get("project_name", "project_default")
    conn = connection_params()

    local_output = _resolve_dataset_subdir(
        config, "repo_manager_output", SRC_REPO_OUTPUT_DIR
    )
    remote_path = REPO_MANAGER_OUTPUT_TEMPLATE.format(project=project)
    # Sync directory containing repo_status.yml
    remote_dir = os.path.dirname(remote_path)

    try:
        _reject_symlinks(local_output)
        result = sync_files(
            mode=conn["mode"],
            src=local_output,
            dest=remote_dir,
            ip=conn["ip"],
            user=conn["user"],
            port=conn["port"],
            auth_secret=conn["auth_secret"],
            ssh_opts=conn["ssh_opts"],
        )
        return result
    except (OSError, RuntimeError, ValueError) as exc:
        return {
            "success": False,
            "details": "",
            "error": f"Output sync failed: {exc}",
        }


def sync_image_build_manager_output(_host, config=None) -> Dict[str, Any]:
    """Sync the image-builder ``build_status.yml`` handoff to the target."""
    config = config or load_test_config()
    project = config.get("project_name", "project_default")
    conn = connection_params()

    local_output = _resolve_dataset_subdir(
        config,
        "image_build_manager_output",
        SRC_IMAGE_BUILD_OUTPUT_DIR,
    )
    remote_path = IMAGE_BUILD_MANAGER_OUTPUT_TEMPLATE.format(project=project)
    remote_dir = os.path.dirname(remote_path)

    try:
        _reject_symlinks(local_output)
        return sync_files(
            mode=conn["mode"],
            src=local_output,
            dest=remote_dir,
            ip=conn["ip"],
            user=conn["user"],
            port=conn["port"],
            auth_secret=conn["auth_secret"],
            ssh_opts=conn["ssh_opts"],
        )
    except (OSError, RuntimeError, ValueError) as exc:
        return {
            "success": False,
            "details": "",
            "error": f"Image build output sync failed: {exc}",
        }
