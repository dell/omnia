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
    run_playbook as _run_playbook,
)
from library.vars.common_vars import PLAYBOOK_ENTRY_POINT, PLAYBOOK_WORKDIR

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

# --- BuildStream health verification ---
from library.functions.build_stream_func import (
    check_build_stream_enabled,
    check_build_stream_health,
    check_postgres_tables,
    check_playbook_paths_yml,
    check_playbook_paths_resolvable,
    check_omnia_venv,
    check_bsm_tls_certificate,
    check_nfs_queue_directory,
    check_playbook_watcher,
)

# --- Pipeline verification ---
from library.functions.pipeline_func import (
    # Trigger
    trigger_build_pipeline_auto,
    # GitLab API
    list_pipelines,
    cancel_pipeline,
    trigger_pipeline_with_variables,
    upload_catalog_file,
    get_catalog_content,
    wait_for_pipeline_triggered,
    # Database
    get_latest_job,
    get_stage_state,
    verify_stage_completed,
    get_image_groups_for_job,
    get_images_for_job,
    # Stage monitoring
    poll_stage_until_complete,
    # GitLab CI/CD stage tracking
    get_child_pipeline_id,
    get_gitlab_pipeline_jobs,
    poll_gitlab_ci_stages,
    # BSM API
    get_catalog_roles,
    verify_registry_images,
    verify_s3_boot_images,
    clear_bsm_token_cache,
    # Initialization verification
    verify_initialization_health,
    verify_initialization_auth,
    verify_initialization_job,
    verify_initialization_upload,
    # Stage convenience wrappers
    verify_create_local_repository,
    verify_build_image,
    verify_build_image_meta,
    get_pipeline_summary,
    # Repo manager output
    check_repo_status,
    # Registry & S3 direct checks
    check_registry_images_exist,
    check_s3_boot_images_exist,
    # Server credentials
    load_server_credentials,
    check_server_credentials,
    clear_server_creds_cache,
    # Catalog from examples
    push_catalog_from_examples,
    update_job_id_in_config,
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
    check_playbook_watcher_service_stopped,
    check_playbook_watcher_service_disabled,
    check_playbook_watcher_service_file_removed,
    check_postgres_container_stopped,
    check_postgres_container_removed,
    check_postgres_quadlet_files_removed,
    check_postgres_services_stopped,
    check_image_groups_marked_cleaned,
    check_postgres_volumes_removed,
    check_postgres_volumes_preserved,
    check_buildstream_directories_removed,
    check_buildstream_credentials_removed,
    check_buildstream_oauth_credentials_removed,
)

# --- Validation ---
from library.functions.validation_func import (
    validate_test_config,
    validate_all,
    ConfigValidationError,
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
    "run_playbook",
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
    # BuildStream health
    "check_build_stream_enabled",
    "check_build_stream_health",
    "check_postgres_tables",
    "check_playbook_paths_yml",
    "check_playbook_paths_resolvable",
    "check_omnia_venv",
    "check_bsm_tls_certificate",
    "check_nfs_queue_directory",
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
    "check_playbook_watcher_service_stopped",
    "check_playbook_watcher_service_disabled",
    "check_playbook_watcher_service_file_removed",
    "check_postgres_container_stopped",
    "check_postgres_container_removed",
    "check_postgres_quadlet_files_removed",
    "check_postgres_services_stopped",
    "check_image_groups_marked_cleaned",
    "check_postgres_volumes_removed",
    "check_postgres_volumes_preserved",
    "check_buildstream_directories_removed",
    "check_buildstream_credentials_removed",
    "check_buildstream_oauth_credentials_removed",
    # Pipeline
    "trigger_build_pipeline_auto",
    "list_pipelines",
    "cancel_pipeline",
    "trigger_pipeline_with_variables",
    "upload_catalog_file",
    "get_catalog_content",
    "wait_for_pipeline_triggered",
    "get_latest_job",
    "get_stage_state",
    "verify_stage_completed",
    "get_image_groups_for_job",
    "get_images_for_job",
    "poll_stage_until_complete",
    "get_child_pipeline_id",
    "get_gitlab_pipeline_jobs",
    "poll_gitlab_ci_stages",
    "get_catalog_roles",
    "verify_registry_images",
    "verify_s3_boot_images",
    "clear_bsm_token_cache",
    "verify_initialization_health",
    "verify_initialization_auth",
    "verify_initialization_job",
    "verify_initialization_upload",
    "verify_create_local_repository",
    "verify_build_image",
    "verify_build_image_meta",
    "get_pipeline_summary",
    "check_repo_status",
    "check_registry_images_exist",
    "check_s3_boot_images_exist",
    "load_server_credentials",
    "check_server_credentials",
    "clear_server_creds_cache",
    "push_catalog_from_examples",
    "update_job_id_in_config",
    # Validation
    "validate_test_config",
    "validate_all",
    "ConfigValidationError",
]
