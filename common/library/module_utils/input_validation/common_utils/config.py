# Copyright 2025 Dell Inc. or its subsidiaries. All Rights Reserved.
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
Configuration utilities for Omnia input validation modules.
"""
from datetime import datetime
import os

INPUT_VALIDATOR_LOG = '/opt/omnia/log/core/playbooks/input_validator/'

module_log_dir = {
    "input_validator_log": INPUT_VALIDATOR_LOG + "/_"+ datetime.now().strftime('_%d-%m-%Y.log')
}

# log path for input validator
INPUT_VALIDATOR_LOG_PATH = '/opt/omnia/log/core/playbooks/'

# Subscription checking paths - checked in order of priority
SYSTEM_ENTITLEMENT_PATH = '/etc/pki/entitlement/*.pem'
SYSTEM_REDHAT_REPO = '/etc/yum.repos.d/redhat.repo'

OMNIA_ENTITLEMENT_PATH = '/opt/omnia/rhel_repo_certs/*.pem'
OMNIA_REDHAT_REPO = '/opt/omnia/rhel_repo_certs/redhat.repo'

# dict to hold the file names. If any file's name changes just change it here.
files = {
    "local_repo_config": "local_repo_config.yml",
    "network_spec": "network_spec.yml",
    "omnia_config": "omnia_config.yml",
    "provision_config": "provision_config.yml",
    "security_config": "security_config.yml",
    "software_config": "software_config.json",
    "storage_config": "storage_config.yml",
    "telemetry_config": "telemetry_config.yml",
    "high_availability_config": "high_availability_config.yml"
    # "additional_software": "additional_software.json"
}

# Tags and the files that will be run based off of it
input_file_inventory = {
    "build_image": [files["provision_config"]],
    "scheduler": [
        files["software_config"],

        files["omnia_config"]
        # files["high_availability_config"]
    ],
    "provision": [
        files["provision_config"],
        files["network_spec"],
        files["software_config"],
        # files["high_availability_config"]
    ],
    "security": [
        files["security_config"]
    ],
    "telemetry": [files["telemetry_config"]],
    "local_repo": [files["local_repo_config"], files["software_config"]],
    "slurm": [
        files["omnia_config"],
        files["storage_config"]
        # files["high_availability_config"]
    ],
    "service_k8s": [
        files["omnia_config"],
        files["storage_config"],
        files["high_availability_config"],
    ],
    "storage": [files["storage_config"]],
    "prepare_oim": [
        files["network_spec"],
    ],
    # "high_availability": [files["high_availability_config"]],
    # "additional_software": [files["additional_software"]],
    "all": [
        files["local_repo_config"],
        files["network_spec"],
        files["omnia_config"],
        files["security_config"],
        files["telemetry_config"],
        files["provision_config"],
        files["software_config"],
        files["storage_config"],
        files["high_availability_config"],
    ],
}

expected_versions = {
    "amdgpu": "6.3.1",
    "cuda": "12.9.1",
    "ofed": "24.10-1.1.4.0",
    "beegfs": "7.4.5",
    "intel_benchmarks": "2024.1.0",
    "ucx": "1.19.0",
    "openmpi": "5.0.8",
    "csi_driver_powerscale": "v2.15.0",
    "rocm": "6.3.1",
    "service_k8s": "1.34.1"
}

# All of the passwords fields
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
    "postgresdb_password",
    "bmc_password",
    "switch_snmp3_password",
    "docker_password"
}

extensions = {
    "json": ".json",
    "yml": ".yml"
}

os_version_ranges = {
    "rhel": ["10.0"],
    #"rocky": ["9.4"],
    #"ubuntu": ["20.04", "22.04", "24.04"]
}


#dictionary used for local repo package type mapping
TYPE_REQUIREMENTS = {
    "rpm": ["package", "repo_name"],
    "rpm_list": ["package_list", "repo_name"],
    "ansible_galaxy_collection": ["package", "version"],
    "git": ["package", "version", "url"],
    "image": ["package", ["tag", "digest"]],  # Special: one of tag or digest
    "tarball": ["package", "url"],
    "shell": ["package", "url"],
    "iso": ["package", "url"],
    "manifest": ["package", "url"],
    "pip_module":["package"]
}

supported_telemetry_collection_type = ["victoria","kafka"]

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
    "slurm_node_aarch64": "compute"
}

# used for security_config.yml validation
supported_ldap_connection_type = ["TLS","SLS"]
EMAIL_MAX_LENGTH = 320
EMAIL_SEARCH_KEY = "@"

# Dict of the file that can be encrypted and it's ansible vault key
def get_vault_password(yaml_file):
    """
    Retrieves the vault password file name associated with a given YAML file.

    This function maps a specific YAML file name to its corresponding Ansible Vault
    password file. It is typically used to locate the decryption key required for
    accessing encrypted configuration files.

    Parameters:
        yaml_file (str): The full path to the YAML configuration file.

    Returns:
        str: The name of the vault password file corresponding to the YAML file.

    Raises:
        KeyError: If the YAML file is not found in the predefined mapping.
    """
    vault_passwords = {
        "omnia_config_credentials.yml": ".omnia_config_credentials_key",
    }
    parts = yaml_file.split(os.sep)
    file = parts[-1]
    return vault_passwords[file]
