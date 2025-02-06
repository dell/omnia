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

db_path = sys.argv[1]
inventory_sources_str = sys.argv[2]

sys.path.insert(0, db_path)

import omniadb_connection as omniadb

def service_tag_host_mapping():
    """
    Maps service tags or node names to host names in inventory files.

    This function connects to a database and iterates through a list of inventory files.
    For each file, it reads the content and modifies the lines that contain service tags,
    node names, or hostnames but do not have the ansible_host parameter. It queries the
    database to get the corresponding host IP for each service tag or node name. If a
    host IP is found, it appends the host IP to the service tag or node name and marks
    the content as modified.

    Parameters:
        None

    Returns:
        None

    Raises:
        ValueError: If a localhost entry is found in an inventory file.
        OSError: If there is an error opening or writing to an inventory file.
        Exception: If there is an error executing a database query.
    """
    try:
        # Create a database connection
        connection = omniadb.create_connection()
        cursor = connection.cursor()
        inventory_sources_list = []
        if inventory_sources_str:
            # Get the list of inventory files
            inventory_sources_list = inventory_sources_str[1:-1].split(',')

        # Iterate through all inventory files and modify them
        for inventory_file_path in inventory_sources_list:
            inventory_file_path = os.path.abspath(inventory_file_path.strip("'| "))
            print("inventory_file_path: " + inventory_file_path)

            # If inventory file don't exist ignore.
            if not os.path.exists(inventory_file_path) or not os.path.basename(inventory_file_path):
                syslog.syslog(syslog.LOG_INFO,
                              f"servicetag_host_mapping:service_tag_host_mapping(): Inventory file: {inventory_file_path} do not exist.")
                continue

            # Write file only if content is modified.
            is_content_modified = False

            # Variable to store modified lines
            result_lines = []
            lines = []
            # Open file in read mode
            with open(inventory_file_path, "r", encoding='utf-8') as f:
                # Read the content of the file
                lines = f.readlines()

            if lines:
                # Iterate content line by line
                for next_line in lines:
                    if next_line.strip(): 
                        group_status = False
                        token = next_line.split()
                        if 'Categories' not in token[0]:
                            host = token[0].strip().lower()
                            
                            if len(token) > 1:
                                group_status = True
                            if host == 'localhost':
                                raise ValueError(f"localhost entry is an invalid entry in '{inventory_file_path}'")

                            # Check if the line have a service tag, node name or hostname but don't have ansible_host
                            if host and host.isalnum() and "ansible_host=" not in next_line:

                                # Query string: get host IP if service tag or node name is given
                                query = "select admin_ip from cluster.nodeinfo where service_tag=%s or node=%s"
                                params = (host.upper(), host)

                                # Query execution
                                cursor.execute(query, params)
                                row = cursor.fetchone()

                                if row:
                                    # Collect host ip if result is valid
                                    host_ip = row[0]
                                    # Append host IP to service tag/node name
                                    if group_status:
                                        host = f"{host} {token[1]}"
                                    
                                    next_line = f"{host} ansible_host={host_ip}"
                                    # Mark content as modified
                                    is_content_modified = True
                                else:
                                    # Query string get host IP if hostname is given
                                    query = "select admin_ip from cluster.nodeinfo where hostname=%s"
                                    params = (host,)

                                    # Query execution
                                    cursor.execute(query, params)
                                    row = cursor.fetchone()

                                    if row:
                                        # Collect host ip if result is valid
                                        host_ip = row[0]
                                        # Append host IP to hostname
                                        if group_status:
                                            host = f"{host} {token[1]}"
                                        next_line = f"{host} ansible_host={host_ip}"
                                        # Mark content as modified
                                        is_content_modified = True


                    # Append service tag string to result lines.
                    result_lines.append(next_line.strip())

            if is_content_modified:
                # Write the modified lines back to the file
                with open(inventory_file_path, 'w', encoding='utf-8') as f:
                    for line in result_lines:
                        f.write(f"{line}\n")

        # Close the cursor and connection
        cursor.close()
        connection.close()
    except (ValueError) as err:
        print(f'{type(err).__name__}: {err}')
    except (OSError, Exception) as err:
        print(f"servicetag_host_mapping: service_tag_host_mapping: {type(err).__name__}: {err}")


if __name__ == "__main__":
    service_tag_host_mapping()
