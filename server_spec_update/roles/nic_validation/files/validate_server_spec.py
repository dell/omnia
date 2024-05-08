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
    Fetches server specification data from a YAML file and returns it as a dictionary.
    
    Args:
        server_spec_file_path (str): The path to the server specification YAML file.
    
    Returns:
        dict: A dictionary containing the server specification data.
    """
    with open(server_spec_file_path, "r") as file:
        data = yaml.safe_load(file)
    json_data = json.dumps(data)

    server_spec_data = json.loads(json_data)

    category_data={}
    for category in server_spec_data['Categories']:
        for ctg_key , ctg_value in category.items():
            grp_dict={}
            if(ctg_key in category_data.keys()):
                sys.exit("Duplicate group details found in server spec.")
            for group in ctg_value:
                for grp_key,grp_value in group.items():
                    net_dict={}
                    for network in grp_value:
                        if(all(keys in net_dict.keys() for keys in dict(network).keys())):
                            sys.exit("Duplicate network details found in server spec.")
                        net_dict = net_dict | dict(network)
                    grp_dict[grp_key] = net_dict
            category_data[ ctg_key ] = grp_dict
    return category_data

def validate_network_details(network_data, category_data):
    """
    Validates the network details provided in the network_data and category_data dictionaries.

    Parameters:
    - network_data (dict): A dictionary containing network details.
    - category_data (dict): A dictionary containing category details.

    Returns:
    - None

    Raises:
    - SystemExit: If any validation fails, a SystemExit exception is raised with an appropriate error message.
    """
    for ctg_val in category_data.values():
        for grp_val in ctg_val.values():
            for net_val in grp_val.values():
                if(net_val.keys()):
                    if('nicnetwork' not in net_val.keys() or len(net_val['nicnetwork']) == 0):
                        sys.exit("Failed, nicnetwork details missing in server spec.")
                    
                    if(net_val['nicnetwork'] not in network_data.keys()):
                        sys.exit("Invalid network name provided in server spec.")

                    if('nictypes' not in net_val.keys() or len(net_val['nictypes']) == 0):
                        sys.exit("Failed, nictypes details missing in server spec.")

                    if(net_val['nictypes'] not in ['ethernet', 'infiniband', 'vlan']):
                        sys.exit("Invalid network type provided in server spec.")
                    
                    if(net_val['nictypes'] == 'vlan'):
                        if('nicdevices' not in net_val.keys() or len(net_val['nicdevices']) == 0):
                            sys.exit("Nic device details missing in server spec.")

                    if(net_val['nictypes'] == 'vlan'):
                        if('VLAN' not in network_data[net_val['nicnetwork']].keys() 
                        or len(network_data[net_val['nicnetwork']]['VLAN']) == 0):
                            sys.exit("VLAN ID not provided in network spec for VLAN network.")
                        
def main():
    """
    This function is the main entry point of the program. It takes in a network specification file path as a command line argument and retrieves network data from an environment variable. It then fetches server specification data from the network specification file and validates the network details against the server specification data.

    Parameters:
    - network_spec_file_path (str): The path to the network specification file.

    Returns:
    - None
    """
    network_spec_file_path = sys.argv[1]
    network_string = os.environ.get('net_data')
    network_data = json.loads(network_string)
    category_data = fetch_server_spec_data(network_spec_file_path)
    validate_network_details(network_data, category_data)

if __name__ == "__main__":
    main()