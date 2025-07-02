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
"""
This script updates the node objects in the cluster.nicinfo table based on the network information.
"""
import shlex
import subprocess
import sys
import os
import time
import json
from distutils.util import strtobool
import yaml

db_path = sys.argv[2]
sys.path.insert(0, db_path)
import omniadb_connection

network_spec_file_path = os.path.abspath(sys.argv[1])

with open(network_spec_file_path, "r", encoding="utf-8") as file:
    data = yaml.safe_load(file)

# Load network data
network_string = os.environ.get('net_data')
network_data = json.loads(network_string)
INVENTORY_STATUS = bool(strtobool(sys.argv[3]))

# Extract network names
NETWORK_NAMES = [
    list(item.keys())[0]
    for item in data["Networks"]
    if list(item.keys())[0] not in ["admin_network", "bmc_network"]
]


def update_node_obj():
    """
    Updates the node objects in the cluster.nicinfo table based on the network information.

    This function establishes a connection with the omniadb, fetches the IDs from the nicinfo table,
    and then iterates through each row. For each row, it fetches the corresponding node from the
    nodeinfo table. If a node exists, it iterates through the NETWORK_NAMES list and fetches the
    network value. It then updates the node objects using the network values.

    Parameters:
        None

    Returns:
        None
    """
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
        sql_query = "SELECT node, status FROM cluster.nodeinfo WHERE id = %s"
        cursor.execute(sql_query, (row[0],))
        node_row = cursor.fetchone()

        # Check if a node exists for the current ID
        if node_row is not None:
            # Extract the node
            node_name = node_row[0]
            status = node_row[1]
            # Check with the inventory and node status
            if (status.lower() != "booted") if INVENTORY_STATUS else (status.lower() == "booted"):
                # Iterate over NETWORK_NAMES list
                for network_name in NETWORK_NAMES:
                    # Fetch the network value
                    network_info = network_data[network_name]
                    sql_query_network = (
                        f"SELECT {network_name}, {network_name}_ip, "
                        f"{network_name}_type, {network_name}_metric "
                        f"FROM cluster.nicinfo WHERE id = %s"
                    )
                    cursor.execute(sql_query_network, (row[0],))
                    network_row = cursor.fetchone()

                    # Extract network values
                    network_nic = network_row[0]
                    network_ip = network_row[1]
                    network_type = network_row[2]
                    network_metric = network_row[3]

                    # updating node objects
                    if (network_nic is not None and network_ip is not None
                            and network_type is not None):
                        if network_type != "vlan":
                            command = [
                                "/opt/xcat/bin/chdef",
                                node_name,
                                f"nictypes.{network_nic}={network_type}",
                                f"nicips.{network_nic}={network_ip}",
                                f"nicnetworks.{network_nic}={network_name}"
                            ]
                            subprocess.run(command, check=False)
                        else:
                            sql_query_network = (
                                f"SELECT {network_name}_device FROM cluster.nicinfo "
                                f"WHERE id = %s"
                            )
                            cursor.execute(sql_query_network, (row[0],))
                            primary_nic = cursor.fetchone()

                            if primary_nic[0]:
                                command = [
                                    "/opt/xcat/bin/chdef",
                                    node_name,
                                    f"nictypes.{primary_nic[0]}=ethernet",
                                    f"nicips.{network_nic}={network_ip}",
                                    f"nicnetworks.{network_nic}={network_name}",
                                    f"nictypes.{network_nic}={network_type}",
                                    f"nicdevices.{network_nic}={primary_nic[0]}",
                                    f"nichostnamesuffixes.{network_nic}=-{primary_nic[0]}"
                                ]
                                subprocess.run(command, check=False)
                        if network_metric and shlex.quote(network_info['network_gateway']):
                            command = [
                                "/opt/xcat/bin/chdef",
                                node_name,
                                (f"nicextraparams.{network_nic}="
                                 f"{network_metric}-{shlex.quote(network_info['network_gateway'])}")
                            ]
                            subprocess.run(command, check=False)

                if not INVENTORY_STATUS:
                    command = [
                        "/opt/xcat/bin/updatenode",
                        node_name,
                        "-P",
                        "confignetwork,omnia_hostname"
                    ]
                    subprocess.run(command, check=False)
                    time.sleep(1)
            else:
                print(f"No NIC update required for node: {node_name}")

    # Close the cursor and connection
    cursor.close()
    conn.close()


update_node_obj()
