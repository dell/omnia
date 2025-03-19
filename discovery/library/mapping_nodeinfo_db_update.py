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
from ansible.module_utils import omniadb_connection

def nodeinfo_db_update(node_details, domain_name, discovery_mechanism):
    """
    Updates the database with node information from the provided JSON node_details.

    This function processes each node entry in the node_details list, checks if the
    service tag exists in the database, and either inserts a new record or logs that the
    node already exists.
    """

    existing_nodes = []
    new_nodes = []

    # Establish database connection
    conn = omniadb_connection.create_connection()
    cursor = conn.cursor()

    for node_data in node_details:
        # Convert all keys in node_data to lowercase
        node_data = {k.lower(): v for k, v in node_data.items()}

        temp_mac = node_data.get("admin_mac")
        temp_service_tag = node_data.get("service_tag")
        temp_admin_ip = node_data.get("admin_ip") or None
        temp_bmc_ip = node_data.get("bmc_ip") or None
        node = node_data.get("hostname")
        fqdn_hostname = f"{node}.{domain_name}"
        group_name = node_data.get("group_name")
        role = node_data.get("roles")
        parent = node_data.get("parent")
        location_id = node_data.get("location_id")
        architecture = node_data.get("architecture")

        # Check if the service tag already exists in the table
        query = "SELECT EXISTS(SELECT 1 FROM cluster.nodeinfo WHERE service_tag=%s)"
        cursor.execute(query, (temp_service_tag,))
        exists = cursor.fetchone()[0]

        if not exists:
            # Insert new node record
            omniadb_connection.insert_node_info(
                temp_service_tag, node, fqdn_hostname, temp_mac, temp_admin_ip, temp_bmc_ip,
                group_name, role, parent, location_id, architecture, discovery_mechanism, None, None, None, None
            )
            new_nodes.append({'node': node, 'service_tag': temp_service_tag, 'mac': temp_mac})
        else:
            existing_nodes.append({'node': node, 'service_tag': temp_service_tag, 'mac': temp_mac})

    conn.close()
    return new_nodes, existing_nodes

def main():
    module_args = dict(
        node_details=dict(type="list", elements="dict", required=True),
        domain_name=dict(type="str", required=True),
        discovery_mechanism=dict(type="str", required=True)
    )

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    node_details = module.params["node_details"]
    domain_name = module.params["domain_name"]
    discovery_mechanism = module.params["discovery_mechanism"]

    try:
        new_nodes, existing_nodes = nodeinfo_db_update(node_details, domain_name, discovery_mechanism)
        module.exit_json(changed=True, msg="Database updated successfully", existing_nodes=existing_nodes, new_nodes=new_nodes)
    except Exception as e:
        module.fail_json(msg=str(e))

if __name__ == "__main__":
    main()
