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
Image Build Manager — Module-specific host utilities (monorepo).

Reads module config and passes ALL params to omnia_auto's
``clone_repo()`` and ``sync_files()``.  No logic in the package —
only in this consumer.

Monorepo changes vs multi-repo:
- Input path resolved from target env vars (OMNIA_DATA_PATH, OMNIA_PROJECT_NAME)
- sync_project_to_remote() copies local project code to target clone_path
- No separate config.yml sync (env vars replace it)

Common functions are re-exported from omnia_auto so existing
callers keep working.
"""

import os
import shutil
import tempfile
from typing import Dict, Any

import yaml

from omnia_auto import (
    load_test_config,
    load_test_credentials,
    is_local_execution,
    get_module_root,
    get_setting,
    sync_files,
    log,
    connection_params,
    read_remote_env,
    ensure_remote_dir,
    resolve_domain_input_path,
    get_testinfra_host,
    encrypt_test_credentials,
    run_on_host,
)

# Declare public API — re-exports for consumer convenience
__all__ = [
    "load_test_config",
    "load_test_credentials",
    "is_local_execution",
    "get_module_root",
    "get_setting",
    "sync_files",
    "log",
    "connection_params",
    "read_remote_env",
    "ensure_remote_dir",
    "resolve_domain_input_path",
    "get_testinfra_host",
    "encrypt_test_credentials",
    "run_on_host",
    "resolve_target_source_root",
    "sync_project_to_remote",
    "sync_image_build_input",
    "sync_repo_manager_output",
]

from ..vars.common_vars import (
    DOMAIN_NAME,
    ENV_OMNIA_DATA_PATH,
    ENV_OMNIA_PROJECT_NAME,
    IBM_CONFIG_FILE,
    CREDENTIALS_FILE_NAME,
    CREDENTIALS_KEY_NAME,
    SRC_INPUT_DIR,
    SRC_REPO_OUTPUT_DIR,
)


# =============================================================================
# NOTE: connection_params, read_remote_env, ensure_remote_dir, and
#       resolve_domain_input_path are now in the omnia-auto pip package.
#       They are imported above and used directly.
# =============================================================================


# =============================================================================
# MODULE-SPECIFIC SYNC
# =============================================================================

_DOMAIN_CREDENTIAL_PATTERNS = (
    CREDENTIALS_FILE_NAME,
    f"{CREDENTIALS_FILE_NAME}.*",
    CREDENTIALS_KEY_NAME,
    f"{CREDENTIALS_KEY_NAME}.*",
)
_input_sync_ignore = shutil.ignore_patterns(*_DOMAIN_CREDENTIAL_PATTERNS)
_project_sync_ignore = shutil.ignore_patterns(
    ".git",
    ".agents",
    ".codex",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "*.pyc",
    ".venv",
    "venv",
    "active-venv",
    "test_creds.yml",
    "test_creds.yml.*",
    ".test_creds.key",
    ".test_creds.key.*",
    *_DOMAIN_CREDENTIAL_PATTERNS,
)


def _link_or_copy(source: str, destination: str) -> str:
    """Hard-link staged project files when possible, otherwise copy them."""
    try:
        os.link(source, destination, follow_symlinks=False)
        return destination
    except OSError:
        return shutil.copy2(
            source, destination, follow_symlinks=False
        )


def _resolve_dataset_subdir(
    config: Dict[str, Any], subdirectory: str, fallback: str
) -> str:
    """Resolve one dataset subdirectory without allowing path traversal."""
    dataset = config.get("dataset", "")
    if not dataset:
        return fallback
    if not isinstance(dataset, str):
        raise ValueError("dataset must be a directory name string")
    if (
        dataset in {".", "..", "generator"}
        or os.path.isabs(dataset)
        or os.path.basename(dataset) != dataset
        or "\x00" in dataset
    ):
        raise ValueError(f"Unsafe dataset name: {dataset!r}")

    datasets_root = os.path.realpath(os.path.join(get_module_root(), "datasets"))
    dataset_path = os.path.join(datasets_root, dataset)
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


def _resolve_remote_clone_path(config: Dict[str, Any]) -> str:
    """Return the validated, normalized remote project destination."""
    raw_clone_path = config.get("clone_path")
    if not isinstance(raw_clone_path, str) or not raw_clone_path.strip():
        raise ValueError(
            "clone_path must be set in test_config.yml for remote execution"
        )
    clone_path = raw_clone_path.strip()
    if not os.path.isabs(clone_path):
        raise ValueError(
            f"clone_path must be absolute for remote execution: {clone_path}"
        )
    return os.path.normpath(clone_path)


def resolve_target_source_root() -> str:
    """Resolve the Omnia source root for the current execution target.

    Local execution reads directly from the current checkout.  Remote
    execution reads from ``clone_path``, where the checkout is synced on the
    target server.  This mirrors the path selection used by the shared
    ``omnia_auto`` playbook runner.

    Returns:
        Absolute source-root path on the execution target.

    Raises:
        ValueError: If remote execution is selected without ``clone_path``.
    """
    if is_local_execution():
        # Module root: test/image_build_manager/ -> repo root: omnia/
        return os.path.dirname(os.path.dirname(get_module_root()))

    return _resolve_remote_clone_path(load_test_config())


def sync_project_to_remote(_host) -> Dict[str, Any]:
    """Sync the local omnia project tree to clone_path on target.

    Copies a filtered working tree from the local monorepo to the remote
    ``clone_path``, using the same rsync/SSH checks as other sync functions.
    Local credential files, vault keys, VCS metadata, virtual environments,
    and caches are excluded. This replaces git-clone when the code is already
    available locally.

    Source: ``<repo_root>/`` (the omnia monorepo root)
    Dest:   ``<clone_path>/`` on the target server
    """
    config = load_test_config()
    conn = connection_params()
    clone_path = _resolve_remote_clone_path(config)

    # Repo root: test/image_build_manager/ -> test/ -> omnia/
    repo_root = os.path.dirname(os.path.dirname(get_module_root()))

    try:
        with tempfile.TemporaryDirectory(
            prefix="omnia_ibm_project_"
        ) as staging_dir:
            staged_project = os.path.join(staging_dir, "omnia")
            shutil.copytree(
                repo_root,
                staged_project,
                symlinks=True,
                ignore=_project_sync_ignore,
                copy_function=_link_or_copy,
            )
            result = sync_files(
                mode=conn["mode"],
                src=staged_project,
                dest=clone_path,
                ip=conn["ip"],
                user=conn["user"],
                auth_secret=conn["auth_secret"],
                ssh_opts=conn["ssh_opts"],
            )
    except OSError as exc:
        return {
            "success": False,
            "details": "",
            "error": f"Failed to stage project for sync: {exc}",
        }

    if result["success"]:
        result["details"] = (
            f"Synced filtered project {repo_root} -> {clone_path} "
            "(local credentials and caches excluded)"
        )
    return result


def _resolve_input_dir(config):
    """Resolve local input directory from dataset or src/."""
    return _resolve_dataset_subdir(config, "input", SRC_INPUT_DIR)


def _resolve_repo_output_dir(config):
    """Resolve local repo_manager_output directory from dataset or src/."""
    return _resolve_dataset_subdir(
        config, "repo_manager_output", SRC_REPO_OUTPUT_DIR
    )


def sync_image_build_input(
    host, config: Dict[str, Any] | None = None
) -> Dict[str, Any]:
    """Push image_build input files from local source to target.

    Reads ``OMNIA_DATA_PATH`` and ``OMNIA_PROJECT_NAME`` from the target
    server's environment to resolve the correct destination::

        <OMNIA_DATA_PATH>/image_build_manager/input/<OMNIA_PROJECT_NAME>/

    Source: src/image_build_manager/input/ (default) or
            datasets/<dataset>/input/ (when dataset is set).

    Any credential artifacts are deliberately excluded. Generated datasets
    contain no credentials; create runtime credentials directly on the
    execution OIM with ``./setup_env.sh --set-domain-creds``.
    """
    if config is None:
        config = load_test_config()
    conn = connection_params()

    local_input = _resolve_input_dir(config)
    remote_input = resolve_domain_input_path(
        host, DOMAIN_NAME, ENV_OMNIA_DATA_PATH, ENV_OMNIA_PROJECT_NAME,
    )
    ensure_remote_dir(host, remote_input)

    try:
        _reject_symlinks(local_input)
        with tempfile.TemporaryDirectory(
            prefix="omnia_ibm_input_"
        ) as staging_dir:
            staged_input = os.path.join(staging_dir, "input")
            shutil.copytree(
                local_input,
                staged_input,
                ignore=_input_sync_ignore,
            )

            result = sync_files(
                mode=conn["mode"], src=staged_input, dest=remote_input,
                ip=conn["ip"], user=conn["user"],
                auth_secret=conn["auth_secret"], ssh_opts=conn["ssh_opts"],
            )
    except OSError as exc:
        return {
            "success": False,
            "details": "",
            "error": f"Failed to stage image-build input: {exc}",
        }

    if result["success"]:
        result["details"] += " (credentials excluded)"
    return result


def sync_repo_manager_output(
    host, config: Dict[str, Any] | None = None
) -> Dict[str, Any]:
    """Push repo_manager_output from local source to target.

    Reads repo_manager_output_dir from image_build_config.yml.
    Falls back to <OMNIA_DATA_PATH>/repo_manager/output/<project_name>/.

    Source: src/.../samples/repo_manager_output/ (default) or
            datasets/<dataset>/repo_manager_output/ (when dataset is set).
    """
    if config is None:
        config = load_test_config()
    conn = connection_params()

    local_output = _resolve_repo_output_dir(config)

    # Read repo_manager_output_path from image_build_config.yml
    # The config has repo_manager_output_path pointing to repo_status.yml;
    # we need its parent directory.
    local_ibm_config = os.path.join(
        _resolve_input_dir(config), IBM_CONFIG_FILE,
    )
    # Derive from target env vars — no fallbacks
    data_path = read_remote_env(host, ENV_OMNIA_DATA_PATH)
    project = read_remote_env(host, ENV_OMNIA_PROJECT_NAME)
    remote_output_dir = f"{data_path}/repo_manager/output/{project}"

    if os.path.isfile(local_ibm_config):
        try:
            with open(local_ibm_config, "r", encoding="utf-8") as fh:
                ibm_cfg = yaml.safe_load(fh) or {}
            configured_path = ibm_cfg.get("repo_manager_output_path", "")
            if configured_path:
                # repo_manager_output_path points to repo_status.yml
                # — use its parent directory as the sync destination
                remote_output_dir = os.path.dirname(configured_path)
        except (yaml.YAMLError, OSError):
            pass

    ensure_remote_dir(host, remote_output_dir)

    return sync_files(
        mode=conn["mode"], src=local_output, dest=remote_output_dir,
        ip=conn["ip"], user=conn["user"],
        auth_secret=conn["auth_secret"], ssh_opts=conn["ssh_opts"],
    )
