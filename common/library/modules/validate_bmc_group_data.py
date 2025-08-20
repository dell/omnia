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

from ansible.module_utils.basic import AnsibleModule
import re
from ansible.module_utils.discovery.omniadb_connection import get_data_from_db # type: ignore

def get_bmc_ips_from_db():
    """
	Retrieves BMC IPs from the cluster.nodeinfo table in the database.

	Parameters:
		None

	Returns:
		list: A list of BMC IPs.
	"""
    query_result = get_data_from_db(
        table_name='cluster.nodeinfo',
        filter_dict={}
    )
    bmc_ips = [row['BMC_IP'] for row in query_result if 'BMC_IP' in row]
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

def main():
    """
    Validates BMC group data and extracts BMC IP addresses.
    Parameters:
        bmc_group_data (list): A list of BMC group data.
        expected_headers (list): A list of expected headers.
        federated_telemetry (bool): A boolean indicating whether federated telemetry is enabled.
    Returns:
        dict: A dictionary containing the validated BMC group data, BMC IP addresses, and other relevant information.
    """
    module_args = dict(
        bmc_group_data=dict(type='list', elements='str', required=True),
        expected_headers=dict(type='list', elements='str', required=True),
        federated_telemetry=dict(type='bool', required=False, default=False)
    )

    result = dict(
        changed=False,
        bmc_dict_list=[],
        bmc_ips={},
        msg=""
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    bmc_group_data = module.params['bmc_group_data']
    expected_headers = module.params['expected_headers']
    federated_telemetry = module.params['federated_telemetry']

    if not bmc_group_data:
        module.fail_json(msg="BMC group data is empty", **result)

    headers = bmc_group_data[0].split(',')
    if headers != expected_headers:
        module.fail_json(msg=f"Invalid headers. Expected: {expected_headers}, Found: {headers}", **result)

    bmc_dict_list = []
    omnia_db_bmc_ips = get_bmc_ips_from_db()
    for line in bmc_group_data[1:]:
        values = line.split(',')
        entry = dict(zip(headers, values))
        ip = entry.get('BMC_IP', '')
        if not is_valid_ip(ip):
            module.fail_json(msg=f"Invalid BMC_IP: {ip}", **result)
        if ip not in omnia_db_bmc_ips:
            if entry.get('PARENT') or entry.get('GROUP'):
                module.fail_json(msg=f"BMC_IP not found in omniadb: {ip}. PARENT and GROUP should not be set", **result)
            module.fail_json(msg=f"BMC_IP not found in omniadb: {ip}", **result)
        bmc_dict_list.append(entry)
    result['bmc_dict_list'] = bmc_dict_list

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

    module.exit_json(**result)

if __name__ == '__main__':
    main()
