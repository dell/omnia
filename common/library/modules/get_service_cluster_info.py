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

# pylint: disable=import-error,no-name-in-module,line-too-long

#!/usr/bin/python

"""Ansible module to check telemetry service cluster node details."""

import yaml
from ansible.module_utils.basic import AnsibleModule

def load_functional_groups_yaml(path, module):
    """Load functional group names from YAML."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return data.get("groups", {})
    except ValueError as e:
        module.fail_json(msg=f"Failed to load functional_groups_config.yml: {str(e)}")

def get_service_cluster_node_details(nodes_info):
    """
    This function retrieves all service cluster node data from the database.
    Returns a dictionary of service cluster node data.
    """

    data = {}

    for sn in nodes_info:
        node = sn['name']
        service_tag = sn['description']
        role = sn['group']
        # cluster_name =  next((g["cluster_name"] for g in functional_groups_info if g["name"] == role), None)

        if "service_kube_node_x86_64" in role or "service_kube_node_aarch64" in role:
            data[service_tag] = {
                'service_tag': service_tag,
                'node': node,
                # 'cluster_name': cluster_name,
                'role': role
            }

    data['MGMT_node'] = {'parent_status' : True, 'service_tag' : 'MGMT_node', 'role': 'service_kube_control_plane'}
    return data

def check_service_cluster_node_details(group, parent, service_cluster_node_details):
    """Check if service cluster node details are available."""

    if not parent:
        return False
    if parent in service_cluster_node_details:
        return True
    raise ValueError(
            f"Error: The service tag '{parent}' specified in the 'parent' field for group '{group}' "
            "may be incorrect, or the node might not be available. "
            "Please verify the input and try again."
        )

def get_service_cluster_data(groups_info, service_cluster_node_details, bmc_group_data):
    """
    Generate service cluster node details by analyzing group relationships and BMC group data.

    This function checks the service cluster node details for each group,
    and adds child group data to service_cluster_node_details. It also checks
    if a parent has child groups in the bmc_group_data and adds them to the parent_data.

    Args:
        groups_info (dict): Dictionary containing group information.
        service_cluster_node_details (dict): Dictionary containing service cluster node information.
        bmc_group_data (list): List of dictionaries containing BMC group data.

    Returns:
        dict: Updated service_cluster_node_details.
    """

    for group, group_data in groups_info.items():
        parent = group_data.get("parent", "")

        # Skip if service cluster node details check fails
        if not check_service_cluster_node_details(group, parent, service_cluster_node_details):
            continue

        # Initialize parent data
        parent_data = service_cluster_node_details.get(parent, {})
        parent_data.setdefault("child_groups", [])

        # Add current group to child_groups if not already present
        if group and group not in parent_data["child_groups"]:
            parent_data["child_groups"].append(group)

        # Add child groups from bmc_group_data
        for entry in bmc_group_data:
            if entry.get("PARENT") == parent:
                bmc_group = entry.get("GROUP_NAME")
                if bmc_group and bmc_group not in parent_data["child_groups"]:
                    parent_data["child_groups"].append(bmc_group)

        # Set parent_status if there are any child groups
        if parent_data["child_groups"]:
            parent_data["parent_status"] = True

        # Update the service_cluster_node_details dictionary
        service_cluster_node_details[parent] = parent_data


    return service_cluster_node_details

def main():
    """
        Main function to execute the check_service_cluster_node_details custom module.
    """
    module_args = {
        'nodes_info': {'type':"list", 'required':True},
        'functional_groups_file_path': {'type':"path", 'required':True},
        'bmc_group_data': {'type':"list", 'required':True}
    }

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    try:
        nodes_info = module.params["nodes_info"]
        bmc_group_data = module.params["bmc_group_data"]
        functional_groups_file_path = module.params["functional_groups_file_path"]
        groups_info = load_functional_groups_yaml(functional_groups_file_path, module)
        service_cluster_node_details = get_service_cluster_node_details(nodes_info)
        service_cluster_node_details = get_service_cluster_data(groups_info, service_cluster_node_details, bmc_group_data)

        module.exit_json(
            changed=False,
            service_cluster_node_details = service_cluster_node_details
        )
    except ValueError as e:
        module.fail_json(msg=str(e).replace('\n', ' '))

if __name__ == "__main__":
    main()
