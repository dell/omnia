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
# pylint: disable=duplicate-code,import-error,line-too-long
# pylint: disable=no-name-in-module,unused-import

"""
Compatibility re-export of local_repo configuration.

Concrete definitions have been split into:
  - repo_paths.py   : directory and file path constants
  - repo_settings.py: general settings and tunables
  - pulp_commands.py: Pulp/CLI command templates
"""

from ansible.module_utils.repo_manager.repo_paths import (
    REPO_MANAGER_BASE_DIR,
    OMNIA_DATA_PATH,
    OMNIA_BASE_DIR,
    REPO_MANAGER_RUNTIME_DIR,
    PROJECT_DEFAULT_DIR,
    REPO_MANAGER_LOG_DIR,
    REPO_MANAGER_OFFLINE_REPO_DIR,
    REPO_MANAGER_DATA_DIR,
    CLI_FILE_PATH,
    PULP_SSL_CA_CERT,
    OMNIA_CREDENTIALS_YAML_PATH,
    OMNIA_CREDENTIALS_VAULT_PATH,
    metadata_rerun_file_path,
)
from ansible.module_utils.repo_manager.repo_settings import (
    DEFAULT_NTHREADS,
    DEFAULT_TIMEOUT,
    DNF_MAX_CONCURRENT_COMMANDS,
    LOG_DIR_DEFAULT,
    DEFAULT_LOG_FILE,
    DEFAULT_SLOG_FILE,
    CSV_FILE_PATH_DEFAULT,
    DEFAULT_REPO_STORE_PATH,
    DEFAULT_STATUS_FILENAME,
    STATUS_CSV_HEADER,
    SOFTWARE_CSV_HEADER,
    REPO_MANAGER_CONFIG_PATH_DEFAULT,
    SOFTWARE_CSV_FILENAME,
    SOFTWARES_KEY,
    RPM_LABEL_TEMPLATE,
    DEFAULT_OS_TYPE,
    ARCH_SUFFIXES,
    SUPPORTED_OS_TYPES,
    PLATFORM_VERSION_ORDER,
    SUBSCRIPTION_REPOSITORIES,
    OS_TARGET_PYTHON,
    ARCH_PIP_PLATFORMS,
    REPO_NAME_FORMAT,
    REPO_NAME_PREFIX_FORMAT,
    DEFAULT_POLICY,
    DEFAULT_CACHING_POLICY,
    POLICY_CACHING_MAP,
    CLEANUP_FILE_TYPES,
    TAR_TIMEOUT_MIN,
    FILE_TIMEOUT_MIN,
    ISO_TIMEOUT_MIN,
    TASK_POLL_INTERVAL,
    FILE_URI,
    CLEANUP_BASE_PATH_DEFAULT,
    PULP_CONTENT_ROUTE,
    PULP_DISTRIBUTION_ROOT,
    PULP_DISTRIBUTION_ROOT_PARTS,
    AGGREGATED_REPO_SUFFIX,
    AGGREGATED_BASE_PATH_TEMPLATE,
    STANDARD_LOG_FILE_PATH,
    CERT_KEYS,
    MIRROR_STATUS_DIR,
    MIRROR_INDEX_FILENAME,
    CATALOG_STATUS_SUFFIX,
    PACKAGE_STATUS_CSV_HEADER,
    GROUP_STATUS_CSV_HEADER,
    RPM_SYNC_STUCK_TIMEOUT,
    RPM_PROGRESS_CHECK_INTERVAL,
    RPM_CLEANUP_ON_TIMEOUT,
    RPM_CLI_QUERY_TIMEOUT,
    RPM_CLI_QUERY_RETRIES,
    RPM_CLI_QUERY_RETRY_DELAY,
    RPM_API_UNAVAILABLE_TIMEOUT,
    iterate_all_repos,
    get_repos_section,
    collect_all_repo_names,
)
from ansible.module_utils.repo_manager.pulp_commands import (
    pulp_file_commands,
    pulp_python_commands,
    pulp_container_commands,
    pulp_rpm_commands,
    DNF_COMMANDS,
    DNF_INFO_COMMANDS,
)

__all__ = (
    [
        "REPO_MANAGER_BASE_DIR",
        "OMNIA_DATA_PATH",
        "OMNIA_BASE_DIR",
        "REPO_MANAGER_RUNTIME_DIR",
        "PROJECT_DEFAULT_DIR",
        "REPO_MANAGER_LOG_DIR",
        "REPO_MANAGER_OFFLINE_REPO_DIR",
        "REPO_MANAGER_DATA_DIR",
        "CLI_FILE_PATH",
        "PULP_SSL_CA_CERT",
        "OMNIA_CREDENTIALS_YAML_PATH",
        "OMNIA_CREDENTIALS_VAULT_PATH",
        "metadata_rerun_file_path",
    ]
    + [
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
        "RPM_CLI_QUERY_TIMEOUT",
        "RPM_CLI_QUERY_RETRIES",
        "RPM_CLI_QUERY_RETRY_DELAY",
        "RPM_API_UNAVAILABLE_TIMEOUT",
        iterate_all_repos,
        get_repos_section,
        collect_all_repo_names,
    ]
    + [
        "pulp_file_commands",
        "pulp_python_commands",
        "pulp_container_commands",
        "pulp_rpm_commands",
        "DNF_COMMANDS",
        "DNF_INFO_COMMANDS",
    ]
)
