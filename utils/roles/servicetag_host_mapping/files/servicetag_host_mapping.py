#  Copyright 2024 Dell Inc. or its subsidiaries. All Rights Reserved.
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

role_path = sys.argv[1]
file_path = sys.argv[2]
inventory_sources_str = sys.argv[3]
db_path = role_path + file_path

sys.path.insert(0, db_path)

import omniadb_connection as omniadb

def service_tag_host_mapping():
    """
    Modifies the inventory files by adding the corresponding host IP for each service tag.

    This function iterates through a list of inventory files and 
    modifies them by adding the host IP for each service tag. 
    """
    try:
        # Create a database connection
        connection = omniadb.create_connection()
        cursor = connection.cursor()

        # Get the list of inventory files
        inventory_sources_list = inventory_sources_str[1:-1].split(',')

        # Iterate through all inventory files and modify them
        for inventory_file_path in inventory_sources_list:

            # If inventory file don't exist ignore.
            if not os.path.exists(inventory_file_path) or not os.path.basename(inventory_file_path):
                syslog.syslog(syslog.LOG_INFO,
                              f"servicetag_host_mapping:service_tag_host_mapping(): Inventory file: {inventory_file_path} do not exist.")
                continue

            # Write file only if content is modified.
            is_content_modified = False

            # Variable to store modified lines
            result_lines = []

            # Open file in read mode
            with open(inventory_file_path, "r", encoding='utf-8') as f:

                # Read the content of the file
                lines = f.readlines()

                # Iterate content line by line
                for line in lines:
                    line = line.strip().lower()

                    if line == 'localhost':
                        raise ValueError(f"localhost entry is an invalid entry in '{inventory_file_path}'")

                    # Check if the line have a service tag, node name or hostname but don't have ansible_host
                    if line and line[0].isalnum() and "ansible_host=" not in line:

                        # Query string: get host IP if service tag or node name is given
                        query = "select admin_ip from cluster.nodeinfo where service_tag=%s or node=%s"
                        params = (line.upper(), line)

                        # Query execution
                        cursor.execute(query, params)
                        row = cursor.fetchone()

                        if row:
                            # Collect host ip if result is valid
                            host_ip = row[0]
                            # Append host IP to service tag/node name
                            line = f"{line} ansible_host={host_ip}"
                            # Mark content as modified
                            is_content_modified = True
                        else:
                            # Query string get host IP if hostname is given
                            query = "select admin_ip from cluster.nodeinfo where hostname=%s"
                            params = (line,)

                            # Query execution
                            cursor.execute(query, params)
                            row = cursor.fetchone()

                            if row:
                                # Collect host ip if result is valid
                                host_ip = row[0]
                                # Append host IP to hostname
                                line = f"{line} ansible_host={host_ip}"
                                # Mark content as modified
                                is_content_modified = True


                    # Append service tag string to result lines.
                    result_lines.append(line)

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
