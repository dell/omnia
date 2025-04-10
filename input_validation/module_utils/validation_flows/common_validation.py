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
import os
import validation_utils
import config
import en_us_validation_msg
import fnmatch

file_names = config.files
create_error_msg = validation_utils.create_error_msg
create_file_path = validation_utils.create_file_path
contains_software = validation_utils.contains_software
check_mandatory_fields = validation_utils.check_mandatory_fields



def validate_software_config(input_file_path, data, logger, module, omnia_base_dir, project_name):
    errors = []
    cluster_os_type = data["cluster_os_type"]
    cluster_os_version = data["cluster_os_version"]
    os_version_ranges = config.os_version_ranges
    softwares_with_versions = config.specific_softwares
    software_config_input_file_path = input_file_path
    file_name = os.path.basename(software_config_input_file_path)
    directory_path = os.path.dirname(input_file_path)
    json_files_directory = f"{directory_path}/config/{cluster_os_type}/{cluster_os_version}"
    
    #check if the sofwtare_config.json has valid json syntax
    is_valid = validation_utils.is_valid_json(input_file_path)
    if not is_valid:
        errors.append(create_error_msg("software_config.json", input_file_path, "The sofwtare_config.json have json syntax errors"))

    # Check if the OS type matches the system level OS value
    oim_os = validation_utils.get_os_type()
    if oim_os.lower() != cluster_os_type.lower():
        errors.append(create_error_msg("oim_os", oim_os, en_us_validation_msg.os_type_fail_msg(cluster_os_type,oim_os)))
    
    #check if os version is in specified range eg: rhel-9.4
    if cluster_os_type.lower() in os_version_ranges:
        version_range = os_version_ranges[cluster_os_type.lower()]
        if cluster_os_type.lower() in ["rhel"]:
            if float(cluster_os_version) != float(version_range[0]):
                errors.append(create_error_msg("cluster_os_version", cluster_os_version, en_us_validation_msg.os_version_fail_msg(cluster_os_type, version_range[0], None)))
        elif cluster_os_type.lower() == "ubuntu":
            if cluster_os_version not in version_range:
                errors.append(create_error_msg("cluster_os_version", cluster_os_version, en_us_validation_msg.os_version_fail_msg(cluster_os_type, version_range[0], version_range[1])))

    # Extract software names
    #eg: software_names: ['amdgpu', 'cuda', 'ofed', 'openldap', 'nfs', 'k8s' , 'slurm'] software_names
    software_names = [software["name"] for software in data["softwares"] if "name" in software]

    # Generate subgroup_softwares dictionary
    #eg:subgroup_softwares: {'amdgpu': [{'name': 'rocm', 'version': '6.3.1'}], 
    #'slurm': [{'name': 'slurm_control_node'}, {'name': 'slurm_node'}, {'name': 'login'}]} subgroup_softwares
    subgroup_softwares = {}
    for item in software_names:
        if item in data:
            subgroup_softwares[item] = data[item]
    
    # Generate software JSON file patterns
    #software_json_list: ['amdgpu.json', 'cuda.json', 'ofed.json', 'openldap.json', 'nfs.json', 'k8s.json', 'slurm.json']
    software_json_list = [f"{name}.json" for name in software_names]

    #this checkf for the above files in the nfs share input directory is present or not
    #only if the files are present it returns the list of those files
    #filtered_json_files_list: ['/opt/omnia/input/project_default/input/config/rhel/9.4/amdgpu.json', 
    #'/opt/omnia/input/project_default/input/config/rhel/9.4/cuda.json', 
    #'/opt/omnia/input/project_default/input/config/rhel/9.4/ofed.json', '/opt/omnia/input/project_default/input/config/rhel/9.4/openldap.json',
    #'/opt/omnia/input/project_default/input/config/rhel/9.4/nfs.json']
    filtered_json_files_list = find_json_files(json_files_directory, software_json_list)

    #the below code performs syntax validation for those files
    validation_results = []
    # For loop to validate JSON syntax for each file in the list
    for json_file_path in filtered_json_files_list:
        is_valid = validation_utils.is_valid_json(json_file_path) 
        if not is_valid:
            validation_results.append((json_file_path, is_valid))

    #if there are syntax errros for the files it will collate them in a list and append it to errors  
    if len(validation_results) > 0:
        errors.append(create_error_msg("JSON Files", validation_results, "The above mentioned files have json syntax errors. Please correct them before proceeding"))



    # Extract file names from filtered_json_files_list
    available_json_list = [os.path.basename(file) for file in filtered_json_files_list]

    #if a software is define din the software_config.json and corresponding json file is missing from config folder
    #it will evaluate it and throw error
    missing_json_list = evaluate_missing_json_files(software_json_list, available_json_list)

    if missing_json_list:
        missing_json_fail_msg = "Mentioned JSON files are missing from "+json_files_directory
        errors.append(create_error_msg("Missing JSON files", missing_json_list, missing_json_fail_msg))

    
    version_result = []

    # Validation of version property for specific softwares
    #version_result: [{'item': {'name': 'amdgpu', 'version': '6.3.1'}, 'evaluated_to': True},
    # {'item': {'name': 'cuda', 'version': '12.5.0'}, 'evaluated_to': True}, 
    # {'item': {'name': 'ofed', 'version': '24.10-1.1.4.0'}, 'evaluated_to': True}, 
    # {'item': {'name': 'k8s', 'version': '1.31.4'}, 'evaluated_to': True}, 
    # {'item': {'name': 'rocm', 'version': '6.3.1'}, 'evaluated_to': True}] 
    for item in data['softwares'] + data.get('amdgpu', []) + data.get('bcm_roce', []):
        if 'name' in item:
            if item['name'] in softwares_with_versions:
                if 'version' in item and item['version']:
                    version_result.append({'item': item, 'evaluated_to': True})
                else:
                    version_result.append({'item': item, 'evaluated_to': False, 'msg': 'Assertion failed'})
            else:
                continue

    # Versions were not defined for softwares
    failed_softwares = [result['item']['name'] for result in version_result if result.get('msg') == 'Assertion failed']
    if failed_softwares:
        errors.append(create_error_msg("failed_softwares", failed_softwares, "failed_softwares"))

    # # Update software versions from software_config.json (softwares)
    # # software_versions: {'amdgpu_version': '6.3.1', 'cuda_version': '12.5.0', 'ofed_version': '24.10-1.1.4.0', 'k8s_version': '1.31.4'} 
    # software_versions = {}
    # for item in data.get("softwares", []):
    #     if "version" in item:
    #         software_versions[f"{item['name']}_version"] = item["version"]

    # # Update software versions from software_config.json (custom)
    # for item in data.get("custom", []):
    #     if "version" in item:
    #         software_versions[f"{item['name']}_version"] = item["version"]

    validate_software_subgroup_config_file, failures= validation_utils.validate_software_subgroup_config_file(filtered_json_files_list,input_file_path)
    errors.append(create_error_msg("Software config subgroup validation failed for",validate_software_subgroup_config_file+failures,"please resolve the issues first before proceeding."))
    
    
    return errors


def find_json_files(directory, patterns):
    matched_files = []
    for root, dirs, files in os.walk(directory):
        for pattern in patterns:
            for filename in fnmatch.filter(files, pattern):
                matched_files.append(os.path.join(root, filename))
    return matched_files

def evaluate_missing_json_files(software_json_list, available_json_list):
    missing_json_list = list(set(software_json_list) - set(available_json_list))
    return missing_json_list

def validate_security_config(input_file_path, data, logger, module, omnia_base_dir, project_name):
    errors = []
    passwordless_ssh_config_file_path = create_file_path(input_file_path, file_names["passwordless_ssh_config"])
    passwordless_ssh_config_json = validation_utils.load_yaml_as_json(passwordless_ssh_config_file_path, omnia_base_dir, project_name, logger, module)
    
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

def validate_network_config(input_file_path, data, logger, module, omnia_base_dir, project_name):
    errors = []
    mlnx_ofed_offline_path = data["mlnx_ofed_offline_path"]
    if mlnx_ofed_offline_path and not validation_utils.verify_path(mlnx_ofed_offline_path):
        errors.append(create_error_msg("mlnx_ofed_offline_path", mlnx_ofed_offline_path, en_us_validation_msg.file_path_fail_msg))

    return errors

def validate_storage_config(input_file_path, data, logger, module, omnia_base_dir, project_name):
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

def validate_high_availability_config(input_file_path, data, logger, module, omnia_base_dir, project_name):
    errors = []
    
    def validate_ha_config(ha_data, mandatory_fields, errors, config_type=None):
        try:
            check_mandatory_fields(mandatory_fields, ha_data, errors)
            
            # Special handling for OIM HA
            if config_type == "oim_ha":
                # Validate NFS share
                if 'nfs_share' in ha_data:
                    nfs_data = ha_data['nfs_share'][0] if isinstance(ha_data['nfs_share'], list) else ha_data['nfs_share']
                    check_mandatory_fields(["server_ip", "server_share_path"], nfs_data, errors)
                
                # Validate passive nodes with detailed node information
                if 'passive_nodes' in ha_data:
                    node_details_fields = ["SERVICE_TAG", "HOSTNAME", "ADMIN_MAC", "ADMIN_IP", "BMC_IP"]
                    for node in ha_data['passive_nodes']:
                        if 'node_details' in node:
                            for detail in node['node_details']:
                                check_mandatory_fields(node_details_fields, detail, errors)
            # Standard passive nodes validation for other HA types
            elif 'passive_nodes' in ha_data:
                for passive_node in ha_data['passive_nodes']:
                    check_mandatory_fields(["node_service_tags"], passive_node, errors)
                    
        except KeyError as e:
            logger.error(f"Missing key in HA data: {e}")
            errors.append(f"Missing key in HA data: {e}")
    
    ha_configs = [
        ("oim_ha", ["virtual_ip_address", "active_node_service_tag", "passive_nodes", "nfs_share"]),
        ("service_node_ha", ["service_nodes"]),
        ("slurm_head_node_ha", ["virtual_ip_address", "active_node_service_tags", "passive_nodes"]),
        ("k8s_head_node_ha", ["virtual_ip_address", "active_node_service_tags"])
    ]
    
    for config_name, mandatory_fields in ha_configs:
        ha_data = data.get(config_name)
        if ha_data:
            ha_data = ha_data[0] if isinstance(ha_data, list) else ha_data
            enable_key = f'enable_{config_name.split("_")[0]}_ha'
            if ha_data.get(enable_key):
                if config_name == "service_node_ha":
                    for service_node in ha_data['service_nodes']:
                        validate_ha_config(service_node, ["virtual_ip_address", "active_node_service_tag", "passive_nodes"], errors)
                else:
                    validate_ha_config(ha_data, mandatory_fields, errors, config_type=config_name)
        else:
            logger.warning(f"Configuration for {config_name} not found.")
    
    return errors

# for k8s_access_config.yml and passwordless_ssh_config.yml this is run
def validate_usernames(input_file_path, data, logger, module, omnia_base_dir, project_name):
    errors = []

    k8s_access_config_file_path = create_file_path(input_file_path, file_names["k8s_access_config"])
    k8s_access_config_json = validation_utils.load_yaml_as_json(k8s_access_config_file_path, omnia_base_dir, project_name, logger, module)
    passwordless_ssh_config_file_path = create_file_path(input_file_path, file_names["passwordless_ssh_config"])
    passwordless_ssh_config_json = validation_utils.load_yaml_as_json(passwordless_ssh_config_file_path, omnia_base_dir, project_name, logger, module)

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

def validate_roce_plugin_config(input_file_path, data, logger, module, omnia_base_dir, project_name):
    errors = []
    return errors

def validate_login_node_security_config(input_file_path, data, logger, module, omnia_base_dir, project_name):
    errors = []
    allowed_services = ["telnet", "lpd", "bluetooth", "rlogin", "rexec"]
    restrict_softwares = data["restrict_softwares"].split(",")
    for software in restrict_softwares:
        if software not in allowed_services:
            errors.append(create_error_msg("restrict_softwares", data["restrict_softwares"], en_us_validation_msg.restrict_softwares_fail_msg(software)))
    return errors

def validate_site_config(input_file_path, data, logger, module, omnia_base_dir, project_name):
    errors = []
    return errors

def validate_server_spec(input_file_path, data, logger, module, omnia_base_dir, project_name):
    errors = []
    server_groups = data["Categories"]
    server_spec_nicnetworks = []
    network_spec_networks = []

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

def get_admin_bmc_networks(input_file_path, logger, module, omnia_base_dir, project_name):
    network_spec_file_path = create_file_path(input_file_path, file_names["network_spec"])
    network_spec_json = validation_utils.load_yaml_as_json(network_spec_file_path, omnia_base_dir, project_name, logger, module)
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

def validate_omnia_config(input_file_path, data, logger, module, omnia_base_dir, project_name):
    errors = []
    admin_bmc_networks = get_admin_bmc_networks(input_file_path, logger, module, omnia_base_dir, project_name)
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

def validate_telemetry_config(input_file_path, data, logger, module, omnia_base_dir, project_name):
    errors = []
    idrac_telemetry_support = data["idrac_telemetry_support"]
    omnia_telemetry_support = data["omnia_telemetry_support"]
    visualization_support = data["visualization_support"]

    software_config_file_path = create_file_path(input_file_path, file_names["software_config"])
    software_config_json = json.load(open(software_config_file_path, "r"))
    # Check that telemetry is present in software_config.json and if at least one of the telemetry_supoort var is true, check that these fields are not empty
    softwares = software_config_json["softwares"]
    
    if contains_software(softwares, "telemetry"):
        if idrac_telemetry_support or omnia_telemetry_support or visualization_support:
            mandatory_fields = ["pod_external_ip_range", "k8s_cni", "k8s_service_addresses", "k8s_pod_network_cidr", "timescaledb_user", "timescaledb_password"]
            check_mandatory_fields(mandatory_fields, data, errors)

    if idrac_telemetry_support:
        mandatory_fields = ["idrac_username", "idrac_password", "mysqldb_user", "mysqldb_password", "mysqldb_root_password"]
        check_mandatory_fields(mandatory_fields, data, errors)

    if omnia_telemetry_support:
        mandatory_fields = ["omnia_telemetry_collection_interval", "collect_regular_metrics", "collect_health_check_metrics", "collect_gpu_metrics", "fuzzy_offset", "metric_collection_timeout"]
        check_mandatory_fields(mandatory_fields, data, errors)

        # fuzzy_offset should be between 60 and omnia_telemetry_collection_interval value
        fuzzy_offset = data["fuzzy_offset"]
        if fuzzy_offset < 60 or fuzzy_offset > data["omnia_telemetry_collection_interval"]:
            errors.append(create_error_msg("fuzzy_offset", fuzzy_offset, en_us_validation_msg.fuzzy_offset_fail_msg))

        # metric_collection_timeout should be greater than 0 and less than omnia_telemetry_collection_interval value
        metric_collection_timeout = data["metric_collection_timeout"]
        if (metric_collection_timeout < 0 or metric_collection_timeout > data["omnia_telemetry_collection_interval"]):
            errors.append(create_error_msg("metric_collection_timeout", metric_collection_timeout, en_us_validation_msg.metric_collection_timeout_fail_msg))

    if visualization_support:
        mandatory_fields = ["grafana_username", "grafana_password", "mount_location"]
        check_mandatory_fields(mandatory_fields, data, errors)

        # '/' is mandatory at the end of the mount_location path.
        mount_location = data["mount_location"]
        if mount_location[-1] != "/":
            errors.append(create_error_msg("mount_location", mount_location, en_us_validation_msg.mount_location_fail_msg))

        # grafana_password should not be kept 'admin'
        grafana_password = data["grafana_password"]
        if grafana_password == "admin":
            errors.append(create_error_msg("grafana_password", grafana_password, en_us_validation_msg.grafana_password_fail_msg))


    # Check that mysqldb_user is not root
    if data["mysqldb_user"] == "root":
        errors.append(create_error_msg("mysqldb_user", data["mysqldb_user"], en_us_validation_msg.mysqldb_user_fail_msg))

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
    admin_bmc_networks = get_admin_bmc_networks(input_file_path, logger, module, omnia_base_dir, project_name)
    admin_static_range = admin_bmc_networks["admin_network"]["static_range"]
    admin_dynamic_range = admin_bmc_networks["admin_network"]["dynamic_range"]
    pod_external_ip_range = data["pod_external_ip_range"]
    k8s_service_addresses = data["k8s_service_addresses"]
    k8s_pod_network_cidr = data["k8s_pod_network_cidr"]
    
    ip_ranges = [admin_static_range, admin_dynamic_range, pod_external_ip_range, k8s_service_addresses, k8s_pod_network_cidr]

    does_overlap, overlap_ips = validation_utils.check_overlap(ip_ranges)
    if does_overlap:
        errors.append(create_error_msg("IP overlap -", None, en_us_validation_msg.telemetry_ip_overlap_fail_msg))

    return errors
