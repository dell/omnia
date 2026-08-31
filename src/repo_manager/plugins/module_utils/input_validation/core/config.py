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
Core configuration for input validation module.

This module contains all configuration constants, paths, and mappings
used across the input validation framework.
"""
from datetime import datetime
import os

from ansible.module_utils.repo_manager.path_resolver import (
    get_omnia_data_path,
    get_repo_manager_data_path,
)

# =============================================================================
# PATH CONFIGURATION
# =============================================================================

# Compute repo_manager base directory relative to this file
REPO_MANAGER_BASE_DIR = os.environ.get('REPO_MANAGER_BASE_DIR') or os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

# Runtime data is resolved from the same environment contract as Repo Manager.
OMNIA_BASE_DIR = get_omnia_data_path()
REPO_MANAGER_RUNTIME_DIR = get_repo_manager_data_path()

REPO_MANAGER_LOG_DIR = os.path.join(REPO_MANAGER_RUNTIME_DIR, 'log')
REPO_MANAGER_DATA_DIR = os.path.join(REPO_MANAGER_RUNTIME_DIR, '.data')
REPO_MANAGER_INPUT_DIR = os.path.join(REPO_MANAGER_RUNTIME_DIR, 'input')
CATALOG_DIR = os.path.join(OMNIA_BASE_DIR, 'catalog')
CATALOG_FILE_PATH = os.environ.get('CATALOG_FILE_PATH')

# Log paths
INPUT_VALIDATOR_LOG = os.path.join(REPO_MANAGER_LOG_DIR, "repo_manager_input_validator")
INPUT_VALIDATOR_LOG_PATH = REPO_MANAGER_LOG_DIR

module_log_dir = {
    "input_validator_log": INPUT_VALIDATOR_LOG + "/_" + datetime.now().strftime('_%d-%m-%Y.log')
}

# =============================================================================
# SUBSCRIPTION PATHS
# =============================================================================

SYSTEM_ENTITLEMENT_PATH = '/etc/pki/entitlement/*.pem'
# Container-mounted RHEL subscription paths (e.g., podman --secret)
CONTAINER_ENTITLEMENT_PATH = '/run/secrets/etc-pki-entitlement/*.pem'
SYSTEM_REDHAT_REPO = '/etc/yum.repos.d/redhat.repo'
CONTAINER_REDHAT_REPO = '/run/secrets/redhat.repo'
OMNIA_ENTITLEMENT_PATH = os.path.join(
    REPO_MANAGER_RUNTIME_DIR, "rhel_repo_certs", "*.pem"
)
OMNIA_REDHAT_REPO = os.path.join(
    REPO_MANAGER_RUNTIME_DIR, "rhel_repo_certs", "redhat.repo"
)

# =============================================================================
# FILE CONFIGURATION
# =============================================================================

files = {
    "repo_manager_config": "repo_manager_config.yml",
    "repo_manager_endpoint_config": "repo_manager_endpoint_config.yml",
    # Internal schema selector only. The user catalog input path is resolved
    # from CATALOG_FILE_PATH and is not required to have this basename.
    "catalog_config": "catalog_rhel.json",
    "omnia_config": "omnia_config.yml",
    "provision_config": "provision_config.yml",
    "storage_config": "storage_config.yml"
}

extensions = {
    "json": ".json",
    "yml": ".yml"
}

# =============================================================================
# TAG TO FILE MAPPING
# =============================================================================

input_file_inventory = {
    "endpoint": [files["repo_manager_endpoint_config"]],
    "prepare": [files["repo_manager_endpoint_config"]],
    "deploy": [files["repo_manager_endpoint_config"]],
    "precheck": [
        files["repo_manager_config"],
        files["repo_manager_endpoint_config"],
        files["catalog_config"]
    ],
    "local_repo": [
        files["repo_manager_config"],
        files["repo_manager_endpoint_config"],
        files["catalog_config"]
    ],
    "repo_manager": [
        files["repo_manager_config"],
        files["repo_manager_endpoint_config"],
        files["catalog_config"]
    ],
    "all": [
        files["repo_manager_config"],
        files["repo_manager_endpoint_config"],
        files["catalog_config"]
    ],
}

# =============================================================================
# VERSION CONFIGURATION
# =============================================================================

expected_versions = {
    "amdgpu": "6.3.1",
    "cuda": "12.9.1",
    "ofed": "24.10-1.1.4.0",
    "beegfs": "7.4.5",
    "intel_benchmarks": "2024.1.0",
    "ucx": "1.19.0",
    "openmpi": "5.0.8",
    "csi_driver_powerscale": "v2.17.0",
    "rocm": "6.3.1",
    "service_k8s": "1.35.1"
}

os_version_ranges = {
    "rhel": ["10.0", "10.1"],
}

# =============================================================================
# PASSWORD FIELDS
# =============================================================================

passwords_set = {
    "slurm_db_password",
    "directory_manager_password",
    "kerberos_admin_password",
    "openldap_db_password",
    "openldap_config_password",
    "openldap_monitor_password",
    "timescaledb_password",
    "idrac_password",
    "mysqldb_password",
    "mysqldb_root_password",
    "grafana_password",
    "provision_password",
    "postgres_password",
    "bmc_password",
    "switch_snmp3_password",
    "docker_password"
}

# =============================================================================
# PACKAGE TYPE REQUIREMENTS
# =============================================================================

TYPE_REQUIREMENTS = {
    "rpm": ["package", "repo_name"],
    "rpm_list": ["package_list", "repo_name"],
    "rpm_file": ["package", "url"],
    "rpm_repo": ["package", "repo_name"],
    "ansible_galaxy_collection": ["package", "version"],
    "git": ["package", "version", "url"],
    "image": ["package", ["tag", "digest"]],
    "tarball": ["package", "url"],
    "shell": ["package", "url"],
    "iso": ["package", "url"],
    "manifest": ["package", "url"],
    "pip_module": ["package"]
}

# =============================================================================
# FUNCTIONAL GROUP CONFIGURATION
# =============================================================================

FUNCTIONAL_GROUP_LAYER_MAP = {
    "service_kube_control_plane_first_x86_64": "management",
    "service_kube_control_plane_x86_64": "management",
    "service_kube_node_x86_64": "management",
    "login_node_x86_64": "management",
    "login_node_aarch64": "management",
    "login_compiler_node_x86_64": "management",
    "login_compiler_node_aarch64": "management",
    "slurm_control_node_x86_64": "management",
    "slurm_node_x86_64": "compute",
    "slurm_node_aarch64": "compute",
    "os_x86_64": "compute",
    "os_aarch64": "compute"
}

# =============================================================================
# SECURITY CONFIGURATION
# =============================================================================

supported_ldap_connection_type = ["TLS", "SLS"]
supported_telemetry_collection_type = ["victoria", "kafka"]
EMAIL_MAX_LENGTH = 320
EMAIL_SEARCH_KEY = "@"

# =============================================================================
# VAULT PASSWORD MAPPING
# =============================================================================


def get_vault_password(yaml_file):
    """
    Retrieves the vault password file name associated with a given YAML file.

    Args:
        yaml_file (str): The full path to the YAML configuration file.

    Returns:
        str: The name of the vault password file corresponding to the YAML file.

    Raises:
        KeyError: If the YAML file is not found in the predefined mapping.
    """
    vault_passwords = {
        "repo_manager_config_credentials.yml": ".repo_manager_config_credentials_key",
    }
    parts = yaml_file.split(os.sep)
    file = parts[-1]
    return vault_passwords[file]
