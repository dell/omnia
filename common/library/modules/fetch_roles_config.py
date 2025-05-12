# Copyright 2025 Dell Inc. or its subsidiaries. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

#!/usr/bin/python

"""
This module provides functions for fetching roles from an OmniDB database.
"""

from ansible.module_utils.basic import AnsibleModule

MANAGEMENT_LAYER_ROLES = {
    "oim_ha_node", "service_node", "login", "compiler_node", "kube_control_plane", "etcd",
    "slurm_control_node", "slurm_dbd", "auth_server"
    }
SECOND_LAYER_ROLES = {"default", "kube_node", "slurm_node"}
NON_SERVICE_ROLES = (MANAGEMENT_LAYER_ROLES | SECOND_LAYER_ROLES) - {"service_node"}

def validate_roles(roles, layer, module, management_layer_roles=MANAGEMENT_LAYER_ROLES, second_layer_roles=SECOND_LAYER_ROLES, non_service_roles=NON_SERVICE_ROLES): # type: ignore
    """
    Validates roles based on multiple conditions:
    1. Roles should only belong to either management_layer or compute-layer roles.
    2. At least one role should exist in the given layer.
    3. Groups associated with management_layer roles should not be in compute-layer roles.
    4. Groups assigned to 'service_node' should not be in other management_layer roles.

    :param roles: Dictionary where keys are role names and values are dictionaries with a 'groups'
                  key containing a list of groups.
    :param management_layer_roles: Set of management_layer role names.
    :param compute_layer_roles: Set of compute-layer role names.
    :param layer: Specifies which layer should have at least one role.
                  Should be 'first' or 'default'.
    :raises RoleValidationError: If validation fails, raises an exception with the list of errors.
    :return: True if validation passes.
    """

    # Create a mapping of roles to groups (converted to sets for efficiency)
    role_groups = {role: set(data.get("groups", [])) for role, data in roles.items()}

    defined_roles = set(roles.keys())  # Extract all roles from input

    # Check 1: Ensure all roles belong to either management_layer or compute-layer roles
    invalid_roles = defined_roles - (management_layer_roles | second_layer_roles)
    errors = []
    if invalid_roles:
        module.warn(
            f"Invalid roles detected: {invalid_roles}. \
                Roles must be from either management_layer or compute-layer roles.")

    # Check 1&2: Ensure at least one role exists in the specified layer
    if layer == "first":
        if not defined_roles.intersection(management_layer_roles):
            raise ValueError("At least one role must be from the management_layer roles.")
    else:
        if 'service_node' in defined_roles:
            if not defined_roles.intersection(second_layer_roles):
                raise ValueError(
                    f"At least one role must be defined from - \
                        {second_layer_roles} in roles_config.yml")
        else:
            if not defined_roles.intersection(non_service_roles):
                raise ValueError(
                    f"At least one role must be defined from - \
                        {non_service_roles} roles_config.yml")

    # Collect all groups used by management_layer and compute-layer roles
    management_layer_groups = {group for role in management_layer_roles \
                               for group in role_groups.get(role, [])}
    second_layer_groups = {group for role in second_layer_roles \
                           for group in role_groups.get(role, [])}

    # Check 3: Ensure groups from management_layer roles are not in compute-layer roles
    common_groups = management_layer_groups.intersection(second_layer_groups)
    if common_groups:
        errors.append(f"Groups {common_groups} \
                      are assigned to both management_layer and compute-layer roles.")

    # Check 4: Ensure groups in 'service_node' role are not part of other management_layer roles
    service_groups = role_groups.get("service_node", set())

    for role in management_layer_roles:
        if role != "service_node":
            overlapping_groups = service_groups.intersection(role_groups.get(role, set()))
            if overlapping_groups:
                errors.append(f"Groups {overlapping_groups} \
                              from 'service_node' role are also part of management_layer role '{role}'.")

    # Raise an error if validation fails
    if errors:
        raise ValueError("\n".join(errors))

def check_switch_required(group_data, layer):
    """Check if switch based provisioning is required."""
    if layer == 'first':
        return False
    switch_data = group_data.get("switch_details", {})
    if switch_data and switch_data.get("ip", '') and switch_data.get("ports", ''):
        return True
    else:
        return False

def check_bmc_required(group_data):
    """Check if bmc based provisioning is required."""
    bmc_data = group_data.get("bmc_details", {})
    if bmc_data and bmc_data.get("static_range", ''):
        return True
    else:
        return False

def filter_roles(roles_data, layer):
    """Filter the roles based on the layer and the roles data."""

    if layer == "first":
        valid_roles = set(roles_data.keys()).intersection(MANAGEMENT_LAYER_ROLES)
    else:
        if 'service_node' in roles_data:
            valid_roles = set(roles_data.keys()).intersection(SECOND_LAYER_ROLES)
        else:
            valid_roles = set(roles_data.keys()).intersection(NON_SERVICE_ROLES)
    return valid_roles


def roles_groups_mapping(groups_data, roles_data, layer):
    """
    Maps the roles to the groups and returns the mapping, along with some additional information.

    Parameters:
        groups_data (dict): A dictionary containing the group data.
        roles_data (dict): A dictionary containing the roles data.
        layer (str): The layer of the roles.

    Returns:
        tuple: A tuple containing the following:
            - bmc_check (bool): A boolean indicating if BMC is required.
            - switch_check (bool): A boolean indicating if switch is required.
            - hierarchical_provision_status (bool): A boolean indicating if hierarchical
                                                    provisioning is required.
            - roles_groups_data (dict): A dictionary containing the roles and groups data.
            - groups_roles_info (dict): A dictionary containing the groups and roles information.

    Raises:
        Exception: If a group doesn't exist in the roles_config.yml Groups dict.
    """


    valid_roles = filter_roles(roles_data, layer)

    bmc_check = False
    switch_check = False
    roles_groups_data = {}
    groups_roles_info = {}

    for role in valid_roles:
        for group in roles_data[role]["groups"]:

            if groups_data.get(group, {}):
                groups_roles_info.setdefault(group, {}).setdefault('roles', []).append(role)
                groups_roles_info[group].update(groups_data.get(group))
                grp_bmc_check = check_bmc_required(groups_data[group])
                grp_switch_check = grp_bmc_check and check_switch_required(groups_data[group], \
                                                                           layer)
                # For a group bmc will be false if switch is true
                grp_bmc_check = False if grp_switch_check else grp_bmc_check
                switch_check = switch_check or grp_switch_check
                bmc_check = bmc_check or grp_bmc_check

                roles_groups_data[role] = {}
                roles_groups_data[role][group] = groups_data[group]
                groups_roles_info[group]["mapping_status"] = False
                groups_roles_info[group]['switch_status'] = grp_switch_check
                groups_roles_info[group]['bmc_static_status'] = grp_bmc_check

            else:
                raise ValueError(
                    f"Group '{group}' doesn't exist in roles_config.yml Groups dict"
                    )

    return bmc_check, switch_check, roles_groups_data, groups_roles_info

def main():
    """
    This function is the main entry point of the Ansible module.
    It takes three parameters: roles_data, groups_data, and layer.
    The roles_data is a list of dictionaries where each dictionary
    contains the role name and other details.
    The groups_data is a dictionary where each key is a group name and the value is another
    dictionary containing group details. The layer parameter is a string that can be either
    "first" or "default". The function processes the roles and groups data, validates the roles,
    and then maps the roles to the groups. It also checks for BMC and switch requirements and
    hierarchical provisioning status. Finally, it returns the processed data in JSON format.

    Parameters:
        roles_data (list): A list of dictionaries where each dictionary contains the role name
                           and other details.
        groups_data (dict): A dictionary where each key is a group name and the value is another
                            dictionary containing group details.
        layer (str): A string that can be either "first" or "default".

    Returns:
        dict: A dictionary containing the processed data, including the roles, groups,
        and other relevant information.
    """
    module_args = dict(
        roles_data=dict(type="list", required=True),
        groups_data=dict(type="dict", required=True),
        layer=dict(type="str", choices=["first", "default"], required=True)
    )

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    try:
        roles_list = module.params["roles_data"]
        groups = module.params["groups_data"]
        layer = module.params["layer"]
        roles = {role.pop('name'): role for role in roles_list}
        validate_roles(roles, layer, module)
        need_bmc, need_switch, roles_groups_data, groups_roles_info = \
            roles_groups_mapping(groups, roles, layer)
        module.exit_json(
            changed=False,
            roles_data=roles,
            groups_data=groups,
            groups_roles_info=groups_roles_info,
            roles_groups_data=roles_groups_data,
            bmc_static_status=need_bmc,
            switch_status=need_switch,
        )
    except ValueError as e:
        module.fail_json(msg=str(e))

if __name__ == "__main__":
    main()
