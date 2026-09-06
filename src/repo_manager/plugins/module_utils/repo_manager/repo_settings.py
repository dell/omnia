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
# pylint: disable=line-too-long

"""
General settings and constants for Ansible repo_manager module utilities.
"""

import os
import logging
import yaml

from ansible.module_utils.repo_manager.repo_paths import (
    REPO_MANAGER_BASE_DIR,
    REPO_MANAGER_RUNTIME_DIR,
    PROJECT_DEFAULT_DIR,
    REPO_MANAGER_LOG_DIR,
)

logger = logging.getLogger(__name__)

# Configuration file path
CONFIG_FILE_PATH = os.path.abspath(
    os.environ.get("REPO_MANAGER_CONFIG_PATH")
    or os.path.join(REPO_MANAGER_BASE_DIR, "vars", "default.yml")
)

def load_config():
    """
    Load configuration from vars/default.yml.

    Returns:
        dict: Configuration dictionary, empty dict if file not found or invalid.
    """
    try:
        if os.path.exists(CONFIG_FILE_PATH):
            with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
    except (OSError, UnicodeError, yaml.YAMLError):
        pass
    return {}

# Load configuration
_config = load_config()

# Helper function to get config value with environment variable fallback
def get_config_value(config_key, default_value, env_var=None):
    """
    Get configuration value from YAML config or environment variable.

    Args:
        config_key (str): Dot-separated key path in config (e.g., 'parallel_config.default_nthreads')
        default_value: Default value if not found in config
        env_var (str): Environment variable name to check as fallback

    Returns:
        Configuration value or default
    """
    # Try environment variable first
    if env_var and env_var in os.environ:
        value = os.environ[env_var]
        # Convert to appropriate type
        if isinstance(default_value, int):
            try:
                return int(value)
            except ValueError:
                pass
        elif isinstance(default_value, bool):
            return value.lower() in ('true', '1', 'yes')
        return value

    # Try YAML config
    keys = config_key.split('.')
    value = _config
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default_value

    return value if value is not None else default_value


def _normalize_relative_config_path(value, config_key):
    """Validate and normalize a slash-delimited relative configuration path."""
    raw_value = str(value).strip()
    if not raw_value or os.path.isabs(raw_value):
        raise ValueError(f"{config_key} must be a non-empty relative path")

    parts = tuple(part for part in raw_value.split('/') if part)
    if not parts or any(part in ('.', '..') for part in parts):
        raise ValueError(f"{config_key} contains an unsafe path segment")
    return '/'.join(parts)


def _normalize_content_route(value):
    """Validate and return the native Pulp content route."""
    relative_route = _normalize_relative_config_path(
        str(value).strip('/'), 'pulp_content_paths.content_route'
    )
    content_route = f"/{relative_route}"
    if content_route != '/pulp/content':
        raise ValueError(
            'pulp_content_paths.content_route must remain /pulp/content'
        )
    return content_route


# ----------------------------
# Parallel Tasks Defaults
# ----------------------------
DEFAULT_NTHREADS = get_config_value('parallel_config.default_nthreads', 1, 'REPO_MANAGER_NTHREADS')
DEFAULT_TIMEOUT = get_config_value('parallel_config.default_timeout_seconds', 60, 'REPO_MANAGER_TIMEOUT')
DNF_MAX_CONCURRENT_COMMANDS = get_config_value(
    'dnf_config.max_concurrent_commands', 1,
    'REPO_MANAGER_DNF_MAX_CONCURRENT_COMMANDS'
)
LOG_DIR_DEFAULT = os.path.join(REPO_MANAGER_LOG_DIR, "thread_logs")
DEFAULT_LOG_FILE = os.path.join(REPO_MANAGER_LOG_DIR, "task_results_table.log")
# setup_standard_logger expects a directory and creates standard.log inside it.
DEFAULT_SLOG_FILE = REPO_MANAGER_LOG_DIR
CSV_FILE_PATH_DEFAULT = [
    os.path.join(REPO_MANAGER_LOG_DIR, "x86_64/status_results_table.csv"),
    os.path.join(REPO_MANAGER_LOG_DIR, "aarch64/status_results_table.csv")
]
DEFAULT_REPO_STORE_PATH = REPO_MANAGER_RUNTIME_DIR
DEFAULT_STATUS_FILENAME = "status.csv"
STATUS_CSV_HEADER = 'name,type,repo_name,status,catalog_name\n'
SOFTWARE_CSV_HEADER = "name,status"

# ----------------------------
# Software tasklist Defaults
# ----------------------------
REPO_MANAGER_CONFIG_PATH_DEFAULT = os.path.join(PROJECT_DEFAULT_DIR, "repo_manager_config.yml")
SOFTWARE_CSV_FILENAME = "groups_status.csv"

# ----------------------------
# Software Utilities Defaults
# ----------------------------
SOFTWARES_KEY = "softwares"
RPM_LABEL_TEMPLATE = "RPMs for {key}"
# Keep architecture traversal deterministic.  Several catalog operations use
# first-wins deduplication, so a set here can change ownership between runs.
DEFAULT_OS_TYPE = str(get_config_value(
    "platform_config.default_os_type", ""
))
ARCH_SUFFIXES = tuple(get_config_value(
    "platform_config.architecture_order", ["x86_64", "aarch64"]
))
PLATFORM_PROFILES = get_config_value("platform_profiles", {})
if not isinstance(PLATFORM_PROFILES, dict):
    raise ValueError("platform_profiles must be a mapping")
SUPPORTED_OS_TYPES = tuple(
    os_type for os_type, profile in PLATFORM_PROFILES.items()
    if isinstance(profile, dict) and bool(profile.get("enabled", False))
)
PLATFORM_VERSION_ORDER = str(get_config_value(
    "platform_config.version_order", "ascending"
)).lower()
if PLATFORM_VERSION_ORDER not in ("ascending", "descending"):
    raise ValueError(
        "platform_config.version_order must be 'ascending' or 'descending'"
    )
SUBSCRIPTION_REPOSITORIES = tuple(get_config_value(
    "platform_profiles.rhel.subscription_repositories",
    ["baseos", "appstream", "codeready-builder"]
))

# Target OS -> Python version mapping for pip cross-version downloads.
OS_TARGET_PYTHON = {
    "rhel": get_config_value(
        "platform_profiles.rhel.target_python_by_os_major", {"10": "3.12"}
    ),
}

# Architecture -> manylinux platform tags for pip --platform flag.
ARCH_PIP_PLATFORMS = {
    "x86_64": [
        "manylinux_2_34_x86_64",
        "manylinux_2_28_x86_64",
        "manylinux_2_17_x86_64",
    ],
    "aarch64": [
        "manylinux_2_34_aarch64",
        "manylinux_2_28_aarch64",
        "manylinux_2_17_aarch64",
    ],
}

# ----------------------------
# Repo Naming Format
# ----------------------------
REPO_NAME_FORMAT = "{arch}_{os_type}_{os_version}_{name}"
REPO_NAME_PREFIX_FORMAT = "{arch}_{os_type}_{os_version}_"

DEFAULT_POLICY = "on_demand"
DEFAULT_CACHING_POLICY = True  # Global caching policy default (True = on_demand, False = immediate)
POLICY_CACHING_MAP = {
    ("always", False): "immediate",
    ("always", True): "on_demand",
    ("partial", False): "streamed",
    ("partial", True): "on_demand",
    ("never", False): "streamed",
    ("never", True): "streamed"
}

# ----------------------------
# Cleanup File Types
# ----------------------------
CLEANUP_FILE_TYPES = [
    "iso",
    "manifest",
    "pip_module",
    "tarball",
    "git",
    "shell",
    "ansible_galaxy_collection",
]

# ----------------------------
# Timeouts and Polling
# ----------------------------
TAR_TIMEOUT_MIN = get_config_value('download_config.tarball_timeout_minutes', 45, 'REPO_MANAGER_TAR_TIMEOUT')
FILE_TIMEOUT_MIN = get_config_value('download_config.file_timeout_minutes', 1, 'REPO_MANAGER_FILE_TIMEOUT')
ISO_TIMEOUT_MIN = get_config_value('download_config.iso_timeout_minutes', 45, 'REPO_MANAGER_ISO_TIMEOUT')
TASK_POLL_INTERVAL = get_config_value('parallel_config.task_poll_interval_seconds', 10, 'REPO_MANAGER_TASK_POLL_INTERVAL')
FILE_URI = "/pulp/api/v3/content/file/files/"

# ----------------------------
# RPM Repository Processing Configuration
# ----------------------------
MAX_THREAD_POOL_SIZE = 10
MIN_THREAD_POOL_SIZE = 1

RPM_THREAD_POOL_SIZE = get_config_value('rpm_repo_config.thread_pool_size', 1, 'REPO_MANAGER_THREAD_POOL_SIZE')

# Enforce safe limits
if RPM_THREAD_POOL_SIZE > MAX_THREAD_POOL_SIZE:
    logger.warning("thread_pool_size=%d exceeds maximum %d. Capping to %d.",
                  RPM_THREAD_POOL_SIZE, MAX_THREAD_POOL_SIZE, MAX_THREAD_POOL_SIZE)
    RPM_THREAD_POOL_SIZE = MAX_THREAD_POOL_SIZE

RPM_THREAD_POOL_SIZE = max(RPM_THREAD_POOL_SIZE, MIN_THREAD_POOL_SIZE)

RPM_CONTINUE_ON_FAILURE = get_config_value('rpm_repo_config.continue_on_failure', True, 'REPO_MANAGER_CONTINUE_ON_FAILURE')
RPM_SYNC_STUCK_TIMEOUT = get_config_value('rpm_repo_config.sync_stuck_timeout', 600, 'REPO_MANAGER_SYNC_STUCK_TIMEOUT')
RPM_PROGRESS_CHECK_INTERVAL = get_config_value('rpm_repo_config.progress_check_interval', 30, 'REPO_MANAGER_PROGRESS_CHECK_INTERVAL')
RPM_CLEANUP_ON_TIMEOUT = get_config_value('rpm_repo_config.cleanup_on_timeout', True, 'REPO_MANAGER_CLEANUP_ON_TIMEOUT')
RPM_CLI_QUERY_TIMEOUT = max(1, get_config_value(
    'rpm_repo_config.cli_query_timeout', 150,
    'REPO_MANAGER_PULP_QUERY_TIMEOUT'
))
RPM_CLI_QUERY_RETRIES = max(1, get_config_value(
    'rpm_repo_config.cli_query_retries', 3,
    'REPO_MANAGER_PULP_QUERY_RETRIES'
))
RPM_CLI_QUERY_RETRY_DELAY = max(0, get_config_value(
    'rpm_repo_config.cli_query_retry_delay', 5,
    'REPO_MANAGER_PULP_QUERY_RETRY_DELAY'
))
RPM_API_UNAVAILABLE_TIMEOUT = max(1, get_config_value(
    'rpm_repo_config.api_unavailable_timeout', 600,
    'REPO_MANAGER_PULP_API_UNAVAILABLE_TIMEOUT'
))

# ----------------------------
# Cleanup Configuration
# ----------------------------
CLEANUP_BASE_PATH_DEFAULT = REPO_MANAGER_LOG_DIR

# ----------------------------
# Additional Repos Aggregation Settings
# ----------------------------
PULP_CONTENT_ROUTE = _normalize_content_route(get_config_value(
    'pulp_content_paths.content_route', '/pulp/content'
))
PULP_DISTRIBUTION_ROOT = _normalize_relative_config_path(
    get_config_value(
        'pulp_content_paths.distribution_root', 'offline_repo/cluster'
    ),
    'pulp_content_paths.distribution_root',
)
PULP_DISTRIBUTION_ROOT_PARTS = tuple(PULP_DISTRIBUTION_ROOT.split('/'))
AGGREGATED_REPO_SUFFIX = "repo_manager-additional"
AGGREGATED_BASE_PATH_TEMPLATE = (
    f"{PULP_DISTRIBUTION_ROOT}/"
    "{arch}/{os_type}/{os_version}/rpms/{repo_name}"
)
STANDARD_LOG_FILE_PATH = os.path.join(REPO_MANAGER_LOG_DIR, "standard.log")

# ----------------------------
# Certificate Keys
# ----------------------------
CERT_KEYS = ["sslcacert", "sslclientkey", "sslclientcert"]

# ----------------------------
# Multi-Catalog Settings
# ----------------------------
MIRROR_STATUS_DIR = "mirror_status"
MIRROR_INDEX_FILENAME = "pulp_mirror_index.json"
CATALOG_STATUS_SUFFIX = "_catalog_status.json"
PACKAGE_STATUS_CSV_HEADER = 'name,type,repo_name,status,catalog_name\n'
GROUP_STATUS_CSV_HEADER = 'name,status\n'


# ----------------------------
# Repository Structure Utilities
# ----------------------------

def iterate_all_repos(repos_section):
    """Iterate all repos from flat and nested structures.

    Yields (repo_name, repo_config) for:
    - Flat repos: baseos, epel, cuda, etc.
    - Nested repos: user_repos.slurm_custom, additional_repos.grafana, etc.

    Args:
        repos_section (dict): Repository section from config

    Yields:
        tuple: (repo_name, repo_config) for each repository
    """
    if not repos_section:
        return
    for repo_name, repo_config in repos_section.items():
        if repo_name in ("additional_repos", "user_repos"):
            nested = repo_config if isinstance(repo_config, dict) else {}
            for nested_name, nested_config in nested.items():
                yield nested_name, nested_config
        else:
            # Only yield if repo_config is a dictionary (skip string values)
            if isinstance(repo_config, dict):
                yield repo_name, repo_config


def get_repos_section(config_data, cluster_os_version, arch):
    """Get the architecture-specific repos section from config.

    Args:
        config_data (dict): Full configuration data
        cluster_os_version (str): OS version (e.g., "10.0")
        arch (str): Architecture (e.g., "x86_64")

    Returns:
        dict: Repository section for the specified architecture
    """
    return config_data.get("repositories", {}).get(cluster_os_version, {}).get(arch, {})


def collect_all_repo_names(repos_section):
    """Collect all repo names from flat and nested structures.

    Args:
        repos_section (dict): Repository section from config

    Returns:
        list: List of repository names
    """
    return [name for name, _ in iterate_all_repos(repos_section)]


def get_caching_policy(config_data, repo_config=None):
    """Resolve caching policy with per-repo override.

    Priority: per-repo caching → global caching_policy → DEFAULT_CACHING_POLICY

    Args:
        config_data (dict): Parsed repo_manager_config.yml
        repo_config (dict, optional): Individual repository configuration

    Returns:
        bool: Caching policy (True = on_demand, False = immediate)
    """
    # Per-repo override takes highest priority
    if repo_config and isinstance(repo_config, dict):
        per_repo = repo_config.get("caching")
        if per_repo is not None:
            return per_repo

    # Global caching_policy from config
    global_policy = config_data.get("caching_policy")
    if global_policy is not None:
        return global_policy

    # Default fallback
    return DEFAULT_CACHING_POLICY


def get_container_sync_policy(config_data):
    """
    Get container image sync policy from vars/default.yml.

    Container images use a unified policy that is independent of
    RPM repository settings.

    Args:
        config_data (dict): Parsed vars/default.yml

    Returns:
        str: 'immediate', 'on_demand', or 'streamed'
    """
    container_policy = config_data.get("container_sync_policy")
    if container_policy and str(container_policy).lower() in (
        "immediate", "on_demand", "streamed"
    ):
        return str(container_policy).lower()
    return "immediate"  # Default for airgap compatibility


__all__ = [
    "DEFAULT_NTHREADS",
    "DEFAULT_TIMEOUT",
    "DNF_MAX_CONCURRENT_COMMANDS",
    "LOG_DIR_DEFAULT",
    "DEFAULT_LOG_FILE",
    "DEFAULT_SLOG_FILE",
    "CSV_FILE_PATH_DEFAULT",
    "DEFAULT_REPO_STORE_PATH",
    "DEFAULT_STATUS_FILENAME",
    "STATUS_CSV_HEADER",
    "SOFTWARE_CSV_HEADER",
    "REPO_MANAGER_CONFIG_PATH_DEFAULT",
    "SOFTWARE_CSV_FILENAME",
    "SOFTWARES_KEY",
    "RPM_LABEL_TEMPLATE",
    "DEFAULT_OS_TYPE",
    "ARCH_SUFFIXES",
    "SUPPORTED_OS_TYPES",
    "PLATFORM_VERSION_ORDER",
    "SUBSCRIPTION_REPOSITORIES",
    "OS_TARGET_PYTHON",
    "ARCH_PIP_PLATFORMS",
    "REPO_NAME_FORMAT",
    "REPO_NAME_PREFIX_FORMAT",
    "DEFAULT_POLICY",
    "DEFAULT_CACHING_POLICY",
    "POLICY_CACHING_MAP",
    "CLEANUP_FILE_TYPES",
    "TAR_TIMEOUT_MIN",
    "FILE_TIMEOUT_MIN",
    "ISO_TIMEOUT_MIN",
    "TASK_POLL_INTERVAL",
    "FILE_URI",
    "CLEANUP_BASE_PATH_DEFAULT",
    "PULP_CONTENT_ROUTE",
    "PULP_DISTRIBUTION_ROOT",
    "PULP_DISTRIBUTION_ROOT_PARTS",
    "AGGREGATED_REPO_SUFFIX",
    "AGGREGATED_BASE_PATH_TEMPLATE",
    "STANDARD_LOG_FILE_PATH",
    "CERT_KEYS",
    "MIRROR_STATUS_DIR",
    "MIRROR_INDEX_FILENAME",
    "CATALOG_STATUS_SUFFIX",
    "PACKAGE_STATUS_CSV_HEADER",
    "GROUP_STATUS_CSV_HEADER",
    "RPM_SYNC_STUCK_TIMEOUT",
    "RPM_PROGRESS_CHECK_INTERVAL",
    "RPM_CLEANUP_ON_TIMEOUT",
    "iterate_all_repos",
    "get_repos_section",
    "collect_all_repo_names",
    "get_caching_policy",
    "get_container_sync_policy",
]
