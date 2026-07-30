#!/usr/bin/python
# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Ansible module to generate BMC discovery report from discovered server inventory."""

import csv
import os
from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = r'''
---
module: generate_discovery_report
short_description: Generate BMC discovery report from server inventory
description:
    - This module generates a BMC discovery report CSV file from discovered
      server inventory data collected from OME.
    - The report includes service tag, BMC details, ethernet NIC details,
      and InfiniBand NIC details with link statuses.
options:
    servers:
        description: List of server dictionaries with inventory details
        required: true
        type: list
    output_file:
        description: Path to the output discovery report CSV file
        required: true
        type: str
'''

EXAMPLES = r'''
- name: Generate BMC discovery report
  generate_discovery_report:
    servers: "{{ discovered_servers }}"
    output_file: "/opt/omnia/discovery/bmc_discovery_report_20260601T120000.csv"
'''

RETURN = r'''
report_file:
    description: Path to the generated report file
    type: str
    returned: success
server_count:
    description: Number of servers written to the report
    type: int
    returned: success
'''

# CSV headers for the discovery report
REPORT_HEADERS = [
    "SERVICE_TAG",
    "BMC_MAC",
    "BMC_IP",
    "BMC_NIC_STATUS",
    "ETHERNET_NIC_MAC",
    "ETHERNET_NIC_LINK_STATUS",
    "IB_NIC_NAME",
    "IB_NIC_LINK_STATUS"
]


def generate_report(servers, output_file):
    """Generate the BMC discovery report CSV file.

    Args:
        servers: List of server dictionaries from OME inventory.
        output_file: Path to the output CSV file.

    Returns:
        Tuple of (report_file_path, server_count).
    """
    output_dir = os.path.dirname(output_file)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    server_count = 0
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(REPORT_HEADERS)

        for server in servers:
            row = [
                server.get('service_tag', ''),
                server.get('idrac_mac', ''),
                server.get('idrac_ip', ''),
                server.get('idrac_link_status', ''),
                server.get('first_nic_mac', ''),
                server.get('first_nic_link_status', ''),
                server.get('ib_nic_name', ''),
                server.get('ib_nic_link_status', '')
            ]
            writer.writerow(row)
            server_count += 1

    return output_file, server_count


def main():
    """Main function for the Ansible module."""
    module = AnsibleModule(
        argument_spec=dict(
            servers=dict(type='list', required=True),
            output_file=dict(type='str', required=True),
        ),
        supports_check_mode=False
    )

    servers = module.params['servers']
    output_file = module.params['output_file']

    try:
        report_file, server_count = generate_report(servers, output_file)
        module.exit_json(
            changed=True,
            report_file=report_file,
            server_count=server_count,
            msg="Discovery report generated with {} servers".format(server_count)
        )
    except Exception as e:
        module.fail_json(
            msg="Failed to generate discovery report: {}".format(str(e))
        )


if __name__ == '__main__':
    main()
