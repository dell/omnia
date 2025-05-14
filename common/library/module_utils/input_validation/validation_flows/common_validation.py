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

import json
from ansible.module_utils.input_validation.common_utils import validation_utils
from ansible.module_utils.input_validation.common_utils import config
from ansible.module_utils.input_validation.common_utils import en_us_validation_msg

file_names = config.files
create_error_msg = validation_utils.create_error_msg
create_file_path = validation_utils.create_file_path
contains_software = validation_utils.contains_software
check_mandatory_fields = validation_utils.check_mandatory_fields

def validate_software_config(input_file_path, data, logger, module, omnia_base_dir, module_utils_base, project_name):
    errors = []
    cluster_os_type = data["cluster_os_type"]
    cluster_os_version = data["cluster_os_version"]
    os_version_ranges = config.os_version_ranges

    if cluster_os_type.lower() in os_version_ranges:
        version_range = os_version_ranges[cluster_os_type.lower()]
        if cluster_os_type.lower() in ["rhel", "rocky"]:
            if float(cluster_os_version) != float(version_range[0]):
                errors.append(create_error_msg("cluster_os_version", cluster_os_version, en_us_validation_msg.os_version_fail_msg(cluster_os_type, version_range[0], None)))
        elif cluster_os_type.lower() == "ubuntu":
            if cluster_os_version not in version_range:
                errors.append(create_error_msg("cluster_os_version", cluster_os_version, en_us_validation_msg.os_version_fail_msg(cluster_os_type, version_range[0], version_range[1])))

    iso_file_path = data.get("iso_file_path", "")
    not_valid_iso_msg = validation_utils.verify_iso_file(iso_file_path, cluster_os_type, cluster_os_version)
    if not_valid_iso_msg:
        errors.append(create_error_msg("iso_file_path", iso_file_path, not_valid_iso_msg))
    softwares = data["softwares"]
    need_additional_software_info = ["bcm_roce", "amdgpu", "vllm", "pytorch", "tensorflow", "intelgaudi"]
    filtered_softwares = [item for item in softwares if item.get("name") in need_additional_software_info]

    for software_name in filtered_softwares:
        name = software_name["name"]
        if not data.get(name):
            errors.append(create_error_msg(f"{name}", None, en_us_validation_msg.software_mandatory_fail_msg(name)))

    return errors

# Below is a validation function for each file in the input folder
def validate_local_repo_config(input_file_path, data, logger, module, omnia_base_dir, module_utils_base, project_name):
    # check to make sure associated os info is filled out
    errors = []
    software_config_file_path = create_file_path(input_file_path, file_names["software_config"])
    software_config_json = json.load(open(software_config_file_path, "r"))
    cluster_os_type = software_config_json["cluster_os_type"]

    ubuntu_os_url = data["ubuntu_os_url"]
    if cluster_os_type == "ubuntu":
        if validation_utils.is_string_empty(ubuntu_os_url):
            errors.append(create_error_msg("ubuntu_os_url", ubuntu_os_url, en_us_validation_msg.ubuntu_os_url_msg))

    rhel_os_url = data["rhel_os_url"]
    if cluster_os_type == "rhel":
        if validation_utils.is_string_empty(rhel_os_url):
            errors.append(create_error_msg("rhel_os_url", rhel_os_url, en_us_validation_msg.rhel_os_url_msg))

    return errors

def validate_security_config(input_file_path, data, logger, module, omnia_base_dir, module_utils_base, project_name):
    errors = []
    passwordless_ssh_config_file_path = create_file_path(input_file_path, file_names["passwordless_ssh_config"])
    passwordless_ssh_config_json = validation_utils.load_yaml_as_json(passwordless_ssh_config_file_path, omnia_base_dir, module_utils_base, project_name, logger, module)

    authentication_type = passwordless_ssh_config_json["authentication_type"]

    if authentication_type == "ldap":
        mandatory_fields = ["ldap_connection_type", "openldap_db_username", "openldap_db_password",
                            "openldap_config_username", "openldap_config_password", "openldap_monitor_password",
                            "openldap_organization", "openldap_organizational_unit"]
        check_mandatory_fields(mandatory_fields, data, errors)
    elif authentication_type == "freeipa":
        mandatory_fields = ["realm_name", "directory_manager_password", "kerberos_admin_password"]
        check_mandatory_fields(mandatory_fields, data, errors)

    certificates = {
        "tls_ca_certificate": data["tls_ca_certificate"],
        "tls_certificate": data["tls_certificate"],
        "tls_certificate_key": data["tls_certificate_key"],
    }

    for cert_name, cert_value in certificates.items():
        if cert_value and not validation_utils.verify_path(cert_value):
            errors.append(create_error_msg(cert_name, cert_value, en_us_validation_msg.file_path_fail_msg))

    return errors

def validate_network_config(input_file_path, data, logger, module, omnia_base_dir, module_utils_base, project_name):
    errors = []
    mlnx_ofed_offline_path = data["mlnx_ofed_offline_path"]
    if mlnx_ofed_offline_path and not validation_utils.verify_path(mlnx_ofed_offline_path):
        errors.append(create_error_msg("mlnx_ofed_offline_path", mlnx_ofed_offline_path, en_us_validation_msg.file_path_fail_msg))

    return errors

def validate_storage_config(input_file_path, data, logger, module, omnia_base_dir, module_utils_base, project_name):
    errors = []
    nfs_client_params = data["nfs_client_params"][0]
    client_mount_options = nfs_client_params["client_mount_options"]

    allowed_options = {"nosuid", "rw", "sync", "hard", "intr"}
    client_mount_options_set = set(client_mount_options.split(","))

    if not (client_mount_options_set.issubset(allowed_options)):
        errors.append(create_error_msg("client_mount_options", client_mount_options, en_us_validation_msg.client_mount_options_fail_msg))

    beegfs_mounts = data["beegfs_mounts"]
    if beegfs_mounts != "/mnt/beegfs":
        beegfs_unmount_client = data["beegfs_unmount_client"]
        if not beegfs_unmount_client:
            errors.append(create_error_msg("beegfs_unmount_client", beegfs_unmount_client, en_us_validation_msg.beegfs_unmount_client_fail_msg))

    return errors

# for k8s_access_config.yml and passwordless_ssh_config.yml this is run
def validate_usernames(input_file_path, data, logger, module, omnia_base_dir, module_utils_base, project_name):
    errors = []

    k8s_access_config_file_path = create_file_path(input_file_path, file_names["k8s_access_config"])
    k8s_access_config_json = validation_utils.load_yaml_as_json(k8s_access_config_file_path, omnia_base_dir, module_utils_base, project_name, logger, module)
    passwordless_ssh_config_file_path = create_file_path(input_file_path, file_names["passwordless_ssh_config"])
    passwordless_ssh_config_json = validation_utils.load_yaml_as_json(passwordless_ssh_config_file_path, omnia_base_dir, module_utils_base, project_name, logger, module)

    k8s_user_name = k8s_access_config_json["user_name"]
    pw_ssh_user_name = passwordless_ssh_config_json["user_name"]

    k8s_user_name = k8s_user_name.split(",")
    pw_ssh_user_name = pw_ssh_user_name.split(",")

    # Combine all usernames into a single list
    all_usernames = k8s_user_name + pw_ssh_user_name

    # Create a dictionary to store the count of each username
    username_count = {}
    for username in all_usernames:
        if username == "":
            continue
        if username in username_count:
            username_count[username] += 1
        else:
            username_count[username] = 1

    # Find usernames that appear more than once
    duplicate_usernames = [username for username, count in username_count.items() if count > 1]
    if len(duplicate_usernames) > 0:
        errors.append(create_error_msg("user_name", data["user_name"], en_us_validation_msg.user_name_duplicate(duplicate_usernames)))

    return errors

def validate_roce_plugin_config(input_file_path, data, logger, module, omnia_base_dir, module_utils_base, project_name):
    errors = []
    return errors

def validate_login_node_security_config(input_file_path, data, logger, module, omnia_base_dir, module_utils_base, project_name):
    errors = []
    allowed_services = ["telnet", "lpd", "bluetooth", "rlogin", "rexec"]
    restrict_softwares = data["restrict_softwares"].split(",")
    for software in restrict_softwares:
        if software not in allowed_services:
            errors.append(create_error_msg("restrict_softwares", data["restrict_softwares"], en_us_validation_msg.restrict_softwares_fail_msg(software)))
    return errors

def validate_site_config(input_file_path, data, logger, module, omnia_base_dir, module_utils_base, project_name):
    errors = []
    return errors

def validate_server_spec(input_file_path, data, logger, module, omnia_base_dir, module_utils_base, project_name):
    errors = []
    server_groups = data["Categories"]
    server_spec_nicnetworks = []
    network_spec_networks = []

    # Early return if Categories are None or empty
    if server_groups is None:
        return errors

    network_spec_file_path = create_file_path(input_file_path, file_names["network_spec"])
    network_spec_json = validation_utils.load_yaml_as_json(network_spec_file_path, omnia_base_dir, project_name, logger, module)

    for server in server_groups:
        for key, value in server.items():
            for item in value:
                # Handle network specifications
                if 'network' in item:
                    for network in item['network']:
                        for network_key, network_value in network.items():
                            # Collecting the nicnetwork
                            server_spec_nicnetworks.append(network_value["nicnetwork"])
                            # Validating nicdevices if present
                            if 'nicdevices' in network_value:
                                if not network_key.startswith(network_value.get('nicdevices')):
                                    errors.append(create_error_msg(f'{network_key}', None, en_us_validation_msg.server_spec_network_key_fail_msg(network_value['nicdevices'])))

    # Collecting network_spec nicnetwork names
    for key, network in network_spec_json.items():
        for nw in network:
            for name, value in nw.items():
                network_spec_networks.append(name)

    # Validating that all server nicnetworks exist in network_spec.yml
    for item in server_spec_nicnetworks:
        if item not in network_spec_networks:
            errors.append(create_error_msg(f'nicnetwork: "{item}"', None, en_us_validation_msg.server_spec_nicnetworks_fail_msg))

    return errors

def get_admin_bmc_networks(input_file_path, logger, module, omnia_base_dir, module_utils_base, project_name):
    network_spec_file_path = create_file_path(input_file_path, file_names["network_spec"])
    network_spec_json = validation_utils.load_yaml_as_json(network_spec_file_path, omnia_base_dir, module_utils_base, project_name, logger, module)
    admin_bmc_networks = {}

    for network in network_spec_json["Networks"]:
        for key, value in network.items():
            if key in ["admin_network", "bmc_network"]:
                static_range = value.get("static_range", "N/A")
                dynamic_range = value.get("dynamic_range", "N/A")
                admin_bmc_networks[key] = {
                    "static_range": static_range,
                    "dynamic_range": dynamic_range,
                }
    return admin_bmc_networks

def validate_omnia_config(input_file_path, data, logger, module, omnia_base_dir, module_utils_base, project_name):
    errors = []
    admin_bmc_networks = get_admin_bmc_networks(input_file_path, logger, module, omnia_base_dir, module_utils_base, project_name)
    admin_static_range = admin_bmc_networks["admin_network"]["static_range"]
    admin_dynamic_range = admin_bmc_networks["admin_network"]["dynamic_range"]
    bmc_static_range = admin_bmc_networks["bmc_network"]["static_range"]
    bmc_dynamic_range = admin_bmc_networks["bmc_network"]["dynamic_range"]
    pod_external_ip_range = data["pod_external_ip_range"]
    k8s_service_addresses = data["k8s_service_addresses"]
    k8s_pod_network_cidr = data["k8s_pod_network_cidr"]

    run_intel_gaudi_tests = data["run_intel_gaudi_tests"]
    csi_powerscale_driver_secret_file_path = data["csi_powerscale_driver_secret_file_path"]
    csi_powerscale_driver_values_file_path = data["csi_powerscale_driver_values_file_path"]

    #verify intel_gaudi with sofwate config json
    software_config_file_path = create_file_path(input_file_path, file_names["software_config"])
    software_config_json = json.load(open(software_config_file_path, "r"))
    softwares = software_config_json["softwares"]
    if contains_software(softwares, "intelgaudi") and not run_intel_gaudi_tests:
        errors.append(create_error_msg("run_intel_gaudi_tests", run_intel_gaudi_tests, en_us_validation_msg.intel_gaudi_fail_msg))

    #verify csi with sofwate config json
    software_config_file_path = create_file_path(input_file_path, file_names["software_config"])
    software_config_json = json.load(open(software_config_file_path, "r"))
    softwares = software_config_json["softwares"]
    if contains_software(softwares, "csi_driver_powerscale"):
         # Validate if secret file path is empty
        if not csi_powerscale_driver_secret_file_path:
            errors.append(create_error_msg("csi_powerscale_driver_secret_file_path", csi_powerscale_driver_secret_file_path, en_us_validation_msg.csi_driver_secret_fail_msg))

        # Validate if values file path is empty
        if not csi_powerscale_driver_values_file_path:
            errors.append(create_error_msg("csi_powerscale_driver_values_file_path", csi_powerscale_driver_values_file_path, en_us_validation_msg.csi_driver_values_fail_msg))

    # Check IP range overlap between omnia IPs, admin network, and bmc network
    ip_ranges = [admin_static_range, bmc_static_range, admin_dynamic_range, bmc_dynamic_range, pod_external_ip_range, k8s_service_addresses, k8s_pod_network_cidr]
    does_overlap, _ = validation_utils.check_overlap(ip_ranges)

    if does_overlap:
        errors.append(create_error_msg("IP overlap -", None, en_us_validation_msg.ip_overlap_fail_msg))

    return errors

def validate_telemetry_config(input_file_path, data, logger, module, omnia_base_dir, module_utils_base, project_name):
    errors = []
    idrac_collection_type = ["Prometheus"] # currently supports only Prometheus
    idrac_telemetry_support = data["idrac_telemetry_support"]
    idrac_telemetry_collection_type = data["idrac_telemetry_collection_type"]
    visualization_support = data["visualization_support"]

    if idrac_telemetry_support:
        valid_collection_types = {item.lower() for item in idrac_collection_type}
        if idrac_telemetry_collection_type.lower() not in valid_collection_types:
            errors.append(create_error_msg("idrac_telemetry_collection_type", idrac_telemetry_collection_type, en_us_validation_msg.unsupported_idrac_telemetry_collection_type))

    # preserved below code for future use
    '''
    # Added code for Omnia 1.7 k8 prometheus support parameters
    # Validate prometheus_gaudi_support, k8s_prometheus_support, and prometheus_scrape_interval
    prometheus_gaudi_support = data["prometheus_gaudi_support"]
    k8s_prometheus_support = data["k8s_prometheus_support"]
    prometheus_scrape_interval = data["prometheus_scrape_interval"]

    if prometheus_gaudi_support:
        mandatory_fields = ["k8s_prometheus_support", "prometheus_scrape_interval"]
        check_mandatory_fields(mandatory_fields, data, errors)

    # Check k8s_prometheus_support is True and prometheus_scrape_interval is >= 15 when prometheus_gaudi_support is True
    if prometheus_gaudi_support and isinstance(prometheus_gaudi_support, str):
        if not k8s_prometheus_support:
            errors.append(create_error_msg("k8s_prometheus_support", k8s_prometheus_support, en_us_validation_msg.k8s_prometheus_support_fail_msg))

        if prometheus_scrape_interval < 15:
            errors.append(create_error_msg("prometheus_scrape_interval", prometheus_scrape_interval, en_us_validation_msg.prometheus_scrape_interval_fail_msg))

    # Check that IP addresses do not overlap with admin network
    admin_bmc_networks = get_admin_bmc_networks(input_file_path, logger, module, omnia_base_dir, module_utils_base, project_name)
    admin_static_range = admin_bmc_networks["admin_network"]["static_range"]
    admin_dynamic_range = admin_bmc_networks["admin_network"]["dynamic_range"]
    pod_external_ip_range = data["pod_external_ip_range"]
    k8s_service_addresses = data["k8s_service_addresses"]
    k8s_pod_network_cidr = data["k8s_pod_network_cidr"]

    ip_ranges = [admin_static_range, admin_dynamic_range, pod_external_ip_range, k8s_service_addresses, k8s_pod_network_cidr]

    does_overlap, overlap_ips = validation_utils.check_overlap(ip_ranges)
    if does_overlap:
        errors.append(create_error_msg("IP overlap -", None, en_us_validation_msg.telemetry_ip_overlap_fail_msg))
    '''
    return errors
