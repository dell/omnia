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

import re
import ipaddress
import sys, os
from ipaddress import IPv4Address
import subprocess

bmc_subnet = sys.argv[1]
bmc_netmask = sys.argv[2]
bmc_netmask = IPv4Address(bmc_netmask)
username = sys.argv[3]
password = sys.argv[4]

ip_list = []
valid_ip_list = []
dhcp_file_path = os.path.abspath(sys.argv[5])
dynamic_ip_path = "/opt/omnia/provision/dynamic_ip_list"


def create_temp_ip_list():
    """
	Creates a temporary list of IP addresses present in the dhcpd.leases file.

	Parameters:
	- None

	Returns:
	- None

	This function reads the dhcpd.leases file and extracts all the IP addresses present in the file.
	It uses a regular expression pattern to match the IP addresses.
	The extracted IP addresses are then appended to the `ip_list` list.

	After extracting the IP addresses, the function calls the `extract_possible_bmc_ip()` function.
	"""

    # opening and reading the file
    with open(dhcp_file_path) as file:
        fstring = file.readlines()

    # declaring the regex pattern for IP addresses
    pattern = re.compile(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})')
    if fstring:
        # extracting the IP addresses
        for line in fstring:
            if pattern.search(line) is not None:
                ip = IPv4Address(pattern.search(line)[0])
                ip_list.append(ip)
                ip = ipaddress.ip_address(f'{ip}')

    file.close()
    extract_possible_bmc_ip()


def extract_possible_bmc_ip():
    """
	Extracts the possible BMC IPs from the available list of IPs.

	Parameters:
	- None

	Returns:
	- None

	This function iterates over the `ip_list` and checks if each IP is part of the `bmc_subnet`.
	If it is, the IP is added to the `temp_ip_list`.

	Then, for each IP in the `temp_ip_list`, a ping command is executed.
	If the ping is successful (return code is 0), the IP is added to the `valid_ip_list`.

	Finally, the `valid_ip_list` is sorted and passed to the `create_dynamic_ip_file()` function.
	"""

    temp_ip_list = []
    for ip in set(ip_list):
        net = ipaddress.ip_network(f"{ip}/{bmc_netmask}", strict=False)
        temp = str(net).split('/')
        if temp[0] == bmc_subnet:
            temp_ip_list.append(str(ip))

    for ip in temp_ip_list:

        # Run the ping command
        response = subprocess.run(['ping', '-c', '1', ip], stdout=subprocess.PIPE, text=True)

        # and then check the response...
        if response.returncode == 0:
            print(ip, 'is up!')

            valid_ip_list.append(ip)
    valid_ip_list.sort()

    create_dynamic_ip_file(valid_ip_list)


def create_dynamic_ip_file(valid_ip_list):
    """
	Create a file named "dynamic_ip_list" in the "/opt/omnia/provision" directory.
	The file contains a list of valid IP addresses, each on a new line.

	Parameters:
	- valid_ip_list (list): A list of valid IP addresses.

	Returns:
	- None
	"""

    with open(dynamic_ip_path, 'w') as fp:
        for ip in valid_ip_list:
            fp.write("%s\n" % ip)
    fp.close()


create_temp_ip_list()
