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
Repo Manager — Host Sync Functions.

Functions to sync project files and input configs
to the target host for test execution.
"""

import os
import shutil
import tempfile
from typing import Any, Dict

from omnia_auto import (
    load_test_config,
    sync_files,
    get_module_root,
    is_local_execution,
    connection_params,
    resolve_domain_input_path,
    ensure_remote_dir,
    log,
)


# Constants
DOMAIN_NAME = "repo_manager"
ENV_OMNIA_DATA_PATH = "OMNIA_DATA_PATH"
ENV_OMNIA_PROJECT_NAME = "OMNIA_PROJECT_NAME"
SRC_INPUT_DIR = "src/repo_manager/input"


def _resolve_dataset_subdir(config: Dict[str, Any], subdirectory: str, src_fallback: str) -> str:
    """Resolve dataset subdirectory or fall back to src/."""
    dataset = config.get("dataset", "")
    if not dataset:
        # Fall back to source directory
        repo_root = os.path.dirname(os.path.dirname(get_module_root()))
        return os.path.join(repo_root, src_fallback)
    
    # Resolve dataset path with security checks
    datasets_root = os.path.realpath(os.path.join(get_module_root(), "datasets"))
    dataset_path = os.path.join(datasets_root, dataset)
    
    # Security checks
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


def sync_project_to_remote() -> Dict[str, Any]:
    """Sync the monorepo project to the remote target host.

    Returns:
        Dict with keys: success, details, error.
    """
    config = load_test_config()
    clone_path = config.get("clone_path", "/root/omnia")
    module_root = get_module_root()
    
    conn = connection_params()
    
    # Repo root: test/repo_manager/ -> test/ -> omnia/
    repo_root = os.path.dirname(os.path.dirname(get_module_root()))

    try:
        sync_files(
            mode=conn["mode"],
            src=repo_root,
            dest=clone_path,
            ip=conn["ip"],
            user=conn["user"],
            auth_secret=conn["auth_secret"],
            ssh_opts=conn["ssh_opts"],
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


def sync_repo_manager_input(host, config: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Sync repo_manager input files to the target host.

    Args:
        host: Testinfra host connection.
        config: Optional config dict (uses load_test_config() if not provided).

    Returns:
        Dict with keys: success, details, error, skipped.
    """
    if config is None:
        config = load_test_config()
    
    project = config.get("project_name", "project_default")
    conn = connection_params()
    
    local_input = _resolve_input_dir(config)
    
    if is_local_execution():
        # Local execution: use local dataset or source files directly
        return {
            "success": True,
            "skipped": True,
            "details": f"Local execution: using input from {local_input}",
            "error": "",
        }
    
    # Remote execution: sync to target
    remote_input = resolve_domain_input_path(
        host, DOMAIN_NAME, ENV_OMNIA_DATA_PATH, ENV_OMNIA_PROJECT_NAME,
    )
    ensure_remote_dir(host, remote_input)

    try:
        _reject_symlinks(local_input)
        with tempfile.TemporaryDirectory(prefix="omnia_rm_input_") as staging_dir:
            staged_input = os.path.join(staging_dir, "input")
            shutil.copytree(local_input, staged_input)

            result = sync_files(
                mode=conn["mode"],
                src=staged_input,
                dest=remote_input,
                ip=conn["ip"],
                user=conn["user"],
                auth_secret=conn["auth_secret"],
                ssh_opts=conn["ssh_opts"],
            )
    except OSError as exc:
        return {
            "success": False,
            "details": "",
            "error": f"Failed to stage repo_manager input: {exc}",
        }

    if result["success"]:
        result["details"] = f"Input synced to {remote_input}"
    return result