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
    # Validation
    "validate_test_config",
    "validate_all",
    "ConfigValidationError",
]
