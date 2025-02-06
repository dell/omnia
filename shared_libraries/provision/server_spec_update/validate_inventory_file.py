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

import os
import sys
import ipaddress
import json
from distutils.util import strtobool

inventory_status = bool(strtobool(sys.argv[1]))

def validate_inventory(category_list, hostvars):
    """
	Validates the inventory file against the server specification.

	Parameters:
		category_list (list): A list of categories.
		hostvars (dict): A dictionary containing host variables.

	Returns:
		None

	Raises:
		SystemExit: If the inventory file is invalid.
	"""

    # Remove localhost from inventory
    hostvars.pop('localhost','none')

    # Validate hosts in inventory file
    for host, host_data in hostvars.items():
        if not inventory_status:
            if 'ansible_host' in host_data.keys():
                host_ip = host_data['ansible_host']
            else:
                host_ip = host_data['inventory_hostname']
            if len(host_ip.split('.')) != 4:
                sys.exit(f"Failed, invalid host-ip in inventory: {host_ip}")
            if not ipaddress.ip_address(host_ip):
                sys.exit(f"Failed, invalid host-ip in inventory: {host_ip}")
        else:
            host_ip = host

    for host, host_data in hostvars.items():
        if 'Categories' not in host_data.keys():
            sys.exit(f"Failed, Categories not provided in inventory for host: {host}")
        if len(host_data['Categories']) == 0:
            sys.exit(f"Failed, Categories not provided in inventory for host: {host}")
            
       # Check if host is part of multiple groups
        group_names = host_data.get('group_names', [])
        if len(group_names) > 1:
            sys.exit(f"Failed, host {host_ip} is part of multiple groups: {group_names}. A host can only belong to one group.")
        print(f"Host {host_ip} belongs to group: {group_names[0]}")
        
    # Validate categories in inventory with server_spec
    for host, host_data in hostvars.items():
        if 'Categories' in host_data.keys() and host_data['Categories'] not in category_list:
            sys.exit(f"Failed, {host_ip}: {host_data['Categories']} category in additional nic inventory not found in server_spec.yml.")

def main():
    """
	Executes the main function of the program.

	This function takes in two command line arguments: `category_data` and `hostvars`.
	It then calls the `validate_inventory` function with these arguments.

	Parameters:
	- None

	Returns:
	- None
	"""

    category_list = os.environ.get('category_list')
    hostvars_str = os.environ.get('host_data')
    if not category_list or not hostvars_str:
        sys.exit("Failed, invalid input")
    hostvars = json.loads(hostvars_str)
    validate_inventory(category_list, hostvars)

if __name__ == "__main__":
    main()
