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
Omnia Shell Functions

Modular organization of Omnia shell deployment and management functions
organized by functionality: functions, variables, and messages.
"""

# Import specific items to avoid circular imports
# Note: Import functions first, then vars and messages to avoid circular dependency
from .functions.omnia_sh_func import (
    # Deploy (install / uninstall) - testinfra based, run omnia.sh source
    check_omnia_sh_exists,
    validate_nfs_config,
    setup_internal_nfs_server,
    run_omnia_sh_install_testinfra,
    run_omnia_sh_uninstall_testinfra,
    # Verification functions
    check_container_running,
    check_file_exists,
    check_service_running,
    check_ssh_to_container,
    check_ssh_from_container,
    check_metadata_file,
    # Cleanup verification functions
    check_container_not_running,
    check_service_not_exists,
    check_fstab_entry_removed,
    check_mount_removed,
)
from .vars.omnia_sh_vars import OMNIA_SH_VARS, TEST_VARS
from .messages.omnia_sh_msgs import OMNIA_SH_MSGS, TEST_NAMES

__all__ = [
    "check_omnia_sh_exists",
    "validate_nfs_config",
    "setup_internal_nfs_server",
    "run_omnia_sh_install_testinfra",
    "run_omnia_sh_uninstall_testinfra",
    "check_container_running",
    "check_file_exists",
    "check_service_running",
    "check_ssh_to_container",
    "check_ssh_from_container",
    "check_metadata_file",
    "check_container_not_running",
    "check_service_not_exists",
    "check_fstab_entry_removed",
    "check_mount_removed",
    "OMNIA_SH_VARS",
    "TEST_VARS",
    "OMNIA_SH_MSGS",
    "TEST_NAMES",
]
