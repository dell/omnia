# Copyright 2025 Dell Inc. or its subsidiaries. All Rights Reserved.
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
#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.local_repo.common_functions import load_yaml_file, get_repo_list
from ansible.module_utils.local_repo.registry_utils import (
    validate_user_registry,
    check_reachability,
    find_invalid_cert_paths
)

def main():
    """
    Ansible module to validate user registry entries.

    This module loads a YAML configuration file, validates the user registry entries,
    checks their reachability, and verifies the cert paths.

    :return: A dictionary with the results of the validation and reachability checks.
    """
    module = AnsibleModule(
        argument_spec=dict(
            timeout=dict(type='int', default=5),
            config_file=dict(type='str', required=True),
        ),
        supports_check_mode=True
    )

    config_path = module.params['config_file']
    timeout = module.params['timeout']

    try:
        config_data = load_yaml_file(config_path)
    except FileNotFoundError as e:
        module.fail_json(msg=str(e))

    user_registry = get_repo_list(config_data, "user_registry")

    # Exit early if user_registry is empty
    if not user_registry:
        module.exit_json(
            changed=False,
            msg="No user registry entries found. Skipping validation.",
            reachable_registries=[],
            unreachable_registries=[],
            unreachable_count=0
        )

    # Validate entries
    is_valid, error_msg = validate_user_registry(user_registry)
    if not is_valid:
        module.fail_json(msg=f"[Validation Error] {error_msg}")

    # Reachability
    reachable, unreachable = check_reachability(user_registry, timeout)

    # Cert path validation
    invalid_paths = find_invalid_cert_paths(user_registry)
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
