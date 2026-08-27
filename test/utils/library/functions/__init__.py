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
Utils Domain — Functions Package.

Re-exports all functions from omnia_auto and domain-specific modules.
Test files should import from this package, not directly from omnia_auto.
"""

# --- Common functions from omnia_auto ---
from omnia_auto import (
    TestLogger,
    Colors,
    Symbols,
    log,
    load_test_config,
    load_test_credentials,
    get_testinfra_host,
    run_on_host,
    is_local_execution,
    read_remote_env,
    run_playbook as _run_playbook,
)

# --- Domain-specific functions ---
from .utils_func import (
    check_target_connectivity,
    check_env_var,
    check_file_exists,
    check_dir_exists,
    read_remote_file,
    validate_yaml_file,
    validate_collect_pxe_file,
    find_log_bundle,
    validate_metadata_file,
    validate_tar_contents,
    validate_bundle_log_files,
    get_hostname,
    check_admin_ip_assigned,
    validate_install_os_config,
    validate_install_os_credentials,
    find_custom_iso,
    verify_iso_checksum,
    verify_kickstart_in_iso,
)

from .host_func import (
    sync_project_to_remote,
    sync_utils_input,
    sync_install_os_credentials,
    get_utils_input_path,
    get_utils_output_path,
)

from .validation_func import (
    validate_all,
    ConfigValidationError,
)

# --- Domain-specific vars ---
from ..vars.common_vars import (
    PLAYBOOK_COLLECT,
    PLAYBOOK_INSTALL_OS,
    PLAYBOOK_WORKDIR,
)


def run_playbook(playbook=None, tag=None, **kwargs):
    """Run an Ansible playbook with domain-specific defaults.

    Args:
        playbook: Playbook filename (default: collect.yml).
        tag: Playbook tag to run.
        **kwargs: Additional arguments passed to omnia_auto.run_playbook().

    Returns:
        dict: {"success": bool, "rc": int, "duration": str, "output": str, "error": str}
    """
    return _run_playbook(
        playbook=playbook or PLAYBOOK_COLLECT,
        playbook_workdir=kwargs.pop("playbook_workdir", PLAYBOOK_WORKDIR),
        tag=tag,
        **kwargs,
    )


__all__ = [
    # omnia_auto exports
    "TestLogger",
    "Colors",
    "Symbols",
    "log",
    "load_test_config",
    "load_test_credentials",
    "get_testinfra_host",
    "run_on_host",
    "is_local_execution",
    "read_remote_env",
    "run_playbook",
    # Domain functions
    "check_target_connectivity",
    "check_env_var",
    "check_file_exists",
    "check_dir_exists",
    "read_remote_file",
    "validate_yaml_file",
    "validate_collect_pxe_file",
    "find_log_bundle",
    "validate_metadata_file",
    "validate_tar_contents",
    "validate_bundle_log_files",
    "get_hostname",
    "check_admin_ip_assigned",
    "validate_install_os_config",
    "validate_install_os_credentials",
    "find_custom_iso",
    "verify_iso_checksum",
    "verify_kickstart_in_iso",
    "sync_project_to_remote",
    "sync_utils_input",
    "sync_install_os_credentials",
    "get_utils_input_path",
    "get_utils_output_path",
    "validate_all",
    "ConfigValidationError",
]
