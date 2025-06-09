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

"""Ansible module to check hierarchical provisioning status and service node HA configuration."""

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.discovery.omniadb_connection import get_data_from_db # type: ignore

def get_booted_service_nodes_data():
    """
    This function retrieves all service node data from the database
    and ensures they are all in 'booted' state. If not, it raises an error.
    Returns a dictionary of booted service node data.
    """
    query_result = get_data_from_db(
        table_name='cluster.nodeinfo',
        filter_dict={'role': "service_node"},
    )

    data = {}
    not_booted_nodes = []

    for sn in query_result:
        node = sn['node']
        status = sn.get('status', '')
        admin_ip = sn['admin_ip']
        service_tag = sn['service_tag']

        if status != 'booted':
            not_booted_nodes.append(service_tag)
            continue

        data[service_tag] = {
            'admin_ip': admin_ip,
            'service_tag': service_tag,
            'node': node
        }

    if not_booted_nodes:
        raise ValueError(
            f"The following service nodes are not in the 'booted' state: \
            {', '.join(not_booted_nodes)}. \
            For hierarchical provisioning of compute nodes or adding new management layer nodes, \
            all service nodes initiated for provisioning must be in the 'booted' state. \
            Please wait until all service nodes are booted, or \
            remove the nodes experiencing provisioning failures \
            using the utils/delete_node.yml playbook."
        )
    return data

def get_service_node_ha_dict(service_node_ha_data, booted_service_nodes_data):
    """
    Generate a dictionary containing the high availability (HA) configuration for service nodes.

    Args:
        service_node_ha_data (dict): Dictionary containing HA data for service nodes.
        booted_service_nodes_data (dict): Dictionary containing data of booted service nodes.

    Returns:
        dict: A dictionary containing the computed HA configuration for service nodes.

    Example:
        {
            'ABCD123': {
                'virtual_ip_address': '10.5.0.111',
                'active': True,
                'passive_nodes': ['PQR1234']
            },
            'PQR1234': {
                'virtual_ip_address': '10.5.0.111',
                'active': False,
                'active_service_tag': 'ABCD123'
            }
        }
    """

    sn_ha_data = {}
    sn_vip_list = []
    invalid_tags = []
    if not service_node_ha_data.get('enable_service_ha', False):
        return sn_ha_data
    ha_service_nodes = service_node_ha_data.get('service_nodes', [])
    for service_node in ha_service_nodes:
        active_sn_tag = service_node.get('active_node_service_tag')
        sn_vip = service_node.get('virtual_ip_address')
        if not active_sn_tag or not sn_vip:
            continue
        if active_sn_tag in sn_ha_data:
            raise ValueError('Duplicate entries found for active_node_service_tag field.')
        if sn_vip in sn_vip_list:
            raise ValueError('Duplicate entries found for service nodes virtual_ip_address field.')
        if active_sn_tag not in booted_service_nodes_data:
            invalid_tags.append(active_sn_tag)

        sn_ha_data[active_sn_tag] = {'virtual_ip_address': sn_vip, 'active': True}
        sn_vip_list.append(sn_vip)
        passive_nodes_tags_list = []
        for passive_nodes in service_node.get('passive_nodes', []):
            passive_nodes_tags = passive_nodes.get('node_service_tags', [])
            if not passive_nodes_tags:
                continue
            for passive_node_tag in passive_nodes_tags:
                if not passive_node_tag:
                    continue
                if passive_node_tag in sn_ha_data:
                    raise ValueError('Duplicate entries found for passive_node_service_tags field.')
                sn_ha_data[passive_node_tag] = {'virtual_ip_address': sn_vip,
                                                'active': False,
                                                'active_service_tag': active_sn_tag }
                if passive_node_tag not in booted_service_nodes_data:
                    invalid_tags.append(passive_node_tag)
                passive_nodes_tags_list.append(passive_node_tag)
        sn_ha_data[active_sn_tag]['passive_nodes'] = passive_nodes_tags_list
    if invalid_tags:
        raise ValueError(f" ERROR: \
            These service tags '{invalid_tags}' mentioned in 'high_availability_config.yml' \
            for service node HA may be incorrect, or the node might not have been provisioned. \
            * If service_node not provisioned, verify the input in roles_config.yml and execute discovery_provision.yml \
            playbook with 'management_layer' tag. \
            * If service_node is already provisioned with management layer nodes, verify the input in\
            high_availability_config.yml and execute discovery_provision.yml"
        )
    return sn_ha_data

def check_hierarchical_provision(group, parent, booted_service_nodes_data):
    """Check if hierarchical provisioning is required."""

    if not parent:
        return False
    if parent in booted_service_nodes_data:
        return True
    raise ValueError(
        f"Error: The service tag '{parent}' specified in the 'parent' field for group '{group}' \
        in roles_config.yml may be incorrect, or the node might not have been provisioned. \
        Please verify the input in roles_config.yml and execute discovery_provision.yml playbook \
        with 'management_layer' tag to provision service nodes."
        )


def combine_booted_service_with_ha_data(booted_service_nodes_data, service_node_ha_data):
    """
    Combines booted service nodes data with service node HA data.

    Parameters:
    booted_service_nodes_data (dict): A dictionary containing booted service nodes data.
    service_node_ha_data (dict): A dictionary containing service node HA data.

    Returns:
    dict: A dict containing the combined data of booted service nodes and service node HA data.
         Example:
         {
             'ABCD123': {
                 'admin_ip': '10.5.0.10',
                 'service_tag': 'ABCD123',
                 'node': 'servicenode1',
                 'child_groups': []
                 'enable_service_ha': True,
                 'virtual_ip_address': '10.5.0.111',
                 'active': True,
                 'passive_nodes': ['PQR123']
             },
             'PQR123': {
                 'admin_ip': '10.5.0.11',
                 'service_tag': 'PQR123',
                 'node': 'servicenode1ha',
                 'child_groups': []
                 'enable_service_ha': True,
                 'virtual_ip_address': '10.5.0.111',
                 'active': False,
                 'active_service_tag': 'ABCD123'
             },
             'XYZ321': {
                 'admin_ip': '10.5.0.12',
                 'service_tag': 'XYZ321',
                 'node': 'servicenode3',
                 'child_groups': []
                 'enable_service_ha': False
             },

         }
    """
    combined_data = {**booted_service_nodes_data}
    for sn_tag, sn_ha_data in service_node_ha_data.items():
        combined_data[sn_tag].update(**sn_ha_data)

    for sn_tag in booted_service_nodes_data:
        if sn_tag in service_node_ha_data:
            combined_data[sn_tag].update({'enable_service_ha': True})
        else:
            combined_data[sn_tag].update({'enable_service_ha': False})
        combined_data[sn_tag].update({'child_groups': []})

    return combined_data

def get_hierarchical_data(groups_roles_info, booted_service_nodes_data):
    """
    Generate hierarchical data from groups_roles_info and booted_service_nodes_data.

    This function checks the hierarchical provisioning status for each group,
    updates the groups_roles_info with the status, and adds child group data
    to booted_service_nodes_data.

    Args:
        groups_roles_info (dict): Dictionary containing group information.
        booted_service_nodes_data (dict): Dictionary containing booted service node information.

    Returns:
        tuple: A tuple containing:
            - updated groups_roles_info (dict)
            - updated booted_service_nodes_data (dict)
            - hierarchical_provision_status (dict)
    """


    hierarchical_provision_status = False

    for group, group_data in groups_roles_info.items():
        parent = group_data.get('parent', '')
        status = check_hierarchical_provision(group, parent, booted_service_nodes_data)
        hierarchical_provision_status = hierarchical_provision_status or status

        if not status:
            groups_roles_info[group]['hierarchical_provision_status'] = False
            continue

        parent_data = booted_service_nodes_data.get(parent, {})
        parent_data.setdefault('child_groups', []).append(group)
        booted_service_nodes_data[parent] = parent_data
        groups_roles_info[group]['hierarchical_provision_status'] = hierarchical_provision_status

    return groups_roles_info, booted_service_nodes_data, hierarchical_provision_status

def main():
    """
        Main function to execute the check_hierarchical_provision custom module.
    """
    module_args = {
        'groups_roles_info': {'type':"dict", 'required':True},
        'service_node_ha_data': {'type':"dict", 'required':True}
    }

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    try:
        groups_roles_info = module.params["groups_roles_info"]
        service_node_ha_data = module.params["service_node_ha_data"]
        booted_service_nodes_data = get_booted_service_nodes_data()
        service_node_ha_data = get_service_node_ha_dict(service_node_ha_data,
                                                        booted_service_nodes_data)
        booted_service_nodes_data = combine_booted_service_with_ha_data(booted_service_nodes_data,
                                                                        service_node_ha_data)

        groups_roles_info, booted_service_nodes_data, hierarchical_provision_status  = \
            get_hierarchical_data(groups_roles_info, booted_service_nodes_data)

        module.exit_json(
            changed=False,
            hierarchical_provision_status = hierarchical_provision_status,
            booted_service_nodes_data = booted_service_nodes_data,
            groups_roles_info = groups_roles_info,
            service_node_ha_dict = service_node_ha_data
        )
    except ValueError as e:
        module.fail_json(msg=str(e))

if __name__ == "__main__":
    main()
