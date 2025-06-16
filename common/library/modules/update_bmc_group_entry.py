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

#!/usr/bin/python
""" Ansible module to update BMC group entry in CSV file. """
import csv
import os
import requests
from requests.auth import HTTPBasicAuth
from ansible.module_utils.basic import AnsibleModule
from requests import packages
from requests.exceptions import (
    ConnectionError as RequestsConnectionError,
    ConnectTimeout,
    HTTPError,
    Timeout,
    RequestException
)
packages.urllib3.disable_warnings()

def is_bmc_reachable_or_auth(ip, username, password, module):
    """
    Check if the BMC is reachable and if the credentials are valid.
    Returns True if reachable and authenticated, False otherwise.
    """
    url = f"https://{ip}/redfish/v1/"
    try:
        response = requests.get(
            url,
            auth=HTTPBasicAuth(username, password),
            timeout=30,
            verify=False
        )

        if response.status_code == 200:
            return True, 200
        if response.status_code == 401:
            module.warn(f"BMC IP {ip} is reachable, but bmc credential is invalid.")
            return False, 401
        if response.status_code == 404:
            module.warn(f"BMC IP {ip} is reachable, but Redfish API not found (404).")
            return False, 404

        module.warn(f"BMC IP {ip} responded with unexpected status code: {response.status_code}")
        return False, response.status_code

    except ConnectTimeout:
        module.warn(f"BMC IP {ip} connection timed out. Not reachable.")
    except HTTPError as http_err:
        module.warn(f"BMC IP {ip} HTTP error occurred: {http_err}")
    except RequestsConnectionError:
        module.warn(f"BMC IP {ip} is unreachable (connection error).")
    except Timeout:
        module.warn(f"BMC IP {ip} request timed out.")
    except RequestException as req_err:
        module.warn(f"BMC IP {ip} encountered a request error: {req_err}")

    return False, 500  # Return 500 for general errors

def read_entries_csv(csv_path, module):
    "Reading existing entries from the CSV file"
    entries = {}
    expected_columns = {'BMC_IP', 'GROUP_NAME', 'PARENT'}

    if os.path.exists(csv_path):
        try:
            with open(csv_path, mode='r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)

                actual_columns = set(reader.fieldnames or [])
                if not actual_columns:
                    return entries
                if expected_columns != actual_columns:
                    module.fail_json(
                        msg=f"CSV file at {csv_path} is missing required columns. \
                            Expected: {expected_columns}, \
                            Found: {actual_columns}"
                    )

                for row in reader:
                    if not row['BMC_IP']:
                        module.fail_json(
                            msg=f"CSV file at {csv_path} contains an entry with an empty 'BMC_IP'."
                        )
                    entries[row['BMC_IP']] = row
        except csv.Error as e:
            module.fail_json(msg=f"Failed to parse CSV file at {csv_path}: {str(e)}")

    return entries


def write_entries_csv(csv_path, entries):
    "Writing BMC with group details entries to the CSV file"
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    with open(csv_path, mode='w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['BMC_IP', 'GROUP_NAME', 'PARENT']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for entry in entries.values():
            writer.writerow(entry)

def delete_bmc_entries(nodes, existing_entries, result):
    """
    Delete BMC entries from the existing entries based on the provided nodes.
    """
    for node in nodes:
        bmc_ip = node.get('bmc_ip')
        if bmc_ip in existing_entries:
            del existing_entries[bmc_ip]
            result['deleted'].append(bmc_ip)
            result['changed'] = True

def add_bmc_entries(nodes, existing_entries, bmc_creds, module, result):
    """
    Add BMC entries to the existing entries based on the provided nodes.
    """
    for node in nodes:
        bmc_ip = node.get('bmc_ip')
        group = node.get('group_name', '')
        parent = node.get('parent', '')

        if bmc_ip and bmc_ip not in existing_entries:
            is_valid, code = is_bmc_reachable_or_auth(bmc_ip, bmc_creds.get('username'),
                                                      bmc_creds.get('password'), module)
            if is_valid:
                existing_entries[bmc_ip] = {
                    'BMC_IP': bmc_ip,
                    'GROUP_NAME': group,
                    'PARENT': parent
                }
                result['added'].append(bmc_ip)
            else:
                if code == 401:
                    result['invalid_creds'].append(bmc_ip)
                elif code == 404:
                    result['redfish_disabled'].append(bmc_ip)
                else:
                    result['unreachable_bmc'].append(bmc_ip)
            result['changed'] = True

def verify_bmc_entries(nodes, bmc_creds, module, result):
    """
    Verify reachability and authentication of BMC entries in the existing entries.
    """

    for node in nodes:
        bmc_ip = node.get('bmc_ip')
        is_valid, code = is_bmc_reachable_or_auth(bmc_ip, bmc_creds.get('username'),
                                                  bmc_creds.get('password'), module)
        if is_valid:
            result['verified_bmc'].append(bmc_ip)
        else:
            if code == 401:
                result['invalid_creds'].append(bmc_ip)
            elif code == 404:
                result['redfish_disabled'].append(bmc_ip)
            else:
                result['unreachable_bmc'].append(bmc_ip)
    result['changed'] = True


def main():
    "Main function for the custom ansible module - update_bmc_group_entry"
    module_args = {
        'csv_path': {'type': 'str', 'required': False, 'default': '/opt/omnia/telemetry/bmc_group_entries.csv' },
        'nodes': {'type': 'list', 'elements': 'dict', 'required': False, 'default': []},
        'bmc_username': {'type': 'str', 'required': False, 'no_log': True},
        'bmc_password': {'type': 'str', 'required': False, 'no_log': True},
        'delete': {'type': 'bool', 'default': False, 'required': False},
        'verify_bmc': {'type': 'bool', 'default': False, 'required': False}
    }

    result = {'changed': False, 'added': [], 'deleted': [], 'invalid_creds': [],
              'unreachable_bmc': [], 'redfish_disabled': [], 'verified_bmc': []}

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=False)

    csv_path = module.params['csv_path']
    nodes = module.params['nodes']
    delete = module.params['delete']
    verify_bmc = module.params['verify_bmc']
    bmc_creds = {}
    bmc_creds['username'] = module.params.get('bmc_username')
    bmc_creds['password'] = module.params.get('bmc_password')

    # Validate username and password only if delete is False
    if not delete and (not bmc_creds.get('username') or not bmc_creds.get('password')):
        module.fail_json(msg="bmc_username and bmc_password are mandatory for add operation.")

    existing_entries = read_entries_csv(csv_path, module)

    if delete:
        delete_bmc_entries(nodes, existing_entries, result)
        write_entries_csv(csv_path, existing_entries)
    elif verify_bmc:
        verify_bmc_entries(nodes, bmc_creds, module, result)
    else:
        add_bmc_entries(nodes, existing_entries, bmc_creds, module, result)
        write_entries_csv(csv_path, existing_entries)
    module.exit_json(**result)

if __name__ == '__main__':
    main()
