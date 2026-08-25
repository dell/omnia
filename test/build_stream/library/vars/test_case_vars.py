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
Build Stream — Test Case Registry

All TC IDs and titles for the build_stream FVT.
Keys match test function names without the ``test_`` prefix.
"""

from typing import Dict

# =============================================================================
# SECTION A: GitLab Installation & Infrastructure
# =============================================================================

TEST_CASES: Dict[str, Dict[str, str]] = {
    # --- Deploy (TC_GI_000) ---
    "deploy_gitlab_install": {
        "id": "TC_GI_000",
        "title": "Deploy build_stream --tags gitlab_install",
    },

    # --- GitLab Install (TC_GI_xxx) ---
    "gitlab_packages_installed": {
        "id": "TC_GI_001",
        "title": "Verify GitLab packages installed",
    },
    "gitlab_server_reachable": {
        "id": "TC_GI_002",
        "title": "Verify GitLab server reachable from OIM",
    },
    "gitlab_runner_container": {
        "id": "TC_GI_003",
        "title": "Verify gitlab-runner container running",
    },
    "gitlab_runner_quadlet_exists": {
        "id": "TC_GI_004",
        "title": "Verify gitlab-runner quadlet file exists",
    },
    "gitlab_runner_services_status": {
        "id": "TC_GI_005",
        "title": "Verify GitLab runner services running",
    },
    "gitlab_url_accessible": {
        "id": "TC_GI_006",
        "title": "Verify GitLab URL accessible from OIM",
    },
    "gitlab_services_running": {
        "id": "TC_GI_007",
        "title": "Verify all GitLab services running",
    },
    "gitlab_resources": {
        "id": "TC_GI_008",
        "title": "Verify GitLab resource requirements met",
    },
    "puma_workers": {
        "id": "TC_GI_009",
        "title": "Verify puma workers configured",
    },
    "sidekiq_concurrency": {
        "id": "TC_GI_010",
        "title": "Verify sidekiq concurrency configured",
    },
    "gitlab_project_exists": {
        "id": "TC_GI_011",
        "title": "Verify GitLab project exists",
    },
    "gitlab_project_visibility": {
        "id": "TC_GI_012",
        "title": "Verify GitLab project visibility",
    },
    "gitlab_default_branch": {
        "id": "TC_GI_013",
        "title": "Verify GitLab default branch",
    },
    "gitlab_pipeline_file_exists": {
        "id": "TC_GI_014",
        "title": "Verify .gitlab-ci.yml exists in repo",
    },
    "gitlab_pipeline_variables": {
        "id": "TC_GI_015",
        "title": "Verify GitLab pipeline variables configured",
    },
    "gitlab_ci_build_file_exists": {
        "id": "TC_GI_016",
        "title": "Verify .gitlab-ci-build.yml exists",
    },
    "gitlab_ci_deploy_file_exists": {
        "id": "TC_GI_017",
        "title": "Verify .gitlab-ci-deploy.yml exists",
    },
    "gitlab_ci_cleanup_file_exists": {
        "id": "TC_GI_018",
        "title": "Verify .gitlab-ci-cleanup.yml exists",
    },
    "gitlab_deploy_child_template_exists": {
        "id": "TC_GI_019",
        "title": "Verify deploy child template exists",
    },
    "gitlab_cleanup_child_template_exists": {
        "id": "TC_GI_020",
        "title": "Verify cleanup child template exists",
    },
    "omnia_env_exists": {
        "id": "TC_GI_021",
        "title": "Verify omnia.env exists in GitLab repo",
    },
    "domain_input_dirs_in_repo": {
        "id": "TC_GI_022",
        "title": "Verify domain input directories in repo",
    },

    # --- BuildStream Health (TC_BH_xxx) ---
    "build_stream_enabled": {
        "id": "TC_BH_001",
        "title": "Verify build_stream enabled in config",
    },
    "build_stream_health": {
        "id": "TC_BH_002",
        "title": "Verify BSM API /health endpoint",
    },
    "postgres_tables": {
        "id": "TC_BH_003",
        "title": "Verify Postgres tables exist",
    },
    "gitlab_server_running": {
        "id": "TC_BH_004",
        "title": "Verify GitLab server running",
    },
    "gitlab_runner_running": {
        "id": "TC_BH_005",
        "title": "Verify GitLab runner running",
    },
    "playbook_paths_yml_exists": {
        "id": "TC_BH_006",
        "title": "Verify playbook_paths.yml exists",
    },
    "playbook_paths_resolvable": {
        "id": "TC_BH_007",
        "title": "Verify playbook paths resolve to files",
    },
    "omnia_venv_exists": {
        "id": "TC_BH_008",
        "title": "Verify shared Python venv exists",
    },
    "bsm_tls_certificate_valid": {
        "id": "TC_BH_009",
        "title": "Verify BSM TLS certificate valid",
    },
    "nfs_queue_directory_accessible": {
        "id": "TC_BH_010",
        "title": "Verify NFS queue directory accessible",
    },
    "playbook_watcher_running": {
        "id": "TC_BH_011",
        "title": "Verify playbook watcher running",
    },

    # =================================================================
    # SECTION C: GitLab Cleanup (TC_GC_xxx)
    # =================================================================

    "deploy_gitlab_cleanup": {
        "id": "TC_GC_000",
        "title": "Deploy build_stream --tags gitlab_cleanup",
    },
    "gitlab_packages_removed": {
        "id": "TC_GC_001",
        "title": "Verify GitLab packages removed",
    },
    "gitlab_runner_container_removed": {
        "id": "TC_GC_002",
        "title": "Verify gitlab-runner container removed",
    },
    "gitlab_runner_quadlet_removed": {
        "id": "TC_GC_003",
        "title": "Verify gitlab-runner quadlet removed",
    },
    "gitlab_runner_services_stopped": {
        "id": "TC_GC_004",
        "title": "Verify GitLab runner services stopped",
    },
    "gitlab_url_not_accessible": {
        "id": "TC_GC_005",
        "title": "Verify GitLab URL not accessible",
    },
    "gitlab_directories_removed": {
        "id": "TC_GC_006",
        "title": "Verify GitLab directories removed",
    },
    "gitlab_services_stopped": {
        "id": "TC_GC_007",
        "title": "Verify all GitLab services stopped",
    },
    "gitlab_port_free": {
        "id": "TC_GC_008",
        "title": "Verify GitLab HTTPS port free",
    },

    # =================================================================
    # SECTION C.1: BuildStream Domain Cleanup (TC_BC_xxx)
    # =================================================================

    "deploy_buildstream_cleanup": {
        "id": "TC_BC_000",
        "title": "Deploy cleanup_build_stream playbook",
    },
    "buildstream_container_stopped": {
        "id": "TC_BC_001",
        "title": "Verify omnia_build_stream container stopped",
    },
    "buildstream_container_removed": {
        "id": "TC_BC_002",
        "title": "Verify omnia_build_stream container removed",
    },
    "buildstream_quadlet_files_removed": {
        "id": "TC_BC_003",
        "title": "Verify omnia_build_stream quadlet removed",
    },
    "buildstream_services_stopped": {
        "id": "TC_BC_004",
        "title": "Verify omnia_build_stream services stopped",
    },
    "playbook_watcher_service_stopped": {
        "id": "TC_BC_005",
        "title": "Verify playbook_watcher stopped",
    },
    "playbook_watcher_service_disabled": {
        "id": "TC_BC_006",
        "title": "Verify playbook_watcher disabled",
    },
    "playbook_watcher_service_file_removed": {
        "id": "TC_BC_007",
        "title": "Verify playbook_watcher file removed",
    },
    "postgres_container_stopped": {
        "id": "TC_BC_008",
        "title": "Verify omnia_postgres container stopped",
    },
    "postgres_container_removed": {
        "id": "TC_BC_009",
        "title": "Verify omnia_postgres container removed",
    },
    "postgres_quadlet_files_removed": {
        "id": "TC_BC_010",
        "title": "Verify omnia_postgres quadlet removed",
    },
    "postgres_services_stopped": {
        "id": "TC_BC_011",
        "title": "Verify omnia_postgres services stopped",
    },
    "image_groups_marked_cleaned": {
        "id": "TC_BC_012",
        "title": "Verify image_groups marked CLEANED",
    },
    "postgres_volumes_removed_no_backup": {
        "id": "TC_BC_013",
        "title": "Verify Postgres volumes removed (no backup)",
    },
    "postgres_volumes_preserved_with_backup": {
        "id": "TC_BC_014",
        "title": "Verify Postgres volumes preserved (backup)",
    },
    "buildstream_directories_removed": {
        "id": "TC_BC_015",
        "title": "Verify build_stream directories removed",
    },
    "buildstream_credentials_removed": {
        "id": "TC_BC_016",
        "title": "Verify build_stream credentials removed",
    },
    "buildstream_oauth_credentials_removed": {
        "id": "TC_BC_017",
        "title": "Verify OAuth credentials removed",
    },
}
