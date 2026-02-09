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
#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.local_repo.common_functions import (
    load_yaml_file,
    get_repo_list,
    is_encrypted,
    process_file
)
from ansible.module_utils.local_repo.registry_utils import (
    validate_user_registry,
    check_reachability,
    find_invalid_cert_paths
)
# from ansible.module_utils.local_repo.config import (
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
    except FileNotFoundError as e:
        module.fail_json(msg=str(e))

    user_registry = get_repo_list(config_data, "user_registry")
    # if user_registry:
    #     # Load credentials
    #     if is_encrypted(user_reg_cred_input):
    #         process_file(user_reg_cred_input, user_reg_key_path, 'decrypt')

    #     file2_data = load_yaml_file(user_reg_cred_input)
    #     cred_lookup = {
    #         entry['name']: entry
    #         for entry in file2_data.get('user_registry_credential', [])
    #     }

    #     # Update user_registry entries with credentials if required
    #     for registry in user_registry:
    #         if registry.get("requires_auth"):
    #             creds = cred_lookup.get(registry.get("name"))
    #             if creds:
    #                 registry["username"] = creds.get("username")
    #                 registry["password"] = creds.get("password")

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
