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
General settings and constants for Ansible local_repo module utilities.
"""

import os

from ansible.module_utils.local_repo.repo_paths import (
    OMNIA_BASE_DIR,
    PROJECT_DEFAULT_DIR,
    REPO_MANAGER_LOG_DIR,
)

# ----------------------------
# Parallel Tasks Defaults
# ----------------------------
DEFAULT_NTHREADS = 4
DEFAULT_TIMEOUT = 60
LOG_DIR_DEFAULT = "/tmp/thread_logs"
DEFAULT_LOG_FILE = "/tmp/task_results_table.log"
DEFAULT_SLOG_FILE = "/tmp/stask_results_table.log"
CSV_FILE_PATH_DEFAULT = [
    "/tmp/x86_64/status_results_table.csv",
    "/tmp/aarch64/status_results_table.csv"
]
DEFAULT_REPO_STORE_PATH = OMNIA_BASE_DIR
USER_JSON_FILE_DEFAULT = ""
DEFAULT_STATUS_FILENAME = "status.csv"
STATUS_CSV_HEADER = 'name,type,repo_name,status\n'
SOFTWARE_CSV_HEADER = "name,status"

# ----------------------------
# Software tasklist Defaults
# ----------------------------
LOCAL_REPO_CONFIG_PATH_DEFAULT = os.path.join(PROJECT_DEFAULT_DIR, "repo_manager_config.yml")
SOFTWARE_CONFIG_PATH_DEFAULT = os.path.join(PROJECT_DEFAULT_DIR, "software_config.json")
SOFTWARE_CSV_FILENAME = "software.csv"
FRESH_INSTALLATION_STATUS = True

# ----------------------------
# Software Utilities Defaults
# ----------------------------
PACKAGE_TYPES = ['rpm', 'deb', 'tarball', 'image', 'manifest', 'git',
                 'pip_module', 'deb', 'shell', 'ansible_galaxy_collection', 'iso', 'rpm_list', 'rpm_file', 'rpm_repo']
CSV_COLUMNS = {"column1": "name", "column2": "status"}
SOFTWARE_CONFIG_SUBDIR = "config"
RPM_LABEL_TEMPLATE = "RPMs for {key}"
RHEL_OS_URL = "rhel_os_url"
SOFTWARES_KEY = "softwares"
USER_REPO_URL = "user_repo_url"
ARCH_SUFFIXES = {"x86_64", "aarch64"}

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
DEFAULT_CACHING = True
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
CLEANUP_FILE_TYPES = ["iso", "manifest", "pip_module", "tarball", "git", "ansible_galaxy_collection"]

# ----------------------------
# Timeouts and Polling
# ----------------------------
TAR_TIMEOUT_MIN = 45    # minutes
FILE_TIMEOUT_MIN = 1    # minutes
ISO_TIMEOUT_MIN = 45    # minutes
TASK_POLL_INTERVAL = 10  # seconds
FILE_URI = "/pulp/api/v3/content/file/files/"

# ----------------------------
# Pulp Concurrency Settings
# ----------------------------
PULP_CONCURRENCY = 1  # Default: 1 (most reliable for NFS)

# ----------------------------
# Cleanup Configuration
# ----------------------------
CLEANUP_BASE_PATH_DEFAULT = REPO_MANAGER_LOG_DIR
CLEANUP_STATUS_FILE_PATH_DEFAULT = os.path.join(REPO_MANAGER_LOG_DIR, "cleanup_status.csv")
CLEANUP_LOG_PATH_DEFAULT = os.path.join(REPO_MANAGER_LOG_DIR, "cleanup.log")

CLEANUP_DELETE_REMOTE_DEFAULT = True
CLEANUP_DELETE_DISTRIBUTION_DEFAULT = True
CLEANUP_CLEANUP_ORPHANS_AFTER_DEFAULT = True
CLEANUP_LIST_ONLY_DEFAULT = False
CLEANUP_FORCE_DEFAULT = False

CLEANUP_STATUS_SUCCESS = "Success"
CLEANUP_STATUS_FAILED = "Failed"
CLEANUP_STATUS_IN_PROGRESS = "In Progress"

CLEANUP_STATUS_FILENAME = "cleanup_status.csv"
CLEANUP_STATUS_CSV_HEADER = "artifact_name,artifact_type,status,message,timestamp\n"
CLEANUP_LOG_FILE_PATH = os.path.join(REPO_MANAGER_LOG_DIR, "cleanup.log")

# ----------------------------
# Additional Repos Aggregation Settings
# ----------------------------
ADDITIONAL_REPOS_KEY = "additional_repos"
AGGREGATED_REPO_SUFFIX = "repo_manager-additional"
AGGREGATED_BASE_PATH_TEMPLATE = "offline_repo/cluster/{arch}/{os_type}/{os_version}/rpms/{repo_name}"
STANDARD_LOG_FILE_PATH = os.path.join(REPO_MANAGER_LOG_DIR, "standard.log")

# ----------------------------
# Certificate Keys
# ----------------------------
CERT_KEYS = ["sslcacert", "sslclientkey", "sslclientcert"]

__all__ = [
    "DEFAULT_NTHREADS",
    "DEFAULT_TIMEOUT",
    "LOG_DIR_DEFAULT",
    "DEFAULT_LOG_FILE",
    "DEFAULT_SLOG_FILE",
    "CSV_FILE_PATH_DEFAULT",
    "DEFAULT_REPO_STORE_PATH",
    "USER_JSON_FILE_DEFAULT",
    "DEFAULT_STATUS_FILENAME",
    "STATUS_CSV_HEADER",
    "SOFTWARE_CSV_HEADER",
    "LOCAL_REPO_CONFIG_PATH_DEFAULT",
    "SOFTWARE_CONFIG_PATH_DEFAULT",
    "SOFTWARE_CSV_FILENAME",
    "FRESH_INSTALLATION_STATUS",
    "PACKAGE_TYPES",
    "CSV_COLUMNS",
    "SOFTWARE_CONFIG_SUBDIR",
    "RPM_LABEL_TEMPLATE",
    "RHEL_OS_URL",
    "SOFTWARES_KEY",
    "USER_REPO_URL",
    "ARCH_SUFFIXES",
    "OS_TARGET_PYTHON",
    "ARCH_PIP_PLATFORMS",
    "REPO_NAME_FORMAT",
    "REPO_NAME_PREFIX_FORMAT",
    "DEFAULT_POLICY",
    "DEFAULT_CACHING",
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
    "ADDITIONAL_REPOS_KEY",
    "AGGREGATED_REPO_SUFFIX",
    "AGGREGATED_BASE_PATH_TEMPLATE",
    "STANDARD_LOG_FILE_PATH",
    "CERT_KEYS",
]
