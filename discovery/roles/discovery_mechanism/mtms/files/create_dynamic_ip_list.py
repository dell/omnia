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

import re
import ipaddress
import sys
from ipaddress import IPv4Address
import subprocess

bmc_subnet = sys.argv[1]
bmc_netmask = sys.argv[2]
bmc_netmask = IPv4Address(bmc_netmask)
username = sys.argv[3]
password = sys.argv[4]

ip_list = []
valid_ip_list = []
dhcp_file_path = sys.argv[5]
dynamic_ip_path = "/opt/omnia/dynamic_ip_list"


def create_temp_ip_list():
    """
       Creates a list of ips present in dhcpd.leases
       Calls:
        function that will extract possible bmc ips from the list of available ips.
    """
    # opening and reading the file
    with open(dhcp_file_path) as file:
        fstring = file.readlines()

    # declaring the regex pattern for IP addresses
    pattern = re.compile(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})')

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
       Extracts the possible bmc ips from the available list of ips
       Returns:
         Valid bmc ip list
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
       Write the valid bmc ips in a file
       Parameters:
         valid_ip_list: valid bmc ip lists
       Returns:
         a file with bmc_ips written in it.
    """
    with open(dynamic_ip_path, 'w') as fp:
        for ip in valid_ip_list:
            fp.write("%s\n" % ip)
    fp.close()


create_temp_ip_list()
