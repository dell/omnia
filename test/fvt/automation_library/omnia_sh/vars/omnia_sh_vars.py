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

This module loads configuration variables for omnia.sh verification tests.
- Non-sensitive settings come from omnia_test_config.yml
- Sensitive credentials (omnia_core_password) come from omnia_test_credentials.yml

Usage:
    from automation_library.omnia_sh.vars.omnia_sh_vars import OMNIA_SH_VARS, TEST_VARS

"""

from typing import Dict, Any

from ...core import (
    load_omnia_test_config,
    load_omnia_test_credentials,
    OIM_METADATA_PATH as _CORE_OIM_METADATA_PATH,
    OMNIA_CORE_CONTAINER as _CORE_CONTAINER,
    OMNIA_SH_PATH as _OMNIA_SH_PATH,
)

_omnia_test_config = load_omnia_test_config()
_omnia_test_credentials = load_omnia_test_credentials()


# =============================================================================
# OMNIA.SH VARIABLES
# - Config values from omnia_test_config.yml
# - Credentials from omnia_test_credentials.yml
# =============================================================================

# OIM server config
_oim_server_ip = _omnia_test_config.get("oim_server_ip", "")

# NFS configuration (from config)
_share_option = _omnia_test_config.get("share_option", "")
_nfs_type = _omnia_test_config.get("nfs_type", "")
_nfs_server_ip = _omnia_test_config.get("nfs_server_ip", "")
_nfs_share_path = _omnia_test_config.get("nfs_share_path", "")
_omnia_shared_path = _omnia_test_config.get("omnia_shared_path", "")

# Credentials (from credentials file)
_omnia_core_password = _omnia_test_credentials.get("omnia_core_password", "")

OMNIA_SH_VARS: Dict[str, Any] = {
    # Container config (hardcoded - same as omnia.sh)
    "container_name": _CORE_CONTAINER,
    "ssh_port": 2222,
    # OIM server
    "oim_server_ip": _oim_server_ip,
    # NFS config from omnia_test_config.yml
    "share_option": _share_option,
    "nfs_type": _nfs_type,
    "nfs_server_ip": _nfs_server_ip,
    "nfs_share_path": _nfs_share_path,
    "omnia_shared_path": _omnia_shared_path,
    "omnia_core_password": _omnia_core_password,
    # omnia.sh script path (from core)
    "omnia_sh_path": _OMNIA_SH_PATH,
    # Timeout and polling intervals for install/uninstall operations
    "install_timeout": 600,       # 10 minutes for install
    "uninstall_timeout": 300,     # 5 minutes for uninstall
    "poll_interval": 10,          # 10 seconds progress poll interval
}


# =============================================================================
# TEST VARIABLES (for pytest validation tests)
# =============================================================================

TEST_VARS: Dict[str, Any] = {
    # Container verification
    "container_name": _CORE_CONTAINER,
    "container_file": f"/etc/containers/systemd/{_CORE_CONTAINER}.container",
    "service_name": f"{_CORE_CONTAINER}.service",
    "metadata_file": _CORE_OIM_METADATA_PATH,
    "ssh_alias": _CORE_CONTAINER,
    "ssh_timeout": 5,
    # From omnia_test_config.yml
    "oim_server_ip": _oim_server_ip,
    "share_option": _share_option,
    "nfs_type": _nfs_type,
    "nfs_server_ip": _nfs_server_ip,
    "nfs_share_path": _nfs_share_path,
    "omnia_shared_path": _omnia_shared_path,
    "omnia_core_password": _omnia_core_password,
}
