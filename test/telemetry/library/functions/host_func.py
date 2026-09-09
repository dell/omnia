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
Telemetry — Module-specific host utilities.

Reads module config and passes ALL params to omnia_auto's
``sync_files()``.  No logic in the package -- only in this consumer.

Monorepo changes vs multi-repo:
- Input path resolved from target env vars (component override or
  OMNIA_DATA_PATH fallback, plus OMNIA_PROJECT_NAME)
- sync_project_to_remote() copies local project code to target clone_path
- No separate config.yml sync (env vars replace it)
"""

import fnmatch
import os
import shutil
import tempfile
from typing import Dict, Any

from omnia_auto import (
    load_test_config,
    get_module_root,
    sync_files,
    connection_params,
    resolve_domain_input_path,
    ensure_remote_dir,
)

from ..vars.common_vars import (
    DOMAIN_NAME,
    ENV_TELEMETRY_DATA_PATH,
    ENV_OMNIA_DATA_PATH,
    ENV_OMNIA_PROJECT_NAME,
    SRC_INPUT_DIR,
)

__all__ = [
    "sync_project_to_remote",
    "sync_telemetry_input",
]


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
    """Sync the local omnia project tree to clone_path on target.

    Source: ``<repo_root>/`` (the omnia monorepo root)
    Dest:   ``<clone_path>/`` on the target server
    """
    config = load_test_config()
    conn = connection_params()

    repo_root = os.path.dirname(os.path.dirname(get_module_root()))

    try:
        with tempfile.TemporaryDirectory(
            prefix="omnia_telemetry_project_"
        ) as staging_dir:
            staged_project = os.path.join(staging_dir, "omnia")
            shutil.copytree(
                repo_root,
                staged_project,
                symlinks=True,
                ignore=_project_sync_ignore(repo_root),
                copy_function=_link_or_copy,
            )
            return sync_files(
                mode=conn["mode"],
                src=staged_project,
                dest=config["clone_path"],
                ip=conn["ip"],
                user=conn["user"],
                port=conn["port"],
                auth_secret=conn["auth_secret"],
                ssh_opts=conn["ssh_opts"],
            )
    except OSError as exc:
        return {
            "success": False,
            "details": "",
            "error": f"Failed to stage project for sync: {exc}",
        }


def _resolve_input_dir(config):
    """Resolve local input directory from dataset or src/."""
    dataset = config.get("dataset", "")
    if dataset:
        return os.path.join(
            get_module_root(), "datasets", dataset, "input",
        )
    return SRC_INPUT_DIR


def sync_telemetry_input(host) -> Dict[str, Any]:
    """Push telemetry input files from local source to target.

    Reads the component data-path override, ``OMNIA_DATA_PATH``, and
    ``OMNIA_PROJECT_NAME`` from the target to resolve the destination::

        <effective-domain-data-path>/input/<OMNIA_PROJECT_NAME>/

    Source: src/telemetry/input/ (default) or
            datasets/<dataset>/input/ (when dataset is set).
    """
    config = load_test_config()
    conn = connection_params()

    local_input = _resolve_input_dir(config)
    remote_input = resolve_domain_input_path(
        host,
        DOMAIN_NAME,
        ENV_OMNIA_DATA_PATH,
        ENV_OMNIA_PROJECT_NAME,
        domain_data_path_var=ENV_TELEMETRY_DATA_PATH,
    )
    ensure_remote_dir(host, remote_input)

    return sync_files(
        mode=conn["mode"], src=local_input, dest=remote_input,
        ip=conn["ip"], user=conn["user"],
        port=conn["port"],
        auth_secret=conn["auth_secret"], ssh_opts=conn["ssh_opts"],
    )
