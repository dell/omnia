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
Main Module — Functions

Self-contained functions for the main module covering:
- Config: Config loading, storage validation
- Formatting: Colors, Symbols, TestLogger
- Host: Testinfra connection, config loading, container exec
- Runner: PlaybookRunner with live-streaming shell execution
- Report: HTML + JSON test report generation
- NFS: Internal NFS server setup/cleanup on RHEL
- Omnia.sh: Install/uninstall verification functions
"""

# --- Formatting ---
from .formatting_func import (
    Colors,
    Symbols,
    log,
    set_debug_mode,
    TestLogger,
    get_test_output,
)

# --- Host / Config ---
from .host_func import (
    get_testinfra_host,
    load_test_config,
    load_test_credentials,
    encrypt_test_credentials,
    get_module_root,
    run_on_oim,
    run_in_container,
    is_local_execution,
)

# --- Runner ---
from .runner_func import PlaybookRunner

# --- Report ---
from .report_func import (
    TestReport,
    get_current_report,
    set_current_report,
)

# --- NFS ---
from .nfs_func import (
    setup_internal_nfs_server,
    verify_nfs_server_running,
    cleanup_internal_nfs_server,
)

# --- Omnia.sh verification and deploy ---
from .omnia_sh_func import (
    check_omnia_sh_exists,
    validate_nfs_config,
    check_container_running,
    check_file_exists,
    check_service_running,
    check_ssh_to_container,
    check_ssh_from_container,
    check_metadata_file,
    check_container_not_running,
    check_service_not_exists,
    check_fstab_entry_removed,
    check_mount_removed,
    check_ssh_key_pair_exists,
    check_ssh_config_entry,
    check_authorized_key,
    check_container_image_exists,
    check_omnia_dir_in_container,
    check_log_dirs_exist,
    check_omnia_version,
    check_ssh_key_pair_removed,
    check_ssh_config_entry_removed,
    check_known_hosts_cleaned,
)
