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

from datetime import datetime
import os

input_validator_log = '/opt/omnia/log/core/playbooks/input_validator/'

module_log_dir = {
    "input_validator_log": input_validator_log + "/_"+ datetime.now().strftime('_%d-%m-%Y.log')
}

# dict to hold the file names. If any file's name changes just change it here.
files = {
    "k8s_access_config": "k8s_access_config.yml",
    "local_repo_config": "local_repo_config.yml",
    "login_node_security_config": "login_node_security_config.yml",
    "network_spec": "network_spec.yml",
    "omnia_config": "omnia_config.yml",
    "passwordless_ssh_config": "passwordless_ssh_config.yml",
    "provision_config_credentials": "provision_config_credentials.yml",
    "provision_config": "provision_config.yml",
    "roce_plugin_config": "roce_plugin_config.yml",
    "security_config": "security_config.yml",
    "server_spec": "server_spec.yml",
    "software_config": "software_config.json",
    "storage_config": "storage_config.yml",
    "telemetry_config": "telemetry_config.yml",
    "site_config": "site_config.yml",
    "roles_config": "roles_config.yml",
    "high_availability_config": "high_availability_config.yml"
}

# Tags and the files that will be run based off of it
input_file_inventory = {
    "scheduler": [files["omnia_config"], files["software_config"]],
    "provision": [
        files["provision_config_credentials"],
        files["provision_config"],
        files["network_spec"],
        files["server_spec"],
        files["software_config"],
        files["roles_config"]
    ],
    "security": [
        files["security_config"],
        files["login_node_security_config"],
        files["passwordless_ssh_config"],
        files["software_config"]
    ],
    "monitoring": [files["telemetry_config"]],
    "local_repo": [files["local_repo_config"], files["software_config"]],
    "k8s": [files["k8s_access_config"]],
    "roce": [files["roce_plugin_config"]],
    "storage": [files["storage_config"]],
    "proxy": [files["site_config"]],
    "high_availability": [files["high_availability_config"]],
    "all": [
        files["passwordless_ssh_config"],
        files["local_repo_config"],
        files["network_spec"],
        files["server_spec"],
        files["omnia_config"],
        files["provision_config_credentials"],
        files["security_config"],
        files["login_node_security_config"],
        files["telemetry_config"],
        files["provision_config"],
        files["roce_plugin_config"],
        files["k8s_access_config"],
        files["software_config"],
        files["storage_config"],
        # files["site_config"],
        files["roles_config"],
        files["high_availability_config"]
    ],
}

# All of the passwords fields
passwords_set = {
    "mariadb_password",
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
    "rhel": ["9.4"],
    "rocky": ["9.4"],  
    "ubuntu": ["20.04", "22.04", "24.04"] 
}

# Dict of the file that can be encrypted and it's ansible vault key
def get_vault_password(yaml_file):
    vault_passwords = {
        "provision_config_credentials.yml": ".provision_credential_vault_key",
        # "telemetry_config.yml": ".telemetry_vault_key",
        "omnia_config.yml": ".omnia_vault_key",
        "security_config.yml": ".security_vault.key"
    }
    parts = yaml_file.split(os.sep)
    file = parts[-1]
    return vault_passwords[file]