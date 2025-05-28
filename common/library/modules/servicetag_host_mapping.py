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

"""
Ansible module for managing inventory sources.

This module provides an interface for managing inventory sources in Ansible.
It allows users to specify the inventory sources to use for a particular
playbook or role.

:param inventory_sources: A string specifying the inventory sources to use.
:type inventory_sources: str
:required: True
"""

import os
from ansible.module_utils.basic import AnsibleModule
import  ansible.module_utils.discovery.omniadb_connection as omniadb # pylint: disable=all

module = AnsibleModule(argument_spec={
    'inventory_sources': {'type': 'str', 'required': True}
})

INVENTORY_SOURCES_STR = module.params['inventory_sources']
CONNECTION = None
CURSOR = None

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
        inventory_sources_list = []
        any_changes = False
        if INVENTORY_SOURCES_STR:
            # Get the list of inventory files
            inventory_sources_list = INVENTORY_SOURCES_STR[1:-1].split(',')

        # Iterate through all inventory files and modify them
        for inventory_file_path in inventory_sources_list:
            inventory_file_path = os.path.abspath(inventory_file_path.strip("'| "))
            module.warn(f"Inventory file path: {inventory_file_path}")

            # If inventory file don't exist ignore.
            if not os.path.exists(inventory_file_path) or not os.path.basename(inventory_file_path):
                module.warn(f"Inventory file: {inventory_file_path} does not exist.")
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
                result_lines, is_content_modified = update_inventory_file_entries(
                    inventory_file_path, lines, result_lines, is_content_modified)

            if is_content_modified:
                any_changes = True
                # Write the modified lines back to the file
                with open(inventory_file_path, 'w', encoding='utf-8') as f:
                    for line in result_lines:
                        f.write(f"{line}\n")

        # Close the cursor and connection
        CURSOR.close()
        CONNECTION.close()

        if not any_changes:
            module.exit_json(changed=False, msg="No changes made to inventory files.")
        else:
            module.exit_json(changed=True, msg="Inventory updated successfully.")

    except (ValueError, OSError) as err:
        # Close the cursor and connection
        if CURSOR:
            CURSOR.close()
        if CONNECTION:
            CONNECTION.close()
        module.fail_json(msg=f"servicetag_host_mapping: {type(err).__name__}: {err}")

def update_inventory_file_entries(
        inventory_file_path,
        lines,
        result_lines,
        is_content_modified
        ):
    """
    Updates inventory file entries by querying the database for host IP addresses.

    Parameters:
        inventory_file_pathlines (list): A list of lines in the inventory file.
        lines (list): A list of lines to update in the inventory file.
        is_content_modified (bool): A flag indicating whether the content has been modified.

    Returns:
        list: A list of updated inventory file entries.
    """
    for next_line in lines:
        if next_line.strip():
            group_status = False
            token = next_line.split()
            if 'Categories' not in token[0]:
                host = token[0].strip().lower()
                if len(token) > 1:
                    group_status = True
                if host == 'localhost':
                    raise ValueError(
                        f"localhost entry is an invalid entry in "
                        f"'{inventory_file_path}'"
                    )
                # Check if the line have a service tag, node name or hostname
                # but doesn't have ansible_host
                if host and host.isalnum() and "ansible_host=" not in next_line:

                    next_line, is_content_modified = get_host_admin_ip(
                        host, group_status, token)

        # Append service tag string to result lines.
        result_lines.append(next_line.strip())
    return result_lines, is_content_modified

def host_ip_update(row, host, group_status, token):
    """
    Updates a host IP based on a given row, group status, and token.

    Parameters:
        row (list): A list containing a host IP.
        group_status (bool): A boolean indicating whether the host is part of a group.
        token (list): A list containing a hostname and a group name.

    Returns:
        tuple: A tuple containing the updated host IP and a 
               boolean indicating whether the content has been modified.
    """
    # Collect host ip if result is valid
    host_ip = row[0]
    # Append host IP to hostname
    if group_status:
        host = f"{host} {token[1]}"
    next_line = f"{host} ansible_host={host_ip}"
    # Mark content as modified
    is_content_modified = True
    return next_line, is_content_modified

def get_host_admin_ip(host, group_status, token):
    """
    Retrieves the admin IP address of a host from the 
    database using service tag, node name, or hostname.

    Parameters:
        cursor (object): Database cursor for executing queries.
        host (str): The identifier for the host (could be service tag, node name, or hostname).
        group_status (str): Status used in the host_ip_update function.
        token (str): Token used in the host_ip_update function.

    Returns:
        tuple: (next_line, is_content_modified) if found, else (None, False)
    """
    # Try to get IP using service tag or node name
    query = "SELECT admin_ip FROM cluster.nodeinfo WHERE service_tag=%s OR node=%s"
    params = (host.upper(), host)
    CURSOR.execute(query, params)
    row = CURSOR.fetchone()

    if row:
        return host_ip_update(row, host, group_status, token)
    # Try to get IP using hostname
    query = "SELECT admin_ip FROM cluster.nodeinfo WHERE hostname=%s"
    params = (host,)
    CURSOR.execute(query, params)
    row = CURSOR.fetchone()

    if row:
        return host_ip_update(row, host, group_status, token)

    return None, False

if __name__ == "__main__":
    CONNECTION = omniadb.create_connection()
    CURSOR = CONNECTION.cursor()
    try:
        service_tag_host_mapping()
    except ValueError as e:
        module.fail_json(msg=f"servicetag_host_mapping: {str(e)}")
