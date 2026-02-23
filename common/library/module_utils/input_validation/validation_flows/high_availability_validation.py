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
# pylint: disable=too-many-arguments,too-many-locals,too-many-positional-arguments,import-error
"""
This module contains functions for validating high availability configuration.
"""
import csv
import os
import yaml
from ansible.module_utils.input_validation.common_utils import validation_utils
from ansible.module_utils.input_validation.common_utils import config
from ansible.module_utils.input_validation.common_utils import en_us_validation_msg

file_names = config.files
create_error_msg = validation_utils.create_error_msg
create_file_path = validation_utils.create_file_path
contains_software = validation_utils.contains_software
check_mandatory_fields = validation_utils.check_mandatory_fields


def get_roles_config_json(input_file_path, logger, module, omnia_base_dir, project_name):
    """
    Retrieves the roles configuration from a YAML file.

    Parameters:
        input_file_path (str): The path to the input file.
        logger (Logger): A logger instance.
        module (AnsibleModule): An Ansible module instance.
        omnia_base_dir (str): The base directory of the Omnia project.
        project_name (str): The name of the project.

    Returns:
        dict: The roles configuration as json.
    """
    roles_config_file_path = create_file_path(input_file_path,
                                              file_names["functional_groups_config"])
    roles_config_json = validation_utils.load_yaml_as_json(
        roles_config_file_path, omnia_base_dir, project_name, logger, module
    )

    return roles_config_json


def check_and_validate_ha_role_in_roles_config(errors, roles_config_json, ha_role):
    """
    Validates the HA role in the roles_config.yml file.

    Parameters:
            errors (list): A list to store error messages.
            roles_config_json (dict): A json containing the roles configuration.
            ha_role (str): The name of the HA role to validate.

    Returns:
            None
    """

    # Get groups and roles
    groups_configured = roles_config_json.get("Groups", {})
    roles_configured = roles_config_json.get("Roles", [])

    # Search for HA role and validate its groups
    ha_role_entry = next((role for role in roles_configured if role.get("name") == ha_role), None)

    if ha_role_entry:
        missing_groups = [g for g in ha_role_entry.get("groups", []) if g not in groups_configured]
        for group in missing_groups:
            errors.append(
                create_error_msg(
                    f"group: '{group}' associated for role",
                    ha_role,
                    en_us_validation_msg.GROUP_NOT_FOUND,
                )
            )
    else:
        errors.append(create_error_msg("role", ha_role, en_us_validation_msg.ROLE_NODE_FOUND))


def get_admin_static_dynamic_ranges(network_spec_json):
    """
    This function takes a network specification JSON object as input
    and returns a dictionary containing the static and dynamic ranges
    of the admin network.

    Args:
        network_spec_json (dict): A JSON object containing the network specification.

    Returns:
        dict: A dictionary containing the static and dynamic ranges of the admin network.
    """
    admin_network = {}
    for network in network_spec_json["Networks"]:
        for key, value in network.items():
            if key == "admin_network":
                static_range = value.get("static_range", "N/A")
                dynamic_range = value.get("dynamic_range", "N/A")
                admin_network = {
                    "static_range": static_range,
                    "dynamic_range": dynamic_range,
                }
    return admin_network


def get_bmc_network(network_spec_json):
    """
    Returns the BMC network configuration from the network specification JSON.

    Parameters:
        network_spec_json (dict): The network specification JSON.

    Returns:
        dict: The BMC network configuration,
        containing dynamic_range and dynamic_conversion_static_range.
    """
    bmc_network = {}
    for network in network_spec_json["Networks"]:
        for key, value in network.items():
            if key == "bmc_network":
                static_range = value.get("dynamic_range", "N/A")
                dynamic_range = value.get("dynamic_conversion_static_range", "N/A")
                bmc_network = {
                    "dynamic_range": static_range,
                    "dynamic_conversion_static_range": dynamic_range,
                }
    return bmc_network


def get_admin_netmaskbits(network_spec_json):
    """
    Retrieves the netmask bits for the admin network.

    Parameters:
        network_spec_json (dict): The network specification JSON.

    Returns:
        str: The netmask bits for the admin network, or "N/A" if not found.
    """
    netmaskbits = ""
    for network in network_spec_json["Networks"]:
        for key, value in network.items():
            if key == "admin_network":
                netmaskbits = value.get("netmask_bits", "N/A")
    return netmaskbits


def get_admin_uncorrelated_node_start_ip(network_spec_json):
    """
    Retrieves the get_admin_uncorrelated_node_start_ip for the admin network.

    Parameters:
        network_spec_json (dict): The network specification JSON.

    Returns:
        str: The get_admin_uncorrelated_node_start_ip for the admin network, or "N/A" if not found.
    """
    admin_uncorrelated_node_start_ip = ""
    for network in network_spec_json["Networks"]:
        for key, value in network.items():
            if key == "admin_network":
                admin_uncorrelated_node_start_ip = value.get(
                    "admin_uncorrelated_node_start_ip", "N/A"
                )
    return admin_uncorrelated_node_start_ip


def get_admin_nic_name(network_spec_json):
    """
    Retrieves the oim_nic_name for the admin network.

    Parameters:
        network_spec_json (dict): The network specification JSON.

    Returns:
        str: The oim_nic_name for the admin network, or "N/A" if not found.
    """
    admin_nic_name = ""
    for network in network_spec_json["Networks"]:
        for key, value in network.items():
            if key == "admin_network":
                admin_nic_name = value.get("oim_nic_name", "N/A")
    return admin_nic_name


def get_bmc_nic_name(network_spec_json):
    """
    Retrieves the oim_nic_name for the admin network.

    Parameters:
        network_spec_json (dict): The network specification JSON.

    Returns:
        str: The oim_nic_name for the bmc network, or "N/A" if not found.
    """
    bmc_nic_name = ""
    for network in network_spec_json["Networks"]:
        for key, value in network.items():
            if key == "bmc_network":
                bmc_nic_name = value.get("oim_nic_name", "N/A")
    return bmc_nic_name


def get_primary_oim_admin_ip(network_spec_json):
    """
    This function retrieves the primary OIM admin IP address from a given network spec JSON object.

    Args:
        network_spec_json (dict): The JSON object containing the network specifications.

    Returns:
        str: The primary OIM admin IP address or "N/A" if not found.
    """
    oim_admin_ip = ""
    for network in network_spec_json["Networks"]:
        for key, value in network.items():
            if key == "admin_network":
                oim_admin_ip = value.get("primary_oim_admin_ip", "N/A")
    return oim_admin_ip


def is_service_tag_present(service_tags_list, input_service_tag):
    """
    Checks if a service tag is present in a given list of service tags.

    Args:
        service_tags_list (list): A list of service tags.
        input_service_tag (str): The service tag to be checked.

    Returns:
        bool: True if the service tag is present, False otherwise.
    """
    return input_service_tag in service_tags_list


def validate_service_tag_presence(
    errors, config_type, all_service_tags, active_node_service_tag, passive_nodes
):
    """
    Validates the presence of service tags in the given list of all service tags.

    Parameters:
        errors (list): A list to store error messages.
        config_type (str): The type of configuration being validated.
        all_service_tags (list): A list of all service tags.
        active_node_service_tag (str): The service tag of the active node.
        passive_nodes (list): A list of passive nodes with their service tags.

    Returns:
        None
    """
    # validate_active_node_uniqueness
    if active_node_service_tag and is_service_tag_present(
        all_service_tags, active_node_service_tag
    ):
        errors.append(
            create_error_msg(
                f"{config_type}",
                active_node_service_tag,
                en_us_validation_msg.DUPLICATE_ACTIVE_NODE_SERVICE_TAG,
            )
        )

    # validate passive_node_uniqueness
    for node_service_tags in passive_nodes:
        for service_tag in node_service_tags.get("node_service_tags", []):
            if service_tag == active_node_service_tag or is_service_tag_present(
                all_service_tags, service_tag
            ):
                errors.append(
                    create_error_msg(
                        f"{config_type}",
                        service_tag,
                        en_us_validation_msg.DUPLICATE_PASSIVE_NODE_SERVICE_TAG,
                    )
                )


def validate_vip_address(
    errors,
    config_type,
    vip_address,
    admin_network,
    pod_external_ip_list,
    admin_netmaskbits,
    oim_admin_ip
):
    """
        Validate a virtual IP address against a list of existing service node VIPs,
    admin network static and dynamic ranges, and admin subnet.

        Parameters:
        - errors (list): A list to store error messages.
        - config_type (str): The type of configuration being validated.
        - vip_address (str): The virtual IP address to be validated.
        - pod_external_ip_list (list): A list of external IP addresses associated with the pods
        - admin_network (dict): A dictionary containing admin network configuration.
        - admin_netmaskbits (str): The netmask bits value of the admin network.
        - oim_admin_ip (str): The IP address of the OIM admin interface.

        Returns:
        - None: The function does not return any value, it only appends
            error messages to the errors list.
    """
    # virtual_ip_address is mutually exclusive with admin dynamic ranges
    vip_within_dynamic_range = validation_utils.is_ip_within_range(
        admin_network["dynamic_range"], vip_address
    )

    if vip_within_dynamic_range:
        errors.append(
            create_error_msg(
                f"{config_type} virtual_ip_address",
                vip_address,
                en_us_validation_msg.VIRTUAL_IP_NOT_VALID,
            )
        )

    # validate virtual_ip_address is in the admin subnet
    if not validation_utils.is_ip_in_subnet(oim_admin_ip, admin_netmaskbits, vip_address):
        errors.append(
            create_error_msg(
                f"{config_type} virtual_ip_address",
                vip_address,
                en_us_validation_msg.VIRTUAL_IP_NOT_IN_ADMIN_SUBNET,
            )
        )

    # pod external
    for pod_ext in pod_external_ip_list:
        vip_within_pod_external = validation_utils.is_ip_within_range(
            pod_ext, vip_address
        )

        if vip_within_pod_external:
            errors.append(
                create_error_msg(
                    f"{config_type} vip in pod external",
                    vip_address,
                    en_us_validation_msg.VIRTUAL_IP_NOT_POD_EXT,
                )
            )

def validate_service_k8s_cluster_ha(
    errors,
    config_type,
    ha_data,
    input_file_path,
    network_spec_data,
    all_service_tags,
    ha_node_vip_list
):
    """
    Validates Kubernetes HA (High Availability) head node configuration for potential issues.
    Args:
        errors (list): A list to which error messages will be appended.
        config_type (str): A string representing the configuration context or type
        ,used in error reporting.
        ha_data (dict): Contains high availability configuration data, including:
            - 'external_loadbalancer_ip' (str): The IP of the external load balancer.
            - 'active_node_service_tag' (list): A list of service tags marked as active.
        network_spec_data (dict): Contains network specification data, including:
            - 'admin_network' (dict): Includes 'static' and 'dynamic' for the admin network.
            - 'oim_admin_ip' (str): The OIM admin IP.
            - 'admin_uncorrelated_node_start_ip' (str): Starting IP for uncorrelated admin nodes.
        roles_config_json (dict): Reserved for future role-based validations (currently unused).
        all_service_tags (list): A list of all service tags defined in the system.
        ha_node_vip_list (list): List of virtual IPs assigned to HA nodes (currently unused).

    Returns:
        None: Errors are collected in the provided `errors` list.
    """
    admin_network = network_spec_data["admin_network"]
    admin_dynamic_range = admin_network.get("dynamic_range", "N/A")
    admin_netmaskbits = network_spec_data.get("admin_netmaskbits")
    oim_admin_ip = network_spec_data["oim_admin_ip"]

    with open(os.path.join(input_file_path, "provision_config.yml"), "r", encoding="utf-8") as f:
        prov_cfg = yaml.safe_load(f)

    with open(prov_cfg.get('pxe_mapping_file_path'), newline='', encoding='utf-8') as csvfile:
        pxe_list = list(csv.DictReader(csvfile, delimiter=","))
        pxe_admin_ips = [item["ADMIN_IP"] for item in pxe_list]
        pxe_bmc_ips   = [item["BMC_IP"]   for item in pxe_list]

    with open(os.path.join(input_file_path, "omnia_config.yml"), "r", encoding="utf-8") as omniacfg:
        omnia_config =  yaml.safe_load(omniacfg)
        pod_external_ip_list = [item.get("pod_external_ip_range")
                                for item in omnia_config.get('service_k8s_cluster')
                                if item.get('deployment', False)]

    if not isinstance(ha_data, list):
        ha_data = [ha_data]
    for hdata in ha_data:
        does_overlap = []
        vip_address = hdata.get("virtual_ip_address")
        # Find the intersection
        if vip_address:
            for ip_list in (ha_node_vip_list, pxe_admin_ips, pxe_bmc_ips):
                if vip_address in ip_list:
                    errors.append(
                        create_error_msg(
                            f"{config_type} virtual_ip_duplicate",
                            vip_address,
                            en_us_validation_msg.DUPLICATE_VIRTUAL_IP))
            validate_vip_address(
                errors,
                config_type,
                vip_address,
                admin_network,
                pod_external_ip_list,
                admin_netmaskbits,
                oim_admin_ip
            )


def load_network_spec(input_file_path):
    """
    Loads network specification from a YAML file and returns it as a dictionary.

    Args:
        input_file_path (str): The path to the directory containing the YAML file.

    Returns:
        dict: A dictionary containing network specification information.
    """
    with open(os.path.join(input_file_path, "network_spec.yml"), "r", encoding="utf-8") as f:
        network_spec_json = yaml.safe_load(f)
    network_spec_info = {
        "admin_network": get_admin_static_dynamic_ranges(network_spec_json),
        "admin_nic_name": get_admin_nic_name(network_spec_json),
        "bmc_network": get_bmc_network(network_spec_json),
        "bmc_nic_name": get_bmc_nic_name(network_spec_json),
        "admin_netmaskbits": get_admin_netmaskbits(network_spec_json),
        "admin_uncorrelated_node_start_ip": get_admin_uncorrelated_node_start_ip(
            network_spec_json
        ),
        "oim_admin_ip": get_primary_oim_admin_ip(network_spec_json)
    }
    return network_spec_info

def validate_ha_config(ha_data, mandatory_fields, errors, config_type,
                       input_file_path, all_service_tags, ha_node_vip_list):
    """
    Validates high availability configuration.

    Args:
        ha_data (dict): The high availability configuration data.
        mandatory_fields (list): The list of mandatory fields in the HA configuration.
        errors (list): The list to store error messages.
        config_type (str): The type of HA configuration.
        input_file_path (str): The path to the directory containing the YAML file.
        all_service_tags (list): The list of all service tags.
        ha_node_vip_list (list): The list of HA node VIPs.

    Returns:
        None
    """
    ha_validation = {
        "service_k8s_cluster_ha": validate_service_k8s_cluster_ha
    }
    network_spec_info = load_network_spec(input_file_path)
    check_mandatory_fields(mandatory_fields, ha_data, errors)
    if config_type in ha_validation:
        ha_validation[config_type](
            errors,
            config_type,
            ha_data,
            input_file_path,
            network_spec_info,
            all_service_tags,
            ha_node_vip_list)

def validate_high_availability_config(
    input_file_path, data, logger, module, omnia_base_dir, _module_utils_base, project_name
):
    """
    Validates high availability configuration for different ha config types.

    Parameters:
        input_file_path (str): The path of the input file.
        data (dict): The data to be validated.
        logger (Logger): The logger object.
        module (AnsibleModule): The Ansible module object.
        omnia_base_dir (str): The base directory of Omnia.
        module_utils_base (str): The base directory of module_utils.
        project_name (str): The name of the project.

    Returns:
        list: A list of errors found during validation.
    """
    errors = []
    ha_node_vip_list = []
    all_service_tags = set()

    ha_configs = [
        ("service_k8s_cluster_ha", ["virtual_ip_address"], "enable_k8s_ha")
    ]

    for config_name, mandatory_fields, enable_key in ha_configs:
        ha_data = data.get(config_name)
        if ha_data:
            ha_data = ha_data[0] if isinstance(ha_data, list) else ha_data
            validate_ha_config(ha_data, mandatory_fields, errors, config_name,
                                os.path.dirname(input_file_path),
                                all_service_tags, ha_node_vip_list)
        else:
            logger.warning(f"Configuration for {config_name} not found.")

    return errors
