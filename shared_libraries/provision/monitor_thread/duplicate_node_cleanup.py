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

import threading
import subprocess
import sys

db_file_path = sys.argv[1]             

sys.path.insert(0, db_file_path)

import omniadb_connection

discovery_mechanism_mtms='mtms'

# CleanupThread is a thread class which reads node details every 30 mins 
# and deletes duplicate nodes
class CleanupThread(threading.Thread):
    def run(self):
        """
        Runs the delete_duplicate_node function.

        This function calls the delete_duplicate_node function, which deletes duplicate nodes created.
        It also deletes the entry for the database and the node object.

        Parameters:
            None

        Returns:
            None
        """
        delete_duplicate_node()

def delete_duplicate_node():
    """
	Delete duplicate nodes created.
	Delete entry for db and node object.

	Parameters:
	    None

	Returns:
	    None
	"""

    conn = omniadb_connection.create_connection()
    cursor = conn.cursor()
    
    sql = f"select service_tag from cluster.nodeinfo group by service_tag having (count(*) > 1)"
    cursor.execute(sql)
    service_tag_output = cursor.fetchall()

    for i in range(0, len(service_tag_output)):
        if service_tag_output[i][0] is not None:
            service_tag_output[i] = str(service_tag_output[i][0])

            print(f"Duplicate service tag: {service_tag_output[i]}")

            # Fetch the node name for duplicate node
            sql = f"select node from cluster.nodeinfo where service_tag='{service_tag_output[i]}' and admin_mac is NULL and (status is NULL or status!='booted')"
            cursor.execute(sql)
            node_output = cursor.fetchone()

            if node_output is not None:
                node_name = node_output[0]

                # Delete entry from cluster.nodeinfo table
                sql = f"delete from cluster.nodeinfo where node='{node_name}' and service_tag='{service_tag_output[i]}' and admin_mac is NULL"
                cursor.execute(sql)

                # Delete the entry from /etc/hosts
                command = ['/opt/xcat/sbin/makehosts', '-d', node_name]
                temp = subprocess.run(command, shell=False, check=False)

                # Delete the nodes from xcat
                command = ['/opt/xcat/bin/rmdef', node_name]
                temp = subprocess.run(command, shell=False, check=False)

                # Run DHCP and dns
                command = ['/opt/xcat/sbin/makedhcp', '-n']
                temp = subprocess.run(command, shell=False, check=False)

                command = ['/opt/xcat/sbin/makedhcp', '-a']
                temp = subprocess.run(command, shell=False, check=False)

                command = ['/opt/xcat/sbin/makedns', '-n']
                temp = subprocess.run(command, shell=False, check=False)

                print(f"Deleted node {node_name}")

    cursor.close()    
    conn.close()

def main():
    """
    The main function that starts the CleanupThread.

    This function creates an instance of the CleanupThread class and sets its Daemon attribute to True.
    It then starts the CleanupThread.

    If an exception occurs during the execution of the CleanupThread, the exception is caught and the
    message "Exception thrown by the cleanup thread: <exception message>" is printed. The program
    exits with a status code of 1.

    Parameters:
        None

    Returns:
        None
    """
    try:
        CleanupThreadObject = CleanupThread()
        CleanupThreadObject.Daemon = True
        CleanupThreadObject.start()
    except Exception as e:
        print("Exception thrown by the cleanup thread:", e)
        sys.exit(1)

if __name__ == '__main__':
    main()
