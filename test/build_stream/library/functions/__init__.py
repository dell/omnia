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
Build Stream — Functions

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

# --- Build Stream verification ---
from .build_stream_func import (
    check_container_running,
    check_bsm_container,
    check_postgres_container,
    check_gitlab_container,
    check_gitlab_runner_container,
    check_build_stream_health,
    verify_postgres_tables,
    verify_gitlab_server_running,
    verify_gitlab_runner_running,
    is_build_stream_enabled,
    check_input_config_exists,
    check_ports_listening,
    check_containers_removed,
    check_ports_closed,
)

# --- Validation ---
from .validation_func import (
    validate_test_config,
    validate_all,
    ConfigValidationError,
)

# --- Shared utilities ---
from .shared_func import (
    get_build_stream_host_ip,
    get_gitlab_host,
    get_gitlab_https_port,
    get_gitlab_project_name,
    get_gitlab_default_branch,
    ssh_to_gitlab,
    run_in_container,
    exec_psql_query,
    skip_if_build_stream_not_enabled,
)

# --- Database ---
from .db_func import (
    get_job_by_id,
    get_latest_job,
    get_job_stages,
    get_stage_state,
    verify_stage_completed,
    get_images_for_job,
    get_image_groups_for_job,
    get_all_image_groups,
)

# --- GitLab ---
from .gitlab_func import (
    get_gitlab_root_token,
    list_pipelines,
    get_pipeline_status,
    get_pipeline_jobs,
    cancel_pipeline,
    get_child_pipeline_id,
    get_pipeline_jobs_by_stage,
    play_manual_job,
    trigger_pipeline_with_variables,
    upload_catalog_file,
    commit_pxe_mapping_file,
    wait_for_pipeline_triggered,
)

# --- API ---
from .api_func import (
    get_catalog_roles,
    verify_registry_images,
    verify_s3_boot_images,
)

# --- Pipeline orchestration ---
from .pipeline_func import (
    get_catalog_content,
    trigger_build_pipeline,
    trigger_deploy_pipeline,
    trigger_cleanup_pipeline,
    select_image_for_deploy,
    select_image_for_cleanup,
    play_trigger_job,
    play_deploy_stage_job,
    play_cleanup_stage_job,
    wait_for_cleanup_completion,
    wait_for_stage_completion,
    get_pipeline_stage_status,
    monitor_pipeline_stages,
)

# --- Generated input verification ---
from .generated_input_func import (
    clone_omnia_repo,
    cleanup_omnia_clone,
    get_software_config,
    compare_software_json,
    verify_generated_inputs,
)


def run_playbook(tag=None, **kwargs):
    """Wrapper that injects module-specific playbook and workdir."""
    return _run_playbook(
        playbook=kwargs.pop("playbook", PLAYBOOK_ENTRY_POINT),
        playbook_workdir=kwargs.pop("playbook_workdir", PLAYBOOK_WORKDIR),
        tag=tag,
        **kwargs,
    )
