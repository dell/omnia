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
import os
from datetime import datetime
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.repo_manager.standard_logger import setup_standard_logger
from ansible.module_utils.repo_manager.common_functions import process_file, load_yaml_file, generate_vault_key
from ansible.module_utils.repo_manager.config import (
    CERT_KEYS,
    REPO_MANAGER_LOG_DIR,
    get_repos_section,
    iterate_all_repos
)

DOCUMENTATION = r"""
---
module: cert_vault_handler
short_description: Handle certificate vault operations
description:
  - This module manages certificate-related vault operations.
  - It handles encryption and decryption of certificate files.
version_added: "1.0.0"
options:
    file_path:
      description: Path to the certificate file
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
      choices: ['encrypt', 'decrypt']

author:
  - Dell Technologies (@dell)
"""

EXAMPLES = r"""
- name: Encrypt certificate file
  cert_vault_handler:
    file_path: "{{ omnia_base }}/certs/server.crt"
    vault_key: "{{ omnia_base }}/.vault_key"
    mode: encrypt
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


def extract_repos_with_certs(repo_entries, log):
    """
    Extracts repositories that include SSL certificate configuration.

    Args:
        repo_entries (list): List of dictionaries with possible keys:
                             'name', 'sslcacert', 'sslclientkey', 'sslclientcert'.

    Returns:
        list: A list of dictionaries, each containing 'name', 'sslcacert',
              'sslclientkey', and 'sslclientcert' for repos where 'sslcacert' is present.
    """
    results = []

    for entry in repo_entries:
        if "sslcacert" in entry and entry["sslcacert"]:
            results.append({
                "name": entry.get("name", "unknown"),
                "sslcacert": entry["sslcacert"],
                "sslclientkey": entry.get("sslclientkey", ""),
                "sslclientcert": entry.get("sslclientcert", "")
            })
    log.info(f"Appended result with number of entries: {len(results)}")
    return results


def main():
    """
    Encrypt or decrypt files using Ansible Vault.

    The module takes in the following parameters:
        * file_path: The path to the file to encrypt or decrypt.
        * dir_path: The path to the directory containing files to encrypt or decrypt.
        * key_path: The path to the Ansible Vault key.
        * mode: The mode of operation, either 'encrypt' or 'decrypt'.

    The module is mutually exclusive for file_path and dir_path.
    The module requires one of file_path or dir_path.
    The module does not support check mode.
    """
    module = AnsibleModule(
    argument_spec={
        'mode': {'type': 'str', 'required': True, 'choices': ['encrypt', 'decrypt']},
        'log_dir': {
            'type': 'str', 'required': False,
            'default': os.path.join(REPO_MANAGER_LOG_DIR, 'thread_logs')
        },
        'key_path': {'type': 'str', 'required': True}
    },
    supports_check_mode=False
    )
    mode = module.params['mode']
    log_dir = module.params["log_dir"]
    vault_key_path = module.params["key_path"]
    log = setup_standard_logger(log_dir)

    start_time = datetime.now().strftime("%I:%M:%S %p")

    log.info(f"Start execution time cert_vault_handler: {start_time}")

    local_repo_path = os.path.join(vault_key_path, "repo_manager_config.yml")
    local_repo_config = load_yaml_file(local_repo_path)
    
    # Get cluster OS version from config
    cluster_os_version = local_repo_config.get("cluster_os_version", "10.0")
    
    # Collect all repos with certificates from new structure
    all_repos_with_certs = []
    for arch in ["x86_64", "aarch64"]:
        repos_section = get_repos_section(local_repo_config, cluster_os_version, arch)
        for repo_name, repo_config in iterate_all_repos(repos_section):
            if repo_config and isinstance(repo_config, dict):
                # Check if repo has any certificate keys
                has_certs = any(repo_config.get(key) for key in CERT_KEYS)
                if has_certs:
                    entry = {"name": repo_name, **repo_config}
                    all_repos_with_certs.append(entry)
    
    if not all_repos_with_certs:
        log.info("No repos with certificates found, proceeding without encryption")
        module.exit_json()

    cert_entries = extract_repos_with_certs(all_repos_with_certs, log)
    for entry in cert_entries:
        for key in CERT_KEYS:
            path = entry.get(key)
            if path and not os.path.isfile(path):
                module.fail_json(msg=f"Missing {key} for repo '{entry['name']}': {path}")

    messages = []
    changed = False

    if cert_entries:
        vault_key_path = os.path.join(vault_key_path, ".local_repo_credentials_key")
        gen_result = {}
        gen_result = generate_vault_key(vault_key_path)
        if gen_result is None:
            module.fail_json(msg=f"Unable to create key: {vault_key_path}")
        log.info("User repo found, proceeding to encrypt")
        for entry in cert_entries:
            for key in CERT_KEYS:
                path = entry.get(key)
                if path:
                    result, msg = process_file(path, vault_key_path, mode)
                    if result is False:
                        module.fail_json(msg=f"Failed to {mode} {key} for '{entry['name']}': {msg}")
                    else:
                        messages.append(msg)
                        changed = True

    module.exit_json(changed=changed, msg="; ".join(messages))


if __name__ == '__main__':
    main()
