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

import sys
import yaml
import json
import os

def insert_nic_metadata_params(network_data, metadata_path):
    """
	Inserts the network data into the NIC metadata file.

	Parameters:
	- network_data (dict): A dictionary containing the network data.
	- metadata_path (str): The path to the NIC metadata file.

	Returns:
	- None
	"""

    nic_info = {'nic_metadata': {}}
    if network_data:
        for net_key,net_value in network_data.items():
            if(net_key not in ['admin_network', 'bmc_network']):
                if('CIDR' in net_value.keys()):
                    nic_info['nic_metadata']['md_'+net_key+'_CIDR'] = net_value['CIDR']
                if('static_range' in net_value.keys()):
                    nic_info['nic_metadata']['md_'+net_key+'_static_range'] = net_value['static_range']
                nic_info['nic_metadata']['md_'+net_key+'_netmask_bits'] = net_value['netmask_bits']

    with open(metadata_path, 'w+') as file:
        yaml.dump(nic_info, file, default_flow_style=False)

def main():
    """
	The main function that processes the command line arguments and environment variables to update the NIC metadata file.

	Parameters:
		None

	Returns:
		None
	"""

    nic_md_file_path = os.path.abspath(sys.argv[1])
    network_string = os.environ.get('net_data')
    network_data = json.loads(network_string)
    insert_nic_metadata_params(network_data, nic_md_file_path)


if __name__ == "__main__":
    main()