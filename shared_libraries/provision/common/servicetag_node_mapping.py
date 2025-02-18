#  Copyright 2025 Dell Inc. or its subsidiaries. All Rights Reserved.
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

import os
import sys
import syslog
import subprocess
import ipaddress

# Get input arguments
file_path = sys.argv[1]
inventory_hostname = sys.argv[2]
kernel_params = sys.argv[3]

# Add the database connection path
sys.path.insert(0, file_path)
import omniadb_connection as omniadb  # Import Omnia database connection module


def is_ip_address(value):
    """
    Checks if the given value is a valid IP address.

    Parameters:
        value (str): Input string to check.

    Returns:
        bool: True if valid IP, False otherwise.
    """
    try:
        ipaddress.ip_address(value)
        return True  # It's a valid IP address
    except ValueError:
        return False  # Not an IP address


def service_tag_node_mapping():
    """
    Retrieves the node name from the database based on the inventory hostname.

    If the input is an IP address, it queries `admin_ip`.
    Otherwise, it queries `service_tag` and `node`.
    If a matching node is found, it updates the kernel command line parameters using `chdef`.

    Returns:
        None

    Raises:
        Exception: If database queries or subprocess execution fails.
    """
    try:
        # Create a database connection
        connection = omniadb.create_connection()
        cursor = connection.cursor()

        node_name = ""

        # Determine the query type based on input
        if is_ip_address(inventory_hostname):
            query = "SELECT node FROM cluster.nodeinfo WHERE admin_ip=%s"
            params = (inventory_hostname,)
        else:
            query = "SELECT node FROM cluster.nodeinfo WHERE service_tag=%s OR node=%s"
            params = (inventory_hostname.upper(), inventory_hostname)

        # Execute the query
        cursor.execute(query, params)
        row = cursor.fetchone()

        if row:
            node_name = row[0]  # Extract node name
            print(f"Found node: {node_name}")
        else:
            syslog.syslog(
                syslog.LOG_INFO,
                f"service_tag_node_mapping: No node found for input: {inventory_hostname}",
            )

        # If a valid node is found, update kernel parameters
        if node_name:
            command = ["/opt/xcat/bin/chdef", node_name, f"addkcmdline={kernel_params}"]
            print(f"Executing command: {' '.join(command)}")
            subprocess.run(command, check=True)

        if not node_name:
           print(f"WARNING:service_tag_node_mapping: No node found for input: {inventory_hostname}", file=sys.stderr)
           sys.exit(1)  # Exit with error to trigger Ansible failure


        # Close the cursor and connection
        cursor.close()
        connection.close()

    except Exception as err:
        syslog.syslog(
            syslog.LOG_ERR,
            f"service_tag_node_mapping: Error occurred - {type(err).__name__}: {err}",
        )
        print(f"Error: {type(err).__name__}: {err}")


if __name__ == "__main__":
    service_tag_node_mapping()
