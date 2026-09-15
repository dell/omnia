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

import fnmatch
import os
import shutil
import tempfile
from typing import Any, Dict

from omnia_auto import (
    connection_params,
    ensure_remote_dir,
    load_test_config,
    is_local_execution,
    resolve_domain_input_path,
    sync_files,
    get_module_root,
    run_on_host,
)

from ..vars.common_vars import (
    DOMAIN_NAME,
    ENV_OMNIA_DATA_PATH,
    ENV_OMNIA_PROJECT_NAME,
    SRC_INPUT_DIR,
)


_PROJECT_SYNC_EXCLUDE_NAMES = {
    ".agents",
    ".codex",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".test_creds.key",
    ".venv",
    "__pycache__",
    "active-venv",
    "powerscale_secret.yaml",
    "powerscale_secret.yml",
    "test_creds.yml",
    "venv",
}
_PROJECT_SYNC_EXCLUDE_PATTERNS = (
    ".*_credentials_key",
    ".*_credentials_key.*",
    ".test_creds.key.*",
    "*.pyc",
    "*_credentials.yml",
    "*_credentials.yml.*",
    "test_creds.yml.*",
)
_INPUT_SYNC_IGNORE = shutil.ignore_patterns(
    "build_stream_credentials.yml",
    "build_stream_credentials.yml.*",
    ".build_stream_credentials_key",
    ".build_stream_credentials_key.*",
)


def _project_sync_ignore(repo_root):
    """Return a copytree filter that keeps credentials out of staging."""

    def ignore(directory, names):
        relative_dir = os.path.relpath(directory, repo_root)
        ignored = []
        for name in names:
            relative_path = (
                name if relative_dir == "." else f"{relative_dir}/{name}"
            ).replace(os.sep, "/")
            required_source_task = (
                relative_path.startswith("src/")
                and ("/playbooks/" in relative_path or "/roles/" in relative_path)
                and fnmatch.fnmatch(name, "*_credentials.yml")
            )
            if required_source_task:
                continue
            if name in _PROJECT_SYNC_EXCLUDE_NAMES or any(
                fnmatch.fnmatch(name, pattern)
                for pattern in _PROJECT_SYNC_EXCLUDE_PATTERNS
            ):
                ignored.append(name)
        return ignored

    return ignore


def _link_or_copy(source: str, destination: str) -> str:
    """Hard-link staged files when possible, otherwise copy them."""
    try:
        os.link(source, destination, follow_symlinks=False)
        return destination
    except OSError:
        return shutil.copy2(source, destination, follow_symlinks=False)


def _resolve_remote_clone_path(config: Dict[str, Any]) -> str:
    """Return a validated absolute remote checkout path."""
    clone_path = config.get("clone_path")
    if not isinstance(clone_path, str) or not clone_path.strip():
        raise ValueError("clone_path is required for remote execution")
    clone_path = clone_path.strip()
    if not os.path.isabs(clone_path) or os.path.normpath(clone_path) == "/":
        raise ValueError("clone_path must be an absolute non-root path")
    return os.path.normpath(clone_path)


def resolve_target_source_root() -> str:
    """Resolve the Omnia checkout used by the execution target."""
    if is_local_execution():
        return os.path.dirname(os.path.dirname(get_module_root()))
    return _resolve_remote_clone_path(load_test_config())


def _resolve_local_input(config: Dict[str, Any]) -> str:
    """Resolve a source or dataset input directory without traversal."""
    dataset = config.get("dataset", "")
    if not dataset:
        return SRC_INPUT_DIR
    if (
        not isinstance(dataset, str)
        or dataset in {".", "..", "generator"}
        or os.path.isabs(dataset)
        or os.path.basename(dataset) != dataset
        or "\x00" in dataset
    ):
        raise ValueError(f"Unsafe dataset name: {dataset!r}")

    datasets_root = os.path.realpath(
        os.path.join(get_module_root(), "datasets")
    )
    dataset_path = os.path.join(datasets_root, dataset)
    if os.path.islink(dataset_path):
        raise ValueError(f"Dataset symlinks are not allowed: {dataset}")
    resolved_dataset = os.path.realpath(dataset_path)
    if os.path.dirname(resolved_dataset) != datasets_root:
        raise ValueError(f"Dataset escapes datasets directory: {dataset!r}")
    input_path = os.path.realpath(os.path.join(resolved_dataset, "input"))
    if os.path.commonpath((resolved_dataset, input_path)) != resolved_dataset:
        raise ValueError(f"Dataset input escapes its dataset: {dataset!r}")
    return input_path


def _reject_symlinks(directory: str) -> None:
    """Reject links in a tree before copying it into sync staging."""
    for current_dir, directory_names, file_names in os.walk(directory):
        for entry_name in directory_names + file_names:
            path = os.path.join(current_dir, entry_name)
            if os.path.islink(path):
                raise OSError(f"Refusing to sync dataset symlink: {path}")


def check_target_connectivity(host) -> Dict[str, Any]:
    """Confirm that the configured execution OIM accepts commands."""
    try:
        command = run_on_host(host, "true")
    except (OSError, RuntimeError, ValueError) as exc:
        return {"success": False, "details": "", "error": str(exc)}
    if command.rc == 0:
        return {
            "success": True,
            "details": "Execution OIM is reachable",
            "error": "",
        }
    return {
        "success": False,
        "details": "",
        "error": f"Connectivity command failed with rc={command.rc}",
    }


def sync_project_to_remote(_host) -> Dict[str, Any]:
    """Sync the monorepo project to the remote target host.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, details, error.
    """
    config = load_test_config()
    clone_path = _resolve_remote_clone_path(config)
    module_root = get_module_root()
    repo_root = os.path.dirname(os.path.dirname(module_root))

    try:
        conn = connection_params()
        with tempfile.TemporaryDirectory(
            prefix="omnia_build_stream_project_"
        ) as staging_dir:
            staged_project = os.path.join(staging_dir, "omnia")
            shutil.copytree(
                repo_root,
                staged_project,
                symlinks=True,
                ignore=_project_sync_ignore(repo_root),
                copy_function=_link_or_copy,
            )
            result = sync_files(
                mode=conn["mode"],
                src=staged_project,
                dest=clone_path,
                ip=conn["ip"],
                user=conn["user"],
                port=conn["port"],
                auth_secret=conn["auth_secret"],
                ssh_opts=conn["ssh_opts"],
            )
        if not result["success"]:
            return result
        return {
            "success": True,
            "details": f"Project synced to {clone_path}",
            "error": "",
        }
    except (OSError, RuntimeError, ValueError) as exc:
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
    try:
        src_path = _resolve_local_input(config)
        dest_path = resolve_domain_input_path(
            host,
            DOMAIN_NAME,
            ENV_OMNIA_DATA_PATH,
            ENV_OMNIA_PROJECT_NAME,
        )
        ensure_remote_dir(host, dest_path)
        conn = connection_params()
        _reject_symlinks(src_path)
        with tempfile.TemporaryDirectory(
            prefix="omnia_build_stream_input_"
        ) as staging_dir:
            staged_input = os.path.join(staging_dir, "input")
            shutil.copytree(
                src_path,
                staged_input,
                ignore=_INPUT_SYNC_IGNORE,
            )
            result = sync_files(
                mode=conn["mode"],
                src=staged_input,
                dest=dest_path,
                ip=conn["ip"],
                user=conn["user"],
                port=conn["port"],
                auth_secret=conn["auth_secret"],
                ssh_opts=conn["ssh_opts"],
            )
        if not result["success"]:
            return result
        return {
            "success": True,
            "details": f"Input synced to {dest_path} (credentials excluded)",
            "error": "",
        }
    except (OSError, RuntimeError, ValueError) as exc:
        return {
            "success": False,
            "details": "",
            "error": str(exc),
        }
