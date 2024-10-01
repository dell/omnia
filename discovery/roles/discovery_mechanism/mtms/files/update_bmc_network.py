# Copyright 2024 Dell Inc. or its subsidiaries. All Rights Reserved.
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
import re
import subprocess
import sys
import calculate_ip_details

class IPAddress:
    def __init__(self, address):
        self.address = address
        self.validate()

    def validate(self):
        # Define regex patterns
        cidr_pattern = r'^(\d{1,3}\.){3}\d{1,3}/\d{1,2}$'
        range_pattern = r'^(\d{1,3}\.){3}\d{1,3}-\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$'
        valid_pattern = f'({cidr_pattern}|{range_pattern}|0.0.0.0)'

        if not re.fullmatch(valid_pattern, self.address):
            raise ValueError("Invalid IP range format")

    def __str__(self):
        return self.address



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
      Insert the network details in the xCAT networks table
      Returns:
       an updated networks table with details of various bmc discovery ranges inserted as a network.
    """
    ip_ranges = discovery_ranges.split(',')
    for ip_range in ip_ranges:
        ip_obj = IPAddress(ip_range)
        start_ip, end_ip = ip_obj.address.split('-')
        details = calculate_ip_details.cal_ip_details(start_ip, netmask_bits)
        netmask = details[0]
        subnet = details[1]
        network_name = create_network_name("bmc_network", subnet)
        command = f"/opt/xcat/bin/chdef -t network -o {network_name} net={subnet} mask={netmask} staticrange={start_ip}-{end_ip}"
        command_list = command.split()
        try:
            subprocess.run(command_list, capture_output=True, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error: {e}")



update_networks_table()