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

import ipaddress
import json
from ansible.module_utils.input_validation.common_utils import validation_utils
from ansible.module_utils.input_validation.common_utils import config
from ansible.module_utils.input_validation.common_utils import en_us_validation_msg

file_names = config.files
create_error_msg = validation_utils.create_error_msg
create_file_path = validation_utils.create_file_path
contains_software = validation_utils.contains_software
check_mandatory_fields = validation_utils.check_mandatory_fields


def get_roles_config_json(input_file_path, logger, module, omnia_base_dir, module_utils_base, project_name):
    roles_config_file_path = create_file_path(input_file_path, file_names["roles_config"])
    roles_config_json = validation_utils.load_yaml_as_json(roles_config_file_path, omnia_base_dir, project_name, logger, module)
    
    return roles_config_json

def check_and_validate_ha_role_in_roles_config(errors, roles_config_json, ha_role):
    
    # Get groups and roles
    groups_configured = roles_config_json.get('Groups',{})
    roles_configured = roles_config_json.get('Roles',[])

    # Search for HA role and validate its groups
    ha_role_entry = next((role for role in roles_configured if role.get('name') == ha_role), None)

    if ha_role_entry:
        missing_groups = [g for g in ha_role_entry.get('groups', []) if g not in groups_configured]
        for group in missing_groups:
            errors.append(create_error_msg(f"group: '{group}' associated for role", ha_role, en_us_validation_msg.group_not_found))
    else:
        errors.append(create_error_msg("role", ha_role, en_us_validation_msg.role_node_found))


def get_admin_static_dynamic_ranges(network_spec_json):
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

def get_admin_netmaskbits(network_spec_json):
    for network in network_spec_json["Networks"]:
        for key, value in network.items():
            if key == "admin_network":
                netmaskbits = value.get("netmask_bits", "N/A")
    return netmaskbits

def get_primary_oim_admin_ip(network_spec_json):
    for network in network_spec_json["Networks"]:
        for key, value in network.items():
            if key == "admin_network":
                oim_admin_ip = value.get("primary_oim_admin_ip", "N/A")
    return oim_admin_ip

def is_service_tag_present(service_tags_list, input_service_tag):
    return input_service_tag in service_tags_list

def validate_service_tag_presence(errors, config_type, all_service_tags, active_node_service_tag, passive_nodes):
    #validate_active_node_uniqueness
    if active_node_service_tag and is_service_tag_present(all_service_tags, active_node_service_tag):
        errors.append(create_error_msg(f"{config_type}", active_node_service_tag, en_us_validation_msg.duplicate_active_node_service_tag))

    #validate passive_node_uniqueness
    for node_service_tags in passive_nodes:
        for service_tag in node_service_tags.get('node_service_tags', []):
            if service_tag == active_node_service_tag or is_service_tag_present(all_service_tags, service_tag):
                errors.append(create_error_msg(f"{config_type}", service_tag, en_us_validation_msg.duplicate_passive_node_service_tag))

def validate_vip_address(errors, config_type, vip_address, service_node_vip, admin_network, admin_netmaskbits, oim_admin_ip):

    # validate if the same virtual_ip_address is already use
    if vip_address in service_node_vip:
        errors.append(create_error_msg(f"{config_type} virtual_ip_address:", vip_address, en_us_validation_msg.duplicate_virtual_ip))
    else:
        # virtual_ip_address is mutually exclusive with admin static and dynamic ranges                 
        vip_within_static_range = validation_utils.is_ip_within_range(admin_network["static_range"], vip_address)
        vip_within_dynamic_range = validation_utils.is_ip_within_range(admin_network["dynamic_range"], vip_address)

        if vip_within_static_range or  vip_within_dynamic_range:
            errors.append(create_error_msg(f"{config_type} virtual_ip_address", vip_address, en_us_validation_msg.virtual_ip_not_valid))

        # validate virtual_ip_address is in the admin subnet
        if not validation_utils.is_ip_in_subnet(oim_admin_ip, admin_netmaskbits, vip_address):
            errors.append(create_error_msg(f"{config_type} virtual_ip_address", vip_address, en_us_validation_msg.virtual_ip_not_in_admin_subnet))

def validate_service_node_ha(errors, config_type, ha_data, network_spec_data, all_service_tags, ha_node_vip_list):
    active_node_service_tag = ha_data.get('active_node_service_tag')
    passive_nodes = ha_data.get('passive_nodes', [])
    vip_address = ha_data.get('virtual_ip_address')

    #get network_spec data
    admin_network = network_spec_data['admin_network']
    admin_netmaskbits = network_spec_data['admin_netmaskbits']
    oim_admin_ip = network_spec_data['oim_admin_ip']

    # validate active_node_service_tag and passive_node_service_tag
    validate_service_tag_presence(errors, config_type, all_service_tags, active_node_service_tag, passive_nodes)

    # validate if duplicate virtual ip address is present
    if vip_address:
        validate_vip_address(errors, config_type, vip_address, ha_node_vip_list, admin_network, admin_netmaskbits, oim_admin_ip)

# Dispatch table maps config_type to validation handler
ha_validation = {
    "service_node_ha": validate_service_node_ha,
    # Add more config_type functions here as needed
    #"oim_ha":validation_oim_ha,
    #"slurm_head_node_ha":validation_slurm_head_node_ha
    #"k8s_head_node_ha":validation_k8s_head_node_ha
}

def validate_high_availability_config(input_file_path, data, logger, module, omnia_base_dir, module_utils_base, project_name):
    errors = []
    ha_node_vip_list = []
    all_service_tags = set()
    network_spec_file_path = create_file_path(input_file_path, file_names["network_spec"])
    network_spec_json = validation_utils.load_yaml_as_json(network_spec_file_path, omnia_base_dir, project_name, logger, module)

    network_spec_info = {
        "admin_network": get_admin_static_dynamic_ranges(network_spec_json),
        "admin_netmaskbits": get_admin_netmaskbits(network_spec_json),
        "oim_admin_ip": get_primary_oim_admin_ip(network_spec_json)
    }
    
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
                ha_validation[config_type](errors, config_type, ha_data, network_spec_info, all_service_tags, ha_node_vip_list)

            # append all the active and passive node service tags to a set
            all_service_tags.add(ha_data['active_node_service_tag'])
            for node_service_tag in ha_data.get('passive_nodes', []):
                all_service_tags.update(node_service_tag.get('node_service_tags', []))

            ha_node_vip_list.append(ha_data['virtual_ip_address'])

        except KeyError as e:
            logger.error(f"Missing key in HA data: {e}")
            errors.append(f"Missing key in HA data: {e}")

    ha_configs = [
        ("oim_ha", ["virtual_ip_address", "active_node_service_tag", "passive_nodes"]),
        ("service_node_ha", ["service_nodes"]),
        ("slurm_head_node_ha", ["virtual_ip_address", "active_node_service_tags", "passive_nodes"]),
        ("k8s_head_node_ha", ["virtual_ip_address", "active_node_service_tags"])
    ]

    # load roles_config for L2 validations
    roles_config_json = get_roles_config_json(input_file_path, logger, module, omnia_base_dir, module_utils_base, project_name)

    for config_name, mandatory_fields in ha_configs:
        ha_data = data.get(config_name)
        if ha_data:
            ha_data = ha_data[0] if isinstance(ha_data, list) else ha_data
            enable_key = f'enable_{config_name.split("_")[0]}_ha'
            if ha_data.get(enable_key):
                if config_name == "service_node_ha":
                    ha_role = "service_node" #expected role to be defined in roles_config
                    check_and_validate_ha_role_in_roles_config(errors, roles_config_json, ha_role)
                    for service_node in ha_data['service_nodes']:
                        validate_ha_config(service_node, ["virtual_ip_address", "active_node_service_tag", "passive_nodes"], errors, config_type=config_name)
                else:
                    validate_ha_config(ha_data, mandatory_fields, errors, config_type=config_name)
        else:
            logger.warning(f"Configuration for {config_name} not found.")

    return errors