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

"""
This module is used to validate server specification inventory.
"""

import ipaddress
from ansible.module_utils.basic import AnsibleModule

def validate_inventory(inventory_status ,category_list, hostvars):
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

    # Validate hosts in inventory file
    for host, host_data in hostvars.items():
        if not inventory_status:
            if 'ansible_host' in host_data.keys():
                host_ip = host_data['ansible_host']
            else:
                host_ip = host_data['inventory_hostname']
            if len(host_ip.split('.')) != 4:
                raise ValueError(f"Failed, invalid host-ip in inventory: {host_ip}")
            if not ipaddress.ip_address(host_ip):
                raise ValueError(f"Failed, invalid host-ip in inventory: {host_ip}")
        else:
            host_ip = host

        if 'Categories' not in host_data.keys():
            raise ValueError(f"Failed, Categories not provided in inventory for host: {host}")
        if len(host_data['Categories']) == 0:
            raise ValueError(f"Failed, Categories not provided in inventory for host: {host}")

        group_names = host_data.get('group_names', [])
        if len(group_names) > 1:
            raise ValueError(
                f"Failed, host {host_ip} is part of multiple groups: {group_names}."
                 " A host can only belong to one group.")
        print(f"Host {host_ip} belongs to group: {group_names[0]}")

        # Validate categories in inventory with server_spec
        if 'Categories' in host_data.keys() and host_data['Categories'] not in category_list:
            raise ValueError(
                f"Failed, {host_ip}: {host_data['Categories']} category in additional NIC inventory"
                " not found in server_spec.yml."
            )


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

    module_args = {
        "inventory_status": {"type": "str", "required": False, "default": "false"},
        "host_data": {"type": "dict", "required": True},
        "category_list": {"type": "str", "required": True}
    }

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
     )

    inventory_status = module.params['inventory_status']
    category_list = module.params['category_list']
    hostvars = module.params['host_data']

    if not category_list or not hostvars:
        module.fail_json(msg="Failed, invalid input: category_list or hostvars missing")

    try:
        validate_inventory(inventory_status, category_list, hostvars)
        module.exit_json(changed=False)
    except ValueError as e:
        module.fail_json(msg=f"Validation failed: {str(e)}")

if __name__ == '__main__':
    main()
