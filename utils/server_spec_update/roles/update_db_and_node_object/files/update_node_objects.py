# Copyright 2024 Dell Inc. or its subsidiaries. All Rights Reserved.
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

import subprocess
import sys
import yaml
import time

db_path = sys.argv[2]
sys.path.insert(0, db_path)
import omniadb_connection

network_spec_file_path = sys.argv[1]

with open(network_spec_file_path, "r") as file:
    data = yaml.safe_load(file)

# Extract network names
network_names = [list(item.keys())[0] for item in data["Networks"] if list(item.keys())[0] not in ["admin_network", "bmc_network"]]


def update_node_obj():
    # Establish a connection with omniadb
    conn = omniadb_connection.create_connection()
    cursor = conn.cursor()

    # Execute the SQL query to fetch the IDs present in the nicinfo table
    sql_query = "SELECT id FROM cluster.nicinfo"
    cursor.execute(sql_query)

    # Fetch all rows from the result set
    rows = cursor.fetchall()

    # Iterate through the rows
    for row in rows:
        # Fetch the node corresponding to the ID from the nodeinfo table
        sql_query = "SELECT node FROM cluster.nodeinfo WHERE id = %s"
        cursor.execute(sql_query, (row[0],))
        node_row = cursor.fetchone()

        # Check if a node exists for the current ID
        if node_row is not None:
            # Extract the node
            node_name = node_row[0]

            # Iterate over network_names list
            for network_name in network_names:
                # Fetch the network value
                sql_query_network = f"SELECT {network_name}, {network_name}_ip, {network_name}_type FROM cluster.nicinfo WHERE id = %s"
                cursor.execute(sql_query_network, (row[0],))
                network_row = cursor.fetchone()

                # Extract network values
                network_nic = network_row[0]
                network_ip = network_row[1]
                network_type = network_row[2]

                # updating node objects
                if network_nic is not None and network_ip is not None and network_type is not None:
                    if network_type != "vlan":
                        command = ["/opt/xcat/bin/chdef", node_name, f"nictypes.{network_nic}={network_type}"]
                        subprocess.run(command)
                        command = ["/opt/xcat/bin/chdef", node_name, f"nicips.{network_nic}={network_ip}"]
                        subprocess.run(command)
                        command = ["/opt/xcat/bin/chdef", node_name, f"nicnetworks.{network_nic}={network_name}"]
                        subprocess.run(command)
                    else:
                        sql_query_network = f"SELECT {network_name}_device FROM cluster.nicinfo WHERE id = %s"
                        cursor.execute(sql_query_network, (row[0],))
                        primary_nic = cursor.fetchone()
 
                        if primary_nic[0]:
                            command = ["/opt/xcat/bin/chdef", node_name, f"nictypes.{primary_nic[0]}=ethernet"]
                            subprocess.run(command)
                            command = ["/opt/xcat/bin/chdef", node_name, f"nicips.{network_nic}={network_ip}"]
                            subprocess.run(command)
                            command = ["/opt/xcat/bin/chdef", node_name, f"nicnetworks.{network_nic}={network_name}"]
                            subprocess.run(command)
                            command = ["/opt/xcat/bin/chdef", node_name, f"nictypes.{network_nic}={network_type}", f"nicdevices.{network_nic}={primary_nic[0]}"]
                            subprocess.run(command)
                            command = ["/opt/xcat/bin/chdef", node_name, f"nichostnamesuffixes.{network_nic}=-{primary_nic[0]}"]
                            subprocess.run(command)

            command = ["/opt/xcat/bin/updatenode", node_name, "-P", "confignetwork,omnia_hostname"]
            subprocess.run(command)
            time.sleep(1)

    # Close the cursor and connection
    cursor.close()
    conn.close()


update_node_obj()
