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

"""Ansible module for atomically writing or operating on Ansible Vault files."""

import os
import tempfile
import yaml

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.repo_manager.common_functions import (
    is_encrypted,
    process_file,
    load_vault_yaml,
    run_vault_command,
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
      choices: ['encrypt', 'decrypt', 'view', 'write']
    data:
      description: YAML mapping to write atomically when mode is write
      required: false
      type: dict

author:
  - Dell Technologies (@dell)
"""

EXAMPLES = r"""
- name: Encrypt a credentials file
  vault_handler:
    file_path: "{{ omnia_base }}/input/credentials.yml"
    vault_key: "{{ omnia_base }}/input/.vault_key"
    mode: encrypt

- name: Decrypt a credentials file
  vault_handler:
    file_path: "{{ omnia_base }}/input/credentials.yml"
    vault_key: "{{ omnia_base }}/input/.vault_key"
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
                "choices": ["encrypt", "decrypt", "view", "write"]
            },
            "data": {"type": "dict", "required": False, "default": None, "no_log": True},
        },
        supports_check_mode=True,
    )

    file_path = module.params["file_path"]
    vault_key = module.params["vault_key"]
    mode = module.params["mode"]
    data = module.params["data"]

    if mode != "write" and not os.path.isfile(file_path):
        module.fail_json(msg=f"File not found: {file_path}")

    if mode == "write":
        if data is None:
            module.fail_json(msg="data is required when mode is write")
        if not os.path.isfile(vault_key):
            module.fail_json(msg=f"Vault key not found: {vault_key}")

        current_data = None
        current_encrypted = False
        if os.path.isfile(file_path):
            current_encrypted = is_encrypted(file_path)
            try:
                current_data = load_vault_yaml(file_path, vault_key)
            except Exception as exc:  # pylint: disable=broad-exception-caught
                module.fail_json(msg=f"Failed to read existing credential file: {exc}")
        if current_encrypted and current_data == data:
            module.exit_json(changed=False, msg="Credential file is already current and encrypted")
        if module.check_mode:
            module.exit_json(changed=True, msg="Credential file would be updated and encrypted")

        parent_dir = os.path.dirname(file_path)
        os.makedirs(parent_dir, mode=0o755, exist_ok=True)
        temp_fd, temp_path = tempfile.mkstemp(
            prefix=".repo_manager_credentials.", dir=parent_dir, text=True
        )
        try:
            with os.fdopen(temp_fd, "w", encoding="utf-8") as temp_file:
                yaml.safe_dump(data, temp_file, default_flow_style=False, sort_keys=False)
            os.chmod(temp_path, 0o600)
            return_code, _stdout, stderr = run_vault_command(
                "encrypt", temp_path, vault_key
            )
            if return_code != 0:
                module.fail_json(msg=f"Failed to encrypt updated credential file: {stderr}")
            os.replace(temp_path, file_path)
            os.chmod(file_path, 0o600)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
        module.exit_json(changed=True, msg="Credential file updated and encrypted atomically")

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
