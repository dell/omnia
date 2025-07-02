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
import sys
import os
import subprocess


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

bmc_range = sys.argv[1]
bmc_range = validate(bmc_range)
stanza_path = os.path.abspath(sys.argv[2])
bmc_mode = sys.argv[3]

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


def create_ranges():
    """
    Create ranges dynamically based on the given BMC mode.

    Args:
        bmc_mode (str): The mode of BMC discovery.

    Returns:
        None
    """
    temp = bmc_range.split('-')
    start_ip = temp[0].split('.')
    end_ip = temp[1].split('.')
    output = cal_ranges(start_ip, end_ip)
    range_status = output[0]
    final_range = output[1]
    if range_status == "true":
        run_bmc_discover(final_range)

def run_bmc_discover(final_range):
    """
	Runs BMC discovery on a range of IP addresses.
    Creates proper stanza file with results of bmcdiscovery, else it gets timed out.


	Parameters:
		final_range (str): The range of IP addresses to discover.

	Returns:
		None
	"""

    command = []
    if bmc_mode == "static":
        command = ["/opt/xcat/bin/bmcdiscover", "--range", final_range, "-z"]
    elif bmc_mode == "dynamic":
        command = ["/opt/xcat/bin/bmcdiscover", "--range", final_range, "-z", "-w"]
    try:
        node_objs = subprocess.run(command, capture_output=True, timeout=600, check=True)
        if os.path.exists(stanza_path):
            with open(stanza_path, 'r+', encoding="utf-8") as f:
                f.write(node_objs.stdout.decode())
        else:
            print(f"File {stanza_path} does not exist. Unable to write to it.")
    except subprocess.TimeoutExpired:
        print(
            "The discovery did not finish within the timeout period.Please provide " \
            "a smaller range or a correct range.")


create_ranges()
