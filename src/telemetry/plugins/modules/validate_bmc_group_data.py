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

def is_valid_ip(ip):
    """
    This function checks if the given IP address is valid.
    Parameters:
        ip (str): IP address to be validated.
    Returns:
        bool: True if IP address is valid, False otherwise.
    """
    return re.match(r'^\d{1,3}(\.\d{1,3}){3}$', ip)

def validate_bmc_group_data(bmc_group_data, bmc_group_data_headers, bmc_group_data_file, nodes_bmc_ips):
    """
    Validates BMC group data and returns the result along with the list of BMC IPs.

    Parameters:
        bmc_group_data (list): List of BMC group data entries.
        bmc_group_data_headers (list): List of expected headers in BMC group data.
        bmc_group_data_file (str): The file containing BMC group data.

    Returns:
        dict: A dictionary containing the validation result, list of BMC IPs and other relevant information.
    """
    invalid_bmc_group_data_file_msg = f"Invalid BMC group data file {bmc_group_data_file}. Please execute discovery_provision.yml to Generate valid BMC data file."
    if not bmc_group_data:
        raise ValueError("BMC group data is empty")
    headers = bmc_group_data[0].split(',')

    if headers != bmc_group_data_headers:
        raise ValueError(f"Failed. Invalid headers in BMC group data file. Expected: {bmc_group_data_headers}, Found: {headers}. {invalid_bmc_group_data_file_msg}")
    bmc_dict_list = []
    invalid_ip = []
    external_ip = []

    if not bmc_group_data[1:]:
        raise ValueError(f"Failed. No BMC entries found in BMC group data file {bmc_group_data_file}")

    for line in bmc_group_data[1:]:
        values = line.split(',')
        entry = dict(zip(headers, values))
        ip = entry.get('BMC_IP', '')
        if not is_valid_ip(ip):
            invalid_ip.append(ip)
        if ip not in nodes_bmc_ips:
            if entry.get('PARENT') or entry.get('GROUP_NAME'):
                external_ip.append(ip)
        bmc_dict_list.append(entry)

    if invalid_ip:
        raise ValueError(f"Failed. Invalid BMC_IP: {invalid_ip} found in {bmc_group_data_file}")

    if external_ip:
        raise ValueError(f"Failed. BMC_IP not found in omniadb: {external_ip}. For EXTERNAL IPs, 'PARENT' and 'GROUP_NAME' should not be set in {bmc_group_data_file}")

    result = {
        "changed": False,
        "bmc_dict_list": bmc_dict_list,
        "bmc_ips": {},
        "msg": ""
    }

    sn_bmc_ips = {}
    for entry in bmc_dict_list:
        parent = entry.get('PARENT')
        if parent:
            sn_bmc_ips.setdefault(parent, []).append(entry['BMC_IP'])

    mgmt_bmc_ips = [entry['BMC_IP'] for entry in bmc_dict_list if not entry.get('PARENT')]
    result['bmc_ips'] = {**sn_bmc_ips, 'MGMT_node': mgmt_bmc_ips}


    return result


def main():
    """
    Main function for the Ansible module.
    """
    module_args = {
        "nodes_bmc_ips": {"type": "list", "elements": "str", "required": True},
        "bmc_group_data": {"type": "list", "elements": "str", "required": True},
        "bmc_group_data_headers": {"type": "list", "elements": "str", "required": True},
        "bmc_group_data_file": {"type": "str", "required": False}
    }

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )
    nodes_bmc_ips = module.params['nodes_bmc_ips']
    bmc_group_data = module.params['bmc_group_data']
    bmc_group_data_headers = module.params['bmc_group_data_headers']
    bmc_group_data_file = module.params['bmc_group_data_file']
    try:
        result = validate_bmc_group_data(bmc_group_data, bmc_group_data_headers, bmc_group_data_file, nodes_bmc_ips)
        module.exit_json(**result)
    except ValueError as e:
        module.fail_json(msg=f"BMC Group Data Validation failed: {str(e)}")

if __name__ == '__main__':
    main()
