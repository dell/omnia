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
import ipaddress
from ansible.module_utils.input_validation.common_utils import validation_utils
from ansible.module_utils.input_validation.common_utils import config
from ansible.module_utils.input_validation.common_utils import en_us_validation_msg

file_names = config.files
create_error_msg = validation_utils.create_error_msg
create_file_path = validation_utils.create_file_path

def check_duplicate_groups(yaml_content):
    """Check for duplicate group names in YAML content."""
    seen_groups = set()
    lines = yaml_content.split('\n')
    for line in lines:
        if line.strip().startswith('grp'):
            group_name = line.split(':')[0].strip()
            if group_name in seen_groups:
                raise ValueError(f"Duplicate group name found: {group_name}")
            seen_groups.add(group_name)

def validate_basic_structure(data, roles, groups):
    """
    Validates the basic structure of roles and groups in the config.

    Args:
        data (dict): The parsed YAML data

    Returns:
        list: List of validation errors
    """
    errors = []

    if roles is None:
        errors.append(create_error_msg("Roles", None, en_us_validation_msg.no_roles_msg))
    elif not isinstance(roles, list):
        errors.append(create_error_msg("Roles", None, en_us_validation_msg.invalid_attributes_role_msg))

    if groups is None:
        errors.append(create_error_msg("Groups", None, en_us_validation_msg.no_groups_msg))

    return errors

def validate_group_duplicates(input_file_path):
    """
    Checks for duplicate group names in the config file.

    Args:
        input_file_path (str): Path to the config file

    Returns:
        list: List of validation errors
    """
    errors = []

    try:
        with open(input_file_path, 'r') as f:
            yaml_content = f.read()
        check_duplicate_groups(yaml_content)
    except ValueError as e:
        errors.append(create_error_msg("Groups", str(e), en_us_validation_msg.duplicate_group_name_msg))
    except Exception as e:
        errors.append(create_error_msg("File", f"Error reading {input_file_path}: {str(e)}",
            "Failed to validate group duplicates"))

    return errors

def validate_layer_group_separation(logger, roles):
    """
    Validates that groups are not shared between frontend and compute layers.

    Args:
        roles (list): List of role dictionaries from the config

    Returns:
        list: List of validation errors
    """
    errors = []

    # Define layer roles
    frontend_roles = {
        "service_node", "login", "auth_server", "compiler_node",
        "kube_control_plane", "etcd", "slurm_control_node", "slurm_dbd"
    }
    compute_roles = {"kube_node", "slurm_node", "default"}

    # Single pass through roles to build mappings and check for same group usage
    group_layer_mapping = {}  # {group: {"frontend": [roles], "compute": [roles]}}

    for role in roles:
        role_name = role.get("name", "")
        role_groups = role.get("groups", [])

        # Determine which layer this role belongs to
        if role_name in frontend_roles:
            layer = "frontend"
        elif role_name in compute_roles:
            layer = "compute"
        else:
            continue

        # Process each group for this role
        for group in role_groups:
            if group not in group_layer_mapping:
                group_layer_mapping[group] = {"frontend": [], "compute": []}
            group_layer_mapping[group][layer].append(role_name)

    # Check for violations and build error messages
    for group, layers in group_layer_mapping.items():
        if layers["frontend"] and layers["compute"]:
            frontend_layer = ', '.join(sorted(layers['frontend']))
            compute_layer = ', '.join(sorted(layers['compute']))
            errors.append(create_error_msg("Roles", None,
                en_us_validation_msg.duplicate_group_name_in_layers_msg.format(group,
                    frontend_layer, compute_layer)))

    return errors

def validate_service_node_in_software_config(input_file_path):
    """
    verifies service_node entry present in sofwate config.json

    Returns: 
        True if service_node entry is present
        False if no entry
    """    
    #verify service_node  with sofwate config json
    software_config_file_path = create_file_path(input_file_path, file_names["software_config"])
    software_config_json = json.load(open(software_config_file_path, "r"))
    softwares = software_config_json["softwares"]
    if validation_utils.contains_software(softwares, "service_node"):
        return True
    return False

def validate_roles_config(input_file_path, data, logger, module, omnia_base_dir, module_utils_base, project_name):
    """
    Validates the L2 logic of the roles_config.yaml file.

    Returns:
        list: A list of errors.
    """
    NAME = "name"
    ROLES = "Roles"
    GROUPS = "Groups"
    ROLE_GROUPS = "groups"
    SLURMWORKER = "slurm_node"
    K8WORKER = "kube_node"
    DEFAULT = "default"
    SWITCH_DETAILS = "switch_details"
    IP = "ip"
    PORTS = "ports"
    PARENT = "parent"
    BMC_DETAILS = "bmc_details"
    STATIC_RANGE = "static_range"
    RESOURCE_MGR_ID = "resource_mgr_id"
    ROLES_PER_GROUP = 5
    MAX_ROLES = 100

    roles_per_group = {}
    empty_parent_roles = {'login', 'compiler_node', 'service_node', 'kube_control_plane', 'etcd', 'slurm_control_plane', 'slurm_dbd', 'auth_server'}

    errors = []
    # Empty file validation
    if not data:
        errors.append(create_error_msg("roles_config.yml,", None, en_us_validation_msg.empty_or_syntax_error_roles_config_msg))
        return errors

    roles = data.get(ROLES, [])
    groups = data.get(GROUPS, [])

    # Validate basic structure
    errors.extend(validate_basic_structure(data, roles, groups))
    if errors:
        return errors

    # Check for duplicate groups if groups section exists
    if groups is not None:
        errors.extend(validate_group_duplicates(input_file_path))
        if errors:
            return errors

    # Validate same group usage among layers
    if roles is not None:
        errors.extend(validate_layer_group_separation(logger, roles))
        if errors:
            return errors

    # List of groups used in roles
    if groups:
        groups_used = set(groups.keys())

    # Check for minimum required sections
    if not groups:
        errors.append(create_error_msg(GROUPS, 'Current number of groups is 0:', en_us_validation_msg.min_number_of_groups_msg))
    if not roles:
        errors.append(create_error_msg(ROLES, 'Current number of roles is 0:', en_us_validation_msg.min_number_of_roles_msg))
    # Check maximum roles limit
    if roles and len(roles) > MAX_ROLES:
        errors.append(create_error_msg(ROLES, f'Current number of roles is {len(roles)}:', en_us_validation_msg.max_number_of_roles_msg))

    # Role Service_node is defined in roles_config.yml,
    # verify service_node entry present in sofwate_config.json
    # If no entry is present, then fail the input validator
    service_role_defined = False
    if validation_utils.key_value_exists(roles, NAME, "service_node"):
        service_role_defined = True
        if not validate_service_node_in_software_config(input_file_path):
            errors.append(create_error_msg("software_config.yml", None, \
                                       en_us_validation_msg.SERVICE_NODE_ENTRY_MISSING_ROLES_CONFIG_MSG))

    if len(errors) <= 0:
        # List of groups which need to have their resource_mgr_id set
        set_resource_mgr_id = set()

        switch_ip_mapping = {}
        switch_ip_port_mapping = {}
        static_range_mapping = {}
        # # Check if the bmc_network is defined
        # bmc_network_defined = check_bmc_network(input_file_path, logger, module, omnia_base_dir, project_name)

        for role in roles:
            # Check role-group association, all roles must have a group
            if role[ROLE_GROUPS] and (None in role[ROLE_GROUPS] or not role[ROLE_GROUPS]):
                errors.append(role[NAME], create_error_msg(None, f'Role {role[NAME]} must be associated with a group:', en_us_validation_msg.min_number_of_groups_msg))
            if role[NAME] == SLURMWORKER or role[NAME] == K8WORKER:
                for group in role[ROLE_GROUPS]:
                    set_resource_mgr_id.add(group)

            if not role[ROLE_GROUPS]:
                role[ROLE_GROUPS] = []
            # Validate each group and its configs under each role
            for group in role[ROLE_GROUPS]:
                if group in groups_used: groups_used.remove(group)
                roles_per_group[group] = roles_per_group.get(group, 0) + 1
                if roles_per_group[group] > ROLES_PER_GROUP:
                    errors.append(create_error_msg(role[NAME], f'Current number of roles for {group} is {str(roles_per_group[group])}:', en_us_validation_msg.max_number_of_roles_per_group_msg))
                if group in groups:
                    # Validate parent field is empty for specific role cases
                    if role[NAME] in empty_parent_roles and not validation_utils.is_string_empty(groups[group].get(PARENT, None)):
                        # If parent is not empty and group is associated with login, compiler_node, service_node, kube_control_plane, or slurm_control_plane
                        errors.append(create_error_msg(group, f'Group {group} should not have parent defined.', en_us_validation_msg.parent_service_node_msg))
                    if not service_role_defined and (role[NAME] == K8WORKER or role[NAME] == SLURMWORKER or role[NAME] == DEFAULT):
                        # If a service_node role is not present, the parent is not empty and the group is associated with worker or default roles.
                        if not validation_utils.is_string_empty(groups[group].get(PARENT, None)):
                            errors.append(create_error_msg(group, f'Group {group} should not have parent defined.', en_us_validation_msg.parent_service_role_msg))
                    elif not service_role_defined and not validation_utils.is_string_empty(groups[group].get(PARENT, None)):
                        errors.append(create_error_msg(group, f'Group {group} parent is provided.', en_us_validation_msg.parent_service_role_dne_msg))
                else:
                    # Error log for if a group under a role does not exist
                    errors.append(create_error_msg(group, f'Group {group} does not exist.', en_us_validation_msg.grp_exist_msg))

        for group in groups.keys():

            switch_ip_provided = not validation_utils.is_string_empty(groups[group].get(SWITCH_DETAILS, {}).get(IP, None))
            switch_ports_provided = not validation_utils.is_string_empty(groups[group].get(SWITCH_DETAILS, {}).get(PORTS, None))
            bmc_static_range_provided = not validation_utils.is_string_empty(groups[group].get(BMC_DETAILS, {}).get(STATIC_RANGE, None))
            if group in groups_used:
                errors.append(create_error_msg(group, f'Group {group} is not associated with a role.', en_us_validation_msg.grp_role_msg))
            if switch_ip_provided and switch_ports_provided:
                switch_ip = groups[group][SWITCH_DETAILS][IP]
                try:
                    ipaddress.IPv4Address(switch_ip)
                except Exception as e:
                    errors.append(create_error_msg(group, f'Group {group} switch IP is invalid:', en_us_validation_msg.invalid_switch_ip_msg))
                if switch_ip in switch_ip_mapping:
                    # Check for any switch IP port overlap
                    if validation_utils.check_port_overlap(switch_ip_port_mapping.get(switch_ip, "") + "," + groups[group][SWITCH_DETAILS].get(PORTS, "")):
                        errors.append(create_error_msg(group, f'Group {group} has duplicate ports for switch IP {switch_ip}, this switch IP is shared with the following groups: {switch_ip_mapping[switch_ip]}.', en_us_validation_msg.duplicate_switch_ip_port_msg))
                if not validation_utils.check_port_ranges(groups[group][SWITCH_DETAILS].get(PORTS, "")):
                    errors.append(create_error_msg(group, f'Group {group} switch port range(s) are invalid, start > end:', en_us_validation_msg.invalid_switch_ports_msg))
                switch_ip_mapping.setdefault(switch_ip, []).append(group)
                switch_ip_port_mapping[switch_ip] = switch_ip_port_mapping.get(switch_ip, "") + "," + groups[group][SWITCH_DETAILS].get(PORTS, "")
            if ((switch_ip_provided and not switch_ports_provided) or (not switch_ip_provided and switch_ports_provided)):
                errors.append(create_error_msg(group, f'Group {group} switch details are incomplete:', en_us_validation_msg.switch_details_incomplete_msg))
            if ((switch_ip_provided and switch_ports_provided) and not bmc_static_range_provided):
                errors.append(create_error_msg(group, f'Group {group} switch details provided:', en_us_validation_msg.switch_details_no_bmc_details_msg))

            # Validate bmc details for each group
            if not validation_utils.is_string_empty(groups[group].get(BMC_DETAILS, {}).get(STATIC_RANGE, None)):
                # # Check if bmc details are defined, but enable_switch_based is true or the bmc_network is not defined
                # if enable_switch_based or not bmc_network_defined:
                #     errors.append(create_error_msg(group, "Group " + group + " BMC static range invalid use case.", en_us_validation_msg.bmc_static_range_msg))
                # Validate the static range is properly defined
                if not validation_utils.validate_ipv4_range(groups[group].get(BMC_DETAILS, {}).get(STATIC_RANGE, "")):
                    errors.append(create_error_msg(group, f'Group {group} BMC static range is invalid.', en_us_validation_msg.bmc_static_range_invalid_msg))
                elif group not in static_range_mapping:
                # A valid static range was provided, now a check is performed to ensure static ranges do not overlap
                    static_range = groups[group][BMC_DETAILS][STATIC_RANGE]
                    grp_overlaps = validation_utils.check_bmc_static_range_overlap(static_range, static_range_mapping)
                    if len(grp_overlaps) > 0:
                        errors.append(create_error_msg(group, f'Static range {static_range} overlaps with the following group(s): {grp_overlaps}.', en_us_validation_msg.overlapping_static_range))
                    static_range_mapping[group] = static_range

            # Validate resource_mgr_id is set for groups that belong to kube_node or slurm_node roles
            if group in set_resource_mgr_id and validation_utils.is_string_empty(groups[group].get(RESOURCE_MGR_ID, None)):
                errors.append(create_error_msg(group, f'Group {group} is missing resource_mgr_id.', en_us_validation_msg.resource_mgr_id_msg))
            elif group not in set_resource_mgr_id and not validation_utils.is_string_empty(groups[group].get(RESOURCE_MGR_ID, None)):
            # Validate resource_mgr_id is not set for groups that do not belong to kube_node or slurm_node roles
                errors.append(create_error_msg(group, f'Group {group} should not have the resource_mgr_id set.', en_us_validation_msg.resource_mgr_id_msg))

    return errors
