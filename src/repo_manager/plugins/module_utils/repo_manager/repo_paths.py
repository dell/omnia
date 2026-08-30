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
Path and directory configuration for Ansible local_repo module utilities.
"""

import os

from ansible.module_utils.repo_manager.path_resolver import (
    get_input_project_dir,
    get_omnia_data_path,
    get_repo_manager_data_path,
)

# Compute repo_manager base directory relative to this file.
# This allows the repo_manager source directory to be copied anywhere.
REPO_MANAGER_BASE_DIR = os.environ.get('REPO_MANAGER_BASE_DIR') or os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', '..'))

# Runtime data is independent from the source checkout. OMNIA_BASE_DIR remains
# exported as a compatibility alias for modules written before OMNIA_DATA_PATH.
OMNIA_DATA_PATH = get_omnia_data_path()
OMNIA_BASE_DIR = OMNIA_DATA_PATH
REPO_MANAGER_RUNTIME_DIR = get_repo_manager_data_path()

PROJECT_DEFAULT_DIR = get_input_project_dir()
REPO_MANAGER_LOG_DIR = os.path.join(REPO_MANAGER_RUNTIME_DIR, 'log')
REPO_MANAGER_OFFLINE_REPO_DIR = os.path.join(
    REPO_MANAGER_RUNTIME_DIR, 'offline_repo'
)
REPO_MANAGER_DATA_DIR = os.path.join(REPO_MANAGER_RUNTIME_DIR, '.data')

CLI_FILE_PATH = "/etc/pulp/cli.toml"
PULP_SSL_CA_CERT = os.path.join(
    REPO_MANAGER_RUNTIME_DIR, "pulp_config", "settings", "certs",
    "pulp_webserver.crt"
)

# Catalog path override (set by Ansible tasks or user environment)
# If not set, will fall back to catalog_config.catalog in repo_manager_config.yml
CATALOG_PATH = os.environ.get('CATALOG_FILE_PATH')

# Credentials paths for parallel tasks
OMNIA_CREDENTIALS_YAML_PATH = os.path.join(PROJECT_DEFAULT_DIR, "repo_manager_config_credentials.yml")
OMNIA_CREDENTIALS_VAULT_PATH = os.path.join(PROJECT_DEFAULT_DIR, ".repo_manager_config_credentials_key")

# Used by process_metadata.py
metadata_rerun_file_path = os.path.join(REPO_MANAGER_OFFLINE_REPO_DIR, ".data", "localrepo_rerun_metadata.yml")

__all__ = [
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
    "CATALOG_PATH",
    "OMNIA_CREDENTIALS_YAML_PATH",
    "OMNIA_CREDENTIALS_VAULT_PATH",
    "metadata_rerun_file_path",
]
