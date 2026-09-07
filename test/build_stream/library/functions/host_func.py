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
    load_test_config,
    sync_files,
    get_module_root,
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


def sync_project_to_remote(_host) -> Dict[str, Any]:
    """Sync the monorepo project to the remote target host.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, details, error.
    """
    config = load_test_config()
    clone_path = config.get("clone_path", "/root/omnia")
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


def sync_build_stream_input(_host) -> Dict[str, Any]:
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
        conn = connection_params()
        result = sync_files(
            mode=conn["mode"],
            src=src_path,
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
            "details": f"Input synced to {dest_path}",
            "error": "",
        }
    except (OSError, RuntimeError, ValueError) as exc:
        return {
            "success": False,
            "details": "",
            "error": str(exc),
        }
