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
Shared helpers for build image verification functions.

- SSH retry wrapper
- Remote config loading (image_build_config.yml, build_status.yml)
- Functional group resolution
"""

import os
import time
from typing import List

import yaml

from omnia_auto import resolve_domain_input_path

from ..vars.common_vars import (
    DOMAIN_NAME,
    ENV_OMNIA_DATA_PATH,
    ENV_OMNIA_PROJECT_NAME,
    IBM_CONFIG_FILE,
    SHARED_PATH,
    CMDS,
)


# =============================================================================
# RETRY ON TRANSIENT SSH FAILURES
# =============================================================================

def _retry_run(host, cmd_str, retries: int = 2, delay: float = 3.0):
    """Run a command on the host with retry on transient failures.

    Retries when the command returns rc=255 (SSH connection error)
    or rc=-1 (connection timeout). Non-SSH failures are not retried.

    Args:
        host: testinfra host object.
        cmd_str: Command string to execute.
        retries: Number of retry attempts (default 2).
        delay: Seconds to wait between retries (default 3.0).

    Returns:
        testinfra CommandResult.
    """
    last_result = None
    for attempt in range(1 + retries):
        last_result = host.run(cmd_str)
        if last_result.rc not in (255, -1):
            return last_result
        if attempt < retries:
            time.sleep(delay)
    return last_result


# =============================================================================
# LOAD CONFIG FROM TARGET
# =============================================================================

def _get_shared_path() -> str:
    """Get shared_path from OMNIA_DATA_PATH env var.

    Constructs ``<OMNIA_DATA_PATH>/image_build_manager`` from the
    local environment (sourced from /etc/omnia/omnia.env).
    Falls back to the SHARED_PATH constant.
    """
    data_path = os.environ.get(ENV_OMNIA_DATA_PATH, "")
    if data_path:
        return f"{data_path}/{DOMAIN_NAME}"
    return SHARED_PATH


def _get_project_name() -> str:
    """Get project_name from OMNIA_PROJECT_NAME env var.

    Reads from the local environment (sourced from /etc/omnia/omnia.env).
    Falls back to 'project_default' if not set.
    """
    return os.environ.get(ENV_OMNIA_PROJECT_NAME, "project_default")


def _get_remote_ibm_config_path(host) -> str:
    """Get the deployed image_build_config.yml path on target.

    Uses env vars to resolve::

        <OMNIA_DATA_PATH>/image_build_manager/input/<project>/image_build_config.yml
    """
    input_dir = resolve_domain_input_path(
        host, DOMAIN_NAME, ENV_OMNIA_DATA_PATH, ENV_OMNIA_PROJECT_NAME,
    )
    return f"{input_dir}/{IBM_CONFIG_FILE}"


def _load_remote_ibm_config(host) -> dict:
    """Load image_build_config.yml from the target host.

    Returns parsed YAML as dict, or empty dict on failure.
    Uses retry for transient SSH errors.
    """
    cfg_path = _get_remote_ibm_config_path(host)
    cmd = _retry_run(host, CMDS["cat_file"].format(path=cfg_path))
    if cmd.rc != 0 or not cmd.stdout.strip():
        return {}
    try:
        return yaml.safe_load(cmd.stdout) or {}
    except yaml.YAMLError:
        return {}


def _get_built_groups_from_status(host, arch: str = None) -> List[str]:
    """Extract actually built group names from build_status.yml.

    In catalog mode, the playbook resolves group names to the full
    ``{role}_{os}_{ver}_{arch}`` format (e.g. slurm_node_rhel_10_0_x86_64).
    This helper reads build_status.yml to discover those actual names.

    Returns:
        List of built functional group name strings (may be empty).
    """
    # Deferred import to avoid circular dependency
    from .build_status_func import check_build_status_file

    status = check_build_status_file(host)
    if not status.get("success") or "data" not in status:
        return []

    groups = []
    fg_images = status["data"].get("functional_group_images", [])
    for arch_block in fg_images:
        if isinstance(arch_block, dict):
            for _key, entries in arch_block.items():
                if not isinstance(entries, list):
                    continue
                for entry in entries:
                    if isinstance(entry, dict):
                        fg_name = entry.get("functional_group", "")
                        if fg_name:
                            groups.append(fg_name)

    if arch:
        groups = [g for g in groups if arch in g]

    return groups


def get_configured_functional_groups(
    host, arch: str = None
) -> List[str]:
    """Get functional groups from image_build_config.yml on target.

    In **config** mode, reads the ``functional_groups`` list from the
    deployed image_build_config.yml.

    In **catalog** mode, the config list contains short (legacy) names
    but the playbook resolves them to ``{role}_{os}_{ver}_{arch}`` format.
    This function returns the *actually built* names from build_status.yml
    so that S3, registry, and package checks match correctly.

    Args:
        host: testinfra host object
        arch: Filter by architecture suffix (x86_64 or aarch64)

    Returns:
        List of functional group name strings.
    """
    cfg = _load_remote_ibm_config(host)
    if not cfg:
        return []

    # Prefer actual built names from build_status.yml when available.
    built = _get_built_groups_from_status(host, arch=arch)
    if built:
        return built

    fg_list = cfg.get("functional_groups", [])
    groups = []
    for entry in fg_list:
        name = ""
        if isinstance(entry, dict):
            name = entry.get("name", "")
        elif isinstance(entry, str):
            name = entry
        if name:
            groups.append(name)

    if arch:
        groups = [g for g in groups if arch in g]

    return groups


def _get_s3_provider(host) -> str:
    """Get S3 provider from image_build_config.yml on target.

    Returns 'minio' or 'powerscale' or empty string.
    """
    cfg = _load_remote_ibm_config(host)
    s3_cfg = cfg.get("s3_configurations", {})
    return s3_cfg.get("provider", "minio").lower()
