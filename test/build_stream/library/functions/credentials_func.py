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

"""
Build Stream — BuildStream domain credentials (build_stream_credentials.yml).

Reads the credentials the product playbook stores in the project input
directory on the execution OIM (plain or ansible-vault encrypted). Values are
only returned to callers; they are never logged.
"""

from typing import Dict

from omnia_auto import run_on_host

from library.vars.common_vars import (
    BUILD_STREAM_CREDENTIALS_FILE,
    BUILD_STREAM_CREDENTIALS_KEY,
    CMDS,
)
from library.vars.execute_vars import OMNIA_ENV_FILE
from ._config_helpers import resolve_build_stream_input_path


_server_creds_cache: Dict[str, str] = {}


def load_server_credentials(host) -> Dict[str, str]:
    """Load credentials from build_stream_credentials.yml on the target host.

    Reads credentials from the Build Stream input directory resolved from
    ``OMNIA_DATA_PATH`` and ``OMNIA_PROJECT_NAME`` on the execution OIM.
    Handles both plain-text and ansible-vault encrypted files.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict of credential key-value pairs. Empty if file not found.
    """
    if _server_creds_cache:
        return dict(_server_creds_cache)

    input_path = resolve_build_stream_input_path(host)
    creds_path = f"{input_path}/{BUILD_STREAM_CREDENTIALS_FILE}"
    key_path = f"{input_path}/{BUILD_STREAM_CREDENTIALS_KEY}"

    creds: Dict[str, str] = {"_path": creds_path}

    # Try reading as plain text first
    cmd = CMDS["cat_file"].format(path=creds_path)
    result = run_on_host(host, cmd)
    if result.rc != 0 or not result.stdout.strip():
        return creds

    content = result.stdout.strip()

    # If vault-encrypted, decrypt
    if content.startswith("$ANSIBLE_VAULT"):
        decrypt_cmd = CMDS["vault_decrypt_creds"].format(
            env_file=OMNIA_ENV_FILE, key_path=key_path, creds_path=creds_path,
        )
        decrypt_result = run_on_host(host, decrypt_cmd)
        if decrypt_result.rc == 0 and decrypt_result.stdout.strip():
            content = decrypt_result.stdout.strip()
        else:
            creds["_error"] = (
                f"cannot decrypt {creds_path} with the venv's ansible-vault "
                f"(OMNIA_VENV_PATH in {OMNIA_ENV_FILE}) and {key_path}"
            )
            return creds

    # Parse YAML key-value pairs
    for line in content.split("\n"):
        line = line.strip()
        if ":" in line and not line.startswith("#") and not line.startswith("---"):
            key, _, val = line.partition(":")
            creds[key.strip()] = val.strip().strip('"').strip("'")

    _server_creds_cache.update(creds)
    return creds
