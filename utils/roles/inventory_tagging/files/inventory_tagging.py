# Copyright 2023 Dell Inc. or its subsidiaries. All Rights Reserved.
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
import configparser
import sys


db_path = sys.argv[1]
omnia_inventory_dir_path = sys.argv[2]
sys.path.insert(0, db_path)

import omniadb_connection

def add_inventory_files(inventory_filename_list: list[str]) -> None:
    """
    Create inventory files.

    Args:
        inventory_filename_list (list[str]): A list of filenames for the inventory files.
    """
    # Create the directory if it doesn't exist
    if not os.path.exists(omnia_inventory_dir_path):
        os.makedirs(omnia_inventory_dir_path, mode=0o644)
    
    # Iterate over the inventory filenames
    for filename in inventory_filename_list:
        file_path = os.path.join(omnia_inventory_dir_path, filename)
        with open(file_path, 'w', encoding='utf-8') as file:
            # Write the group name to the file
            group_name = f"[{filename}]"
            file.write(group_name)
    

def get_cluster_details_db():
    """
    Retrieves the cluster details from the database.
    Returns:
        nodes_info (list): A list of tuples containing the service tag, admin IP, CPU, and GPU of each node in the cluster.
    """
    # Create a connection to the database
    conn = omniadb_connection.create_connection()
    cursor = conn.cursor()

    # Define the SQL query to retrieve the nodes information
    query = """
        SELECT
            node,
            service_tag,
            admin_ip,
            cpu,
            gpu
        FROM
            cluster.nodeinfo
        WHERE
            status = 'booted'
    """

    # Execute the SQL query
    cursor.execute(query)

    # Fetch all the rows returned by the query
    nodes_info = cursor.fetchall()
    
    # Close the database connection
    conn.close()

    # Return the nodes information
    return nodes_info


def add_servicetag_inventory(inventory_file: str, service_tag: str) -> None:
    """
    Adds a service tag to the inventory file.
    Args:
        inventory_file (str): The path to the inventory file.
        service_tag (str): The service tag to add.
    """
    try:
        # Read the config file
        config = configparser.ConfigParser(allow_no_value=True)
        config.read(inventory_file, encoding='utf-8')
        
        # Set the service tag
        config.set(inventory_file, service_tag)
        
        # Write the inventory file
        with open(inventory_file, 'w', encoding='utf-8') as configfile:
            config.write(configfile, space_around_delimiters=False)
    except (configparser.DuplicateOptionError,
            configparser.DuplicateSectionError,
            configparser.NoSectionError,
            Exception) as err:
        print(f'''inventory_tagging:add_servicetag_inventory: 
              Error adding service tag {service_tag} to inventory file {inventory_file}.
              Error type: {str(type(err))}. 
              Error message: {str(err)}''')


def update_inventory(node_detail):
    """
    Update the inventory based on the given node details.
    Args:
        node_detail (tuple): A tuple containing the service tag, admin IP, CPU, and GPU.
    Returns:
        None
    """
    # Unpack the node_detail tuple
    node, service_tag, admin_ip, cpu, gpu = node_detail

    # Check if service_tag is empty or None
    if not service_tag:
        # Inventory files will not be updated if service_tag is empty or None
        print(f'''inventory_tagging:update_inventory: 
              Service tag is unavailable for node {node}, skipping inventory update.''')
        return

    try:
        # Change the working directory to /opt/omnia/omnia_inventory
        if os.getcwd() != omnia_inventory_dir_path:
            os.chdir(omnia_inventory_dir_path)
    except OSError as err:
         # Log an error message if changing directory fails
        print(f'''inventory_tagging:update_inventory: 
              Error changing current working directory to {omnia_inventory_dir_path}.
              Error type: {str(type(err))}. 
              Error message: {str(err)}''')

    # Update inventory files based on CPU info
    if cpu:
        # Add service tag to corresponding inventory file
        inventory_file_str = "compute_cpu_intel" if cpu == "intel" else "compute_cpu_amd"
        add_servicetag_inventory(inventory_file_str, service_tag)
        # Add service tag and admin ip to compute_servicetag_ip inventory file
        service_tag_ip_str = f"{service_tag} ansible_host={admin_ip}"
        add_servicetag_inventory("compute_servicetag_ip", service_tag_ip_str)
    
    # Update inventory files based on GPU info
    if gpu:
        inventory_file_str = "compute_gpu_nvidia" if gpu == "nvidia" else "compute_gpu_amd"
        add_servicetag_inventory(inventory_file_str, service_tag)


def change_inventory_file_permission(inventory_files: list[str]):
    """
    Change the permission of the inventory files to read-only.
    Args:
        inventory_files (list[str]): A list of inventory files to change permission.
    """
    # Iterate over the inventory files
    for inventory_file in inventory_files:
        try:
            # Change the permission of the file to read-only
            os.chmod(inventory_file, 0o444)
        except OSError as err:
            # Log the error if changing the permission fails
            print(f'''inventory_tagging:change_inventory_file_permission: 
              Error changing file permission to read-only for {inventory_file}.
              Error type: {str(type(err))}. 
              Error message: {str(err)}''')


if __name__ == "__main__":
    # Define the list of inventory filenames
    inventory_files = ["compute_cpu_intel", "compute_cpu_amd", "compute_gpu_nvidia", "compute_gpu_amd", "compute_servicetag_ip"]
    add_inventory_files(inventory_files)                # Add new inventory files
    node_detail_list = get_cluster_details_db()         # Get details for all node from DB.
    for node_detail in node_detail_list:
        update_inventory(node_detail)                   # Update inventory files with service tag entries.
    change_inventory_file_permission(inventory_files)   # Change permission of inventory files to read-only.
