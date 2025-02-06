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


groups_switch_based = 'switch_based,all'

def create_node_object(conn):
    """
	Create node objects in the database based on switch information.

	Parameters:
	conn (object): The database connection object.

	Returns:
	None
	"""


    cursor = conn.cursor()
    sql = '''select switch_name,switch_port from cluster.nodeinfo where switch_port is not NULL'''
    cursor.execute(sql)
    switch_port_output = cursor.fetchall()

    for i in range(0, len(switch_port_output)):
        if switch_port_output[i][0] is not None:
            
            switch_name=switch_port_output[i][0]
            switch_port=switch_port_output[i][1]
            
            sql = f"select node,admin_ip,bmc_ip,switch_name,switch_port from cluster.nodeinfo where switch_port='{switch_port}' and switch_name='{switch_name}'"
            cursor.execute(sql)
            row_output = cursor.fetchone()

            command = ["/opt/xcat/bin/chdef", row_output[0], f"groups={groups_switch_based}", "mgt=ipmi", "cons=ipmi", f"ip={row_output[1]}", f"bmc={row_output[2]}", "netboot=xnba", "installnic=mac", "primarynic=mac", f"switch={row_output[3]}", f"switchport={row_output[4]}"]
            subprocess.run(command)

            print(f"Created node object with name {row_output[0]}")

    cursor.close()

def main():
    """
    Executes the main function of the program.

    This function establishes a connection with omniadb and calls the `create_node_object` function.
    It then closes the database connection.

    Parameters:
		None

    Returns:
    	None
    """

    conn = omniadb_connection.create_connection()
    create_node_object(conn)
    conn.close()

if __name__ == '__main__':
    main()
