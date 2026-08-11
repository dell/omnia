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
Repo Manager — Functions

Common utilities come from the omnia_auto package.
Module-specific functions remain here.
"""

# --- Common (from omnia_auto package) ---
from omnia_auto import (
    Colors,
    Symbols,
    log,
    set_debug_mode,
    TestLogger,
    get_test_output,
    get_testinfra_host,
    load_test_config,
    load_test_credentials,
    get_module_root,
    run_on_host,
    is_local_execution,
    TestReport,
    get_current_report,
    set_current_report,
    run_playbook as _run_playbook,
)
from ..vars.common_vars import PLAYBOOK_ENTRY_POINT, PLAYBOOK_WORKDIR

# --- Repo Manager verification ---
from .repo_manager_func import (
    # Pulp container checks
    check_pulp_container_running,
    check_pulp_healthy,
    check_pulp_port_listening,
    check_pulp_cli_configured,
    check_pulp_api_endpoint,
    # Pulp infrastructure checks
    check_pulp_quadlet_exists,
    check_pulp_certs,
    check_pulp_directories,
    # Input file checks
    check_input_config_exists,
    check_credentials_present,
    check_endpoint_config_exists,
    check_software_config_exists,
    check_software_config_valid,
    # Repo status verification
    check_repo_status_file,
    check_repos_synced,
    # Cleanup verification
    check_pulp_removed,
    check_pulp_data_removed,
    check_pulp_image_removed,
    check_pulp_quadlet_removed,
    check_services_removed,
    check_containers_removed,
    check_pulp_logs_cleaned,
    check_credentials_removed,
)

# --- Validation ---
from .validation_func import (
    validate_test_config,
    validate_all,
    ConfigValidationError,
)


def run_playbook(tag=None, **kwargs):
    """Wrapper that injects module-specific playbook and workdir."""
    return _run_playbook(
        playbook=kwargs.pop("playbook", PLAYBOOK_ENTRY_POINT),
        playbook_workdir=kwargs.pop("playbook_workdir", PLAYBOOK_WORKDIR),
        tag=tag,
        **kwargs,
    )
