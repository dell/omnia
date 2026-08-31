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
    OMNIA_BASE_DIR,
    REPO_MANAGER_RUNTIME_DIR,
    PROJECT_DEFAULT_DIR,
    REPO_MANAGER_LOG_DIR,
)

logger = logging.getLogger(__name__)

# Configuration file path
CONFIG_FILE_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "vars", "default.yml")
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
    except Exception:
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

def _get_nested_value(dct, keys):
    """Helper to get nested dictionary value."""
    for key in keys:
        if isinstance(dct, dict) and key in dct:
            dct = dct[key]
        else:
            return None
    return dct

# ----------------------------
# Parallel Tasks Defaults
# ----------------------------
DEFAULT_NTHREADS = get_config_value('parallel_config.default_nthreads', 1, 'REPO_MANAGER_NTHREADS')
DEFAULT_TIMEOUT = get_config_value('parallel_config.default_timeout_seconds', 60, 'REPO_MANAGER_TIMEOUT')
DNF_MAX_CONCURRENT_COMMANDS = get_config_value(
    'dnf_config.max_concurrent_commands', 1,
    'REPO_MANAGER_DNF_MAX_CONCURRENT_COMMANDS'
)
# nosec B108 - These are default paths, actual paths are configurable via parameters
LOG_DIR_DEFAULT = os.path.join(REPO_MANAGER_LOG_DIR, "thread_logs")  # nosec B108
DEFAULT_LOG_FILE = os.path.join(REPO_MANAGER_LOG_DIR, "task_results_table.log")  # nosec B108
# setup_standard_logger expects a directory and creates standard.log inside it.
DEFAULT_SLOG_FILE = REPO_MANAGER_LOG_DIR
CSV_FILE_PATH_DEFAULT = [
    os.path.join(REPO_MANAGER_LOG_DIR, "x86_64/status_results_table.csv"),  # nosec B108
    os.path.join(REPO_MANAGER_LOG_DIR, "aarch64/status_results_table.csv")  # nosec B108
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
FRESH_INSTALLATION_STATUS = True

# ----------------------------
# Software Utilities Defaults
# ----------------------------
PACKAGE_TYPES = ['rpm', 'deb', 'tarball', 'image', 'manifest', 'git',
                 'pip_module', 'deb', 'shell', 'ansible_galaxy_collection', 'iso', 'rpm_list', 'rpm_file', 'rpm_repo']
CSV_COLUMNS = {"column1": "name", "column2": "status"}
SOFTWARES_KEY = "softwares"
RPM_LABEL_TEMPLATE = "RPMs for {key}"
# Keep architecture traversal deterministic.  Several catalog operations use
# first-wins deduplication, so a set here can change ownership between runs.
ARCH_SUFFIXES = ("x86_64", "aarch64")

# Target OS -> Python version mapping for pip cross-version downloads.
OS_TARGET_PYTHON = {
    "rhel": {"10": "3.12"},
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
# Pulp Concurrency Settings
# ----------------------------
PULP_CONCURRENCY = get_config_value('pulp_config.concurrency', 1, 'REPO_MANAGER_PULP_CONCURRENCY')

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

if RPM_THREAD_POOL_SIZE < MIN_THREAD_POOL_SIZE:
    RPM_THREAD_POOL_SIZE = MIN_THREAD_POOL_SIZE

RPM_PULP_TIMEOUT = get_config_value('rpm_repo_config.pulp_timeout', 86400, 'REPO_MANAGER_PULP_TIMEOUT')
RPM_CONTINUE_ON_FAILURE = get_config_value('rpm_repo_config.continue_on_failure', True, 'REPO_MANAGER_CONTINUE_ON_FAILURE')
RPM_FILE_LOCK_TIMEOUT = get_config_value('rpm_repo_config.file_lock_timeout', 60, 'REPO_MANAGER_FILE_LOCK_TIMEOUT')
RPM_SYNC_STUCK_TIMEOUT = get_config_value('rpm_repo_config.sync_stuck_timeout', 600, 'REPO_MANAGER_SYNC_STUCK_TIMEOUT')
RPM_PROGRESS_CHECK_INTERVAL = get_config_value('rpm_repo_config.progress_check_interval', 30, 'REPO_MANAGER_PROGRESS_CHECK_INTERVAL')
RPM_CLEANUP_ON_TIMEOUT = get_config_value('rpm_repo_config.cleanup_on_timeout', True, 'REPO_MANAGER_CLEANUP_ON_TIMEOUT')
RPM_CLEANUP_ORPHANS_ONLY = get_config_value('rpm_repo_config.cleanup_orphans_only', False, 'REPO_MANAGER_CLEANUP_ORPHANS_ONLY')

# ----------------------------
# Cleanup Configuration
# ----------------------------
CLEANUP_BASE_PATH_DEFAULT = REPO_MANAGER_LOG_DIR
CLEANUP_STATUS_FILE_PATH_DEFAULT = os.path.join(REPO_MANAGER_LOG_DIR, "cleanup_status.csv")
CLEANUP_LOG_PATH_DEFAULT = os.path.join(REPO_MANAGER_LOG_DIR, "cleanup.log")

CLEANUP_DELETE_REMOTE_DEFAULT = get_config_value('cleanup_config.delete_remote', True, 'REPO_MANAGER_CLEANUP_DELETE_REMOTE')
CLEANUP_DELETE_DISTRIBUTION_DEFAULT = get_config_value('cleanup_config.delete_distribution', True, 'REPO_MANAGER_CLEANUP_DELETE_DISTRIBUTION')
CLEANUP_CLEANUP_ORPHANS_AFTER_DEFAULT = get_config_value('cleanup_config.cleanup_orphans', True, 'REPO_MANAGER_CLEANUP_ORPHANS')
CLEANUP_LIST_ONLY_DEFAULT = get_config_value('cleanup_config.list_only', False, 'REPO_MANAGER_CLEANUP_LIST_ONLY')
CLEANUP_FORCE_DEFAULT = get_config_value('cleanup_config.force', False, 'REPO_MANAGER_CLEANUP_FORCE')

CLEANUP_STATUS_SUCCESS = "Success"
CLEANUP_STATUS_FAILED = "Failed"
CLEANUP_STATUS_IN_PROGRESS = "In Progress"

CLEANUP_STATUS_FILENAME = "cleanup_status.csv"
CLEANUP_STATUS_CSV_HEADER = "artifact_name,artifact_type,status,message,timestamp\n"
CLEANUP_LOG_FILE_PATH = os.path.join(REPO_MANAGER_LOG_DIR, "cleanup.log")

# ----------------------------
# Additional Repos Aggregation Settings
# ----------------------------
AGGREGATED_REPO_SUFFIX = "repo_manager-additional"
AGGREGATED_BASE_PATH_TEMPLATE = "offline_repo/cluster/{arch}/{os_type}/{os_version}/rpms/{repo_name}"
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
    "FRESH_INSTALLATION_STATUS",
    "PACKAGE_TYPES",
    "CSV_COLUMNS",
    "SOFTWARES_KEY",
    "RPM_LABEL_TEMPLATE",
    "ARCH_SUFFIXES",
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
    "PULP_CONCURRENCY",
    "CLEANUP_BASE_PATH_DEFAULT",
    "CLEANUP_STATUS_FILE_PATH_DEFAULT",
    "CLEANUP_LOG_PATH_DEFAULT",
    "CLEANUP_DELETE_REMOTE_DEFAULT",
    "CLEANUP_DELETE_DISTRIBUTION_DEFAULT",
    "CLEANUP_CLEANUP_ORPHANS_AFTER_DEFAULT",
    "CLEANUP_LIST_ONLY_DEFAULT",
    "CLEANUP_FORCE_DEFAULT",
    "CLEANUP_STATUS_SUCCESS",
    "CLEANUP_STATUS_FAILED",
    "CLEANUP_STATUS_IN_PROGRESS",
    "CLEANUP_STATUS_FILENAME",
    "CLEANUP_STATUS_CSV_HEADER",
    "CLEANUP_LOG_FILE_PATH",
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
    "RPM_CLEANUP_ORPHANS_ONLY",
    "iterate_all_repos",
    "get_repos_section",
    "collect_all_repo_names",
    "get_caching_policy",
    "get_container_sync_policy",
]
