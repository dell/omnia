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

#!/usr/bin/python
# pylint: disable=import-error,no-name-in-module

"""Ansible module for encrypting, decrypting, or viewing Ansible Vault files."""

import os

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.local_repo.common_functions import (
    is_encrypted,
    process_file,
    load_vault_yaml,
)


def main():
    """Run the vault handler module."""
    module = AnsibleModule(
        argument_spec={
            "file_path": {"type": "str", "required": True},
            "vault_key": {"type": "str", "required": True},
            "mode": {
                "type": "str",
                "required": True,
                "choices": ["encrypt", "decrypt", "view"]
            },
        },
        supports_check_mode=True,
    )

    file_path = module.params["file_path"]
    vault_key = module.params["vault_key"]
    mode = module.params["mode"]

    if not os.path.isfile(file_path):
        module.fail_json(msg=f"File not found: {file_path}")

    file_is_encrypted = is_encrypted(file_path)

    if mode == "view":
        data = load_vault_yaml(file_path, vault_key)
        module.exit_json(changed=False, data=data)

    # Determine if the operation will actually modify the file.
    will_change = (
        (mode == "decrypt" and file_is_encrypted) or
        (mode == "encrypt" and not file_is_encrypted)
    )

    success, message = process_file(file_path, vault_key, mode)
    if not success:
        module.fail_json(msg=message)

    module.exit_json(changed=will_change, msg=message)


if __name__ == "__main__":
    main()
