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

import subprocess
import sys

import calculate_ip_details

discovery_ranges = sys.argv[1]
netmask_bits = sys.argv[2]


def create_network_name(nw_name, subnet):
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
    ip_address = discovery_ranges.split(',')
    for ip in ip_address:
        start_ip = ip.split('-')[0]
        end_ip = ip.split('-')[1]
        details = calculate_ip_details.cal_ip_details(start_ip, netmask_bits)
        netmask = details[0]
        subnet = details[1]
        network_name = create_network_name("bmc_network", subnet)
        command = f"/opt/xcat/bin/chdef -t network -o {network_name} net={subnet} mask={netmask} staticrange={start_ip}-{end_ip}"
        command_list = command.split()
        try:
            subprocess.run(command_list, capture_output=True)
        except Exception as e:
            print({e})


update_networks_table()
