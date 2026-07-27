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
Omnia.sh Test - Configuration Variables.

Variables only — all loading logic lives in functions/config_func.py.

PRECEDENCE:
  - By default, values come from test_config.yml directly.
  - If use_dataset is true in test_config.yml, storage parameters are
    overridden by values from datasets/<dataset>/install_config.yml.
  - Sensitive credentials come from test_creds.yml (vault encrypted).

Usage:
    from main.library.vars.omnia_sh_vars import OMNIA_SH_VARS, TEST_VARS
"""

from typing import Dict, Any

from .common_vars import OMNIA_CORE_CONTAINER, CONTAINER_SSH_PORT, OMNIA_SH_PATH
from .paths_vars import OIM_METADATA_PATH

# Direct absolute import to avoid circular dependency through functions/__init__.py
from main.library.functions.config_func import (
    load_test_config,
    load_test_credentials,
    load_storage_config,
    validate_storage_params,
)


# =============================================================================
# LOAD CONFIG AT IMPORT TIME
# =============================================================================

_test_config = load_test_config()
_test_credentials = load_test_credentials()
_storage = load_storage_config()

_oim_ip = _test_config.get("oim_server_ip", "")
_admin_nic_ip = _storage.get("admin_nic_ip", "") or _test_config.get("admin_nic_ip", "")
_omnia_core_password = _test_credentials.get("omnia_core_password", "")


# =============================================================================
# OMNIA.SH VARIABLES
# - Storage config from test_config.yml (or dataset override)
# - Credentials from test_creds.yml
# =============================================================================

OMNIA_SH_VARS: Dict[str, Any] = {
    # Container config
    "container_name": OMNIA_CORE_CONTAINER,
    "ssh_port": CONTAINER_SSH_PORT,
    # OIM server
    "oim_server_ip": _oim_ip,
    "admin_nic_ip": _admin_nic_ip,
    # Storage config (from test_config.yml or dataset)
    "share_option": _storage.get("share_option", ""),
    "nfs_type": _storage.get("nfs_type", ""),
    "nfs_server_ip": _storage.get("nfs_server_ip", ""),
    "nfs_share_path": _storage.get("nfs_server_share_path", ""),
    "omnia_shared_path": _storage.get("omnia_shared_path", ""),
    "omnia_core_password": _omnia_core_password,
    # Config source tracking
    "_source": _storage.get("_source", "test_config.yml"),
    "_dataset_name": _storage.get("_dataset_name", ""),
    # omnia.sh script path
    "omnia_sh_path": OMNIA_SH_PATH,
    # Force rebuild
    "force_rebuild": _test_config.get("force_rebuild", True),
    # Timeout and polling intervals
    "build_timeout": 1800,
    "install_timeout": 600,
    "uninstall_timeout": 300,
    "poll_interval": 10,
}


# =============================================================================
# TEST VARIABLES (for pytest validation tests)
# =============================================================================

TEST_VARS: Dict[str, Any] = {
    # Container verification
    "container_name": OMNIA_CORE_CONTAINER,
    "container_file": f"/etc/containers/systemd/{OMNIA_CORE_CONTAINER}.container",
    "service_name": f"{OMNIA_CORE_CONTAINER}.service",
    "metadata_file": OIM_METADATA_PATH,
    "ssh_alias": OMNIA_CORE_CONTAINER,
    "ssh_timeout": 5,
    # From test_config.yml
    "oim_server_ip": _oim_ip,
    "admin_nic_ip": _admin_nic_ip,
    # Storage config (resolved)
    "share_option": _storage.get("share_option", ""),
    "nfs_type": _storage.get("nfs_type", ""),
    "nfs_server_ip": _storage.get("nfs_server_ip", ""),
    "nfs_share_path": _storage.get("nfs_server_share_path", ""),
    "omnia_shared_path": _storage.get("omnia_shared_path", ""),
    "omnia_core_password": _omnia_core_password,
}


def validate_current_dataset() -> None:
    """Validate the current storage configuration.

    Thin wrapper — delegates to config_func.validate_storage_params.
    """
    validate_storage_params(_storage)
