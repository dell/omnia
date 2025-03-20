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

from ansible.module_utils.basic import AnsibleModule

def fetch_mapping_details(groups_roles_info, csv_data):
    """
    Fetches the mapping details for the given groups and roles.

    Args:
        groups_roles_info (dict): A dictionary containing groups as keys,
                                  with all details including associated roles.
        node_df (DataFrame): A DataFrame containing node information.

    Returns:
        list: A list of dictionaries containing the filtered node details.

    """

    filtered_nodes = []
    nodes = {mac: details for mac, details in csv_data.items() if details["GROUP_NAME"] in groups_roles_info}

    for _, node  in nodes.items():
        group = node["GROUP_NAME"]

        node_data = {
            "service_tag": node["SERVICE_TAG"],
            "hostname": node["HOSTNAME"],
            "admin_mac": node["ADMIN_MAC"],
            "admin_ip": node["ADMIN_IP"],
            "bmc_ip": node["BMC_IP"],
            "group_name": group,
            "roles": ",".join(groups_roles_info[group]["roles"]),
            "location_id": groups_roles_info[group]["location_id"],
            "resource_mgr_id": groups_roles_info[group]["resource_mgr_id"],
            "parent": groups_roles_info[group]["parent"],
            "bmc_details": groups_roles_info[group]["bmc_details"],
            "switch_details": groups_roles_info[group]["switch_details"],
            "architecture": groups_roles_info[group]["architecture"],
            "hierarchical_provision_status": groups_roles_info[group]["hierarchical_provision_status"]
        }
        filtered_nodes.append(node_data)

    return filtered_nodes

def main():
    module_args = dict(
        groups_roles_info=dict(type="dict", required=True),
        mapping_file_data=dict(type="dict", required=True)
    )

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    try:
        groups_roles_info = module.params["groups_roles_info"]
        node_df = module.params["mapping_file_data"]

        filtered_nodes = fetch_mapping_details(groups_roles_info, node_df)

        module.exit_json(changed=False, mapping_details=filtered_nodes, mapping_required=bool(filtered_nodes))

    except Exception as e:
        module.fail_json(error=str(e))

if __name__ == "__main__":
    main()