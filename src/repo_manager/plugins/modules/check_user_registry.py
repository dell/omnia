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

"""Validate configured container registries and their TLS settings."""

# pylint: disable=import-error,no-name-in-module

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.repo_manager.common_functions import (
    load_yaml_file,
)
from ansible.module_utils.repo_manager.registry_utils import (
    validate_user_registry,
    check_reachability,
    find_invalid_cert_paths
)

DOCUMENTATION = r"""
---
module: check_user_registry
short_description: Validate user container registry configuration
description:
  - This module validates user-provided container registry configurations.
  - It checks connectivity and authentication to specified registries.
version_added: "1.0.0"
options:
    config_file:
      description: Path to repo_manager_config.yml
      required: true
      type: str
    timeout:
      description: Connection timeout in seconds
      required: false
      type: int
      default: 30

author:
  - Dell Technologies (@dell)
"""

EXAMPLES = r"""
- name: Check configured registry connectivity
  check_user_registry:
    config_file: "{{ repo_manager_runtime_dir }}/input/project_default/repo_manager_config.yml"
    timeout: 5
"""

RETURN = r"""
valid_registries:
  description: List of valid registries
  type: list
  returned: always
invalid_registries:
  description: List of invalid registries with errors
  type: list
  returned: always
"""
# from ansible.module_utils.repo_manager.config import (
#     USER_REG_CRED_INPUT,
#     USER_REG_KEY_PATH
# )


def main():
    """
    Ansible module to validate user registry entries.
    """
    module = AnsibleModule(
        # argument_spec=dict(
        #     timeout=dict(type='int', default=5),
        #     config_file=dict(type='str', required=True),
        #     user_reg_cred_input=dict(type='str', required=False, default=USER_REG_CRED_INPUT),
        #     user_reg_key_path=dict(type='str', required=False, default=USER_REG_KEY_PATH)
        # ),
        argument_spec=dict(
            timeout=dict(type='int', default=5),
            config_file=dict(type='str', required=True)
        ),
        supports_check_mode=True
    )

    # config_path = module.params['config_file']
    # timeout = module.params['timeout']
    # user_reg_cred_input = module.params["user_reg_cred_input"]
    # user_reg_key_path = module.params["user_reg_key_path"]

    config_path = module.params['config_file']
    timeout = module.params['timeout']
    try:
        config_data = load_yaml_file(config_path)
    except FileNotFoundError:
        module.fail_json(msg="Registry configuration file was not found")

    registries = config_data.get("registries") or {}

    if not registries:
        module.exit_json(
            changed=False,
            msg="No configured registry entries found. Skipping validation.",
            reachable_registries=[],
            unreachable_registries=[],
            unreachable_count=0
        )

    # Validate entries
    is_valid, error_msg = validate_user_registry(registries)
    if not is_valid:
        module.fail_json(msg=f"[Validation Error] {error_msg}")

    # Reachability
    reachable, unreachable = check_reachability(registries, timeout)

    # Cert path validation
    invalid_paths = find_invalid_cert_paths(registries)
    if invalid_paths:
        module.fail_json(msg=f"[Cert Path Error] Invalid cert_path(s): {invalid_paths}")

    module.exit_json(
        changed=False,
        reachable_registries=reachable,
        unreachable_registries=unreachable,
        unreachable_count=len(unreachable)
    )


if __name__ == '__main__':
    main()
