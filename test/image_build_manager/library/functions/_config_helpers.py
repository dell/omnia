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

import json
import os
import time
from typing import Any, Dict, List

import yaml

from omnia_auto import read_remote_env, resolve_domain_input_path

from ..vars.common_vars import (
    DOMAIN_NAME,
    ENV_CATALOG_FILE_PATH,
    ENV_OMNIA_DATA_PATH,
    ENV_OMNIA_PROJECT_NAME,
    IBM_CONFIG_FILE,
    PACKAGE_GROUPS_FILENAME,
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


def _read_remote_text(host, path: str, description: str):
    """Read a required target-host file and return text plus an error."""
    result = _retry_run(host, CMDS["cat_file"].format(path=path))
    if result.rc != 0 or not result.stdout.strip():
        return "", f"{description} is unavailable or empty at {path}"
    return result.stdout, ""


def _config_mode_groups(host, input_dir: str, arch: str):
    """Resolve groups using the same selection rules as config-mode builds."""
    package_groups_path = f"{input_dir}/{PACKAGE_GROUPS_FILENAME}"
    content, error = _read_remote_text(
        host, package_groups_path, PACKAGE_GROUPS_FILENAME,
    )
    if error:
        return [], error

    try:
        package_groups = yaml.safe_load(content)
    except yaml.YAMLError as exc:
        return [], f"Failed to parse {PACKAGE_GROUPS_FILENAME}: {exc}"

    if not isinstance(package_groups, dict):
        return [], f"{PACKAGE_GROUPS_FILENAME} must contain a YAML mapping"
    functional_groups = package_groups.get("functional_groups")
    if not isinstance(functional_groups, dict):
        return [], (
            f"{PACKAGE_GROUPS_FILENAME}.functional_groups must be a mapping"
        )

    groups = []
    suffix = f"_{arch}"
    for name, group_data in functional_groups.items():
        if not isinstance(name, str):
            return [], (
                f"{PACKAGE_GROUPS_FILENAME} contains a non-string group name"
            )
        if not name.endswith(suffix) or "driver_group" in name:
            continue
        # The shipped package_groups.yml uses null-valued placeholders.
        # Ansible's ``fg_data.packages | default([])`` treats an absent group
        # mapping as an empty package list, so mirror that source behavior.
        if group_data is None:
            continue
        if not isinstance(group_data, dict):
            return [], f"Functional group '{name}' must be a mapping"
        packages = group_data.get("packages", [])
        if not isinstance(packages, list):
            return [], f"Functional group '{name}'.packages must be a list"
        if packages:
            groups.append(name)

    return groups, ""


def _catalog_mode_groups(host, arch: str):
    """Resolve compute layer names using the source catalog rules."""
    try:
        catalog_path = read_remote_env(host, ENV_CATALOG_FILE_PATH)
    except ValueError as exc:
        return [], str(exc)

    content, error = _read_remote_text(host, catalog_path, "Catalog JSON")
    if error:
        return [], error

    try:
        raw_catalog = json.loads(content)
    except (json.JSONDecodeError, ValueError) as exc:
        return [], f"Failed to parse catalog JSON: {exc}"

    if not isinstance(raw_catalog, dict):
        return [], "Catalog JSON root must be a mapping"
    catalog = raw_catalog.get("catalog")
    if not isinstance(catalog, dict):
        return [], "Catalog JSON is missing the 'catalog' mapping"
    layers = catalog.get("functionallayer")
    if not isinstance(layers, list):
        return [], "Catalog functionallayer must be a list"

    groups = []
    suffix = f"_{arch}"
    for layer in layers:
        if not isinstance(layer, dict):
            return [], "Catalog functionallayer entries must be mappings"
        name = layer.get("name", "")
        if not isinstance(name, str):
            return [], "Catalog functional layer names must be strings"
        if name.endswith(suffix) and not name.startswith("baseos"):
            if name not in groups:
                groups.append(name)

    return groups, ""


def _configured_functional_groups_result(
    host, arch: str = None
) -> Dict[str, Any]:
    """Resolve expected build groups independently from build_status.yml."""
    if arch is not None and arch not in ("x86_64", "aarch64"):
        return {
            "success": False,
            "groups": [],
            "skipped": False,
            "error": f"Unsupported architecture '{arch}'",
        }

    try:
        config_path = _get_remote_ibm_config_path(host)
    except ValueError as exc:
        return {
            "success": False,
            "groups": [],
            "skipped": False,
            "error": str(exc),
        }

    content, error = _read_remote_text(
        host, config_path, IBM_CONFIG_FILE,
    )
    if error:
        return {
            "success": False,
            "groups": [],
            "skipped": False,
            "error": error,
        }

    try:
        config = yaml.safe_load(content)
    except yaml.YAMLError as exc:
        return {
            "success": False,
            "groups": [],
            "skipped": False,
            "error": f"Failed to parse {IBM_CONFIG_FILE}: {exc}",
        }
    if not isinstance(config, dict):
        return {
            "success": False,
            "groups": [],
            "skipped": False,
            "error": f"{IBM_CONFIG_FILE} must contain a YAML mapping",
        }

    arm_host = config.get("aarch64_inventory_host_ip", "")
    arm_enabled = isinstance(arm_host, str) and bool(arm_host.strip())
    if arch == "aarch64" and not arm_enabled:
        return {
            "success": True,
            "groups": [],
            "skipped": True,
            "source": config.get("functional_groups_source", "config"),
            "image_build_type": config.get(
                "image_build_type", "image-thrillhouse",
            ),
            "details": (
                "aarch64_inventory_host_ip is not configured — "
                "aarch64 image build is disabled"
            ),
            "error": None,
        }

    source = config.get("functional_groups_source", "config")
    if source not in ("config", "catalog"):
        return {
            "success": False,
            "groups": [],
            "skipped": False,
            "error": f"Invalid functional_groups_source '{source}'",
        }

    build_type = config.get("image_build_type", "image-thrillhouse")
    if build_type not in ("image-builder", "image-thrillhouse"):
        return {
            "success": False,
            "groups": [],
            "skipped": False,
            "error": f"Invalid image_build_type '{build_type}'",
        }

    input_dir = config_path.rsplit("/", 1)[0]
    arches = [arch] if arch else ["x86_64"]
    if arch is None and arm_enabled:
        arches.append("aarch64")

    groups = []
    for requested_arch in arches:
        if source == "config":
            resolved, error = _config_mode_groups(
                host, input_dir, requested_arch,
            )
        else:
            resolved, error = _catalog_mode_groups(host, requested_arch)
        if error:
            return {
                "success": False,
                "groups": [],
                "skipped": False,
                "error": error,
            }
        groups.extend(resolved)

    return {
        "success": True,
        "groups": groups,
        "skipped": False,
        "source": source,
        "image_build_type": build_type,
        "details": (
            f"Resolved {len(groups)} functional group(s) from {source} input"
        ),
        "error": None,
    }


def get_configured_functional_groups(
    host, arch: str = None
) -> List[str]:
    """Get expected functional groups from target-host build input.

    Config mode mirrors package_groups.yml selection. Catalog mode mirrors
    functional-layer selection. It never derives expectations from build
    output, allowing callers to detect groups omitted from build_status.yml.

    Args:
        host: testinfra host object
        arch: Filter by architecture suffix (x86_64 or aarch64)

    Returns:
        List of functional group name strings.
    """
    result = _configured_functional_groups_result(host, arch=arch)
    return result["groups"] if result["success"] else []


def _get_s3_provider(host) -> str:
    """Get S3 provider from image_build_config.yml on target.

    Returns 'minio' or 'powerscale' or empty string.
    """
    cfg = _load_remote_ibm_config(host)
    s3_cfg = cfg.get("s3_configurations", {})
    return s3_cfg.get("provider", "minio").lower()
