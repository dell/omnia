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
import ansible.module_utils.input_validation.common_utils.data_fetch as get
import ansible.module_utils.input_validation.common_utils.data_validation as validate
from ansible.module_utils.input_validation.common_utils import config
from ansible.module_utils.input_validation.common_utils import validation_utils
from ansible.module_utils.input_validation.common_utils import data_verification
from ansible.module_utils.input_validation.common_utils import config
from ansible.module_utils.input_validation.common_utils import en_us_validation_msg
from ansible.modules.validate_input import generate_log_failure_message
from ansible.module_utils.input_validation.validation_flows import scheduler_validation

from ansible.module_utils.local_repo.software_utils import (
    load_json,
    set_version_variables,
    get_subgroup_dict,
    get_software_names,
    get_json_file_path
)

file_names = config.files
create_error_msg = validation_utils.create_error_msg
create_file_path = validation_utils.create_file_path
contains_software = validation_utils.contains_software
check_mandatory_fields = validation_utils.check_mandatory_fields
flatten_sub_groups = validation_utils.flatten_sub_groups
file_exists = data_verification.file_exists

def validate_software_config(
    input_file_path, data,
    logger, module, omnia_base_dir,
    module_utils_base, project_name):
    errors = []
    cluster_os_type = data["cluster_os_type"]
    cluster_os_version = data["cluster_os_version"]
    os_version_ranges = config.os_version_ranges

    if cluster_os_type.lower() in os_version_ranges:
        version_range = os_version_ranges[cluster_os_type.lower()]
        if cluster_os_type.lower() in ["rhel", "rocky"]:
            if float(cluster_os_version) != float(version_range[0]):
                errors.append(
                    create_error_msg(
                        "cluster_os_version", cluster_os_version,
                        en_us_validation_msg.os_version_fail_msg(
                            cluster_os_type, version_range[0], None)))
        elif cluster_os_type.lower() == "ubuntu":
            if cluster_os_version not in version_range:
                errors.append(
                    create_error_msg(
                        "cluster_os_version", cluster_os_version,
                        en_us_validation_msg.os_version_fail_msg(
                            cluster_os_type, version_range[0], version_range[1])))

    iso_file_path = data.get("iso_file_path", "")
    not_valid_iso_msg = validation_utils.verify_iso_file(
                            iso_file_path, cluster_os_type, cluster_os_version)
    if not_valid_iso_msg:
        errors.append(
            create_error_msg(
                "iso_file_path", iso_file_path, not_valid_iso_msg))

    # Check for the additional software field
    if "additional_software" in data:
        # Run schema validation and call validate_additional_software()
        schema_base_file_path = os.path.join(module_utils_base,'input_validation','schema')
        passwords_set = config.passwords_set
        extensions = config.extensions
        fname = "additional_software"
        schema_file_path = schema_base_file_path + "/" + fname + extensions['json']
        json_files = get.files_recursively(omnia_base_dir + "/" + project_name, extensions['json'])
        json_files_dic = {}

        for file_path in json_files:
            json_files_dic.update({get.file_name_from_path(file_path): file_path})
        new_file_path = json_files_dic.get("additional_software.json", None)

        # Validate the schema of the input file (L1)
        validation_status = {}
        vstatus = []
        project_data = {project_name: {"status": [], "tag": "additional_software"}}
        validation_status.update(project_data)
        schema_status = validate.schema(
            new_file_path, schema_file_path, passwords_set,
            omnia_base_dir, project_name, logger, module)
        vstatus.append(schema_status)

        # Append the validation status for the input file
        validation_status[project_name]["status"].append(
            {new_file_path: "Passed" if schema_status else "Failed"})

        if False in vstatus:
            log_file_name = os.path.join(
                config.input_validator_log_path, f"validation_omnia_{project_name}.log")
            generate_log_failure_message(log_file_name, project_name, validation_status, module)

        # Check for the addtional_software.json file exist
        if new_file_path is None or not file_exists(new_file_path, module, logger):
            logger.info("The additional_software.json does not exist...")
            errors.append(
                create_error_msg(
                    "additional_software.json",
                    new_file_path,
                    en_us_validation_msg.MISSING_ADDITIONAL_SOFTWARE_JSON_FILE))
            return errors
        additional_software_data = json.load(open(json_files_dic["additional_software.json"], "r"))

        additional_software_errors = validate_additional_software(
            new_file_path, additional_software_data,
            logger, module, omnia_base_dir, module_utils_base, project_name)
        errors.extend(additional_software_errors)

    #create the subgroups and softwares dictionary with version details
    software_json_data = load_json(input_file_path)
    subgroup_dict, software_names = get_subgroup_dict(software_json_data)
    version_variables = set_version_variables(software_json_data, software_names, cluster_os_version)

    #check if the corresponding json files for softwares and subgroups exists in config folder
    software_list = get_software_names(input_file_path)
    validation_results = []
    failures=[]
    fail_data=[]
    for software in software_list:
        json_path = get_json_file_path(software, cluster_os_type, cluster_os_version, input_file_path)
        # Check if json_path is None or if the JSON syntax is invalid
        if json_path is None:
            errors.append(create_error_msg("Validation Error: ", None ,en_us_validation_msg.json_file_mandatory(json_path)))
        else:
            try:
                subgroup_softwares = subgroup_dict.get(software, None)
                #for each subgroup for a software check for corresponding entry in software.json
                #eg: for amd the amd.json should contain both amd and rocm entries
                with open(json_path, 'r') as file:
                    json_data = json.load(file)
                for subgroup_software in subgroup_softwares:
                    result, fail_data = validation_utils.validate_softwaresubgroup_entries(subgroup_software,json_path,json_data,validation_results,failures)

            except (FileNotFoundError, json.JSONDecodeError) as e:
                errors.append(create_error_msg("Error opening or reading JSON file:", json_path, str(e)))

    if fail_data:
        errors.append(create_error_msg("Software config subgroup validation failed for",fail_data,"Please resolve the issues first before proceeding."))

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
    software_config_file_path = create_file_path(input_file_path, file_names["software_config"])
    software_config_json = json.load(open(software_config_file_path, "r"))
    softwares = software_config_json["softwares"]
    for software in softwares:
        if software.get('name') == 'beegfs' and 'version' not in software:
            errors.append(create_error_msg("beegfs", "", en_us_validation_msg.BEEGFS_VERSION_FAIL_MSG))

    allowed_options = {"nosuid", "rw", "sync", "hard", "intr"}
    slurm_share_val = False
    k8s_share_val = False
    multiple_slurm_share_val = False
    multiple_k8s_share_val = False
    for nfs_client_params in data["nfs_client_params"]:
        client_mount_options = nfs_client_params["client_mount_options"]
        client_mount_options_set = set(client_mount_options.split(","))
        if not (client_mount_options_set.issubset(allowed_options)):
            errors.append(create_error_msg("client_mount_options", client_mount_options, en_us_validation_msg.CLIENT_MOUNT_OPTIONS_FAIL_MSG))
        if nfs_client_params["slurm_share"] == "true":
            if not slurm_share_val:
                slurm_share_val = True
            else:
                multiple_slurm_share_val = True

        if nfs_client_params["k8s_share"] == "true":
            if not k8s_share_val:
                k8s_share_val = True
            else:
                multiple_k8s_share_val = True

    if (contains_software(softwares, "slurm") and not slurm_share_val) or multiple_slurm_share_val:
        errors.append(create_error_msg("slurm_share", slurm_share_val, en_us_validation_msg.SLURM_SHARE_FAIL_MSG))

    if (contains_software(softwares, "k8s") and not k8s_share_val) or multiple_k8s_share_val:
        errors.append(create_error_msg("k8s_share", k8s_share_val, en_us_validation_msg.K8S_SHARE_FAIL_MSG))

    if contains_software(softwares, "ucx") or contains_software(softwares, "openmpi"):
        if not k8s_share_val or not slurm_share_val:
            errors.append(create_error_msg("nfs_client_params", "", en_us_validation_msg.BENCHMARK_TOOLS_FAIL_MSG))
        elif multiple_slurm_share_val or multiple_k8s_share_val:
            errors.append(create_error_msg("nfs_client_params", "", en_us_validation_msg.MULT_SHARE_FAIL_MSG))

    beegfs_mounts = data["beegfs_mounts"]
    if beegfs_mounts != "/mnt/beegfs":
        beegfs_unmount_client = data["beegfs_unmount_client"]
        if not beegfs_unmount_client:
            errors.append(create_error_msg("beegfs_unmount_client", beegfs_unmount_client, en_us_validation_msg.BEEGFS_UMOUNT_CLIENT_FAIL_MSG))

    return errors

# for k8s_access_config.yml and passwordless_ssh_config.yml this is run
def validate_usernames(input_file_path, data, logger, module, omnia_base_dir, module_utils_base, project_name):
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

def validate_omnia_config(input_file_path, data, logger, module, omnia_base_dir, module_utils_base, project_name):
    errors = []
    results=[]
    tag_names = eval(module.params["tag_names"])

    admin_bmc_networks = get_admin_bmc_networks(input_file_path, logger, module, omnia_base_dir, module_utils_base, project_name)
    admin_static_range = admin_bmc_networks["admin_network"]["static_range"]
    admin_dynamic_range = admin_bmc_networks["admin_network"]["dynamic_range"]
    bmc_static_range = admin_bmc_networks["bmc_network"]["static_range"]
    bmc_dynamic_range = admin_bmc_networks["bmc_network"]["dynamic_range"]
    pod_external_ip_range = data["pod_external_ip_range"]
    k8s_service_addresses = data["k8s_service_addresses"]
    k8s_pod_network_cidr = data["k8s_pod_network_cidr"]

    if 'k8s' in tag_names:
        results= scheduler_validation.validate_k8s_parameters(admin_static_range, bmc_static_range, admin_dynamic_range, bmc_dynamic_range, k8s_service_addresses, k8s_pod_network_cidr)
        if results:
            errors.append(create_error_msg("IP overlap -", results, en_us_validation_msg.ip_overlap_fail_msg))

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
    ip_ranges = [admin_static_range, bmc_static_range, admin_dynamic_range, bmc_dynamic_range, k8s_service_addresses, k8s_pod_network_cidr]
    does_overlap, _ = validation_utils.check_overlap(ip_ranges)

    if does_overlap:
        errors.append(create_error_msg("IP overlap -", None, en_us_validation_msg.ip_overlap_fail_msg))

    return errors

def validate_telemetry_config(input_file_path, data, logger, module, omnia_base_dir, module_utils_base, project_name):
    errors = []

    idrac_telemetry_support = data.get("idrac_telemetry_support")

    if idrac_telemetry_support:
        collection_type = data.get("idrac_telemetry_collection_type")
        if collection_type and collection_type not in config.supported_telemetry_collection_type:
            errors.append(create_error_msg("idrac_telemetry_collection_type", collection_type, en_us_validation_msg.unsupported_idrac_telemetry_collection_type))

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

def validate_additional_software(
        input_file_path, data, logger, module, omnia_base_dir,
        module_utils_base, project_name):
    """
    Validates the additional software configuration.

    Args:
        input_file_path (str): The path to the input file.
        data (dict): The data to be validated.
        logger (Logger): A logger instance.
        module (Module): A module instance.
        omnia_base_dir (str): The base directory of the Omnia configuration.
        module_utils_base (str): The base directory of the module utils.
        project_name (str): The name of the project.

    Returns:
        list: A list of errors encountered during validation.

    """
    errors = []
    # Get all keys in the data
    raw_subgroups = list(data.keys())
    flattened_sub_groups = set(flatten_sub_groups(list(data.keys())))

    # Check if additional_software is not given in the config
    if "additional_software" not in flattened_sub_groups:
        errors.append(
            create_error_msg(
                "additional_software.json",
                None,
                en_us_validation_msg.ADDITIONAL_SOFTWARE_FAIL_MSG))
        return errors

    # Get the roles config file
    config_file_path = omnia_base_dir.replace("../", "")
    roles_config_file_path = create_file_path(
        config_file_path, file_names["roles_config"])

    roles_config_json = validation_utils.load_yaml_as_json(
        roles_config_file_path, omnia_base_dir, project_name, logger, module)
    valid_roles = roles_config_json['Roles']

    # Set of unique role names
    available_roles_and_groups = set(role['name'] for role in roles_config_json['Roles'])
    available_roles_and_groups.add("additional_software")

    # Add the set of all unique group names
    available_roles_and_groups.update(group for role in valid_roles for group in role['groups'])

    # Check if a role or group name is present in the roles config file
    for sub_group in flattened_sub_groups:
        if sub_group not in available_roles_and_groups:
            errors.append(
                create_error_msg(
                    "additional_software.json",
                    None,
                    en_us_validation_msg.ADDITIONAL_SOFTWARE_SUBGROUP_FAIL_MSG.format(sub_group)))

    # Validate subgroups defined for additional_software in software_config.json
    # also present in additioanl_software.json
    software_config_file_path = create_file_path(config_file_path, file_names["software_config"])
    software_config_json = json.load(open(software_config_file_path, "r"))

    # check if additional_software is present in software_config.json
    if "additional_software" not in software_config_json:
        logger.info("The additional_software field is not present in software_config.json")
        software_config_json["additional_software"] = []

    sub_groups_in_software_config = list(sub_group['name'] for sub_group in
                                            software_config_json["additional_software"])

    # Check for the additional_software key in software_config.json
    for sub_group in sub_groups_in_software_config:
        if sub_group not in raw_subgroups:
            errors.append(
                create_error_msg(
                    "software_config.json",
                    None,
                    en_us_validation_msg.MISSING_IN_ADDITIONAL_SOFTWARE_MSG.format(sub_group)))
    return errors
