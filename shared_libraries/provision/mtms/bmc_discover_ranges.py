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
This module provides functionality for running BMC discovery on a range of IP addresses.
"""

import re
import sys, os
import subprocess
import calculate_ip_details


def validate(ip_range):
    """
    Validates an IP range.

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

if len(sys.argv) <= 3:
    bmc_dynamic_range = sys.argv[1]
    bmc_dynamic_range = validate(bmc_dynamic_range)
    dynamic_stanza = os.path.abspath(sys.argv[2])


# Pass proper variables
if len(sys.argv) > 3:
    discovery_ranges = sys.argv[1]
    discover_stanza = os.path.abspath(sys.argv[2])
    bmc_static_subnet = sys.argv[3]
    static_stanza = os.path.abspath(sys.argv[4])
    netmask_bits = sys.argv[5]
    bmc_static_range = sys.argv[6]
    bmc_static_range = validate(bmc_static_range)

def cal_ranges(start_ip, end_ip):
    """
	Generate a range of IP addresses based on the start and end IP addresses.

	Parameters:
	- start_ip (str): The starting IP address.
	- end_ip (str): The ending IP address.

	Returns:
	- range_status (str): The status of the range. "true" if the range is valid, "false" otherwise.
	- final_range (str): The generated range of IP addresses.
	"""

    final_range = ""
    range_status = "true"
    for i in range(0, 3):
        if int(start_ip[i]) == int(end_ip[i]):
            final_range = final_range + start_ip[i] + "."
        elif int(start_ip[i]) < int(end_ip[i]):
            final_range = final_range + start_ip[i] + "-" + end_ip[i] + "."
        elif int(start_ip[i]) > int(end_ip[i]):
            print("Please provide a proper range")
            range_status = "false"
    if int(start_ip[3]) == int(end_ip[3]):
        final_range = final_range + start_ip[3]
    elif int(start_ip[3]) < int(end_ip[3]):
        final_range = final_range + start_ip[3] + "-" + end_ip[3]
    elif int(start_ip[3]) > int(end_ip[3]):
        print("Please provide a proper range")
        range_status = "false"
    return range_status, final_range


def create_ranges_dynamic(bmc_mode):
    """
    Create ranges dynamically based on the given BMC mode.

    Args:
        bmc_mode (str): The mode of BMC discovery.

    Returns:
        None
    """
    temp = bmc_dynamic_range.split('-')
    start_ip = temp[0].split('.')
    end_ip = temp[1].split('.')
    output = cal_ranges(start_ip, end_ip)
    range_status = output[0]
    final_range = output[1]
    if range_status == "true":
        run_bmc_discover(final_range, dynamic_stanza, bmc_mode)


def create_ranges_static(bmc_mode):
    """
	Create static ranges based on the given bmc_mode.

	Parameters:
		bmc_mode (str): The mode of the BMC.

	Returns:
		None
	"""

    temp = bmc_static_range.split('-')
    start_ip = temp[0].split('.')
    end_ip = temp[1].split('.')
    output = cal_ranges(start_ip, end_ip)
    range_status = output[0]
    final_range = output[1]
    if range_status == "true":
        run_bmc_discover(final_range, static_stanza, bmc_mode)


def create_ranges_discovery(bmc_mode):
    """
	Create ranges for BMC discovery.

	Parameters:
		bmc_mode (str): The mode of the BMC.

	Returns:
		None
	"""

    discover_range_list = discovery_ranges.split(',')
    for ip_range in discover_range_list:
        ip_obj = validate(ip_range)
        temp = ip_obj.split('-')
        start_ip = temp[0].split('.')
        end_ip = temp[1].split('.')
        discover_subnet = calculate_ip_details.cal_ip_details(temp[0], netmask_bits)[1]
        if discover_subnet != bmc_static_subnet:
            output = cal_ranges(start_ip, end_ip)
            range_status = output[0]
            final_range = output[1]
            if range_status == "true":
                run_bmc_discover(final_range, discover_stanza, bmc_mode)

        elif discover_subnet == bmc_static_subnet:
            output = cal_ranges(start_ip, end_ip)
            range_status = output[0]
            final_range = output[1]
            if range_status == "true":
                run_bmc_discover(final_range, static_stanza, bmc_mode)


def run_bmc_discover(final_range, stanza_path, bmc_mode):
    """
	Runs BMC discovery on a range of IP addresses.
    Creates proper stanza file with results of bmcdiscovery, else it gets timed out.


	Parameters:
		final_range (str): The range of IP addresses to discover.
		stanza_path (str): The path to the stanza file.
		bmc_mode (str): The mode of the BMC.

	Returns:
		None
	"""


    if bmc_mode == "static" or bmc_mode == "discovery":
        command = ["/opt/xcat/bin/bmcdiscover", "--range", final_range, "-z"]
    elif bmc_mode == "dynamic":
        command = ["/opt/xcat/bin/bmcdiscover", "--range", final_range, "-z", "-w"]
    try:
        node_objs = subprocess.run(command, capture_output=True, timeout=600, check=True)
        with open(stanza_path, 'r+') as f:
            f.write(node_objs.stdout.decode())
    except subprocess.TimeoutExpired:
        print(
            "The discovery did not finish within the timeout period.Please provide a smaller range or a correct range.")


def create_ranges():
    """
	Calls the function to create ranges for different mtms discovery mode.

	Parameters:
		None

	Returns:
		None
	"""

    if len(sys.argv) > 3:
        if discovery_ranges != "0.0.0.0":
            bmc_mode = "discovery"
            create_ranges_discovery(bmc_mode)
        if bmc_static_range != "":
            bmc_mode = "static"
            create_ranges_static(bmc_mode)
    elif len(sys.argv) <= 3:
        if bmc_dynamic_range != "":
            bmc_mode = "dynamic"
            create_ranges_dynamic(bmc_mode)


create_ranges()