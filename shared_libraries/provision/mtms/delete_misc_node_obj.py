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

import subprocess
import sys

db_path = sys.argv[1]
sys.path.insert(0, db_path)

import omniadb_connection

reg_value = "node-"


def extract_nodes():
    """
    Extracts nodes from the nodelist table in the xcatdb.

    This function connects to the xcatdb and retrieves the list of nodes from the nodelist table.
    It then iterates over the list of nodes and checks if the node name contains the value of the
    `reg_value` variable. If it does, it splits the node name by '-' and takes the last element
    (uppercased) as the `st` variable. It then executes a SQL query to check if the `service_tag`
    of the node exists in the `cluster.nodeinfo` table and the `bmc_mode` is either 'static' or NULL.
    If the query returns a positive result, it executes a command to remove the node from the
    nodelist using the `rmdef` command.

    Parameters:
        None

    Returns:
        None
    """
    conn = omniadb_connection.create_connection()
    cursor = conn.cursor()

    conn_x = omniadb_connection.create_connection_xcatdb()
    cursor_x = conn_x.cursor()
    sql = "SELECT node FROM nodelist"
    cursor_x.execute(sql)
    node_names = cursor_x.fetchall()
    for node in node_names:
        if reg_value in node[0]:
            st = node[0].split('-')[-1].upper()
            print(st)
            sql = f"select exists(select service_tag from cluster.nodeinfo where service_tag='{st}' and (bmc_mode='static' or bmc_mode is NULL))"
            cursor.execute(sql)
            op = cursor.fetchone()[0]
            if op:
                print(op)
                command = f"/opt/xcat/bin/rmdef {node[0]}"
                command_list = command.split()
                subprocess.run(command_list, capture_output=True)

    cursor_x.close()
    conn_x.close()
    cursor.close()
    conn.close()


extract_nodes()
