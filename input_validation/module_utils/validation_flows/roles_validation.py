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
import validation_utils
import config
import en_us_validation_msg

file_names = config.files
create_error_msg = validation_utils.create_error_msg
create_file_path = validation_utils.create_file_path

def validate_roles_config(input_file_path, data, logger, module, omnia_base_dir, project_name):
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
    empty_parent_roles = {'login', 'compiler', 'service', 'kube_control_plane', 'etcd', 'slurm_control_plane', 'slurm_dbd', 'auth_server'}

    errors = []

    # Catch any empty config files or malformed config files
    if not data:
        errors.append(create_error_msg("config_roles.yml,", None, "EMPTY roles_config.yml"))
    else:
        try:
            roles = data[ROLES]
        except:
            errors.append(create_error_msg(ROLES, None, en_us_validation_msg.no_roles_msg))
        try:
            groups = data[GROUPS]
        except:
            errors.append(create_error_msg(GROUPS, None, en_us_validation_msg.no_groups_msg))
    if errors:
        return errors

    if groups:
        groups_used = set(list(groups.keys()))

    # Check for at least 1 group
    # Check for at least 1 role
     # Check to make sure there are not more than 100 roles
    if not groups:
        errors.append(create_error_msg(GROUPS, f'Current number of groups is 0:', en_us_validation_msg.min_number_of_groups_msg))
    if not roles:
        errors.append(create_error_msg(ROLES, f'Current number of roles is 0:', en_us_validation_msg.min_number_of_roles_msg))
    if roles and len(roles) > MAX_ROLES:
        errors.append(create_error_msg(ROLES, f'Current number of roles is {str(len(roles))}:', en_us_validation_msg.max_number_of_roles_msg))

    if len(errors) <= 0:
        # List of groups which need to have their resource_mgr_id set
        set_resource_mgr_id = set()

        switch_ip_mapping = {}
        switch_ip_port_mapping = {}
        static_range_mapping = {}
        # # Check if the bmc_network is defined
        # bmc_network_defined = check_bmc_network(input_file_path, logger, module, omnia_base_dir, project_name)

        service_role_defined = False
        if validation_utils.key_value_exists(roles, NAME, "service"):
            service_role_defined = True

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
                        # If parent is not empty and group is associated with login, compiler, service, kube_control_plane, or slurm_control_plane
                        errors.append(create_error_msg(group, f'Group {group} should not have parent defined.', en_us_validation_msg.parent_service_node_msg))
                    if not service_role_defined and (role[NAME] == K8WORKER or role[NAME] == SLURMWORKER or role[NAME] == DEFAULT):
                        # If a service role is not present, the parent is not empty and the group is associated with worker or default roles.
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

# def check_bmc_network(input_file_path, logger, module, omnia_base_dir, project_name) -> bool:
    # """
    # Check if the BMC network is defined in the given input file.

    # Returns:
    #     bool: True if the BMC network's nic_name and netmask_bits are defined, False otherwise.
    # """
#     admin_bmc_networks = common_validation.get_admin_bmc_networks(input_file_path, logger, module, omnia_base_dir, project_name)
#     bmc_network_defined = admin_bmc_networks["bmc_network"].get("nic_name", None) != None and admin_bmc_networks["bmc_network"].get("netmask_bits", None) != None

#     return bmc_network_defined
