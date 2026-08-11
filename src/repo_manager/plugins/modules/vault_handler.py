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
from ansible.module_utils.repo_manager.common_functions import (
    is_encrypted,
    process_file,
    load_vault_yaml,
)

DOCUMENTATION = r"""
---
module: vault_handler
short_description: Encrypt, decrypt, or view Ansible Vault files
description:
  - This module handles Ansible Vault operations including encryption, decryption, and viewing of vault-encrypted files.
  - It uses the ansible-vault library to perform cryptographic operations.
version_added: "1.0.0"
options:
    file_path:
      description: Path to the file to encrypt/decrypt/view
      required: true
      type: str
    vault_key:
      description: Path to the vault password file
      required: true
      type: str
    mode:
      description: Operation mode
      required: true
      type: str
      choices: ['encrypt', 'decrypt', 'view']

author:
  - Dell Technologies (@dell)
"""

EXAMPLES = r"""
- name: Encrypt a credentials file
  vault_handler:
    file_path: /opt/omnia/input/credentials.yml
    vault_key: /opt/omnia/input/.vault_key
    mode: encrypt

- name: Decrypt a credentials file
  vault_handler:
    file_path: /opt/omnia/input/credentials.yml
    vault_key: /opt/omnia/input/.vault_key
    mode: decrypt
"""

RETURN = r"""
changed:
  description: Whether the file was modified
  type: bool
  returned: always
msg:
  description: Status message
  type: str
  returned: always
"""


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
