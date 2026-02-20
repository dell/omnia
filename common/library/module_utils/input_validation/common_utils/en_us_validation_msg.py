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

### All of these messages are used in logical_validation.py
"""
This module contains validation messages in English (US) for input validation.
These messages are used to provide user-friendly error messages during configuration validation.
"""
PRIMARY_ADMIN_IP_INTERFACE_MISMATCH_MSG = "primary_oim_admin_ip does not match the actual IP configured on the specified interface"
NETMASK_BITS_INTERFACE_MISMATCH_MSG = "netmask_bits does not match the netmask configured on the specified interface"
MISSING_CLUSTER_NAME_MSG = "Cluster name is mandatory for all kubernetes roles."
CLUSTER_NAME_OVERLAP_MSG = "The cluster name '{0}' cannot be shared between service and compute Kubernetes roles."
CLUSTER_NAME_INCONSISTENT_MSG = (
    "Inconsistent 'cluster_name' values found across Service or Compute Kubernetes roles. "
    "Each of the following role sets must use the same 'cluster_name': "
    "[service_kube_control_plane, service_kube_node, service_etcd] and "
    "[kube_control_plane, kube_node, etcd].")
CLUSTER_ROLE_MISSING_MSG = (
    "Cluster '{0}' is missing the following required Kubernetes roles: {1}.")
MAX_NUMBER_OF_ROLES_MSG = "A max of 100 roles can be supported."
MIN_NUMBER_OF_GROUPS_MSG = "At least 1 group is required."
MIN_NUMBER_OF_ROLES_MSG = "At least 1 role is required."
MAX_NUMBER_OF_ROLES_PER_GROUP_MSG = "Groups can support a maximum of 5 roles."
RESOURCE_MGR_ID_MSG = ("The resource_mgr_id is mandatory if the group is mapped to "
                       "kube_node, slurm_node roles, service_kube_node, etcd, service_etcd roles.")
GRP_EXIST_MSG = "A valid group must be provided."
INVALID_SWITCH_IP_MSG = "Please provide a valid switch IPv4 address (example: 10.5.0.1)."
GRP_ROLE_MSG = "Please associate this group with a role."
PARENT_SERVICE_NODE_MSG = ("A group associated with the management_layer should not have a parent value.")
PARENT_SERVICE_ROLE_DNE_MSG = ("Parent field is only supported when 'service_kube_control_plane, service_kube_node' role is defined,"
    " Please remove the 'parent' field from this role's group definition.")
PARENT_SERVICE_ROLE_MSG = (" A 'service_kube_control_plane, service_kube_node' role is not defined, so the 'parent' field should"
    " be empty for groups associated with 'worker' or 'default' roles.")
PARENT_SERVICE_ROLE_REQUIRED_MSG = ("When 'service_kube_control_plane', 'service_kube_node' role is defined,"
    " the 'parent' field is required for groups associated with 'worker' or 'default' roles.")
BMC_STATIC_RANGE_INVALID_MSG = ("Static range should be in the following format: "
                               "IPv4Start-IPv4End (example: 10.5.0.1-10.5.0.200).")
OVERLAPPING_STATIC_RANGE = "bmc_detail's static_range is overlapping with other static ranges."
DUPLICATE_SWITCH_IP_PORT_MSG = "Please remove duplicate ports."
SWITCH_DETAILS_INCOMPLETE_MSG = ("If providing switch details, please provide both the IP "
                                 "and Ports fields.")
SWITCH_DETAILS_NO_BMC_DETAILS_MSG = ("If switch details are provided then bmc_detail's "
                                    "static_range must also be provided.")
INVALID_GROUP_NAME_MSG = "Groups must be defined in the form of grp<n> where n is 0-99."
INVALID_LOCATION_ID_MSG = ("location_id must follow the format SU-<n>.RACK-<n> where n is 0-99. "
                          "This input is case-sensitive. Please use uppercase letters only.")
INVALID_ATTRIBUTES_ROLE_MSG = ("Please provide valid attributes for the role, "
                              "both 'name' and 'groups' are mandatory.")
NO_GROUPS_MSG = "Outer Group object was probably not defined."
NO_ROLES_MSG = "Outer Role object was probably not defined."
INVALID_SWITCH_PORTS_MSG = "Please provide any port ranges as start-end (example: 0-15,4:4,51-53)."
DUPLICATE_GROUP_NAME_MSG = "Duplicate group names are not allowed."
EMPTY_OR_SYNTAX_ERROR_ROLES_CONFIG_MSG = ("File is either empty or contains syntax errors. "
                                         "File must contain valid YAML with 'Roles' and 'Groups' "
                                         "sections along with valid syntax. Check the file content "
                                         "and ensure proper YAML formatting.")
DUPLICATE_GROUP_NAME_IN_LAYERS_MSG = ("The following groups are mapped to both frontend and "
                                     "compute layers, which is not allowed for group: [{0}] in "
                                     "frontend layer: [{1}] and compute layer: [{2}]")
SERVICE_NODE_ENTRY_MISSING_ROLES_CONFIG_MSG = ("The role service_node defined in roles_config.yml,"
    " but service_node entry missing in sofware_config.json, "
    "Please rerun local repo with service_node entry in software_config.json "
    "to deploy service nodes successfully")
SERVICE_K8S_ENTRY_MISSING_SOFTWARE_CONFIG_MSG = ("The role service_kube_control_plane is defined in roles_config.yml, "
    "but the service_k8s package entry is missing in software_config.json. "
    "To deploy Kubernetes in the service_k8s cluster, the package must be added to software_config.json.")
SERVICE_NODE_ENTRY_INVALID_ROLES_CONFIG_MSG = ("The 'service_node' role defined in roles_config.yml"
    " is not currently supported and is reserved for future use. Please remove or update this role"
    " to avoid configuration errors.")

# Functional Groups Config Validation Messages

EMPTY_OR_SYNTAX_ERROR_FUNCTIONAL_GROUPS_CONFIG_MSG = (
    "The functional_groups_config.yml file is empty or has syntax errors." 
    "It must contain a valid 'functional_groups' section with proper YAML formatting."
    "Check the file content and rerun the playbook."
)
MISSING_GROUPS_SECTION_MSG = (
    "The functional_groups_config.yml file is empty or has syntax errors." 
    "It must contain a valid 'groups' section with proper YAML formatting."
    "Check the file content and rerun the playbook."
)
MISSING_FUNCTIONAL_GROUPS_SECTION_MSG = (
    "The functional_groups_config.yml file must contain a valid 'functional_groups' section. It must be a non-empty list."
)
NON_EMPTY_CLUSTER_NAME_MSG = "Cluster name must not be empty for '{name}' functional group."
FUNCTIONAL_GROUPS_NOT_LIST_MSG = (
    "The 'functional_groups' key must be associated with a list of functional group definitions."
)
EACH_FUNCTIONAL_GROUP_NOT_DICT_MSG = (
    "Each functional group entry must be a dictionary with required fields."
)
MISSING_FIELD_FUNCTIONAL_GROUP_MSG = "Missing required field: {field}"
DUPLICATE_FUNCTIONAL_GROUP_NAME_MSG = (
    "Duplicate functional group name found."
)
LOGIN_NODE_WITHOUT_SLURM_MSG = (
    "Login node defined for cluster '{cluster}' but no corresponding slurm_control_node exists."
    "Please make sure cluster name is same for slurm cluster and login_node functional groups."
)
SLURM_NODE_PARENT_MISSING_MSG = (
    "Functional group '{name}' must have a non-empty 'parent' field."    
)
MISSING_FUNCTIONAL_GROUPS_SECTION_MSG = (
    "The 'functional_groups' section is missing or null. It must be a non-empty list."
)
SLURM_NODE_WITHOUT_CONTROL_MSG = (
    "Slurm node defined for cluster '{cluster}' but no corresponding slurm_control_node exists. "
    "Please make sure cluster name is same for slurm_control_node and slurm_node functional groups."
)
SLURM_KUBE_CLUSTER_OVERLAP_MSG = (
    "Cluster '{cluster}' is defined for both SLURM nodes and Kubernetes nodes. Overlap not allowed."
)

# Mapping File Validation Messages
PROVISION_CONFIG_NOT_FOUND = (
    "provision_config.yml not found."
)
PXE_MAPPING_FILE_NOT_FOUND = (
    "PXE mapping file not found."
)
PXE_MAPPING_FILE_EMPTY_SERVICE_CLUSTER_MSG = (
    "PXE mapping file does not have functional groups for service cluster."
)
PXE_MAPPING_FILE_EMPTY_SLURM_CLUSTER_MSG = (
    "PXE mapping file does not have functional groups for slurm cluster."
)

# provision_config.yml
PRIMARY_ADMIN_BMC_IP_SAME_MSG = "primary_oim_admin_ip and primary_oim_bmc_ip should not be the same."
PRIMARY_ADMIN_IP_INVALID_MSG = "primary_oim_admin_ip is not a valid IPv4 address."
PRIMARY_BMC_IP_INVALID_MSG = "primary_oim_bmc_ip is not a valid IPv4 address."
PRIMARY_ADMIN_IP_IN_DYNAMIC_RANGE_MSG = "primary_oim_admin_ip should not be within the dynamic_range."
PRIMARY_BMC_IP_IN_DYNAMIC_RANGE_MSG = "primary_oim_bmc_ip should not be within the dynamic_range."
DEFAULT_LEASE_TIME_FAIL_MSG = "Please provide a valid default_lease_time."
ENABLE_SWITCH_BASED_FAIL_MSG = "enable_switch_based must be set to either true or false."
LANGUAGE_FAIL_MSG = "Only en_US.UTF-8 language supported"
LANGUAGE_EMPTY_MSG = "Language setting cannot be empty"
PUBLIC_NIC_FAIL_MSG = "public_nic is empty. Please provide a public_nic value."
PXE_MAPPING_FILE_PATH_FAIL_MSG = ("File path is invalid. Please ensure the file path specified in "
                                 "pxe_mapping_file_path exists and points to a valid file, "
                                 "not a directory.")
PXE_MAPPING_FILE_EXT_FAIL_MSG = ("File path is invalid. Please ensure that the file ends with "
                                 ".csv extension")
CLUSTER_OS_FAIL_MSG = "Cluster OS must be 'rhel' for RHEL Omnia Infrastructure Manager"

# local_repo.yml
REPO_STORE_PATH_MSG = "Please provide a valid repo_store_path value."
OMNIA_REPO_URL_MSG = "Repo urls are empty. Please provide a url and corresponding key."
RHEL_OS_URL_MSG = "is empty. Please provide a rhel_os_url value."
UBUNTU_OS_URL_MSG = "ubuntu_os_url is empty. Please provide a ubuntu_os_url value."
LDMS_REQUIRES_SERVICE_K8S_MSG = (
    "requires service_k8s to be present in the 'softwares' list in software_config.json."
)
LDMS_REQUIRES_SLURM_MSG = (
    "requires Slurm package 'slurm_custom' to be present in the 'softwares' list in software_config.json."
)

# omnia_config.yml
INVALID_PASSWORD_MSG = ("Provided password is invalid. Password must meet the specified "
                       "requirements: should not be empty, must have a length of at least "
                       "8 characters, and should not contain the following characters: "
                       "'-', '\\', \"'\", or '\"'")
K8S_CNI_FAIL_MSG = "k8s_cni is empty or invalid. k8s_cni must be set to either calico or flannel. "
POD_EXTERNAL_IP_RANGE_FAIL_MSG = ("pod_external_ip_range value is either empty or invalid. Please "
                                 "provide one of the following acceptable formats: '10.11.0.100-"
                                 "10.11.0.150' (range between start and end IP addresses) or "
                                 "'10.11.0.0/16' (CIDR notation).")
SLURM_INSTALLATION_TYPE_FAIL_MSG = ("slurm_installation_type is empty or invalid. "
                                   "slurm_installation_type_fail_msg must either be set to "
                                   "nfs_share or configless.")
RESTART_SLURM_SERVICES_FAIL_MSG = ("restart_slurm_services is empty or invalid. "
                                  "restart_slurm_services must be set to either true or false.")
K8S_SERVICE_ADDRESSES_FAIL_MSG = ("k8s_service_addresses are empty. "
                                  "Please provide k8s_service_addresses value.")
K8S_POD_NETWORK_CIDR_FAIL_MSG = ("k8s_pod_network_cidr is empty. "
                                 "Please provide a k8s_pod_network_cidr value.")
INTEL_GAUDI_FAIL_MSG = "should not be false as intel_gaudi exists in software_config.json"
CSI_DRIVER_SECRET_FAIL_MSG = "CSI Powerscale driver secret file path should not be empty."
CSI_DRIVER_VALUES_FAIL_MSG = "CSI Powerscale driver values file path should not be empty."

# provision_config_credentials.yml
PROVISION_PASSWORD_FAIL_MSG = ("Incorrect provision_password format. Password must meet the  "
                              "specified requirements: should not be empty, must have a "
                              "length of at least 8 characters, and should not contain the "
                              "following characters: '-', '\\', \"'\", or '\"'")
POSTGRESDB_PASSWORD_FAIL_MSG = ("Failed. postgresdb_password should contain only alphanumeric "
                               "characters and minimum length 8")
def bmc_username_fail_msg(min_username_length, max_length):
    """Returns a formatted message indicating bmc_username_fail_msg."""
    return (f"bmc_username length must be between {min_username_length} and "
            f"{max_length} characters. Must not contain '-', '\\', \"'\", or '\"'")

BMC_PASSWORD_FAIL_MSG = ("Incorrect bmc_password format. Password must meet the specified "
                        "requirements: should not be empty, must have a length of at least "
                        "3 characters, and should not contain the following characters: "
                        "'-', '\\', \"'\", or '\"'")
DOCKER_PASSWORD_FAIL_MSG = "Docker password must not be empty."
SWITCH_SNMP3_USERNAME_EMPTY_MSG = ("enabled_switch_based is set to true, "
                                   "switch_snmp3_username must not be empty")
SWITCH_SNMP3_PASSWORD_EMPTY_MSG = ("enabled_switch_based is set to true, "
                                   "switch_snmp3_password must not be empty")
def switch_snmp3_username_fail_msg(min_username_length, max_length):
    """Returns a formatted message indicating switch_snmp3_username_fail_msg."""
    return (f"switch_snmp3_username length must be between {min_username_length} "
            f"and {max_length} characters. Must not contain '-', '\\', \"'\", or '\"'")
SWITCH_SNMP3_PASSWORD_FAIL_MSG = ("switch_snmp3_password must be at least 3 characters. "
                                 "Must not contain '-', '\\', \"'\", or '\"'")


# telemetry_config.yml
KAFKA_ENABLE_FEDERATED_IDRAC_TELEMETRY_COLLECTION= ("requires federated_idrac_telemetry_collection "
                                             "to be enabled. Please rerun the playbook "
                                             "with federated_idrac_telemetry_collection true"
                                             "in telemetry_config.yml.")
TELEMETRY_SERVICE_CLUSTER_ENTRY_MISSING_ROLES_CONFIG_MSG= ("requires service k8s roles(service_kube_control_plane and service_kube_node)"
                                             " to be defined in 'pxe_mapping_file.csv'. Please either configure "
                                             "service k8s roles in the mapping file "
                                             "or disable idrac_telemetry_support in in telemetry_config.yml "
                                             "and rerun the playbook.")
TELEMETRY_SERVICE_CLUSTER_ENTRY_FOR_LDMS_MISSING_ROLES_CONFIG_MSG= ("requires service k8s roles(service_kube_control_plane "
                                             "and service_kube_node) or slurm nodes(slurm_control_node_x86_64 and slurm_node) "
                                             " to be defined in 'pxe_mapping_file.csv'. Please either configure "
                                             "service k8s/slurm roles in the mapping file or remove ldms from "
                                             "software_config.json and rerun the playbook.")

def boolean_fail_msg(value):
    """Returns a formatted message indicating boolean_fail_msg."""
    return f"{value} must be set to either true or false."
APPLIANCE_K8S_POD_NET_CIDR_FAIL_MSG = ("appliance_k8s_pod_net_cidr value is either empty or "
                                      "invalid. Please provide CIDR notation such as "
                                      "192.168.0.0/16")
K8S_PROMETHEUS_SUPPORT_FAIL_MSG = ("k8s_prometheus_support must be True when "
                                   "prometheus_gaudi_support is True.")
PROMETHEUS_SCRAPE_INTERVAL_FAIL_MSG = ("prometheus_scrape_interval must be at least 15 when "
                                      "prometheus_gaudi_support is True.")

# security_config.yml
DOMAIN_NAME_FAIL_MSG = "domain_name is empty. Please provide a domain_name value."
REALM_NAME_FAIL_MSG = "Failed. Incorrect realm_name formate in security_config.yml"
LDAP_CONNECTION_TYPE_FAIL_MSG = "Failed. LDAP Connection type must be: SSL, TLS, ssl or tls"
OPENLDAP_ORGANIZATION_FAIL_MSG = ("openldap_organization is empty. "
                                  "Please provide a openldap_organization value.")
OPENLDAP_ORGANIZATIONAL_UNIT_FAIL_MSG = ("openldap_organizational_unit is empty. "
                                         "Please provide a openldap_organizational_unit value.")
AUTHENTICATION_SYSTEM_FAIL_MSG = ("[WARNING] authentication_system variable in security_config.yml "
                                 "should be openldap")
AUTHENTICATION_SYSTEM_SUCCESS_MSG = "authentication_system variable successfully validated"
LDAP_CERT_PATH_FAIL_MSG = "Failed, LDAP certificate path doesn't exist."
ALERT_EMAIL_WARNING_MSG = ("[WARNING] alert_email_address is empty. "
                           "Authentication failure alerts won't be configured.")
ALERT_EMAIL_FAIL_MSG = ("Failed. Incorrect alert_email_address value "
                        "in login_node_security_config.yml")
SMTP_SERVER_FAIL_MSG = ("Failed. smtp_server details are mandatory when "
                        "alert_email_address provide in login_node_security_config.yml.")

# software_config.json

def os_version_fail_msg(cluster_os_type, min_version, max_version):
    """Returns a formatted message indicating os_version_fail_msg."""
    if cluster_os_type == "ubuntu":
        return (f"For OS type '{cluster_os_type}', the version must be either {min_version} or "
                f"{max_version}.")
    return f"For OS type '{cluster_os_type}', the supported version is {min_version}."
def software_mandatory_fail_msg(software_name):
    """Returns a formatted message indicating software_mandatory_fail_msg."""
    return (f"in software_config.json. Please add the corresponding field '{software_name}' "
            "to the JSON. Look at /examples/template_ubuntu_software_config.json for an example")
def json_file_mandatory(file_path):
    """Returns a formatted message indicating json_file_mandatory."""
    return (f"is present in software_config.json. Please make sure that the corresponding JSON file"
            f" is present at location '{file_path}'")

# network_spec.json
RANGE_IP_CHECK_FAIL_MSG = ("Failed. IP range should be in valid format "
                           "(Example: 192.168.1.1-192.168.1.254)")
RANGE_IP_CHECK_OVERLAP_MSG = "Static range and dynamic range in admin_network must not overlap"
NETWORK_GATEWAY_FAIL_MSG = ("Failed. network_gateway should be a valid IP address "
                            "(Example: 192.168.1.1)")
ADMIN_NETWORK_MISSING_MSG = "Failed. admin_network configuration is mandatory in network_spec.yml"
NETMASK_BITS_FAIL_MSG = "Netmask bit must be a valid number between 1 and 32"
RANGE_NETMASK_BOUNDARY_FAIL_MSG = ("IP range is outside the valid address range for "
                                   "the specified netmask.")
ADMIN_IP_OUTSIDE_NETWORK_RANGE_MSG = (
    "ADMIN_IP is outside the admin network range defined in "
    "network_spec.yml. Please ensure all ADMIN_IP addresses fall "
    "within the configured network range."
)
ADMIN_IP_IN_DYNAMIC_RANGE_MSG = (
    "ADMIN_IP falls within the dynamic_range which is reserved for DHCP. "
    "Please use a static IP address outside the dynamic range."
)
ADMIN_IP_CONFLICTS_WITH_PRIMARY_MSG = (
    "ADMIN_IP conflicts with the primary_oim_admin_ip defined in "
    "network_spec.yml. Please use a different IP address."
)
ADMIN_NETWORK_NOT_FOUND_MSG = (
    "admin_network configuration not found in network_spec.yml. "
    "Please ensure the Networks section contains admin_network."
)
PRIMARY_ADMIN_IP_NETMASK_REQUIRED_MSG = (
    "primary_oim_admin_ip and netmask_bits must be defined in "
    "network_spec.yml admin_network section."
)
INVALID_NETWORK_CONFIG_MSG = (
    "Invalid network configuration in network_spec.yml. "
    "Please verify primary_oim_admin_ip and netmask_bits are correct."
)
INVALID_DYNAMIC_RANGE_FORMAT_MSG = (
    "Invalid dynamic_range format in network_spec.yml. "
    "Expected format: 'start_ip-end_ip' (e.g., 10.1.1.10-10.1.1.50)."
)
ADMIN_IP_HOSTNAME_COLUMN_MISSING_MSG = (
    "ADMIN_IP or HOSTNAME column not found in PXE mapping file. "
    "Please ensure the CSV file has the required headers."
)
NETWORK_SPEC_FILE_NOT_FOUND_MSG = "network_spec.yml file not found in input folder."
IB_NETMASK_BITS_MISMATCH_MSG = (
    "netmask_bits configured for ib_network must match admin_network netmask_bits in network_spec.yml."
)
IB_SUBNET_IN_ADMIN_RANGE_MSG = (
    "ib_network subnet must be outside the admin network range derived from primary_oim_admin_ip/netmask_bits in network_spec.yml."
)

# telemetry
MANDATORY_FIELD_FAIL_MSG = "must not be empty"
MYSQLDB_USER_FAIL_MSG = "username should not be kept 'root'."
FUZZY_OFFSET_FAIL_MSG = "should be between 60 and omnia_telemetry_collection_interval value"
METRIC_COLLECTION_TIMEOUT_FAIL_MSG = ("should be greater than 0 and less than "
                                      "omnia_telemetry_collection_interval value")
MOUNT_LOCATION_FAIL_MSG = "should have '/' at the end of the path"
GRAFANA_PASSWORD_FAIL_MSG = "should not be kept 'admin'"

# security
FILE_PATH_FAIL_MSG = "path does not exist"
def tls_ext_fail_msg(valid_extensions):
    """Returns a formatted message indicating tls_ext_fail_msg."""
    extensions_list = ' or '.join(valid_extensions)
    return f"should have {extensions_list} extension"

# storage
BEEGFS_VERSION_FAIL_MSG = "Failed, Ensure version of beegfs is mentioned in software_config.json"
CLIENT_MOUNT_OPTIONS_FAIL_MSG = "should only contain nosuid,rw,sync,hard as options"
SLURM_SHARE_FAIL_MSG = "Exactly one entry should be present in nfs_client_params with slurm_share as true in storage_config.yml"
K8S_SHARE_FAIL_MSG = "Exactly one entry should be present in nfs_client_params with k8s_share as true in storage_config.yml"
BENCHMARK_TOOLS_FAIL_MSG = "Atleast one out of k8s_share or slurm_share in storage_config.yml should be true \
  when ucx/openmpi mentioned in software_config.json."
MULT_SHARE_FAIL_MSG = "Exactly one entry should be present in nfs_client_params with slurm_share as true or \
    k8s_share as true in storage_config.yml"
BEEGFS_UMOUNT_CLIENT_FAIL_MSG = "should be set to true since beegfs_mounts value has been changed"

# server_spec
SERVER_SPEC_NICNETWORKS_FAIL_MSG = ("in server_spec.yml must exist within network_spec.yml as a "
                                    "network name. Please check both files")
def server_spec_network_key_fail_msg(nic_device):
    """Returns a formatted message indicating server_spec_network_key_fail_msg."""
    return f"in server_spec.yml does not start with '{nic_device}' (nicdevices)"
IP_OVERLAP_FAIL_MSG = ("admin network, bmc network and k8 network and IP ranges should "
                       "not have any IP overlap. Check omnia_config.yml and network_spec.yml")
TELEMETRY_IP_OVERLAP_FAIL_MSG = ("admin network, telemetry network and IP ranges should "
                                 "not have any IP overlap. "
                                 "Check telemetry_config.yml and network_spec.yml")

# high_availability
VIRTUAL_IP_NOT_IN_ADMIN_SUBNET = ("virtual ip address provided is not in admin subnet. "
                                 "Check high_availability_config.yml and network_spec.yml")
VIRTUAL_IP_NOT_VALID = ("should be outside the admin static and dynamic ranges. "
                       "Check high_availability_config.yml and network_spec.yml")
VIRTUAL_IP_NOT_POD_EXT = ("should be outside the pod_external_ip ranges. "
                       "Check high_availability_config.yml and omnia_config.yml")
BMC_VIRTUAL_IP_NOT_VALID = ("should be outside any bmc static and dynamic ranges. "
                            "Check high_availability_config.yml, network_spec.yml, and "
                            "roles_config.yml")
FEILD_MUST_BE_EMPTY = "feild must be empty."
DUPLICATE_VIRTUAL_IP = "is already used. Please give unique virtual ip address"
INVALID_PASSIVE_NODE_SERVICE_TAG = "active node and passive node service tag cannot be same."
GROUP_NOT_FOUND = "is not defined in the roles_config.yml. Please define the group in roles_config.yml"
ROLE_NODE_FOUND = "is not defined in roles_config.yml. Please define the role in roles_config.yml"
DUPLICATE_ACTIVE_NODE_SERVICE_TAG = ("the service tag configured for a active node is already "
                                    "present elsewhere in the config file. ")
DUPLICATE_PASSIVE_NODE_SERVICE_TAG = ("the service tag configured for a passive node is already "
                                     "present elsewhere in the config file. ")

# build_stream_config.yml
ENABLE_BUILD_STREAM_REQUIRED_MSG = "Field 'enable_build_stream' is required in build_stream_config.yml."
ENABLE_BUILD_STREAM_BOOLEAN_MSG = "Field 'enable_build_stream' must be a boolean (true or false)."
BUILD_STREAM_CONFIG_EMPTY_MSG = ("build_stream_config.yml file is empty or has syntax errors. "
                                 "It must contain valid YAML with 'enable_build_stream' field.")
BUILD_STREAM_HOST_IP_INVALID_MSG = ("Field 'build_stream_host_ip' must be either the admin IP or public IP of OIM. "
                                    "Provided IP does not match admin IP from network_spec.yml.")
AARCH64_INVENTORY_HOST_IP_INVALID_SUBNET_MSG = ("Field 'aarch64_inventory_host_ip' must be in the same subnet as OIM admin IP. "
                                                "Check network_spec.yml for admin network configuration.")

# addtional_software
ADDITIONAL_SOFTWARE_FAIL_MSG = "The additional_software is mandatory in additional_software.json"
ADDITIONAL_SOFTWARE_SUBGROUP_FAIL_MSG = ("The role or group name, [{0}] is present in subgroup "
                                         "but not present in roles_config.yml")
MISSING_IN_ADDITIONAL_SOFTWARE_MSG = ("The role or group name is present in software_config.json, "
                                     "but [{0}] is not present in additional_software.json")

# login_node_security
def restrict_softwares_fail_msg(software):
    """Returns error message for invalid software restriction in
       login node security configuration."""
    return (f'Invalid software "{software}". Can only disable these services: '
            f'telnet,lpd,bluetooth,rlogin,rexec.')

def get_header():
    """Returns a formatted header string for execution logs."""
    return f"{'#' * 30} START EXECUTION {'#' * 30}"

def get_footer():
    """Returns a formatted footer string for execution logs."""
    return f"{'#' * 30} END EXECUTION {'#' * 30}"

def get_validation_initiated(input_file_path):
    """Returns a formatted message indicating validation has started for a file."""
    return f"{'#' * 10} Validation Initiated for {input_file_path} {'#' * 10}"

def get_schema_failed(input_file_path):
    """Returns a formatted message indicating schema validation failure for a file."""
    return f"{'#' * 10} Schema validation failed for {input_file_path} {'#' * 10}"

def get_schema_success(input_file_path):
    """Returns a formatted message indicating schema validation success for a file."""
    return f"{'#' * 10} Schema validation successful for {input_file_path} {'#' * 10}"

def get_logic_failed(input_file_path):
    """Returns a formatted message indicating logic validation failure for a file."""
    return f"{'#' * 10} Logic validation failed for {input_file_path} {'#' * 10}"

def get_logic_success(input_file_path):
    """Returns a formatted message indicating logic validation success for a file."""
    return f"{'#' * 10} Logic validation successful for {input_file_path} {'#' * 10}"

