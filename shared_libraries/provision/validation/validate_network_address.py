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
This script validates the network address of a given network interface.
"""
import subprocess
import json
import os
import ipaddress
import sys

def get_network_address(ip_address_netmask):
    """
	Returns the network address of a given IP address and netmask.

	Parameters:
	- ip_address_netmask (str): The IP address and netmask in the format "IP/netmask".

	Returns:
	- str: The network address of the given IP address and netmask.
	"""

    ip_net_address = ipaddress.ip_network(ip_address_netmask, strict=False)
    return str(ip_net_address.network_address)

def main():
    """
    Retrieves the network data from the environment variable 'net_data'
        and performs network validation.

	Parameters:
	- None

	Returns:
	- None
	"""

    network_string = os.environ.get('net_data')
    network_data = json.loads(network_string)
    network_interface = sys.argv[1]
    network_interface_ip = []
    result = subprocess.run(
            ['ip', 'addr', 'show', network_data[network_interface]["oim_nic_name"]],
            capture_output=True, text=True, check=True)
    for ip in result.stdout.split("inet ")[1:]:
        network_interface_ip.append(ip.split()[0])

    # Extract static IP and netmask
    static_ip = network_data[network_interface]["dynamic_conversion_static_range"].split("-")[0]
    dynamic_ip = network_data[network_interface]["dynamic_range"].split("-")[0]
    netmask = network_data[network_interface]["netmask_bits"]

    input_network_static_ip_netmask = f"{static_ip}/{netmask}"
    input_network_dynamic_ip_netmask = f"{dynamic_ip}/{netmask}"

    for ip in network_interface_ip:
        if ( get_network_address(ip) == get_network_address(input_network_dynamic_ip_netmask)
            or get_network_address(ip) == get_network_address(input_network_static_ip_netmask)):
            print(ip.split("/")[0])

if __name__ == "__main__":
    main()
