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

def fetch_server_spec_data(server_spec_file_path):
    """
	Fetches server specification data from a YAML file.

	:param server_spec_file_path: The path to the YAML file.
	:type server_spec_file_path: str

	:return: A dictionary containing the server specification data.
	:rtype: dict
	"""

    with open(server_spec_file_path, "r") as file:
        data = yaml.safe_load(file)

    json_data = json.dumps(data)

    server_spec_data = json.loads(json_data)

    category_data = {}
    for category in server_spec_data['Categories']:
        for ctg_key, ctg_value in category.items():
            grp_dict = {}
            if ctg_key in category_data.keys():
                sys.exit("Duplicate group details found in server spec.")

            for group in ctg_value:
                for grp_key, grp_value in group.items():
                    net_dict = {}
                    nicnetwork_set = set()  # To track duplicate nicnetwork values
                    for network in grp_value:
                        for net_key, net_val in network.items():
                            if 'nicnetwork' in net_val:
                                if net_val['nicnetwork'] in nicnetwork_set:
                                    sys.exit(f"Duplicate nicnetwork '{net_val['nicnetwork']}' found in group '{ctg_key}' in server spec.")
                                nicnetwork_set.add(net_val['nicnetwork'])
                            if all(keys in net_dict.keys() for keys in dict(network).keys()):
                                sys.exit("Duplicate network details found in server spec.")
                            net_dict.update(dict(network))
                    grp_dict[grp_key] = net_dict
            category_data[ctg_key] = grp_dict

    return category_data

def validate_network_details(network_data, category_data):
    """
	Validates the network details in the category data against the network data.

	Parameters:
	- network_data (dict): A dictionary containing the network data.
	- category_data (dict): A dictionary containing the category data.

	Returns:
	- None

	Raises:
	- SystemExit: If the network details are invalid.
	"""

    for ctg_val in category_data.values():
        for grp_key, grp_val in ctg_val.items():
            if grp_key == "os":
                for ker_key, ker_val in grp_val.items():
                    if ker_key == "kernel":
                        if ker_val is None:
                            sys.exit("Failed, cmdline variable is missing in server spec.")
                        if 'cmdline' not in ker_val[0] :
                            sys.exit("Failed, cmdline not defined")
            if grp_key == "network":
                for net_val in grp_val.values():
                    if 'nicnetwork' not in net_val or not net_val['nicnetwork']:
                        sys.exit("Failed, nicnetwork details missing in server spec.")

                    if net_val['nicnetwork'] not in network_data.keys():
                        sys.exit("Invalid network name provided in server spec.")

                    if 'nictypes' not in net_val or not net_val['nictypes']:
                        sys.exit("Failed, nictypes details missing in server spec.")

                    if net_val['nictypes'] not in ['ethernet', 'infiniband', 'vlan']:
                        sys.exit("Invalid network type provided in server spec.")

                    if net_val['nictypes'] == 'vlan':
                        if 'nicdevices' not in net_val or not net_val['nicdevices']:
                            sys.exit("Nic device details missing in server spec.")

                    if (net_val['nictypes'] == 'vlan'):
                        if ('VLAN' not in network_data[net_val['nicnetwork']].keys() or len(network_data[net_val['nicnetwork']]['VLAN']) == 0):
                            sys.exit("VLAN ID not provided in network spec for VLAN network.")

            elif grp_key == "os":
                for ker_key, ker_val in grp_val.items():
                    if ker_key == "kernel":
                        if ker_val is None:
                            sys.exit("Failed, cmdline variable is missing in server spec.")
                        if 'cmdline' not in ker_val[0] :
                            sys.exit("Failed, cmdline not defined")

def main():
    """
	The main function of the program.

	This function takes the path of the network specification file from the command line argument,
	retrieves the network data from the environment variable, loads it as JSON,
	fetches the category data from the network specification file, and validates the network details.

	Parameters:
	- None

	Returns:
	- None
	"""

    network_spec_file_path = os.path.abspath(sys.argv[1])
    network_string = os.environ.get('net_data')
    network_data = json.loads(network_string)
    category_data = fetch_server_spec_data(network_spec_file_path)
    validate_network_details(network_data,category_data)

if __name__ == "__main__":
    main()
