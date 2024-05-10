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

def fetch_nic_metadata_params(metadata_path):
    """
    Fetches the NIC metadata parameters from the specified metadata path.

    Args:
        metadata_path (str): The path to the metadata file.

    Returns:
        dict: The loaded metadata parameters as a dictionary.
    """
    with open(metadata_path, "r") as file:
        data = yaml.safe_load(file)
    return data

def validate_nic_metadata_params(network_data, md_data):
    """
    Validates the network details in the NIC metadata file against the server specification data.
    
    Args:
        network_data (dict): A dictionary containing the network details in the NIC metadata file.
        category_data (dict): A dictionary containing the server specification data.
    
    Returns:
        None
    """
    for net_key,net_value in network_data.items():
        if net_key not in ['admin_network', 'bmc_network']:
            if net_key in md_data.keys():
                if('CIDR' in net_value.keys()):
                    if(net_value['CIDR'] != md_data['nic_metadata']['md_'+net_key+'_CIDR']):
                        sys.exit("md_"+net_key+"_CIDR"+" provided during previous execution is different from the value provided in current execution")
                if('static_range' in net_value.keys()):
                    if(net_value['static_range'] != md_data['nic_metadata']['md_'+net_key+'_static_range']):
                        sys.exit("md_"+net_key+"_static_range"+" provided during previous execution is different from the value provided in current execution")
                if(net_value['netmask_bits'] != md_data['nic_metadata']['md_'+net_key+'_netmask_bits']):
                    sys.exit("md_"+net_key+"_netmask_bits"+" provided during previous execution is different from the value provided in current execution")

def main():
    """
    This function is the entry point of the program. It takes no arguments.
    It fetches the path of the NIC metadata file from the command line argument,
    retrieves the network data from the environment variable, loads it as JSON,
    fetches the metadata data from the NIC metadata file, validates the metadata
    data against the network data, and returns nothing.
    """
    nic_md_file_path = sys.argv[1]
    network_string = os.environ.get('net_data')
    network_data = json.loads(network_string)
    md_data = fetch_nic_metadata_params(nic_md_file_path)
    validate_nic_metadata_params(network_data, md_data)


if __name__ == "__main__":
    main()