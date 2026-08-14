#!/usr/bin/python3
# -*- coding: utf-8 -*-
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

"""Ansible module to validate the BMC Redfish vendor configuration CSV."""

import csv
import os

from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = r'''
---
module: validate_bmc_redfish_config
short_description: Validate the BMC Redfish vendor configuration CSV
description:
  - Reads a two-column key-value CSV and validates the vendor-specific
    Redfish endpoint configuration consumed by bmc_lease_handler.yml and
    magellan_discovery.
options:
  csv_path:
    description: Path to bmc_redfish_config.csv
    required: true
    type: str
'''

EXAMPLES = r'''
- name: Validate BMC Redfish config
  validate_bmc_redfish_config:
    csv_path: "{{ input_project_dir }}/bmc_redfish_config.csv"
'''

RETURN = r'''
data:
    description: Dictionary of key-value pairs from the CSV
    type: dict
    returned: always
'''

REQUIRED_KEYS = [
    "vendor_profile",
    "system_endpoint",
    "manager_attributes_endpoint",
    "service_tag_field",
    "static_ip_address_key",
    "static_ip_netmask_key",
    "static_ip_gateway_key",
    "static_ip_dhcp_enable_key",
    "dhcp_disable_value",
]

ENDPOINT_KEYS = [
    "system_endpoint",
    "systems_collection_endpoint",
    "system_network_adapters_endpoint",
    "system_ethernet_interfaces_endpoint",
    "manager_endpoint",
    "managers_collection_endpoint",
    "manager_attributes_endpoint",
    "manager_ethernet_interfaces_endpoint",
    "location_endpoint",
]


def read_csv(csv_path):
    """Read a two-column key-value CSV into a dict."""
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        raise ValueError(f"CSV file is empty: {csv_path}")

    start = 0
    if (
        len(rows[0]) >= 2
        and rows[0][0].strip().lower() == "key"
        and rows[0][1].strip().lower() == "value"
    ):
        start = 1

    data = {}
    for idx, row in enumerate(rows[start:], start=start + 1):
        if not row:
            continue
        if len(row) < 2:
            raise ValueError(f"Row {idx}: expected two columns, got {len(row)}")
        key = row[0].strip()
        value = row[1].strip()
        if not key:
            continue
        data[key] = value

    return data


def validate(data):
    """Validate the parsed configuration."""
    errors = []

    for key in REQUIRED_KEYS:
        if key not in data or data[key] == "":
            errors.append(f"Missing required key '{key}'")

    for key in ENDPOINT_KEYS:
        if key in data and data[key] != "" and not data[key].startswith("/"):
            errors.append(f"Endpoint key '{key}' must start with '/': '{data[key]}'")

    if errors:
        raise ValueError("; ".join(errors))


def main():
    module = AnsibleModule(
        argument_spec=dict(
            csv_path=dict(type="str", required=True),
        ),
        supports_check_mode=True,
    )

    csv_path = module.params["csv_path"]

    if not os.path.exists(csv_path):
        module.fail_json(msg=f"CSV file not found: {csv_path}")

    try:
        data = read_csv(csv_path)
        validate(data)
    except ValueError as exc:
        module.fail_json(msg=str(exc))

    module.exit_json(
        changed=False,
        data=data,
        msg="BMC Redfish config validated successfully",
    )


if __name__ == "__main__":
    main()
