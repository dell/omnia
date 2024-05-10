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

import configparser
import os
import syslog
from psycopg2.extensions import cursor

def get_count(line: str) -> int:
    """
    Given a string `line`, returns the integer value after the first occurrence of the '=' character, if any.
    Otherwise, returns 0.
    """
    # Split the input string by '=' character
    split_line = line.split('=')

    # If the split string has more than one element, return the second element as an integer
    if len(split_line) > 1:
        return int(split_line[1])
    
    # If the split string has only one element, return 0
    return 0


def get_node_info_db(cursor: cursor, node: str) -> tuple:
    """
    Retrieves node information from the database based on the given node.

    Parameters:
        cursor (Cursor): The database cursor object.
        node (str): The node for which to retrieve the information.

    Returns:
        tuple: A tuple containing the node information retrieved from the database.
    """
    # Define the SQL query to retrieve node information
    query = """
        SELECT 
            service_tag,
            admin_ip,
            cpu,
            gpu,
            cpu_count,
            gpu_count,
            status,
            admin_mac
        FROM 
            cluster.nodeinfo
        WHERE 
            node = %s
    """
    
    # Execute the SQL query with the given node
    cursor.execute(query, (node,))
    
    # Fetch the node info
    node_info = cursor.fetchone()
    
    # Return the node information
    return node_info


def get_updated_cpu_gpu_info(node: str) -> tuple:
    """
    Retrieves the updated CPU and GPU information for a given node.

    Parameters:
        node (str): The name of the node for which the information is retrieved.

    Returns:
        tuple: A tuple containing the CPU (str), GPU (str), CPU count (int), and GPU count (int).
    """
    # Define the strings to search for GPU and CPU
    nvidia_gpu_str = "NVIDIA GPU Found"
    amd_gpu_str = "AMD GPU Found"
    no_gpu_str = "No GPU Found"
    intel_cpu_str = "Intel CPU Found"
    amd_cpu_str = "AMD CPU Found"
    no_cpu_str = "No CPU Found"
    
    # Initialize variables
    cpu = ""
    cpu_count = 0
    gpu = ""
    gpu_count = 0
    gpu_found = False
    cpu_found = False
    
    # Define the path to the log file
    computes_log_file_path = '/var/log/xcat/computes.log'

    try:
        # Open the log file
        with open(computes_log_file_path, 'r', encoding='utf-8') as file:
            # Read the contents of the file
            contents = file.readlines()
            
            # Iterate over the lines in reverse order
            for line in reversed(contents):
                # Check if the node name is present in the line
                if node in line:
                    # Check if the GPU have been found
                    if gpu_found == False:
                        # Check if the Nvidia GPU str is present in the line
                        if nvidia_gpu_str in line:
                            gpu = "nvidia"
                            gpu_count = get_count(line)
                            gpu_found = True
                        # Check if the AMD GPU str is present in the line
                        elif amd_gpu_str in line:
                            gpu = "amd"
                            gpu_count = get_count(line)
                            gpu_found = True
                        # Check if the No GPU str is present in the line
                        elif no_gpu_str in line:
                            gpu_found = True

                    # Check if the CPU has been found
                    if cpu_found == False:
                        # Check if the Intel CPU str is present in the line
                        if intel_cpu_str in line:
                            cpu = "intel"
                            cpu_count = get_count(line)
                            cpu_found = True
                        # Check if the AMD CPU str is present in the line
                        elif amd_cpu_str in line:
                            cpu = "amd"
                            cpu_count = get_count(line)
                            cpu_found = True
                        # Check if the No CPU str is present in the line
                        elif no_cpu_str in line:
                            cpu_found = True
                    
                    # Break out of the loop if both GPU and CPU have been found
                    if cpu_found == True and gpu_found == True:
                        break
    
    except FileNotFoundError:
        # Log an error if the file is not found
        syslog.syslog(syslog.LOG_ERR, f"parse_syslog:get_updated_cpu_gpu_info: File '{computes_log_file_path}' not found")
    except IOError as err:
        # Log an error if there is an issue reading the file
        syslog.syslog(syslog.LOG_ERR, f"parse_syslog:get_updated_cpu_gpu_info: Error reading file '{computes_log_file_path}'")
    except Exception as err:
        # Log an error if there is any other exception
        syslog.syslog(syslog.LOG_ERR, f"parse_syslog:get_updated_cpu_gpu_info: Exception in '{computes_log_file_path}' parsing: " + str(type(err)) + " " + str(err))
    finally:
        # Return the CPU and GPU information
        return (cpu, gpu, cpu_count, gpu_count)


def update_db(cursor: cursor, node: str, updated_node_info: tuple) -> None:
    """
    Update the database with the updated node information.
    Args:
        cursor (cursor): The cursor object for executing SQL queries.
        node (str): The name of the node to update.
        updated_node_info (tuple): A tuple containing the updated information for the node.
    """
    # Unpack the updated node information tuple
    cpu, gpu, cpu_count, gpu_count = updated_node_info
    
    # Prepare the SQL query for updating the database
    sql_update_db = """
        UPDATE
            cluster.nodeinfo
        SET
            cpu = %s,
            gpu = %s,
            cpu_count = %s,
            gpu_count = %s
        WHERE
            node = %s
    """
    # Execute the SQL query with the updated parameters
    params = (cpu, gpu, cpu_count, gpu_count, node)
    cursor.execute(sql_update_db, params)


def remove_servicetag_inventory(inventory_file: str, service_tag: str) -> None:
    """
    Removes a service tag from the inventory file.

    Args:
        inventory_file (str): The name of the inventory file.
        service_tag (str): The service tag to remove.
    """
    try:
        # Read the inventory file
        config = configparser.ConfigParser(allow_no_value=True)
        config.read(inventory_file, encoding='utf-8')
        
        # Change the permission of the file
        os.chmod(inventory_file, 0o644)

        # Remove service tag if exists in the inventory file
        if not config.remove_option(inventory_file, service_tag):
            # Log a message if the service tag is not found
            syslog.syslog(syslog.LOG_INFO, f"parse_syslog:remove_servicetag_inventory: '{service_tag}' is not found in '{inventory_file}'")
            return
        
        # Write the updated inventory file
        with open(inventory_file, 'w', encoding='utf-8') as configfile:
            config.write(configfile, space_around_delimiters=False)

    except (configparser.DuplicateOptionError,
            configparser.DuplicateSectionError,
            configparser.NoSectionError,
            Exception) as err:
        syslog.syslog(syslog.LOG_ERR, f"parse_syslog:remove_servicetag_inventory: {str(type(err))} {str(err)}")
    finally:
        # Change the permission of the file to readonly
        os.chmod(inventory_file, 0o444)


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
        
        # Change the permission of the file
        os.chmod(inventory_file, 0o644)

        # Set the service tag
        config.set(inventory_file, service_tag)
        
        # Write the inventory file
        with open(inventory_file, 'w', encoding='utf-8') as configfile:
            config.write(configfile, space_around_delimiters=False)

    except (configparser.DuplicateOptionError,
            configparser.DuplicateSectionError,
            configparser.NoSectionError,
            OSError,
            Exception) as err:
        syslog.syslog(syslog.LOG_ERR, f"parse_syslog:add_servicetag_inventory: {str(type(err))} {str(err)}")
    finally:
        # Change the permission of the file to readonly
        os.chmod(inventory_file, 0o444)


def update_inventory(node_info_db: tuple, updated_node_info: tuple) -> None:
    """
    Update the inventory files based on the updated node information.
    
    Args:
        node_info_db (tuple): A tuple containing the node information from the database.
        updated_node_info (tuple): A tuple containing the updated node information.
    """
    
    try:
        # Unpack the node information from the tuples
        service_tag, admin_ip, db_cpu, db_gpu = node_info_db[0], node_info_db[1], node_info_db[2], node_info_db[3]
        updated_cpu, updated_gpu = updated_node_info[0], updated_node_info[1]
        
        # No modification in inventory if no service tag
        if not service_tag:
            return

        # Change the current working directory to the inventory directory
        curr_dir = os.getcwd()
        omnia_inventory_dir = "/opt/omnia/omnia_inventory/"
        if curr_dir != omnia_inventory_dir:
            os.chdir(omnia_inventory_dir)
        
        # Update inventory files if the CPU has been modified
        if updated_cpu != db_cpu:
            if db_cpu:
                # Remove existing service tag from corresponding inventory file
                inventory_file_str = "compute_cpu_intel" if db_cpu == "intel" else "compute_cpu_amd"
                remove_servicetag_inventory(inventory_file_str, service_tag)
            if updated_cpu:
                # Add service tag to corresponding inventory file
                inventory_file_str = "compute_cpu_intel" if updated_cpu == "intel" else "compute_cpu_amd"
                add_servicetag_inventory(inventory_file_str, service_tag)
                # Add service tag and admin ip to compute_servicetag_ip inventory file
                service_tag_ip_str = f"{service_tag} ansible_host={admin_ip}"
                add_servicetag_inventory("compute_servicetag_ip", service_tag_ip_str)
        
        # Update inventory files if the GPU has been modified
        if updated_gpu != db_gpu:
            if db_gpu:
                # Remove existing service tag from corresponding inventory file
                inventory_file_str = "compute_gpu_nvidia" if db_gpu == "nvidia" else "compute_gpu_amd"
                remove_servicetag_inventory(inventory_file_str, service_tag)
            if updated_gpu:
                # Add service tag to corresponding inventory file
                inventory_file_str = "compute_gpu_nvidia" if updated_gpu == "nvidia" else "compute_gpu_amd"
                add_servicetag_inventory(inventory_file_str, service_tag)
    except Exception as e:
        syslog.syslog(syslog.LOG_ERR, f"parse_syslog:update_inventory: Exception occurred: {str(type(e))} {str(e)}")
