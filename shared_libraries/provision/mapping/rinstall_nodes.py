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
import subprocess

db_path = sys.argv[1]
sys.path.insert(0, db_path)

import omniadb_connection
discovery_mechanism = "mapping"


def provision_map_nodes_bmc():
    """
    Retrieves a list of nodes based on the discovery mechanism from the cluster.nodeinfo database.
    Then, checks if each node exists in the nodelist table of the xcatdb.
    If a node exists, it runs the rinstall command.

    Parameters:
        None

    Returns:
        None
    """

    # Establish connection with cluster.nodeinfo
    conn = omniadb_connection.create_connection()
    cursor = conn.cursor()
    sql = "SELECT node FROM cluster.nodeinfo WHERE discovery_mechanism = %s AND bmc_ip IS NOT NULL"
    cursor.execute(sql, (discovery_mechanism,))
    node_name = cursor.fetchall()
    cursor.close()
    conn.close()

    # Establish connection with xcatdb
    conn_x = omniadb_connection.create_connection_xcatdb()
    cursor_x = conn_x.cursor()
    mapping_bmc_nodes = []
    for node in node_name:
        sql = "SELECT exists(SELECT node FROM nodelist WHERE node = %s AND status IS NULL)"
        cursor_x.execute(sql, (node[0],))
        op = cursor_x.fetchone()[0]
        if op:
            mapping_bmc_nodes.append(node[0])
            command = f"/opt/xcat/bin/rinstall {node[0]}"
            command_list = command.split()
            node_objs = subprocess.run(command_list, capture_output=True)
    print(mapping_bmc_nodes)
    cursor_x.close()
    conn_x.close()


provision_map_nodes_bmc()