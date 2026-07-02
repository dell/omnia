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

#!/usr/bin/python
# pylint: disable=import-error,no-name-in-module,line-too-long

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.local_repo.validate_utils import validate_certificates

"""Ansible module to validate certificates for a repository."""
def main():
    """
    Main function for the Ansible module.

    Initializes the module, parses input arguments, and invokes the
    certificate validation logic. Based on the validation result,
    it either fails with a detailed error message or exits successfully
    with a success message.

    This function also handles exceptions gracefully and returns a
    well-structured response in compliance with Ansible's module API.
    """
    module_args = {
        "local_repo_config_path": {"type": "str", "required": True},
        "certs_path": {"type": "str", "required": True},
        "repo_key": {"type": "str", "required": False, "default": "user_repo_url"},
    }

    result = {
        "changed": False,
        "failed": False,
        "msg": "",
    }

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    try:
        validation_result = validate_certificates(
            local_repo_config_path=module.params['local_repo_config_path'],
            certs_path=module.params['certs_path'],
            repo_key=module.params['repo_key']
        )

        if validation_result.get("status") == "error":
            result["failed"] = True
            result["msg"] = "Certificate validation failed for the following repositories:\n"
            for item in validation_result.get("missing", []):
                repo_name = item.split(" ")[0]
                result["msg"] += (
                    f"  - {item}\n"
                    f"    Expected certificate files should exist under: "
                    f"{module.params['certs_path']}/{repo_name}/\n"
                )
        else:
            result["msg"] = f"All certificate checks passed for '{module.params['repo_key']}'."
    except Exception as e:
        # Catching general exception at top level to return a clean failure via Ansible
        result["failed"] = True
        result["msg"] = f"Validation failed: {str(e)}"
        module.fail_json(**result)

    module.exit_json(**result)


if __name__ == '__main__':
    main()
