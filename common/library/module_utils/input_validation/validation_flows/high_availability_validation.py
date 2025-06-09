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

from ansible.module_utils.input_validation.common_utils import validation_utils
from ansible.module_utils.input_validation.common_utils import config
from ansible.module_utils.input_validation.common_utils import en_us_validation_msg

file_names = config.files
create_error_msg = validation_utils.create_error_msg
create_file_path = validation_utils.create_file_path
contains_software = validation_utils.contains_software
check_mandatory_fields = validation_utils.check_mandatory_fields


def get_roles_config_json(
    input_file_path,
    logger,
    module,
    omnia_base_dir,
    project_name
):
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
    roles_config_file_path = create_file_path(input_file_path, file_names["roles_config"])
    roles_config_json = validation_utils.load_yaml_as_json(
        roles_config_file_path, omnia_base_dir, project_name, logger, module
    )

    return roles_config_json

def check_and_validate_ha_role_in_roles_config(
    errors,
    roles_config_json,
    ha_role
):
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
    groups_configured = roles_config_json.get('Groups',{})
    roles_configured = roles_config_json.get('Roles',[])

    # Search for HA role and validate its groups
    ha_role_entry = next((role for role in roles_configured if role.get('name') == ha_role), None)

    if ha_role_entry:
        missing_groups = [g for g in ha_role_entry.get('groups', []) if g not in groups_configured]
        for group in missing_groups:
            errors.append(create_error_msg(
                f"group: '{group}' associated for role",
                ha_role,
                en_us_validation_msg.group_not_found
                ))
    else:
        errors.append(create_error_msg("role", ha_role, en_us_validation_msg.role_node_found))


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
    for network in network_spec_json["Networks"]:
        for key, value in network.items():
            if key == "admin_network":
                admin_uncorrelated_node_start_ip = value.get("admin_uncorrelated_node_start_ip", "N/A")
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

def is_service_tag_present(
    service_tags_list,
    input_service_tag
):
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
    errors,
    config_type,
    all_service_tags,
    active_node_service_tag,
    passive_nodes
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
    #validate_active_node_uniqueness
    if (
        active_node_service_tag
        and is_service_tag_present(all_service_tags, active_node_service_tag)
    ):
        errors.append(create_error_msg(
            f"{config_type}",
            active_node_service_tag,
            en_us_validation_msg.duplicate_active_node_service_tag
        ))

    #validate passive_node_uniqueness
    for node_service_tags in passive_nodes:
        for service_tag in node_service_tags.get('node_service_tags', []):
            if (
                service_tag == active_node_service_tag
                or is_service_tag_present(all_service_tags, service_tag)
            ):
                errors.append(create_error_msg(
                    f"{config_type}",
                    service_tag,
                    en_us_validation_msg.duplicate_passive_node_service_tag
                ))

def validate_vip_address(
    errors,
    config_type,
    vip_address,
    service_node_vip,
    admin_network,
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
	- service_node_vip (list): A list of existing service node VIPs.
	- admin_network (dict): A dictionary containing admin network configuration.
	- admin_netmaskbits (str): The netmask bits value of the admin network.
	- oim_admin_ip (str): The IP address of the OIM admin interface.

	Returns:
	- None: The function does not return any value, it only appends error messages to the errors list.
	"""

    # validate if the same virtual_ip_address is already use
    if vip_address in service_node_vip:
        errors.append(create_error_msg(
            f"{config_type} virtual_ip_address:",
            vip_address,
            en_us_validation_msg.duplicate_virtual_ip
        ))
    else:
        # virtual_ip_address is mutually exclusive with admin static and dynamic ranges
        vip_within_static_range = validation_utils.is_ip_within_range(
            admin_network["static_range"],
            vip_address
        )
        vip_within_dynamic_range = validation_utils.is_ip_within_range(
            admin_network["dynamic_range"],
            vip_address
        )

        if vip_within_static_range or  vip_within_dynamic_range:
            errors.append(create_error_msg(
                f"{config_type} virtual_ip_address",
                vip_address,
                en_us_validation_msg.virtual_ip_not_valid
            ))

        # validate virtual_ip_address is in the admin subnet
        if not validation_utils.is_ip_in_subnet(oim_admin_ip, admin_netmaskbits, vip_address):
            errors.append(create_error_msg(
                f"{config_type} virtual_ip_address",
                vip_address,
                en_us_validation_msg.virtual_ip_not_in_admin_subnet
            ))

def validate_k8s_head_node_ha(
    errors, config_type,
    ha_data, network_spec_data,
    roles_config_json,
    all_service_tags,
    ha_node_vip_list):
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
    #get network_spec data
    admin_network = network_spec_data['admin_network']
    admin_static_range = admin_network.get("static_range", "N/A")
    admin_dynamic_range = admin_network.get("dynamic_range","N/A")
    oim_admin_ip = network_spec_data['oim_admin_ip']
    does_overlap=[]
    external_loadbalancer_ip = ha_data.get("external_loadbalancer_ip")
    active_node_service_tags = ha_data.get('active_node_service_tags')
    # validate active_node_service_tag and passive_node_service_tag
    all_service_tags_set = set(all_service_tags)
    active_node_service_tags_set = set(active_node_service_tags)

    # Find the intersection
    common_tags = all_service_tags_set & active_node_service_tags_set

    # Optional: check if there are common values
    if common_tags:
        errors.append(
            create_error_msg(
                f"{config_type}",
                common_tags,
                en_us_validation_msg.duplicate_active_node_service_tag
            )
        )

    if external_loadbalancer_ip:
        ip_ranges = [admin_static_range, admin_dynamic_range, external_loadbalancer_ip]
        does_overlap, _ = validation_utils.check_overlap(ip_ranges)

    if does_overlap:
        errors.append(
                create_error_msg
                ("IP overlap -", None, en_us_validation_msg.ip_overlap_fail_msg))

def validate_service_node_ha(
    errors, config_type,
    ha_data, network_spec_data,
    _roles_config_json,
    all_service_tags,
    ha_node_vip_list
):
    """
    Validates the high availability configuration for a service node.

    Parameters:
    errors (list): A list to store error messages.
    config_type (str): The type of high availability configuration.
    ha_data (dict): A dictionary containing high availability data.
    network_spec_data (dict): A dictionary containing network specification data.
    _roles_config_json (dict): A dictionary containing roles configuration data.
    all_service_tags (list): A list of all service tags.
    ha_node_vip_list (list): A list of virtual IP addresses for high availability nodes.

    Returns:
    None
    """
    active_node_service_tag = ha_data.get('active_node_service_tag')
    passive_nodes = ha_data.get('passive_nodes', [])
    vip_address = ha_data.get('virtual_ip_address')

    #get network_spec data
    admin_network = network_spec_data['admin_network']
    admin_netmaskbits = network_spec_data['admin_netmaskbits']
    oim_admin_ip = network_spec_data['oim_admin_ip']

    # validate active_node_service_tag and passive_node_service_tag
    validate_service_tag_presence(
        errors,
        config_type,
        all_service_tags,
        active_node_service_tag,
        passive_nodes
    )

    # validate if duplicate virtual ip address is present
    if vip_address:
        validate_vip_address(errors,
            config_type,
            vip_address,
            ha_node_vip_list,
            admin_network,
            admin_netmaskbits,
            oim_admin_ip
        )

def validate_oim_ha(
    errors,
    config_type,
    ha_data,
    network_spec_data,
    roles_config_json,
    _all_service_tags,
    ha_node_vip_list
):
    """
    Validates the high availability configuration for a oim node.

    Parameters:
    errors (list): A list to store error messages.
    config_type (str): The type of high availability configuration.
    ha_data (dict): A dictionary containing high availability data.
    network_spec_data (dict): A dictionary containing network specification data.
    _roles_config_json (dict): A dictionary containing roles configuration data.
    all_service_tags (list): A list of all service tags.
    ha_node_vip_list (list): A list of virtual IP addresses for high availability nodes.

    Returns:
    None
    """
    admin_virtual_ip = ha_data.get('admin_virtual_ip_address', "")
    bmc_virtual_ip = ha_data.get('bmc_virtual_ip_address', "")

    admin_network = network_spec_data['admin_network']
    admin_netmaskbits = network_spec_data['admin_netmaskbits']
    oim_admin_ip = network_spec_data['oim_admin_ip']

    bmc_network = network_spec_data['bmc_network']

    if admin_virtual_ip:
        validate_vip_address(
            errors,
            config_type,
            admin_virtual_ip,
            ha_node_vip_list,
            admin_network,
            admin_netmaskbits,
            oim_admin_ip
        )

    if bmc_virtual_ip:
        roles_groups = roles_config_json.get("Groups", [])
        for _, group_data in roles_groups.items():
            static_range = group_data.get("bmc_details", {}).get("static_range", '')
            if static_range and bmc_virtual_ip:
                bmc_vip_conflict = validation_utils.is_ip_within_range(static_range, bmc_virtual_ip)
                if bmc_vip_conflict:
                    errors.append(create_error_msg(
                        f"{config_type} bmc_virtual_ip_address conflict with roles_config",
                        bmc_virtual_ip,
                        en_us_validation_msg.bmc_virtual_ip_not_valid
                    ))

        bmc_vip_conflict_dynamic = False
        bmc_vip_conflict_dynamic_conversion = False
        if (
            bmc_network["dynamic_range"]
            and bmc_network["dynamic_range"] != 'N/A'
            and bmc_virtual_ip
        ):
            bmc_vip_conflict_dynamic = validation_utils.is_ip_within_range(
                bmc_network["dynamic_range"],
                bmc_virtual_ip
            )

        if (
            bmc_network["dynamic_conversion_static_range"]
            and bmc_network["dynamic_conversion_static_range"] != 'N/A'
            and bmc_virtual_ip
        ):
            bmc_vip_conflict_dynamic_conversion = validation_utils.is_ip_within_range(
                bmc_network["dynamic_conversion_static_range"],
                bmc_virtual_ip
            )

        if bmc_vip_conflict_dynamic or bmc_vip_conflict_dynamic_conversion:
            errors.append(create_error_msg(
                f"{config_type} bmc_virtual_ip_address conflict with network_spec",
                bmc_virtual_ip,
                en_us_validation_msg.bmc_virtual_ip_not_valid
            ))

# Dispatch table maps config_type to validation handler
ha_validation = {
    "service_node_ha": validate_service_node_ha,
    # Add more config_type functions here as needed
    "oim_ha": validate_oim_ha,
    #"slurm_head_node_ha":validation_slurm_head_node_ha
    "k8s_head_node_ha":validate_k8s_head_node_ha
}

def validate_high_availability_config(
    input_file_path,
    data,
    logger,
    module,
    omnia_base_dir,
    _module_utils_base,
    project_name
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
    network_spec_file_path = create_file_path(input_file_path, file_names["network_spec"])
    network_spec_json = validation_utils.load_yaml_as_json(
        network_spec_file_path,
        omnia_base_dir,
        project_name,
        logger,
        module
    )

    # load roles_config for L2 validations
    roles_config_json = get_roles_config_json(
        input_file_path,
        logger,
        module,
        omnia_base_dir,
        project_name
    )

    network_spec_info = {
        "admin_network": get_admin_static_dynamic_ranges(network_spec_json),
        "admin_nic_name": get_admin_nic_name(network_spec_json),
        "bmc_network": get_bmc_network(network_spec_json),
        "bmc_nic_name": get_bmc_nic_name(network_spec_json),
        "admin_netmaskbits": get_admin_netmaskbits(network_spec_json),
        "admin_uncorrelated_node_start_ip": get_admin_uncorrelated_node_start_ip(network_spec_json),
        "oim_admin_ip": get_primary_oim_admin_ip(network_spec_json)
    }

    # pylint: disable=too-many-branches
    def validate_ha_config(ha_data, mandatory_fields, errors, config_type=None):
        try:
            check_mandatory_fields(mandatory_fields, ha_data, errors)

            # Special handling for OIM HA
            if config_type == "oim_ha":
                # Validate passive nodes with node_service_tags
                if 'passive_nodes' in ha_data:
                    for node in ha_data['passive_nodes']:
                        check_mandatory_fields(["node_service_tags"], node, errors)
            # Standard passive nodes validation for other HA types
            elif 'passive_nodes' in ha_data:
                for passive_node in ha_data['passive_nodes']:
                    check_mandatory_fields(["node_service_tags"], passive_node, errors)

            if config_type in ha_validation:
                ha_validation[config_type](errors,
                    config_type,
                    ha_data,
                    network_spec_info,
                    roles_config_json,
                    all_service_tags,
                    ha_node_vip_list
                )

            # append all the active and passive node service tags to a set
            if 'active_node_service_tag' in ha_data:
                all_service_tags.add(ha_data['active_node_service_tag'])
            elif 'active_node_service_tags' in ha_data:
                all_service_tags.update(ha_data.get('active_node_service_tags',[]))

            if 'passive_nodes' in ha_data:
                for node_service_tag in ha_data.get('passive_nodes', []):
                    all_service_tags.update(node_service_tag.get('node_service_tags', []))

            if 'virtual_ip_address' in ha_data:
                ha_node_vip_list.append(ha_data['virtual_ip_address'])
            elif 'admin_virtual_ip_address' in ha_data:
                ha_node_vip_list.append(ha_data['admin_virtual_ip_address'])
            elif 'bmc_virtual_ip_address' in ha_data:
                ha_node_vip_list.append(ha_data['bmc_virtual_ip_address'])

        except KeyError as e:
            logger.error(f"Missing key in HA data: {e}")
            errors.append(f"Missing key in HA data: {e}")

    ha_configs = [
        ("oim_ha", ["admin_virtual_ip_address", "active_node_service_tag", "passive_nodes"]),
        ("service_node_ha", ["service_nodes"]),
        ("slurm_head_node_ha", ["virtual_ip_address", "active_node_service_tag", "passive_nodes"]),
        ("k8s_head_node_ha", ["virtual_ip_address", "active_node_service_tags"])
    ]

    for config_name, mandatory_fields in ha_configs:
        ha_data = data.get(config_name)
        if ha_data:
            ha_data = ha_data[0] if isinstance(ha_data, list) else ha_data
            enable_key = f'enable_{config_name.split("_", maxsplit=1)[0]}_ha'
            if ha_data.get(enable_key):
                if config_name == "oim_ha":
                    ha_role = "oim_ha_node" #expected role to be defined in roles_config
                    check_and_validate_ha_role_in_roles_config(errors, roles_config_json, ha_role)
                    validate_ha_config(ha_data, mandatory_fields, errors, config_type=config_name)
                elif config_name == "service_node_ha":
                    ha_role = "service_node" #expected role to be defined in roles_config
                    check_and_validate_ha_role_in_roles_config(errors, roles_config_json, ha_role)
                    for service_node in ha_data['service_nodes']:
                        validate_ha_config(
                            service_node,
                            [
                                "virtual_ip_address",
                                "active_node_service_tag",
                                "passive_nodes"
                            ],
                            errors,
                            config_type=config_name
                        )
                else:
                    validate_ha_config(ha_data, mandatory_fields, errors, config_type=config_name)
        else:
            logger.warning(f"Configuration for {config_name} not found.")

    return errors
