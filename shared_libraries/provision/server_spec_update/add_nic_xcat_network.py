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
import sys, os
import yaml

nic_info = {}
cal_path = sys.argv[1]
sys.path.insert(0, cal_path)
import calculate_ip_details

network_spec_path = os.path.abspath(sys.argv[2])
metadata_nic_info_path = os.path.abspath(sys.argv[3])
with open(network_spec_path, "r") as file:
    data = yaml.safe_load(file)


def run_command_nw_update(col, start_ip, end_ip, netmask_bits, nic_mode, network_gateway, mtu):
    """
	Runs a command to update the network settings.

	Parameters:
	- col (str): The column name.
	- start_ip (str): The starting IP address.
	- end_ip (str): The ending IP address.
	- netmask_bits (int): The number of bits in the netmask.
	- nic_mode (str): The network interface mode.
	- network_gateway (str): The network gateway.
	- mtu (int): The maximum transmission unit.

	Returns:
	- None

	Raises:
	- Exception: If there is an error running the command.
	"""

    details = calculate_ip_details.cal_ip_details(start_ip, netmask_bits)
    netmask = details[0]
    subnet = details[1]
    nic_range = start_ip + '-' + end_ip
    command = f"/opt/xcat/bin/chdef -t network -o {col} net={subnet} mask={netmask} gateway={network_gateway} staticrange={start_ip}-{end_ip} mtu={mtu}"
    command_list = command.split()
    try:
        subprocess.run(command_list, capture_output=True)
        nic_info[col] = [nic_range, nic_mode]
    except Exception as e:
        print({e})


def create_metadata_nic():
    """
	Create or update the metadata file for NIC information.

	This function reads the existing data from the metadata file located at `metadata_nic_info_path`.
	If the file does not exist, it creates an empty dictionary.
	It then updates the existing data with the new `nic_info` dictionary.
	Finally, it writes the updated data back to the metadata file.

	Parameters:
	- None

	Returns:
	- None
	"""

    try:
        with open(metadata_nic_info_path, 'r') as file:
            existing_data = yaml.safe_load(file)
            if existing_data is None:
                existing_data = {}
    except FileNotFoundError:
        existing_data = {}

    # Update with new data
    existing_data.update(nic_info)

    with open(metadata_nic_info_path, 'w') as f:
        yaml.dump(existing_data, f, default_flow_style=False)


def update_networks_table():
    """
	Updates the xCAT networks table with the specified network details.

	This function iterates over the `data["Networks"]` dictionary and updates the xCAT networks table
	with the specified network details. It checks if the current network is not an admin network
	or a bmc network. If it is not, it checks if the network has a CIDR or a static range. If it
	has a CIDR, it calculates the start and end IP addresses, and the netmask. It then calls the
	`run_command_nw_update()` function with the necessary parameters. If the network has a static
	range, it calculates the start and end IP addresses, and the netmask. It then calls the
	`run_command_nw_update()` function with the necessary parameters. Finally, it calls the
	`create_metadata_nic()` function to update the NIC metadata.

	Parameters:
	- None

	Returns:
	- None
	"""

    for info in data["Networks"]:
        for col, value in info.items():
            if col not in ('admin_network', 'bmc_network'):
                if value.get('CIDR'):
                    netmask_bits = value.get('netmask_bits')
                    network_gateway = value.get('network_gateway')
                    mtu = value.get('MTU')
                    cidr = value.get('CIDR') + '/' + netmask_bits
                    output = calculate_ip_details.create_cidr_range(cidr)
                    start_ip = output[0]
                    end_ip = output[1]
                    nic_mode = "cidr"
                    run_command_nw_update(col, start_ip, end_ip, netmask_bits, nic_mode, network_gateway, mtu)

                if value.get('static_range'):
                    netmask_bits = value.get('netmask_bits')
                    network_gateway = value.get('network_gateway')
                    static_range = value.get('static_range')
                    mtu = value.get('MTU')
                    start_ip = static_range.split('-')[0]
                    end_ip = static_range.split('-')[1]
                    nic_mode = "static"
                    run_command_nw_update(col, start_ip, end_ip, netmask_bits, nic_mode, network_gateway, mtu)

    create_metadata_nic()


update_networks_table()
