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

import commentedconfigparser
import os
import syslog
from psycopg2.extensions import cursor

def get_count(line: str) -> int:
    """
	Splits a line of text by the '=' character and returns the second element of the resulting list as an integer.

	Parameters:
		line (str): The line of text to be split.

	Returns:
		int: The second element of the split line as an integer. If the split line has only one element, returns 0.
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
	Retrieves the node information from the database.

	Parameters:
		cursor (cursor): The cursor object used to execute the SQL query.
		node (str): The node name.

	Returns:
		tuple: A tuple containing the service tag, admin IP, CPU, GPU, CPU count, GPU count, status, admin MAC, and hostname of the node.
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
            admin_mac,
            hostname
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
		node (str): The name of the node.

	Returns:
		tuple: A tuple containing the updated CPU and GPU information.
				The tuple contains the following elements:
					- cpu (str): The type of CPU.
					- gpu (str): The type of GPU.
					- cpu_count (int): The count of CPU.
					- gpu_count (int): The count of GPU.

	Raises:
		FileNotFoundError: If the log file is not found.
		IOError: If there is an issue reading the log file.
		Exception: If there is any other exception.
	"""

    # Define the strings to search for GPU and CPU
    nvidia_gpu_str = "NVIDIA GPU Found"
    amd_gpu_str = "AMD GPU Found"
    no_gpu_str = "No GPU Found"
    intel_cpu_str = "Intel CPU Found"
    amd_cpu_str = "AMD CPU Found"
    intel_gpu_str = "Intel GPU Found"
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
            if contents:
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
                            # Check if the Intel GPU str is present in the line
                            elif intel_gpu_str in line:
                                gpu = "intel"
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
	Update the database with the provided updated node information.

	Parameters:
		cursor (cursor): The cursor object used to execute the SQL query.
		node (str): The name of the node.
		updated_node_info (tuple): A tuple containing the updated CPU, GPU, CPU count, and GPU count.

	Returns:
		None
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


def remove_hostname_inventory(inventory_file: str, hostname: str) -> None:
    """
	Remove a hostname from the inventory file.

	Parameters:
		inventory_file (str): The path to the inventory file.
		hostname (str): The hostname to remove.

	Returns:
		None
	"""

    try:
        # Read the inventory file
        config = commentedconfigparser.CommentedConfigParser(allow_no_value=True)
        config.read(inventory_file, encoding='utf-8')

        # Change the permission of the file
        os.chmod(inventory_file, 0o644)

        # Remove hostname if exists in the inventory file
        if not config.remove_option(inventory_file, hostname):
            # Log a message if the hostname is not found
            syslog.syslog(syslog.LOG_INFO, f"parse_syslog:remove_hostname_inventory: '{hostname}' is not found in '{inventory_file}'")
            return

        # Write the updated inventory file
        with open(inventory_file, 'w', encoding='utf-8') as configfile:
            config.write(configfile, space_around_delimiters=False)

    except (OSError,
            Exception) as err:
        syslog.syslog(syslog.LOG_ERR, f"parse_syslog:remove_hostname_inventory: {str(type(err))} {str(err)}")
    finally:
        # Change the permission of the file to readonly
        os.chmod(inventory_file, 0o444)


def add_hostname_inventory(inventory_file: str, hostname: str) -> None:
    """
	Adds a hostname to the inventory file.

	Parameters:
		inventory_file (str): The path to the inventory file.
		hostname (str): The hostname to add.

	Returns:
		None
	"""

    try:
        # Read the config file
        config = commentedconfigparser.CommentedConfigParser(allow_no_value=True)
        config.read(inventory_file, encoding='utf-8')

        # Change the permission of the file
        os.chmod(inventory_file, 0o644)

        # Set the hostname
        config.set(inventory_file, hostname)

        # Write the inventory file
        with open(inventory_file, 'w', encoding='utf-8') as configfile:
            config.write(configfile, space_around_delimiters=False)

    except (OSError,
            Exception) as err:
        syslog.syslog(syslog.LOG_ERR, f"parse_syslog:add_hostname_inventory: {str(type(err))} {str(err)}")
    finally:
        # Change the permission of the file to readonly
        os.chmod(inventory_file, 0o444)


def update_inventory(node_info_db: tuple, updated_node_info: tuple) -> None:
    """
	Update the inventory files based on the changes in the node information.

	Parameters:
		node_info_db (tuple): A tuple containing the service tag, admin IP, CPU, GPU, and hostname from the database.
		updated_node_info (tuple): A tuple containing the updated CPU and GPU information.

	Returns:
		None

	Raises:
		Exception: If an error occurs during the update process.
    """

    try:
        # Unpack the node information from the tuples
        service_tag, admin_ip, db_cpu, db_gpu, hostname = node_info_db[0], node_info_db[1], node_info_db[2], node_info_db[3], node_info_db[8]
        updated_cpu, updated_gpu = updated_node_info[0], updated_node_info[1]

        # No modification in inventory if no hostname
        if not hostname:
            return

        # Change the current working directory to the inventory directory
        curr_dir = os.getcwd()
        omnia_inventory_dir = "/opt/omnia/omnia_inventory/"
        if curr_dir != omnia_inventory_dir:
            os.chdir(omnia_inventory_dir)

        # Update inventory files if the CPU has been modified
        if updated_cpu != db_cpu:
            if db_cpu:
                # Remove existing hostname from corresponding inventory file
                inventory_file_str = "compute_cpu_intel" if db_cpu == "intel" else "compute_cpu_amd"
                remove_hostname_inventory(inventory_file_str, hostname)
            if updated_cpu:
                # Add hostname to corresponding inventory file
                inventory_file_str = "compute_cpu_intel" if updated_cpu == "intel" else "compute_cpu_amd"
                add_hostname_inventory(inventory_file_str, hostname)
                # Add hostname and admin ip to compute_hostname_ip inventory file
                hostname_ip_str = f"{hostname} ansible_host={admin_ip}"
                add_hostname_inventory("compute_hostname_ip", hostname_ip_str)

        # Update inventory files if the GPU has been modified
        if updated_gpu != db_gpu:
            if db_gpu:
                # Remove existing hostname from corresponding inventory file
                if db_gpu == "nvidia":
                    inventory_file_str = "compute_gpu_nvidia"
                elif db_gpu == "amd":
                    inventory_file_str = "compute_gpu_amd"
                elif db_gpu == "intel":
                    inventory_file_str = "compute_gpu_intel"
                remove_hostname_inventory(inventory_file_str, hostname)
            if updated_gpu:
                # Add hostname to corresponding inventory file
                if updated_gpu == "nvidia":
                    inventory_file_str = "compute_gpu_nvidia"
                elif updated_gpu == "amd":
                    inventory_file_str = "compute_gpu_amd"
                elif updated_gpu == "intel":
                    inventory_file_str = "compute_gpu_intel"
                add_hostname_inventory(inventory_file_str, hostname)
    except Exception as e:
        syslog.syslog(syslog.LOG_ERR, f"parse_syslog:update_inventory: Exception occurred: {str(type(e))} {str(e)}")
