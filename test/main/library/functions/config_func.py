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
Configuration Loading Functions.

Loads test_config.yml, test_creds.yml, and dataset-based storage
configuration with proper precedence. Kept separate from vars to
avoid circular imports with host_func and omnia_sh_func.

Usage:
    from main.library.functions.config_func import (
        load_test_config,
        load_test_credentials,
        load_storage_config,
        validate_storage_params,
    )
"""

import os
import subprocess
from typing import Dict, Any

import yaml

# Compute MODULE_ROOT directly to avoid circular import.
# config_func.py is in library/functions/, MODULE_ROOT is main/
# functions/ -> library/ -> main/
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
MODULE_ROOT = os.path.dirname(os.path.dirname(_THIS_DIR))

# Config file names (same as common_vars.py, inlined to avoid circular import)
TEST_CONFIG_FILE = "test_config.yml"
TEST_CREDENTIALS_FILE = "test_creds.yml"
TEST_CREDENTIALS_KEY = ".test_creds.key"

# Storage parameter keys that can be overridden by dataset
STORAGE_KEYS = [
    "admin_nic_ip", "share_option", "nfs_type", "nfs_server_ip",
    "nfs_server_share_path", "omnia_shared_path",
]


def load_test_config() -> Dict[str, Any]:
    """Load test_config.yml from module root."""
    config_path = os.path.join(MODULE_ROOT, TEST_CONFIG_FILE)
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def load_test_credentials() -> Dict[str, Any]:
    """Load test_creds.yml with vault auto-decrypt support."""
    creds_path = os.path.join(MODULE_ROOT, TEST_CREDENTIALS_FILE)
    key_path = os.path.join(MODULE_ROOT, TEST_CREDENTIALS_KEY)

    if not os.path.exists(creds_path):
        return {}

    # Check if vault encrypted
    with open(creds_path, "r", encoding="utf-8") as f:
        first_line = f.readline().strip()

    if first_line.startswith("$ANSIBLE_VAULT"):
        if os.path.exists(key_path):
            try:
                result = subprocess.run(
                    ["ansible-vault", "view", creds_path,
                     "--vault-password-file", key_path],
                    capture_output=True, text=True, timeout=30, check=True
                )
                return yaml.safe_load(result.stdout) or {}
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                raise ValueError(f"Failed to decrypt {creds_path}: {e}") from e
        else:
            raise ValueError(
                f"Credentials encrypted but key not found: {key_path}\n"
                f"  Ensure {TEST_CREDENTIALS_KEY} exists in module root."
            )
    else:
        # Plain text — read, create key, encrypt
        with open(creds_path, "r", encoding="utf-8") as f:
            creds = yaml.safe_load(f) or {}

        if not os.path.exists(key_path):
            import secrets
            key = secrets.token_urlsafe(32)[:32]
            with open(key_path, "w", encoding="utf-8") as f:
                f.write(key)
            os.chmod(key_path, 0o600)

        try:
            subprocess.run(
                ["ansible-vault", "encrypt", creds_path,
                 "--vault-password-file", key_path],
                capture_output=True, text=True, timeout=30, check=True
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass  # Non-fatal: creds loaded, encryption failed

        return creds


def load_storage_config() -> Dict[str, Any]:
    """Load storage configuration with proper precedence.

    Precedence:
      1. test_config.yml values are loaded first (always).
      2. If use_dataset is true, non-empty dataset values override.

    Returns:
        Dict with resolved storage parameters.
    """
    config = load_test_config()

    # Start with values from test_config.yml
    storage: Dict[str, Any] = {}
    for key in STORAGE_KEYS:
        storage[key] = config.get(key, "")

    # Track source for error messages
    storage["_source"] = "test_config.yml"
    storage["_dataset_name"] = ""

    # If use_dataset is enabled, overlay dataset values
    use_dataset = config.get("use_dataset", False)
    if use_dataset:
        dataset_name = config.get("dataset", "nfs_external")
        dataset_path = os.path.join(
            MODULE_ROOT, "datasets", dataset_name, "install_config.yml"
        )

        if os.path.exists(dataset_path):
            with open(dataset_path, "r", encoding="utf-8") as f:
                dataset_config = yaml.safe_load(f) or {}

            # Dataset values override test_config values (only non-empty)
            for key in STORAGE_KEYS:
                dataset_val = dataset_config.get(key, "")
                if dataset_val:
                    storage[key] = dataset_val

            storage["_source"] = f"datasets/{dataset_name}/install_config.yml"
            storage["_dataset_name"] = dataset_name

    return storage


def validate_storage_params(storage: Dict[str, Any]) -> None:
    """Validate required storage parameters and raise clear errors.

    Delegates to the centralized validation module to avoid duplicate logic.
    Raises ValueError if any required parameter is missing or invalid.
    """
    from main.library.validation.functions.validation_func import (
        validate_storage_params as _validate_storage,
    )
    errors = _validate_storage(storage=storage)
    if errors:
        raise ValueError("\n".join(errors))
