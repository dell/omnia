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

# pylint: disable=import-error,no-name-in-module,unused-argument,too-many-locals,too-many-branches
"""
This module contains functions for validating roles configuration.
"""

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
    lines = yaml_content.split("\n")
    for line in lines:
        if line.strip().startswith("grp"):
            group_name = line.split(":")[0].strip()
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
        errors.append(create_error_msg("Roles", None, en_us_validation_msg.NO_ROLES_MSG))
    elif not isinstance(roles, list):
        errors.append(
            create_error_msg("Roles", None, en_us_validation_msg.INVALID_ATTRIBUTES_ROLE_MSG)
        )

    if groups is None:
        errors.append(create_error_msg("Groups", None, en_us_validation_msg.NO_GROUPS_MSG))

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
        with open(input_file_path, "r") as f:
            yaml_content = f.read()
        check_duplicate_groups(yaml_content)
    except ValueError as e:
        errors.append(
            create_error_msg("Groups", str(e), en_us_validation_msg.DUPLICATE_GROUP_NAME_MSG)
        )
    except Exception as e:
        errors.append(
            create_error_msg(
                "File",
                f"Error reading {input_file_path}: {str(e)}",
                "Failed to validate group duplicates"
            )
        )

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
        "service_node",
        "login",
        "auth_server",
        "compiler_node",
        "kube_control_plane",
        "etcd",
        "slurm_control_node",
        "slurm_dbd",
        "service_kube_control_plane",
        "service_etcd"
    }
    compute_roles = {"service_kube_node", "kube_node", "slurm_node", "default"}

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
            frontend_layer = ", ".join(sorted(layers["frontend"]))
            compute_layer = ", ".join(sorted(layers["compute"]))
            errors.append(
                create_error_msg(
                    "Roles",
                     group,
                    en_us_validation_msg.DUPLICATE_GROUP_NAME_IN_LAYERS_MSG.format(
                        group, frontend_layer, compute_layer
                    ),
                )
            )

    return errors

def validate_group_role_separation(logger, roles):
    """
    Validates that groups are not shared between service cluster roles and corresponding Kubernetes roles.
    """
    errors = []

    service_cluster_roles = {"service_kube_control_plane", "service_etcd", "service_kube_node"}
    k8s_cluster_roles = {"kube_control_plane", "etcd", "kube_node"}

    # Collect groups for each role
    role_groups = {}
    for role in roles:
        role_name = role.get("name", "")
        role_groups[role_name] = set(role.get("groups", []))

    # Cross-check all service roles against all k8s roles
    for service_role in service_cluster_roles:
        for k8s_role in k8s_cluster_roles:
            if service_role in role_groups and k8s_role in role_groups:
                shared = role_groups[service_role] & role_groups[k8s_role]
                if shared:
                    group_str = ', '.join(shared)
                    msg = f"Group is shared between {service_role} and {k8s_role} roles."
                    errors.append(create_error_msg("Roles", group_str, msg))

    return errors

def validate_service_node_in_software_config(input_file_path):
    """
    verifies service_node entry present in sofwate config.json

    Returns:
        True if service_node entry is present
        False if no entry
    """

    # verify service_node  with sofwate config json
    software_config_file_path = create_file_path(input_file_path, file_names["software_config"])
    software_config_json = json.load(open(software_config_file_path, "r"))
    softwares = software_config_json["softwares"]
    if validation_utils.contains_software(softwares, "service_node"):
        return True
    return False


def validate_roles_config(
    input_file_path, data, logger, _module, _omnia_base_dir, _module_utils_base, _project_name
):
    """
    Validates the L2 logic of the roles_config.yaml file.

    Returns:
        list: A list of errors.
    """

    name = "name"
    roles = "Roles"
    groups = "Groups"
    role_groups = "groups"
    slurmworker = "slurm_node"
    service_k8s_worker = "service_kube_node"
    k8worker = "kube_node"
    default = "default"
    switch_details = "switch_details"
    ip = "ip"
    ports = "ports"
    parent = "parent"
    bmc_details = "bmc_details"
    static_range = "static_range"
    resource_mgr_id = "resource_mgr_id"
    max_roles_per_group = 5
    max_roles = 100

    roles_per_group = {}
    empty_parent_roles = {
        "login",
        "compiler_node",
        "service_node",
        'service_kube_control_plane',
        'service_etcd',
        "kube_control_plane",
        "etcd",
        "slurm_control_plane",
        "slurm_dbd",
        "auth_server"
    }

    errors = []
    # Empty file validation
    if not data:
        errors.append(
            create_error_msg(
                "roles_config.yml,",
                None,
                en_us_validation_msg.EMPTY_OR_SYNTAX_ERROR_ROLES_CONFIG_MSG
            )
        )
        return errors

    roles = data.get(roles, [])
    groups = data.get(groups, [])

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
        errors.extend(validate_group_role_separation(logger, roles))
        if errors:
            return errors

    groups_used = set()  # Initialize as empty set
    # List of groups used in roles
    if groups:
        groups_used = set(groups.keys())

    # Check for minimum required sections
    if not groups:
        errors.append(
            create_error_msg(
                groups,
                "Current number of groups is 0:",
                en_us_validation_msg.MIN_NUMBER_OF_GROUPS_MSG
            )
        )
    if not roles:
        errors.append(
            create_error_msg(
                roles,
                "Current number of roles is 0:",
                en_us_validation_msg.MIN_NUMBER_OF_ROLES_MSG
            )
        )
    # Check maximum roles limit
    if roles and len(roles) > max_roles:
        errors.append(
            create_error_msg(
                roles,
                f"Current number of roles is {len(roles)}:",
                en_us_validation_msg.MAX_NUMBER_OF_ROLES_MSG
            )
        )

    service_cluster_roles = ["service_kube_control_plane", "service_etcd", "service_kube_node"]
    defined_service_roles = [role["name"] for role in roles if role["name"] in service_cluster_roles]

    if 0 < len(defined_service_roles) < len(service_cluster_roles):
        service_cluster_str = ', '.join(defined_service_roles)
        errors.append(create_error_msg("Roles", service_cluster_str, en_us_validation_msg.service_cluster_roles_msg))

    # Role Service_node is defined in roles_config.yml,
    # verify service_node entry present in sofwate_config.json
    # If no entry is present, then fail the input validator
    service_role_defined = False
    if validation_utils.key_value_exists(roles, name, "service_node"):
        service_role_defined = True

        try:
            if not validate_service_node_in_software_config(input_file_path):
                errors.append(
                    create_error_msg(
                        "software_config.json",
                        None,
                        en_us_validation_msg.SERVICE_NODE_ENTRY_MISSING_ROLES_CONFIG_MSG
                    )
                )
        except Exception as e:
            errors.append(
                create_error_msg("software_config.json",
                                 None,
                                f"An error occurred while validating software_config.json: {str(e)}"))


    if len(errors) <= 0:
        # List of groups which need to have their resource_mgr_id set
        set_resource_mgr_id = set()

        switch_ip_mapping = {}
        switch_ip_port_mapping = {}
        static_range_mapping = {}
        # # Check if the bmc_network is defined
        # bmc_network_defined = check_bmc_network(
        #     input_file_path, logger, module, omnia_base_dir, project_name)

        for role in roles:
            # Check role-group association, all roles must have a group
            if role[role_groups] and (None in role[role_groups] or not role[role_groups]):
                errors.append(
                    role[name],
                    create_error_msg(
                        None,
                        f"Role {role[name]} must be associated with a group:",
                        en_us_validation_msg.MIN_NUMBER_OF_GROUPS_MSG
                    ),
                )
            if role[name] == slurmworker or role[name] == k8worker or role[name] == service_k8s_worker:
                for group in role[role_groups]:
                    set_resource_mgr_id.add(group)

            if not role[role_groups]:
                role[role_groups] = []
            # Validate each group and its configs under each role
            for group in role[role_groups]:
                if group in groups_used:
                    groups_used.remove(group)
                roles_per_group[group] = roles_per_group.get(group, 0) + 1
                if roles_per_group[group] > max_roles_per_group:
                    errors.append(
                        create_error_msg(
                            role[name],
                            f"Current number of roles for {group} "
                            f"is {str(roles_per_group[group])}:",
                            en_us_validation_msg.MAX_NUMBER_OF_ROLES_PER_GROUP_MSG
                        )
                    )
                if group in groups:
                    # Validate parent field is empty for specific role cases
                    if role[name] in empty_parent_roles and not validation_utils.is_string_empty(
                        groups[group].get(parent, None)
                    ):
                        # If parent is not empty and group is associated with login,
                        #  compiler_node, service_node, kube_control_plane,
                        # or slurm_control_plane
                        errors.append(
                            create_error_msg(
                                group,
                                f"Group {group} should not have parent defined.",
                                en_us_validation_msg.PARENT_SERVICE_NODE_MSG
                            )
                        )
                    if not service_role_defined and (
                        role[name] == k8worker
                        or role[name] == slurmworker
                        or role[name] == default
                    ):
                        # If a service_node role is not present,
                        # the parent is not empty and the group is
                        # associated with worker or default roles.
                        if not validation_utils.is_string_empty(groups[group].get(parent, None)):
                            errors.append(
                                create_error_msg(
                                    group,
                                    f"Group {group} should not have parent defined.",
                                    en_us_validation_msg.PARENT_SERVICE_ROLE_MSG
                                )
                            )
                    elif not service_role_defined and not validation_utils.is_string_empty(
                        groups[group].get(parent, None)
                    ):
                        errors.append(
                            create_error_msg(
                                group,
                                f"Group {group} parent is provided.",
                                en_us_validation_msg.PARENT_SERVICE_ROLE_DNE_MSG
                            )
                        )
                else:
                    # Error log for if a group under a role does not exist
                    errors.append(
                        create_error_msg(
                            group,
                            f"Group {group} does not exist.",
                            en_us_validation_msg.GRP_EXIST_MSG
                        )
                    )

        for group in groups.keys():

            switch_ip_provided = not validation_utils.is_string_empty(
                groups[group].get(switch_details, {}).get(ip, None)
            )
            switch_ports_provided = not validation_utils.is_string_empty(
                groups[group].get(switch_details, {}).get(ports, None)
            )
            bmc_static_range_provided = not validation_utils.is_string_empty(
                groups[group].get(bmc_details, {}).get(static_range, None)
            )
            if group in groups_used:
                errors.append(
                    create_error_msg(
                        group,
                        f"Group {group} is not associated with a role.",
                        en_us_validation_msg.GRP_ROLE_MSG
                    )
                )
            if switch_ip_provided and switch_ports_provided:
                switch_ip = groups[group][switch_details][ip]
                try:
                    ipaddress.IPv4Address(switch_ip)
                except Exception as _e:
                    errors.append(
                        create_error_msg(
                            group,
                            f"Group {group} switch ip is invalid:",
                            en_us_validation_msg.INVALID_SWITCH_IP_MSG
                        )
                    )
                if switch_ip in switch_ip_mapping:
                    # Check for any switch ip port overlap
                    if validation_utils.check_port_overlap(
                        switch_ip_port_mapping.get(switch_ip, "")
                        + ","
                        + groups[group][switch_details].get(ports, "")
                    ):
                        errors.append(
                            create_error_msg(
                                group,
                                f"Group {group} has duplicate ports for switch ip {switch_ip}, "
                                f"this switch ip is shared with "
                                f"the following groups: {switch_ip_mapping[switch_ip]}.",
                                en_us_validation_msg.DUPLICATE_SWITCH_IP_PORT_MSG
                            )
                        )
                if not validation_utils.check_port_ranges(
                    groups[group][switch_details].get(ports, "")
                ):
                    errors.append(
                        create_error_msg(
                            group,
                            f"Group {group} switch port range(s) are invalid, start > end:",
                            en_us_validation_msg.INVALID_SWITCH_PORTS_MSG
                        )
                    )
                switch_ip_mapping.setdefault(switch_ip, []).append(group)
                switch_ip_port_mapping[switch_ip] = (
                    switch_ip_port_mapping.get(switch_ip, "")
                    + ","
                    + groups[group][switch_details].get(ports, "")
                )
            if (switch_ip_provided and not switch_ports_provided) or (
                not switch_ip_provided and switch_ports_provided
            ):
                errors.append(
                    create_error_msg(
                        group,
                        f"Group {group} switch details are incomplete:",
                        en_us_validation_msg.SWITCH_DETAILS_INCOMPLETE_MSG
                    )
                )
            if (switch_ip_provided and switch_ports_provided) and not bmc_static_range_provided:
                errors.append(
                    create_error_msg(
                        group,
                        f"Group {group} switch details provided:",
                        en_us_validation_msg.SWITCH_DETAILS_NO_BMC_DETAILS_MSG
                    )
                )

            # Validate bmc details for each group
            if not validation_utils.is_string_empty(
                groups[group].get(bmc_details, {}).get(static_range, None)
            ):
                # # Check if bmc details are defined, but enable_switch_based
                # is true or the bmc_network is not defined
                # if enable_switch_based or not bmc_network_defined:
                #     errors.append(create_error_msg(group,
                #                   "Group " + group + " BMC static range invalid use case.",
                #                    en_us_validation_msg.bmc_static_range_msg))
                # Validate the static range is properly defined
                if not validation_utils.validate_ipv4_range(
                    groups[group].get(bmc_details, {}).get(static_range, "")
                ):
                    errors.append(
                        create_error_msg(
                            group,
                            f"Group {group} BMC static range is invalid.",
                            en_us_validation_msg.BMC_STATIC_RANGE_INVALID_MSG
                        )
                    )
                elif group not in static_range_mapping:
                    # A valid static range was provided,
                    # now a check is performed to ensure static ranges do not overlap
                    static_range = groups[group][bmc_details][static_range]
                    grp_overlaps = validation_utils.check_bmc_static_range_overlap(
                        static_range, static_range_mapping
                    )
                    if len(grp_overlaps) > 0:
                        errors.append(
                            create_error_msg(
                                group,
                                f"Static range {static_range} "
                                f"overlaps with the following group(s): {grp_overlaps}.",
                                en_us_validation_msg.OVERLAPPING_STATIC_RANGE
                            )
                        )
                    static_range_mapping[group] = static_range

            # Validate resource_mgr_id is set for groups that belong
            #  to kube_node, service_kube_node, slurm_node roles
            if group in set_resource_mgr_id and validation_utils.is_string_empty(
                groups[group].get(resource_mgr_id, None)
            ):
                errors.append(
                    create_error_msg(
                        group,
                        f"Group {group} is missing resource_mgr_id.",
                        en_us_validation_msg.RESOURCE_MGR_ID_MSG
                    )
                )
            elif group not in set_resource_mgr_id and not validation_utils.is_string_empty(
                groups[group].get(resource_mgr_id, None)
            ):
                # Validate resource_mgr_id is not set for groups
                # that do not belong to kube_node, service_kube_node, slurm_node roles
                errors.append(
                    create_error_msg(
                        group,
                        f"Group {group} should not have the resource_mgr_id set.",
                        en_us_validation_msg.RESOURCE_MGR_ID_MSG
                    )
                )

    return errors
