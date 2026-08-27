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

"""Log and error messages for credential management."""

from typing import Dict

CREDENTIAL_LOG_MSGS: Dict[str, str] = {
    "vault_key_created": "Vault key created: {key_path}",
    "vault_key_exists": "Vault key already exists: {key_path}",
    "creds_encrypted": "Credentials encrypted: {creds_path}",
    "creds_already_encrypted": "Credentials already encrypted: {creds_path}",
    "creds_decrypted": "Credentials decrypted successfully",
    "creds_written": "Credentials written and encrypted: {creds_path}",
    "field_read": "Read field '{field}' from {creds_path}",
    "field_not_found": "Field '{field}' not found in {creds_path}",
    "creds_file_created": "Credentials file created: {creds_path}",
    "fields_merged": "Merged {count} field(s) into {creds_path}",
}

CREDENTIAL_ERROR_MSGS: Dict[str, str] = {
    "vault_not_installed": (
        "ansible-vault not found.\n"
        "\n"
        "  HOW TO FIX:\n"
        "    1. Install ansible-core: pip install ansible-core\n"
        "    2. Or activate the omnia venv: source /opt/omnia/venv/bin/activate"
    ),
    "encrypt_failed": (
        "Failed to encrypt {creds_path}: {error}\n"
        "\n"
        "  HOW TO FIX:\n"
        "    1. Verify vault key exists: ls -la {key_path}\n"
        "    2. Verify file permissions: ls -la {creds_path}\n"
        "    3. Re-create vault key and re-encrypt"
    ),
    "decrypt_failed": (
        "Failed to decrypt {creds_path}: {error}\n"
        "\n"
        "  HOW TO FIX:\n"
        "    1. Verify vault key matches: {key_path}\n"
        "    2. If key is lost, delete the creds file and re-create it\n"
        "    3. Check: ansible-vault view {creds_path}"
        " --vault-password-file {key_path}"
    ),
    "creds_not_found": (
        "Credentials file not found: {creds_path}\n"
        "\n"
        "  HOW TO FIX:\n"
        "    1. Run setup_env.sh --set-domain-creds to create it\n"
        "    2. Or create manually and encrypt with ansible-vault"
    ),
    "key_not_found": (
        "Vault key not found: {key_path}\n"
        "  Credentials are encrypted but the key is missing.\n"
        "\n"
        "  HOW TO FIX:\n"
        "    1. If you have a backup of the key, restore it\n"
        "    2. Otherwise delete {creds_path} and re-create credentials"
    ),
    "env_var_missing": (
        "Required environment variable '{var}' is not set.\n"
        "\n"
        "  HOW TO FIX:\n"
        "    1. Source the omnia env: source /opt/omnia/venv/bin/activate\n"
        "    2. Or set manually: export {var}=<value>"
    ),
}
