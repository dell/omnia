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

Common utilities from omnia_auto and domain-specific
verification functions for GitLab and BuildStream health.
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
    build_report_name,
    record_playbook_failure,
    run_playbook as _run_playbook,
)
from library.vars.common_vars import PLAYBOOK_ENTRY_POINT, PLAYBOOK_WORKDIR
from library.functions.host_func import (
    check_target_connectivity,
    sync_build_stream_input,
    sync_project_to_remote,
)

# --- GitLab verification ---
from library.functions.gitlab_func import (
    check_gitlab_packages_installed,
    check_gitlab_server_reachable,
    check_gitlab_runner_container,
    check_gitlab_runner_quadlet,
    check_gitlab_runner_services,
    check_gitlab_url_accessible,
    check_gitlab_services_running,
    check_gitlab_resources,
    check_puma_workers,
    check_sidekiq_concurrency,
    check_gitlab_project_exists,
    check_gitlab_project_visibility,
    check_gitlab_default_branch,
    check_gitlab_repo_file_exists,
    check_gitlab_pipeline_variables,
    check_omnia_env_in_repo,
    check_domain_input_dirs,
)

# --- GitLab mode (hosted / external) and external GitLab verification ---
from library.functions.gitlab_mode_func import (
    mode_applies,
    reset_gitlab_mode_cache,
    resolve_gitlab_mode,
)
from library.functions.gitlab_external_func import (
    check_external_ca_bundle,
    check_external_ci_token,
    check_external_credentials,
    check_external_gitlab_api,
    check_external_journal,
    check_external_project,
    check_external_runner,
    check_external_trigger_and_variables,
    check_gitlab_mode_inputs,
)

# --- BuildStream health verification ---
from library.functions.build_stream_func import (
    check_build_stream_enabled,
    check_build_stream_health,
    check_postgres_tables,
    check_omnia_venv,
    check_bsm_tls_certificate,
    check_nfs_queue_directory,
    check_buildstream_directories_present,
    check_playbook_watcher,
)

# --- Legacy pipeline functions (old FVT build/deploy/cadence/cleanup suites, NFT) ---

# --- BuildStream domain credentials ---
from library.functions.credentials_func import (
    load_server_credentials,
)

# --- Cleanup verification ---
from library.functions.cleanup_func import (
    # GitLab cleanup
    check_gitlab_packages_removed,
    check_gitlab_runner_container_removed,
    check_gitlab_runner_quadlet_removed,
    check_gitlab_runner_services_stopped,
    check_gitlab_url_not_accessible,
    check_gitlab_directories_removed,
    check_gitlab_services_stopped,
    check_gitlab_port_free,
    # BuildStream domain cleanup
    check_buildstream_container_stopped,
    check_buildstream_container_removed,
    check_buildstream_quadlet_files_removed,
    check_buildstream_services_stopped,
    check_playbook_watcher_service_disabled,
    check_playbook_watcher_service_stopped,
    check_playbook_watcher_service_file_removed,
    check_postgres_container_stopped,
    check_postgres_container_removed,
    check_postgres_quadlet_files_removed,
    check_postgres_services_stopped,
    check_buildstream_directories_removed,
    check_buildstream_runtime_caches_removed,
    check_buildstream_api_port_closed,
    check_credentials_per_flag,
    check_job_data_per_backup,
    check_postgres_data_per_backup,
)

# --- exec -> verify run state ---
from library.functions.state_func import clear_run_state, load_run_state, save_run_state

# --- Streamed omnia.sh / playbook execution ---
from library.functions.command_func import run_ansible_playbook, run_omnia_sh

# --- Prepare base (BuildStream prerequisites) ---
from library.functions.prepare_base_func import (
    check_prepare_base_prerequisites,
    check_repo_manager_ready,
    check_image_build_manager_ready,
    check_orchestrator_ready,
)

# --- Shared probes and result rendering ---
from library.functions.probe_func import (
    failure_summary,
    result_fields,
)

# --- Precheck (build_stream.yml --tags precheck) ---
from library.functions.precheck_func import (
    check_precheck_environment,
    check_precheck_oim_identity,
    check_precheck_admin_ipv4,
    check_precheck_data_path_export,
    check_precheck_containers,
    check_precheck_credentials,
    check_precheck_domain_files,
)

# --- Prepare (build_stream.yml --tags prepare) ---
from library.functions.prepare_func import (
    check_prepare_containers,
    check_prepare_services,
    check_prepare_status_file,
)

# --- Execute: build/deploy (automatic + manual), cadence, image cleanup ---
from library.functions.cadence_toggle_func import (
    verify_cadence_disable_live,
    verify_cadence_reenable_live,
)
from library.functions.config_func import (
    cleanup_settings,
    gitlab_settings,
    installation_settings,
)
from library.functions.image_cleanup_func import (
    build_auto_cleanup_image_step,
    build_pipeline_cleanup_image_step,
    precheck_auto_cleanup_step,
    run_auto_cleanup_step,
    run_pipeline_cleanup,
    start_pipeline_cleanup,
    verify_auto_cleanup_artifacts_step,
    verify_auto_cleanup_db_step,
    verify_pipeline_cleanup_db,
    verify_pipeline_cleanup_nfs,
    verify_pipeline_cleanup_registry,
    verify_pipeline_cleanup_s3,
)
from library.functions.report_func import report_check, report_tag_playbook
from library.functions.log_func import failure_fields, run_step, skip_test
from library.functions.pipeline_steps_func import (
    run_deploy_stage,
    run_stage_step,
    select_deploy_image,
    start_build_pipeline,
    start_cadence_pipeline,
    start_deploy_pipeline,
    verify_build_result,
    verify_cadence_result,
    verify_deploy_result,
    verify_image_build_artifacts,
    verify_job_image_group_mapping,
    verify_oauth_client,
    verify_repo_manager_status,
    verify_restart_node_results,
)

# --- Execute: pipeline log observability (ER-BSM-003, log_query suite) ---
from library.functions.log_query_func import (
    resolve_log_target,
    verify_log_errors,
    verify_log_full,
    verify_log_job_metadata,
    verify_log_scopes,
    verify_log_stage_filter,
    verify_log_tail,
)
from library.functions.log_redaction_func import verify_write_time_redaction
from library.functions.log_ci_func import verify_ci_log_preview, verify_ci_log_templates
from library.functions.log_fixture_func import (
    release_log_fixture_job,
    verify_log_concurrency_limit,
    verify_log_full_truncation,
    verify_log_job_ownership,
    verify_log_missing_file,
    verify_log_path_violation,
    verify_log_rate_limit,
    verify_log_response_redaction,
    verify_log_unavailable_reasons,
)

# --- Validation ---
from library.functions.validation_func import (
    validate_test_config,
    validate_all,
    ConfigValidationError,
)

# --- Non-functional security (file permissions / ownership) ---
from library.functions.security_func import (
    check_file_permissions,
)

# --- Non-functional resilience and security ---
from library.functions.nft_func import (
    artifact_path_absent,
    bsm_request,
    build_child_pipeline_id,
    cancel_nft_pipeline,
    create_disposable_job,
    forbidden_upload_absent,
    get_bsm_context,
    get_bsm_job_details,
    get_scoped_token,
    pipeline_status,
    restart_service,
    secret_absent_from_bsm_logs,
    stop_service,
    trigger_catalog_job,
    update_job_id_in_config,
    upload_inline_file,
    upload_oversized_file,
    wait_for_pipeline_status,
    wait_for_queue_claimed,
    wait_for_queue_entry,
)


def run_playbook(extra_vars=None, **kwargs):
    """Wrapper that injects module-specific playbook and workdir."""
    return _run_playbook(
        playbook=kwargs.pop("playbook", PLAYBOOK_ENTRY_POINT),
        playbook_workdir=kwargs.pop("playbook_workdir", PLAYBOOK_WORKDIR),
        extra_vars=extra_vars,
        **kwargs,
    )


__all__ = [
    "report_check",
    "report_tag_playbook",
    # Common
    "Colors",
    "Symbols",
    "log",
    "set_debug_mode",
    "TestLogger",
    "get_test_output",
    "get_testinfra_host",
    "load_test_config",
    "load_test_credentials",
    "get_module_root",
    "run_on_host",
    "is_local_execution",
    "TestReport",
    "get_current_report",
    "set_current_report",
    "build_report_name",
    "record_playbook_failure",
    "run_playbook",
    "artifact_path_absent",
    "bsm_request",
    "build_child_pipeline_id",
    "cancel_nft_pipeline",
    "create_disposable_job",
    "forbidden_upload_absent",
    "get_bsm_context",
    "get_bsm_job_details",
    "get_scoped_token",
    "pipeline_status",
    "restart_service",
    "secret_absent_from_bsm_logs",
    "stop_service",
    "trigger_catalog_job",
    "update_job_id_in_config",
    "upload_inline_file",
    "upload_oversized_file",
    "wait_for_pipeline_status",
    "wait_for_queue_claimed",
    "wait_for_queue_entry",
    "check_target_connectivity",
    "sync_build_stream_input",
    "sync_project_to_remote",
    # GitLab
    "check_gitlab_packages_installed",
    "check_gitlab_server_reachable",
    "check_gitlab_runner_container",
    "check_gitlab_runner_quadlet",
    "check_gitlab_runner_services",
    "check_gitlab_url_accessible",
    "check_gitlab_services_running",
    "check_gitlab_resources",
    "check_puma_workers",
    "check_sidekiq_concurrency",
    "check_gitlab_project_exists",
    "check_gitlab_project_visibility",
    "check_gitlab_default_branch",
    "check_gitlab_repo_file_exists",
    "check_gitlab_pipeline_variables",
    "check_omnia_env_in_repo",
    "check_domain_input_dirs",
    "gitlab_settings",
    "mode_applies",
    "reset_gitlab_mode_cache",
    "resolve_gitlab_mode",
    "check_external_ca_bundle",
    "check_external_ci_token",
    "check_external_credentials",
    "check_external_gitlab_api",
    "check_external_journal",
    "check_external_project",
    "check_external_runner",
    "check_external_trigger_and_variables",
    "check_gitlab_mode_inputs",
    # BuildStream health
    "check_build_stream_enabled",
    "check_build_stream_health",
    "check_postgres_tables",
    "check_omnia_venv",
    "check_bsm_tls_certificate",
    "check_nfs_queue_directory",
    "check_buildstream_directories_present",
    "check_playbook_watcher",
    # GitLab cleanup
    "check_gitlab_packages_removed",
    "check_gitlab_runner_container_removed",
    "check_gitlab_runner_quadlet_removed",
    "check_gitlab_runner_services_stopped",
    "check_gitlab_url_not_accessible",
    "check_gitlab_directories_removed",
    "check_gitlab_services_stopped",
    "check_gitlab_port_free",
    # BuildStream domain cleanup
    "check_buildstream_container_stopped",
    "check_buildstream_container_removed",
    "check_buildstream_quadlet_files_removed",
    "check_buildstream_services_stopped",
    "check_playbook_watcher_service_disabled",
    "check_playbook_watcher_service_stopped",
    "check_playbook_watcher_service_file_removed",
    "check_postgres_container_stopped",
    "check_postgres_container_removed",
    "check_postgres_quadlet_files_removed",
    "check_postgres_services_stopped",
    "check_buildstream_directories_removed",
    "check_buildstream_runtime_caches_removed",
    "check_buildstream_api_port_closed",
    "check_credentials_per_flag",
    "check_job_data_per_backup",
    "check_postgres_data_per_backup",
    "load_server_credentials",
    # Prepare base
    "check_prepare_base_prerequisites",
    "clear_run_state",
    "load_run_state",
    "save_run_state",
    "run_ansible_playbook",
    "run_omnia_sh",
    "check_repo_manager_ready",
    "check_image_build_manager_ready",
    "check_orchestrator_ready",
    "failure_summary",
    "result_fields",
    # Precheck
    "check_precheck_environment",
    "check_precheck_oim_identity",
    "check_precheck_admin_ipv4",
    "check_precheck_data_path_export",
    "check_precheck_containers",
    "check_precheck_credentials",
    "check_precheck_domain_files",
    # Prepare
    "check_prepare_containers",
    "check_prepare_services",
    "check_prepare_status_file",
    # Execute: build/deploy (automatic + manual), cadence, image cleanup
    "failure_fields",
    "installation_settings",
    "skip_test",
    "cleanup_settings",
    "build_auto_cleanup_image_step",
    "build_pipeline_cleanup_image_step",
    "precheck_auto_cleanup_step",
    "run_auto_cleanup_step",
    "run_pipeline_cleanup",
    "run_step",
    "start_pipeline_cleanup",
    "verify_auto_cleanup_artifacts_step",
    "verify_auto_cleanup_db_step",
    "verify_pipeline_cleanup_db",
    "verify_pipeline_cleanup_nfs",
    "verify_pipeline_cleanup_registry",
    "verify_pipeline_cleanup_s3",
    "start_cadence_pipeline",
    "verify_cadence_result",
    "verify_cadence_disable_live",
    "verify_cadence_reenable_live",
    "run_deploy_stage",
    "run_stage_step",
    "select_deploy_image",
    "start_build_pipeline",
    "start_deploy_pipeline",
    "verify_build_result",
    "verify_deploy_result",
    "verify_image_build_artifacts",
    "verify_job_image_group_mapping",
    "verify_oauth_client",
    "verify_repo_manager_status",
    "verify_restart_node_results",
    # Execute: pipeline log observability (ER-BSM-003)
    "release_log_fixture_job",
    "resolve_log_target",
    "verify_ci_log_preview",
    "verify_ci_log_templates",
    "verify_log_concurrency_limit",
    "verify_log_errors",
    "verify_log_full",
    "verify_log_full_truncation",
    "verify_log_job_metadata",
    "verify_log_job_ownership",
    "verify_log_scopes",
    "verify_log_missing_file",
    "verify_log_path_violation",
    "verify_log_rate_limit",
    "verify_log_response_redaction",
    "verify_log_stage_filter",
    "verify_log_tail",
    "verify_log_unavailable_reasons",
    "verify_write_time_redaction",
    # Validation
    "validate_test_config",
    "validate_all",
    "ConfigValidationError",
    # NFT security (file permissions / ownership)
    "check_file_permissions",
]
