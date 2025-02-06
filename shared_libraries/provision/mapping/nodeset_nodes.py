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

"""
This module contains functions for validating and processing nodeset nodes.
"""

import sys
import subprocess

db_path = sys.argv[1]
sys.path.insert(0, db_path)
import omniadb_connection

DISCOVERY_MECHANISM = "mapping"

def validate_osimage(osimage):
    """
	Validates if the given `osimage` is a string.

	Parameters:
		osimage (Any): The object to be validated.

	Raises:
		ValueError: If `osimage` is not a string.

	Returns:
		None
	"""

    if not isinstance(osimage, str):
        raise ValueError("osimage must be a string")
    return osimage

def nodeset_mapping_nodes():
    """
    Retrieves the list of nodes from the `cluster.nodeinfo` table in the database
    and checks if each node is present in the `nodelist` table of the `xcatdb` database.
    If a node is present in both tables and status is NULL,
    it is added to the `new_mapping_nodes` list.
    The function then executes the `/opt/xcat/sbin/nodeset` command for each node in the
    `new_mapping_nodes` list with the specified `osimage` parameter.

    Parameters:
        None

    Returns:
        None
    """

    # Establish connection with cluster.nodeinfo
    conn = omniadb_connection.create_connection()
    cursor = conn.cursor()
    sql = "SELECT node FROM cluster.nodeinfo WHERE discovery_mechanism = %s"
    cursor.execute(sql, (DISCOVERY_MECHANISM,))
    node_name = cursor.fetchall()
    cursor.close()
    conn.close()

    osimage = validate_osimage(sys.argv[2])

    # Establish connection with xcatdb
    conn_x = omniadb_connection.create_connection_xcatdb()
    cursor_x = conn_x.cursor()
    new_mapping_nodes = []
    for node in node_name:
        sql = "SELECT exists(SELECT node FROM nodelist WHERE node = %s AND status IS NULL)"
        cursor_x.execute(sql, (node[0],))
        output = cursor_x.fetchone()[0]
        if output:
            new_mapping_nodes.append(node[0])
            command = ["/opt/xcat/sbin/nodeset", node[0], f"osimage={osimage}"]
            subprocess.run(command, capture_output=True, shell=False, check=True)

    print(new_mapping_nodes)
    cursor_x.close()
    conn_x.close()

nodeset_mapping_nodes()
