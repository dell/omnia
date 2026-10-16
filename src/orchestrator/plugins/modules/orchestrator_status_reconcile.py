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

# pylint: disable=import-error,no-name-in-module
"""Reconcile persistent Omnia Orchestrator PXE lifecycle reports."""

from __future__ import annotations

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.orchestrator_status import (
    StatusReconcileError,
    reconcile_pxeboot_status,
)

DOCUMENTATION = r'''
---
module: orchestrator_status_reconcile
short_description: Reconcile Omnia Orchestrator PXE lifecycle status
version_added: "2.3.0"
description:
  - Normalizes and merges PXE or external boot-verification results.
  - Produces the aggregate Orchestrator status and failed-node report without
    writing files.
options:
  previous_status:
    description: Previously persisted aggregate status.
    type: dict
    default: {}
  current_nodes:
    description: Node results from a normal PXE run.
    type: list
    elements: dict
    default: []
  failed_nodes:
    description: Compact failure entries from a normal PXE run.
    type: list
    elements: dict
    default: []
  inventory_source:
    description: Absolute source inventory path.
    type: str
    required: true
  timestamp:
    description: ISO-8601 report timestamp.
    type: str
    required: true
  run_id:
    description: Unique lifecycle run identifier.
    type: str
    required: true
  verification_enabled:
    description: Whether SSH and cloud-init verification was enabled.
    type: bool
    required: true
  custom_inventory:
    description: Whether the PXE run used a custom inventory.
    type: bool
    default: false
  preserve_unselected:
    description: Preserve previous nodes omitted by a partial retry.
    type: bool
    default: false
  unverified_count:
    description: Number of nodes intentionally not verified.
    type: int
    default: 0
  provisioning_report:
    description: Provisioning report for the active inventory.
    type: dict
    default: {}
  selected_xnames:
    description: XNAMEs selected for external boot verification.
    type: list
    elements: str
  verification_results:
    description: Results returned for external boot verification.
    type: list
    elements: dict
author:
  - Dell Omnia Team
'''

EXAMPLES = r'''
- name: Reconcile PXE lifecycle status
  omnia.orchestrator.orchestrator_status_reconcile:
    previous_status: "{{ previous_status }}"
    current_nodes: "{{ current_nodes }}"
    failed_nodes: "{{ failed_nodes }}"
    inventory_source: "{{ pxe_mapping_file_path }}"
    timestamp: "{{ ansible_date_time.iso8601 }}"
    run_id: "{{ ansible_date_time.epoch }}"
    verification_enabled: true
  register: lifecycle_status
'''

RETURN = r'''
orchestrator_status:
  description: Canonical aggregate lifecycle status.
  type: dict
  returned: always
failed_nodes_report:
  description: Canonical failed-node report.
  type: dict
  returned: always
failed_xnames:
  description: XNAMEs that failed the current PXE or verification operation.
  type: list
  elements: str
  returned: always
'''


def main() -> None:
    """Run the Ansible module."""
    module = AnsibleModule(
        argument_spec={
            "previous_status": {"type": "dict", "default": {}},
            "current_nodes": {"type": "list", "elements": "dict", "default": []},
            "failed_nodes": {"type": "list", "elements": "dict", "default": []},
            "inventory_source": {"type": "str", "required": True},
            "timestamp": {"type": "str", "required": True},
            "run_id": {"type": "str", "required": True},
            "verification_enabled": {"type": "bool", "required": True},
            "custom_inventory": {"type": "bool", "default": False},
            "preserve_unselected": {"type": "bool", "default": False},
            "unverified_count": {"type": "int", "default": 0},
            "provisioning_report": {"type": "dict", "default": {}},
            "selected_xnames": {"type": "list", "elements": "str"},
            "verification_results": {"type": "list", "elements": "dict"},
        },
        supports_check_mode=True,
    )
    try:
        result = reconcile_pxeboot_status(**module.params)
    except (StatusReconcileError, TypeError, ValueError) as error:
        module.fail_json(msg=f"Unable to reconcile Orchestrator status: {error}")
    module.exit_json(changed=False, **result)


if __name__ == "__main__":
    main()
