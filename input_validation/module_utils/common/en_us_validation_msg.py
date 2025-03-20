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

### All of these messages are used in logical_validation.py

# roles_config.yml
max_number_of_roles_msg = "A max of 100 roles can be supported."
min_number_of_groups_msg = "At least 1 group is required."
min_number_of_roles_msg = "At least 1 role is required."
max_number_of_roles_per_group_msg = "Groups can support a maximum of 5 roles."
resource_mgr_id_msg = "The resource_mgr_id needs to be set if and only if the group belongs to kube_node or slurm_node roles."
grp_exist_msg = "A valid group must be provided."
invalid_switch_ip_msg = "Please provide a valid switch IPv4 address (example: 10.5.0.1)."
grp_role_msg = "Please associate this group with a role."
parent_service_node_msg = "Group is associated with login, compiler, service, kube_control_plane, slurm_control_plane role(s)."
parent_service_role_dne_msg = "A service role must be present when the parent is provided."
parent_service_role_msg = "A service role does not exist, the parent should be empty for any group associated with worker or default roles."
bmc_static_range_invalid_msg = "Static range should be in the following format: IPv4Start-IPv4End (example: 10.5.0.1-10.5.0.200)."
overlapping_static_range = "bmc_detail's static_range is overlapping with other static ranges."
duplicate_switch_ip_port_msg = "Please remove duplicate ports."
switch_details_incomplete_msg = "If providing switch details, please provide both the IP and Ports fields."
switch_details_no_bmc_details_msg = "If switch details are provided then bmc_detail's static_range must also be provided."
invalid_group_name_msg = "Groups must be defined in the form of grp<n> where n is 0-99."
invalid_location_id_msg = "location_id must follow the format SU-<n>.RACK-<n> where n is 0-99."
no_groups_msg = "Outer Group object was probably not defined."
no_roles_msg = "Outer Role object was probably not defined."
invalid_switch_ports_msg = "Please provide any port ranges as start-end (example: 0-15,4:4,51-53)."

# provision_config.yml
default_lease_time_fail_msg = "Please provide a valid default_lease_time."
timezone_fail_msg = "Unsupported Timezone. Please check the timezone.txt file for a list of valid timezones."
enable_switch_based_fail_msg = "enable_switch_based must be set to either true or false."
language_fail_msg = "Only en-US language supported"
nodename_chars_fail_msg = "node_name is empty or invalid in provision_config.yml. node_name should not contain _ or . or space or node- as it might result in issues with provisioning/authentication tools like FreeIPA."
public_nic_fail_msg = "public_nic is empty. Please provide a public_nic value."
pxe_mapping_file_path_fail_msg = "File path is invalid. Please ensure that the file exists at the specified pxe_mapping_file_path."
pxe_mapping_file_ext_fail_msg = "File path is invalid. Please ensure that the file ends with .csv extension"
ntp_support_empty_msg = "The ntp_support must have a boolean value set to either true or false."

# local_repo.yml
repo_store_path_msg = "Please provide a valid repo_store_path value."
omnia_repo_url_msg = "Repo urls are empty. Please provide a url and corresponding key."
rhel_os_url_msg = "is empty. Please provide a rhel_os_url value."
ubuntu_os_url_msg = "ubuntu_os_url is empty. Please provide a ubuntu_os_url value."

#omnia_config.yml
invalid_password_msg = "Provided password is invalid. Password must meet the specified requirements: should not be empty, must have a length of at least 8 characters, and should not contain the following characters: '-', '\', "'", or '"'"
k8s_cni_fail_msg = "k8s_cni is empty or invalid. k8s_cni must be set to either calico or flannel. "
ansible_config_file_path_fail_msg = "Please provide a valid ansible_config_file_path value."
pod_external_ip_range_fail_msg = "pod_external_ip_range value is either empty or invalid. Please provide one of the following acceptable formats: '10.11.0.100-10.11.0.150' (range between start and end IP addresses) or '10.11.0.0/16' (CIDR notation)."
slurm_installation_type_fail_msg = "slurm_installation_type is empty or invalid. slurm_installation_type_fail_msg must either be set to nfs_share or configless."
restart_slurm_services_fail_msg = "restart_slurm_services is empty or invalid. restart_slurm_services must be set to either true or false."
k8s_service_addresses_fail_msg = "k8s_service_addresses are empty. Please provide k8s_service_addresses value."
k8s_pod_network_cidr_fail_msg = "k8s_pod_network_cidr is empty. Please provide a k8s_pod_network_cidr value."
intel_gaudi_fail_msg = "should not be false as intel_gaudi exists in software_config.json"
csi_driver_secret_fail_msg = "CSI Powerscale driver secret file path should not be empty."
csi_driver_values_fail_msg = "CSI Powerscale driver values file path should not be empty."

# provision_config_credentials.yml
provision_password_fail_msg = "Incorrect provision_password format. Password must meet the specified requirements: should not be empty, must have a length of at least 8 characters, and should not contain the following characters: '-', '\', "'", or '"'"
postgresdb_password_fail_msg = "Failed. postgresdb_password should contain only alphanumeric characters and minimum length 8"
def bmc_username_fail_msg(min_username_length, max_length):
    return f"bmc_username length must be between {min_username_length} and {max_length} characters. Must not contain '-', '\', "'", or '"'"
bmc_password_fail_msg = "Incorrect bmc_password format. Password must meet the specified requirements: should not be empty, must have a length of at least 3 characters, and should not contain the following characters: '-', '\', "'", or '"'"
docker_password_fail_msg = "Docker password must not be empty."
switch_snmp3_username_empty_msg = "enabled_switch_based is set to true, switch_snmp3_username must not be empty"
switch_snmp3_password_empty_msg = "enabled_switch_based is set to true, switch_snmp3_password must not be empty"
def switch_snmp3_username_fail_msg(min_username_length, max_length):
    return f"switch_snmp3_username length must be between {min_username_length} and {max_length} characters. Must not contain '-', '\\', "'", or '"'"
switch_snmp3_password_fail_msg = "switch_snmp3_password must be at least 3 characters. Must not contain '-', '\\', "'", or '"'"

# telemetry_config.yml
def boolean_fail_msg(value):
    return f"{value} must be set to either true or false."
appliance_k8s_pod_net_cidr_fail_msg = "appliance_k8s_pod_net_cidr value is either empty or invalid. Please provide CIDR notation such as 192.168.0.0/16"
k8s_prometheus_support_fail_msg = "k8s_prometheus_support must be True when prometheus_gaudi_support is True."
prometheus_scrape_interval_fail_msg = "prometheus_scrape_interval must be at least 15 when prometheus_gaudi_support is True."

#security_config.yml
domain_name_fail_msg = "domain_name is empty. Please provide a domain_name value."
realm_name_fail_msg = "realm_name is empty. Please provide a realm_name value."
ldap_connection_type_fail_msg = "ldap_connection_type is empty. Please provide a ldap_connection_type value."
openldap_organization_fail_msg = "openldap_organization is empty. Please provide a openldap_organization value."
openldap_organizational_unit_fail_msg = "openldap_organizational_unit is empty. Please provide a openldap_organizational_unit value."

#software_config.json
iso_file_path_fail_msg = "The provided ISO file path is invalid. Please ensure that the ISO file exists at the specified iso_file_path."
iso_file_path_not_contain_iso_msg = "The provided ISO file path must have the .iso extension."
def iso_file_path_not_contain_os_msg(iso_file_path, provision_os, provision_os_version):
    return f'Make sure iso_file_path variable in provision_config.yml contains value mentioned in the variables cluster_type: {provision_os} and cluster_os_version: {provision_os_version} mentioned in software_config.json'
def os_version_fail_msg(cluster_os_type, min_version, max_version):
    if (cluster_os_type == "ubuntu"):
        return f"For OS type '{cluster_os_type}', the version must be either {min_version} or {max_version}."
    return f"For OS type '{cluster_os_type}', the version must be {min_version}."
def software_mandatory_fail_msg(software_name):
    return f"in software_config.json. Please add the corresponding field '{software_name}' to the JSON. Look at /examples/template_ubuntu_software_config.json for an example"

# telemetry
mandatory_field_fail_msg = "must not be empty"
mysqldb_user_fail_msg = "username should not be kept 'root'."
fuzzy_offset_fail_msg = "should be between 60 and omnia_telemetry_collection_interval value"
metric_collection_timeout_fail_msg = "should be greater than 0 and less than omnia_telemetry_collection_interval value"
mount_location_fail_msg = "should have '/' at the end of the path"
grafana_password_fail_msg = "should not be kept 'admin'"

#security
file_path_fail_msg = "path does not exist"
def tls_ext_fail_msg(valid_extensions):
    extensions_list = ' or '.join(valid_extensions)
    return f"should have {extensions_list} extension"

# storage
client_mount_options_fail_msg = "should only contain nosuid,rw,sync,hard as options"
beegfs_unmount_client_fail_msg = "should be set to true since beegfs_mounts value has been changed"

# server_spec
server_spec_nicnetworks_fail_msg = "in server_spec.yml must exist within network_spec.yml as a network name. Please check both files"
def server_spec_network_key_fail_msg(nic_device):
    return f"in server_spec.yml does not start with '{nic_device}' (nicdevices)"
ip_overlap_fail_msg = "admin network, bmc network and k8 network and IP ranges should not have any IP overlap. Check omnia_config.yml and network_spec.yml"
telemetry_ip_overlap_fail_msg = "admin network, telemetry network and IP ranges should not have any IP overlap. Check telemetry_config.yml and network_spec.yml"

def user_name_duplicate(duplicate_usernames):
    return f'duplicate username detected {duplicate_usernames}. Check that usernames are unique in k8s_access_config.yml and passwordless_ssh_config.yml'

# login_node_security
def restrict_softwares_fail_msg(software):
    return f"Invalid software '{software}'. Can only disable these services: telnet,lpd,bluetooth,rlogin,rexec."

def get_header():
    return f"{'#' * 30} START EXECUTION {'#' * 30}"

def get_footer():
    return f"{'#' * 30} END EXECUTION {'#' * 30}"

def get_validation_initiated(input_file_path):
    return f"{'#' * 10} Validation Initiated for {input_file_path} {'#' * 10}"

def get_schema_failed(input_file_path):
    return f"{'#' * 10} Schema validation failed for {input_file_path} {'#' * 10}"

def get_schema_success(input_file_path):
    return f"{'#' * 10} Schema validation successful for {input_file_path} {'#' * 10}"

def get_logic_failed(input_file_path):
    return f"{'#' * 10} Logic validation failed for {input_file_path} {'#' * 10}"

def get_logic_success(input_file_path):
    return f"{'#' * 10} Logic validation successful for {input_file_path} {'#' * 10}"
