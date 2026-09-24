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

# pylint: disable=import-error,missing-function-docstring,no-name-in-module,too-many-branches
"""Declarative Ansible entry point for Omnia's OpenCHAMI integration."""

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.openchami.client import OpenChamiError
from ansible.module_utils.openchami.identity import IdentityError
from ansible.module_utils.openchami.reconciler import OpenChamiReconciler

DOCUMENTATION = r'''
---
module: openchami_reconcile
short_description: Reconcile Omnia node state with OpenCHAMI services
description:
  - Uses verified HTTPS and TokenSmith JWT authentication.
  - Resolves persistent XNAME identities, reconciles SMD groups, cleans scoped
    SMD artifacts, runs static discovery, verifies registrations, and
    idempotently reconciles Metadata Service InstanceInfo resources.
options:
  action:
    description: Reconciliation operation to perform.
    type: str
    required: true
    choices:
      - check_apis
      - resolve_identities
      - reconcile_groups
      - remove_group_memberships
      - delete_groups
      - cleanup_smd
      - discover_static
      - verify_components
      - reconcile_instanceinfos
  cluster_uri:
    description: HTTPS URL of the OpenCHAMI gateway.
    type: str
    required: true
  access_token:
    description: TokenSmith JWT used to authenticate with OpenCHAMI.
    type: str
    required: true
  ca_cert:
    description: CA certificate used to verify the OpenCHAMI gateway.
    type: path
    required: true
  nodes:
    description: PXE mapping rows to reconcile with SMD identity records.
    type: list
    elements: dict
    default: []
  smd_groups:
    description: Desired SMD groups and their complete member sets.
    type: list
    elements: dict
    default: []
  group_labels:
    description: Explicit SMD group labels to delete.
    type: list
    elements: str
    default: []
  protected_group_labels:
    description: SMD groups excluded from stale membership removal.
    type: list
    elements: str
    default: []
  target_xnames:
    description: Node XNAMEs removed from non-protected SMD groups.
    type: list
    elements: str
    default: []
  component_endpoint_xnames:
    description: Component endpoint XNAMEs targeted by scoped cleanup.
    type: list
    elements: str
    default: []
  redfish_endpoint_xnames:
    description: Redfish endpoint XNAMEs targeted by scoped cleanup.
    type: list
    elements: str
    default: []
  interface_macs:
    description: Ethernet interface MACs targeted by scoped cleanup.
    type: list
    elements: str
    default: []
  nodes_file:
    description: Static discovery YAML file consumed by ochami.
    type: path
  token_env_key:
    description: Environment-variable name expected by the ochami CLI.
    type: str
  expected_xnames:
    description: Node XNAMEs that must exist after discovery.
    type: list
    elements: str
    default: []
  instance_infos:
    description: Desired Metadata Service InstanceInfo resources.
    type: list
    elements: dict
    default: []
  timeout:
    description: Per-request network timeout in seconds.
    type: int
    default: 15
  retries:
    description: Maximum attempts for safe retryable HTTP operations.
    type: int
    default: 3
author:
  - Dell Omnia Team
'''

EXAMPLES = r'''
- name: Verify OpenCHAMI APIs with JWT and CA validation
  omnia.orchestrator.openchami_reconcile:
    action: check_apis
    cluster_uri: "https://{{ cluster_name }}.{{ cluster_domain }}:8443"
    access_token: "{{ openchami_access_token }}"
    ca_cert: "{{ openchami_ca_cert_path }}"

- name: Resolve internal XNAME identities
  omnia.orchestrator.openchami_reconcile:
    action: resolve_identities
    cluster_uri: "https://{{ cluster_name }}.{{ cluster_domain }}:8443"
    access_token: "{{ openchami_access_token }}"
    ca_cert: "{{ openchami_ca_cert_path }}"
    nodes: "{{ mapping_nodes }}"
  register: resolved_identities

- name: Reconcile per-node hostnames without duplicate InstanceInfo records
  omnia.orchestrator.openchami_reconcile:
    action: reconcile_instanceinfos
    cluster_uri: "https://{{ cluster_name }}.{{ cluster_domain }}:8443"
    access_token: "{{ openchami_access_token }}"
    ca_cert: "{{ openchami_ca_cert_path }}"
    instance_infos: "{{ desired_instance_infos }}"
'''

RETURN = r'''
result:
  description: Structured action-specific reconciliation result.
  type: dict
  returned: always
'''


def _required(module, parameter):
    value = module.params.get(parameter)
    if value in (None, "", []):
        module.fail_json(msg=f"{parameter} is required for action {module.params['action']}")
    return value


def main():
    module = AnsibleModule(
        argument_spec={
            "action": {
                "type": "str",
                "required": True,
                "choices": [
                    "check_apis",
                    "resolve_identities",
                    "reconcile_groups",
                    "remove_group_memberships",
                    "delete_groups",
                    "cleanup_smd",
                    "discover_static",
                    "verify_components",
                    "reconcile_instanceinfos",
                ],
            },
            "cluster_uri": {"type": "str", "required": True},
            "access_token": {"type": "str", "required": True, "no_log": True},
            "ca_cert": {"type": "path", "required": True},
            "nodes": {"type": "list", "elements": "dict", "default": []},
            "smd_groups": {
                "type": "list",
                "elements": "dict",
                "default": [],
            },
            "group_labels": {
                "type": "list",
                "elements": "str",
                "default": [],
            },
            "protected_group_labels": {
                "type": "list",
                "elements": "str",
                "default": [],
            },
            "target_xnames": {
                "type": "list",
                "elements": "str",
                "default": [],
            },
            "component_endpoint_xnames": {
                "type": "list",
                "elements": "str",
                "default": [],
            },
            "redfish_endpoint_xnames": {
                "type": "list",
                "elements": "str",
                "default": [],
            },
            "interface_macs": {
                "type": "list",
                "elements": "str",
                "default": [],
            },
            "nodes_file": {"type": "path"},
            "token_env_key": {"type": "str"},
            "expected_xnames": {
                "type": "list",
                "elements": "str",
                "default": [],
            },
            "instance_infos": {
                "type": "list",
                "elements": "dict",
                "default": [],
            },
            "timeout": {"type": "int", "default": 15},
            "retries": {"type": "int", "default": 3},
        },
        supports_check_mode=True,
    )

    try:
        reconciler = OpenChamiReconciler(
            base_url=module.params["cluster_uri"],
            token=module.params["access_token"],
            ca_cert=module.params["ca_cert"],
            timeout=module.params["timeout"],
            retries=module.params["retries"],
        )
        action = module.params["action"]
        if action == "check_apis":
            result = reconciler.check_apis()
        elif action == "resolve_identities":
            result = reconciler.resolve_identities(
                nodes=_required(module, "nodes"),
                check_mode=module.check_mode,
            )
        elif action == "reconcile_groups":
            result = reconciler.reconcile_groups(
                desired=_required(module, "smd_groups"),
                check_mode=module.check_mode,
            )
        elif action == "remove_group_memberships":
            result = reconciler.remove_group_memberships(
                target_xnames=_required(module, "target_xnames"),
                protected_labels=module.params["protected_group_labels"],
                check_mode=module.check_mode,
            )
        elif action == "delete_groups":
            result = reconciler.delete_groups(
                labels=_required(module, "group_labels"),
                check_mode=module.check_mode,
            )
        elif action == "cleanup_smd":
            result = reconciler.cleanup_smd(
                component_endpoint_xnames=module.params["component_endpoint_xnames"],
                redfish_endpoint_xnames=module.params["redfish_endpoint_xnames"],
                interface_macs=module.params["interface_macs"],
                check_mode=module.check_mode,
            )
        elif action == "discover_static":
            result = reconciler.discover_static(
                nodes_file=_required(module, "nodes_file"),
                access_token=module.params["access_token"],
                token_env_key=_required(module, "token_env_key"),
                expected_xnames=_required(module, "expected_xnames"),
                check_mode=module.check_mode,
            )
        elif action == "verify_components":
            result = {
                "changed": False,
                "verification": reconciler.verify_components(
                    _required(module, "expected_xnames")
                ),
            }
        else:
            result = reconciler.reconcile_instance_infos(
                desired=_required(module, "instance_infos"),
                check_mode=module.check_mode,
            )
        module.exit_json(**result)
    except (OpenChamiError, IdentityError, TypeError, ValueError) as exc:
        module.fail_json(msg=str(exc), action=module.params.get("action"))


if __name__ == "__main__":
    main()
