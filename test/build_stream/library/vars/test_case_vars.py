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
    "deploy_buildstream_install": {
        "id": "TC_GI_000",
        "title": "Deploy build_stream --tags buildstream_install",
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
    "omnia_venv_exists": {
        "id": "TC_BH_006",
        "title": "Verify shared Python venv exists",
    },
    "bsm_tls_certificate_valid": {
        "id": "TC_BH_007",
        "title": "Verify BSM TLS certificate valid",
    },
    "nfs_queue_directory_accessible": {
        "id": "TC_BH_008",
        "title": "Verify NFS queue directory accessible",
    },
    "playbook_watcher_running": {
        "id": "TC_BH_009",
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

    # =================================================================
    # SECTION D: Build Pipeline (TC_BP_xxx)
    #
    # Stage names match the BSM StageType enum in
    # src/build_stream/app/core/jobs/value_objects.py:
    #   create-local-repository, build-image, upload   (build pipeline)
    #   validate, restart, deploy                      (deploy pipeline)
    #
    # test_playbook.py  (deploy marker — runs with --test only)
    #   TC_BP_001  Push catalog and trigger pipeline
    #
    # build_pipeline/   (verify tests — runs with --test and --verify)
    #   TC_BP_PRE        Credentials pre-check
    #   TC_BP_002 – 012  Post-execution verification
    # =================================================================

    # --- test_playbook.py (deploy) ---
    "deploy_build_pipeline": {
        "id": "TC_BP_001",
        "title": "Push catalog, trigger pipeline, monitor stages",
    },

    # --- build_pipeline/ (verify) --- credentials gate ---
    "build_credentials_configured": {
        "id": "TC_BP_PRE",
        "title": "Verify build_stream credentials configured",
    },

    # --- build_pipeline/ (verify) ---
    "build_bsm_health_check": {
        "id": "TC_BP_002",
        "title": "Verify BSM API /health endpoint",
    },
    "build_oauth_auth": {
        "id": "TC_BP_003",
        "title": "Verify OAuth credentials registered",
    },
    "build_job_created": {
        "id": "TC_BP_004",
        "title": "Verify job created in DB",
    },
    "build_job_accessible_via_api": {
        "id": "TC_BP_005",
        "title": "Verify job accessible via BSM API",
    },
    "build_stage_create_local_repository": {
        "id": "TC_BP_006",
        "title": "Verify create-local-repository stage completed",
    },
    "build_stage_build_image": {
        "id": "TC_BP_007",
        "title": "Verify build-image stage completed",
    },
    "build_repo_status": {
        "id": "TC_BP_008",
        "title": "Verify repo_status.yml overall_status success",
    },
    "build_registry_images": {
        "id": "TC_BP_009",
        "title": "Verify container images in registry",
    },
    "build_s3_boot_images": {
        "id": "TC_BP_010",
        "title": "Verify boot images in S3",
    },
    "build_pipeline_result": {
        "id": "TC_BP_011",
        "title": "Build pipeline final result",
    },

    # --- Prepare BuildStream (TC_PREP_xxx) ---
    "deploy_prepare_buildstream": {
        "id": "TC_PREP_000",
        "title": "Deploy prepare_buildstream (repo_manager + image_build_manager prepare)",
    },
    "pulp_container_running": {
        "id": "TC_PREP_001",
        "title": "Verify Pulp container is running",
    },
    "pulp_health_endpoint": {
        "id": "TC_PREP_002",
        "title": "Verify Pulp health endpoint is accessible",
    },
    "pulp_cli_available": {
        "id": "TC_PREP_003",
        "title": "Verify pulp CLI is available",
    },
    "minio_container_running": {
        "id": "TC_PREP_004",
        "title": "Verify MinIO container is running",
    },
    "minio_health_endpoint": {
        "id": "TC_PREP_005",
        "title": "Verify MinIO health endpoint is accessible",
    },
    "registry_container_running": {
        "id": "TC_PREP_006",
        "title": "Verify local container registry is running",
    },
    "registry_health_endpoint": {
        "id": "TC_PREP_007",
        "title": "Verify registry health endpoint is accessible",
    },
    "repo_manager_credentials_exist": {
        "id": "TC_PREP_008",
        "title": "Verify repo_manager credentials file exists",
    },
    "repo_manager_credentials_filled": {
        "id": "TC_PREP_010",
        "title": "Verify repo_manager credentials are filled with valid data",
    },
    "image_build_credentials_exist": {
        "id": "TC_PREP_009",
        "title": "Verify image_build_credentials.yml exists",
    },
    "image_build_credentials_filled": {
        "id": "TC_PREP_011",
        "title": "Verify image_build credentials are filled with valid data",
    },
}
