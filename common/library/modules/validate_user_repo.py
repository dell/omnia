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
# pylint: disable=import-error
#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.local_repo.validate_utils import validate_certificates

def main():
    """
    Ansible module to validate certificates for a repository.

    This module takes in the path to a local repository configuration file,
    the path to a directory containing certificates, and an optional key to
    specify which repository to validate. It then checks if the expected
    certificate files exist for the specified repository.

    :return: A dictionary with the result of the validation, including a
             boolean indicating whether the validation failed, and a message
             describing the result.
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
        module.fail_json(msg=f"Validation failed: {str(e)}", **result)

    module.exit_json(**result)

if __name__ == '__main__':
    main()
