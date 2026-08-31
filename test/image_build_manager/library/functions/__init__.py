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
Image Build Manager — Functions

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

# --- Build Image verification ---
from .build_image_func import (
    check_container_running,
    check_s3_containers,
    check_s3_bucket_images,
    check_s3_buckets,
    check_registry_images,
    check_build_status_file,
    check_functional_groups_built,
    check_build_status_s3_match,
    get_configured_functional_groups,
    check_containers_removed,
    check_s3_artifacts_removed,
    check_s3_images_removed,
    verify_image_packages,
    check_services_removed,
    check_firewall_ports_removed,
    check_s3cfg_removed,
    check_credentials_removed,
    check_build_output_removed,
    check_registry_cleaned,
    check_s3cmd_configured,
    check_firewall_ports_open,
    check_services_active,
    check_credentials_present,
    check_clone_status,
    check_registry_reachable,
    check_input_config_exists,
    check_target_connectivity,
    check_env_vars_present,
    check_hostname_domain,
    check_admin_ip,
    check_omnia_setup,
    check_repo_ssl_verify_config,
    check_repo_ssl_verify_applied,
    collect_build_logs,
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
