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

# pylint: disable=import-error,no-name-in-module,line-too-long

#!/usr/bin/python

"""Ansible module to check telemetry service cluster node details."""

import re
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.discovery.omniadb_connection import execute_select_query # type: ignore

def get_bmc_ips_from_db():
    """
	Retrieves BMC IPs from the cluster.nodeinfo table in the database.

	Parameters:
		None

	Returns:
		list: A list of BMC IPs.
	"""
    sql = "SELECT bmc_ip FROM cluster.nodeinfo"
    query_result = execute_select_query(query=sql)
    bmc_ips = [row.get('bmc_ip') for row in query_result if row.get('bmc_ip') is not None]
    return bmc_ips

def is_valid_ip(ip):
    """
    This function checks if the given IP address is valid.
    Parameters:
        ip (str): IP address to be validated.
    Returns:
        bool: True if IP address is valid, False otherwise.
    """
    return re.match(r'^\d{1,3}(\.\d{1,3}){3}$', ip)

def validate_bmc_group_data(bmc_group_data, bmc_group_data_headers, federated_telemetry):
    """
    Validates BMC group data and extracts BMC IP addresses.
    Parameters:
        bmc_group_data (list): A list of BMC group data.
        bmc_group_data_headers (list): A list of expected headers.
        federated_telemetry (bool): A boolean indicating whether federated telemetry is enabled.
    Returns:
        dict: A dictionary containing the validated BMC group data, BMC IP addresses, and other relevant information.
    """
    if not bmc_group_data:
        raise ValueError("BMC group data is empty")

    headers = bmc_group_data[0].split(',')
    if headers != bmc_group_data_headers:
        raise ValueError(f"Invalid headers. Expected: {bmc_group_data_headers}, Found: {headers}")

    omnia_db_bmc_ips = get_bmc_ips_from_db()
    bmc_dict_list = []
    for line in bmc_group_data[1:]:
        values = line.split(',')
        entry = dict(zip(headers, values))
        ip = entry.get('BMC_IP', '')
        if not is_valid_ip(ip):
            raise ValueError(f"Invalid BMC_IP: {ip}")
        if ip not in omnia_db_bmc_ips:
            if entry.get('PARENT') or entry.get('GROUP_NAME'):
                raise ValueError(f"BMC_IP not found in omniadb: {ip}. PARENT and GROUP should not be set")
        bmc_dict_list.append(entry)

    result = {
        "changed": False,
        "bmc_dict_list": bmc_dict_list,
        "bmc_ips": {},
        "msg": ""
    }

    if federated_telemetry:
        sn_bmc_ips = {}
        for entry in bmc_dict_list:
            parent = entry.get('PARENT')
            if parent:
                sn_bmc_ips.setdefault(parent, []).append(entry['BMC_IP'])

        oim_bmc_ips = [entry['BMC_IP'] for entry in bmc_dict_list if not entry.get('PARENT')]
        result['bmc_ips'] = {**sn_bmc_ips, 'oim': oim_bmc_ips}
    else:
        unique_ips = list({entry['BMC_IP'] for entry in bmc_dict_list})
        result['bmc_ips'] = {'oim': unique_ips}

    return result


def main():
    """
    Main function for the Ansible module.
    """
    module_args = {
        "bmc_group_data": {"type": "list", "elements": "str", "required": True},
        "bmc_group_data_headers": {"type": "list", "elements": "str", "required": True},
        "federated_telemetry": {"type": "bool", "required": False, "default": False}
    }

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    bmc_group_data = module.params['bmc_group_data']
    bmc_group_data_headers = module.params['bmc_group_data_headers']
    federated_telemetry = module.params['federated_telemetry']
    try:
        result = validate_bmc_group_data(bmc_group_data, bmc_group_data_headers, federated_telemetry)
        module.exit_json(**result)
    except ValueError as e:
        module.fail_json(msg=f"BMC Group Data Validation failed: {str(e)}")

if __name__ == '__main__':
    main()
