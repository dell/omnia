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

"""Ansible module to validate and expand a sparse admin inventory CSV."""

import os

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.omnia.discovery.plugins.module_utils import inventory_expander

DOCUMENTATION = r'''
---
module: validate_admin_inventory
short_description: Validate sparse admin inventory and expand to complete CSV
description:
  - Reads the sparse admin_inventory.csv, validates USLOT uniqueness and that each
    GROUP_NAME's RANGE has enough IPs for its entries, then expands and writes
    a complete inventory CSV with BMC_IP values.
options:
  input_csv:
    description: Path to the sparse admin_inventory.csv
    required: true
    type: str
  output_csv:
    description: Path to write the complete inventory CSV
    required: false
    type: str
'''

EXAMPLES = r'''
- name: Validate and expand admin inventory
  validate_admin_inventory:
    input_csv: "/opt/omnia/discovery/input/project_default/admin_inventory.csv"
    output_csv: "/opt/omnia/discovery/output/project_default/admin_complete_inventory.csv"
'''


def main():
    """Validate and expand a sparse admin inventory CSV."""
    module = AnsibleModule(
        argument_spec={
            "input_csv": {"type": "str", "required": True},
            "output_csv": {"type": "str", "required": False, "default": None},
        },
        supports_check_mode=True,
    )

    input_csv = module.params["input_csv"]
    output_csv = module.params["output_csv"]

    if not os.path.exists(input_csv):
        module.fail_json(msg=f"Input CSV not found: {input_csv}")

    # Parse raw sparse rows and perform validation here before expansion.
    try:
        rows = inventory_expander.parse_csv(input_csv)
    except ValueError as exc:
        module.fail_json(msg=str(exc))

    validation_errors = []

    try:
        inventory_expander.assign_uslots(rows)
    except ValueError as exc:
        validation_errors.append(str(exc))

    validation_errors.extend(inventory_expander.check_subnet_lengths(rows))

    if validation_errors:
        module.fail_json(msg="Validation failed: " + "; ".join(validation_errors))

    try:
        inventory_expander.allocate_ips(rows)
    except ValueError as exc:
        module.fail_json(msg=f"IP allocation failed: {exc}")

    complete = inventory_expander.build_complete(rows)

    changed = False
    if output_csv and not module.check_mode:
        inventory_expander.save_complete_inventory_csv(output_csv, complete)
        changed = True

    module.exit_json(
        changed=changed,
        complete=complete,
        complete_inventory_path=output_csv,
        msg=f"Validated and expanded {len(complete)} entries from {input_csv}",
    )


if __name__ == "__main__":
    main()
