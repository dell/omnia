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

import sys
import json

db_path = sys.argv[1]
sys.path.insert(0, db_path)

import omniadb_connection

mapping_details = json.loads(sys.argv[2])
domain_name = sys.argv[3]
discovery_mechanism = "mapping"
admin_mac = []
hostname = []
admin_ip = []
bmc_ip = []
nan = float('nan')



def mapping_file_db_update():
    """
    Updates the database with node information from the provided JSON mapping_details.

    This function processes each node entry in the mapping_details list, checks if the
    service tag exists in the database, and either inserts a new record or logs that the
    node already exists.

    Parameters:
        None

    Returns:
        None
    """
    existing_mac = []

    # Establish database connection
    conn = omniadb_connection.create_connection()
    cursor = conn.cursor()

    for node_data in mapping_details:
        temp_mac = node_data.get("admin_mac")
        temp_service_tag = node_data.get("service_tag")
        temp_admin_ip = node_data.get("admin_ip")
        temp_bmc_ip = node_data.get("bmc_ip")
        node = node_data.get("hostname")
        fqdn_hostname = f"{node}.{domain_name}"
        group_name = node_data.get("group_name")
        role = node_data.get("roles")
        parent = node_data.get("parent")
        location_id = node_data.get("location_id")
        architecture = node_data.get("architecture")

        # Validate BMC IP, set to None if invalid
        if not temp_bmc_ip:
            temp_bmc_ip = None

        # Validate admin IP, set to None if invalid
        if not temp_admin_ip:
            temp_admin_ip = None

        # Check if the service tag already exists in the table
        query = "SELECT EXISTS(SELECT 1 FROM cluster.nodeinfo WHERE service_tag=%s)"
        cursor.execute(query, (temp_service_tag,))
        exists = cursor.fetchone()[0]

        if not exists:
            # Insert new node record
            omniadb_connection.insert_node_info(temp_service_tag, node, fqdn_hostname, temp_mac, temp_admin_ip, temp_bmc_ip,
            group_name, role, parent, location_id, architecture, discovery_mechanism, None, None, None, None)
        else:
            existing_mac.append(temp_mac)
            sys.stdout.write(f"{temp_mac} already present in DB.\n")

    conn.close()

mapping_file_db_update()