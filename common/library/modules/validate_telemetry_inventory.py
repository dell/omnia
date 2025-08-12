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

# pylint: disable=import-error

#!/usr/bin/python

""" This module is used to validate service node status"""

import csv
import os
import yaml
import json
from ansible.module_utils.discovery.omniadb_connection import get_data_from_db

from ansible.module_utils.basic import AnsibleModule

required_k8s_roles = ['kube_node', 'etcd', 'kube_control_plane']


def get_service_cluster_details():

    """
    Retrieves service cluster details from the database and
    returns a dictionary mapping roles to hostnames.

    Args:

    Returns:
        bool: if all service k8s roles are discovered then return true
        dict: A dictionary where the keys are roles
        ('service_kube_node', 'service_etcd', 'service_kube_control_plane')
        and the values are lists of hostnames.

    Raises:
        None
    """

    is_all_service_roles_discovered = False
    query_result = get_data_from_db(
        table_name='cluster.nodeinfo',
        filter_dict = {'role': ['service_kube_node', 'service_etcd', 'service_kube_control_plane']}
    )

    roles_to_hostname_dict = {}
    for record in query_result:
        service_role = record['role']
        k8s_roles = service_role.replace("service_","")
        hostname = record['hostname']
        admin_ip = record['admin_ip']
        service_tag = record['service_tag']
        role_list = k8s_roles.split(',') # if node is associcated to multiple roles then spilt

        for role in role_list:
            roles_to_hostname_dict.setdefault(role, []).append([hostname,admin_ip,service_tag])


    if all(role in roles_to_hostname_dict for role in required_k8s_roles):
        is_all_service_roles_discovered = True

    return is_all_service_roles_discovered, roles_to_hostname_dict

def validate_inventory_and_db_nodes(inventory_groups_dict,
                                    db_roles_to_hostname):

    """
    Validates the consistency between inventory groups and database nodes.

    Args:
        inventory_groups_dict (dict): A dictionary of inventory groups where
                            each key is a group name and each value is a list of hostnames.
        db_roles_to_hostname (dict): A dictionary of database roles to hostnames where
                            each key is a role and each value is a list of hostnames.

    Returns:
        dict: A dictionary where each key is a group name and each value is a set of hostnames
            that are present in the inventory group but not in the database.

    Raises:
        None

    Notes:
        This function compares the hostnames in each inventory group
        with the hostnames in the corresponding database role.
        If there are any hostnames in the inventory group that are not in the database role,
        they are added to the `grps_to_mismatch_hosts` dictionary.

    """
    grps_to_mismatch_hosts = {}

    for group in inventory_groups_dict:
        if group in required_k8s_roles:
            inv_hosts = inventory_groups_dict[group]
            if group in db_roles_to_hostname:
                db_role_details_list = db_roles_to_hostname[group]
                for host in inv_hosts:
                    if not any(host in sublist for sublist in db_role_details_list):
                        grps_to_mismatch_hosts.setdefault(group, []).append(host)
            else:
                grps_to_mismatch_hosts.setdefault(group, []).extend(inv_hosts)

    return grps_to_mismatch_hosts

def valid_groups_in_inventory(inventory_groups_dict):
    """
    Validate if all required Kubernetes roles are present in the inventory groups.

    Args:
        inventory_groups_dict (dict): A dictionary of inventory groups where
        each key is a group name and each value is a list of hostnames.

    Returns:
        bool: True if all required Kubernetes roles are present in the inventory groups,
        False otherwise.
    """
    return all(role in inventory_groups_dict for role in required_k8s_roles)

def main():
    """Main module function."""
    module_args = {
        'telemetry_inventory_groups': {"type": "dict", "required": True},
        'is_federated_idrac_telemetry_collection':{"type":"bool", "required":False,"default":False}
    }

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)
    inventory_groups_dict = module.params["telemetry_inventory_groups"]
    federated_idrac_telemetry_collection = module.params["is_federated_idrac_telemetry_collection"]
    all_service_roles_discovered = False

    try:

        all_service_roles_discovered, db_service_roles_to_hostname = \
                get_service_cluster_details()

        # if federated_idrac_telemetry_collection, only then validate inventory and db roles
        if federated_idrac_telemetry_collection:
            grps_to_mismatch_hosts = validate_inventory_and_db_nodes(inventory_groups_dict,
                                                               db_service_roles_to_hostname)
            if grps_to_mismatch_hosts:
                module.fail_json(msg=f"Inventory validation failed. "\
                        f"Invalid hosts provided in inventory {grps_to_mismatch_hosts}")

        module.exit_json(changed=False,
                         is_all_service_roles_discovered=all_service_roles_discovered
                        )
    except ValueError as e:
        module.fail_json(msg=f"Failed to validate Service Cluster data. {e}")

if __name__ == "__main__":
    main()
