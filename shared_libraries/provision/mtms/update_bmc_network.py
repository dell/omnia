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
This module provides functionality for updating the xCAT networks table
with details of various BMC discovery ranges inserted as a network.
"""

import re
import subprocess
import sys
import calculate_ip_details

def validate(ip_range):
    """
    Validates the format of an IP range.

    Args:
        ip_range (str): The IP range to validate.

    Returns:
        str: The validated IP range.

    Raises:
        ValueError: If the IP range format is invalid.
    """
    # Define regex patterns
    cidr_pattern = r'^(\d{1,3}\.){3}\d{1,3}/\d{1,2}$'
    range_pattern = r'^(\d{1,3}\.){3}\d{1,3}-\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$'
    valid_pattern = f'({cidr_pattern}|{range_pattern}|0.0.0.0)'
    ip_range = ip_range.strip()
    if not re.fullmatch(valid_pattern, ip_range):
        raise ValueError("Invalid IP range format")
    return ip_range

discovery_ranges = sys.argv[1]
netmask_bits = sys.argv[2]


def create_network_name(nw_name, subnet):
    """
	Create a network name based on the given network name and subnet.

	Args:
	    nw_name (str): The base network name.
	    subnet (str): The subnet address.

	Returns:
	    str: The generated network name.
	"""

    subnet = str(subnet)
    temp = subnet.split('.')
    n_w_name = nw_name + "_" + temp[0] + "_" + temp[1] + "_" + temp[2] + "_" + temp[3]
    return n_w_name


def update_networks_table():
    """
	Inserts the network details in the xCAT networks table.

	This function takes a comma-separated string of IP ranges and a netmask,
	validates the IP ranges, and inserts the network details in the xCAT
	networks table.

	Parameters:
	- None

	Returns:
	- None

	Raises:
	- subprocess.CalledProcessError: If there is an error while running the
		command to insert the network details.
	"""

    ip_ranges = []
    if discovery_ranges:
        ip_ranges = discovery_ranges.split(',')

    for ip_range in ip_ranges:
        ip_obj = validate(ip_range)
        start_ip, end_ip = ip_obj.split('-')
        details = calculate_ip_details.cal_ip_details(start_ip, netmask_bits)
        netmask = details[0]
        subnet = details[1]
        network_name = create_network_name("bmc_network", subnet)
        command = ["/opt/xcat/bin/chdef", "-t", "network", "-o", network_name, f"net={subnet}", f"mask={netmask}", f"staticrange={start_ip}-{end_ip}"]
        try:
            subprocess.run(command, capture_output=True, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error: {e}")


update_networks_table()