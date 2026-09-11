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
    # --- Deploy (BSM_FVT_BUILDSTREAM_INSTALL_E001) ---
    "deploy_buildstream_install": {
        "id": "BSM_FVT_BUILDSTREAM_INSTALL_E001",
        "title": "Deploy build_stream --tags buildstream_install",
    },

    # --- GitLab installation verification ---
    "gitlab_packages_installed": {
        "id": "BSM_FVT_BUILDSTREAM_INSTALL_V001",
        "title": "Verify GitLab packages installed",
    },
    "gitlab_server_reachable": {
        "id": "BSM_FVT_BUILDSTREAM_INSTALL_V002",
        "title": "Verify GitLab server reachable from OIM",
    },
    "gitlab_runner_container": {
        "id": "BSM_FVT_BUILDSTREAM_INSTALL_V003",
        "title": "Verify gitlab-runner container running",
    },
    "gitlab_runner_quadlet_exists": {
        "id": "BSM_FVT_BUILDSTREAM_INSTALL_V004",
        "title": "Verify gitlab-runner quadlet file exists",
    },
    "gitlab_runner_services_status": {
        "id": "BSM_FVT_BUILDSTREAM_INSTALL_V005",
        "title": "Verify GitLab runner services running",
    },
    "gitlab_url_accessible": {
        "id": "BSM_FVT_BUILDSTREAM_INSTALL_V006",
        "title": "Verify GitLab URL accessible from OIM",
    },
    "gitlab_services_running": {
        "id": "BSM_FVT_BUILDSTREAM_INSTALL_V007",
        "title": "Verify all GitLab services running",
    },
    "gitlab_resources": {
        "id": "BSM_FVT_BUILDSTREAM_INSTALL_V008",
        "title": "Verify GitLab resource requirements met",
    },
    "puma_workers": {
        "id": "BSM_FVT_BUILDSTREAM_INSTALL_V009",
        "title": "Verify puma workers configured",
    },
    "sidekiq_concurrency": {
        "id": "BSM_FVT_BUILDSTREAM_INSTALL_V010",
        "title": "Verify sidekiq concurrency configured",
    },
    "gitlab_project_exists": {
        "id": "BSM_FVT_BUILDSTREAM_INSTALL_V011",
        "title": "Verify GitLab project exists",
    },
    "gitlab_project_visibility": {
        "id": "BSM_FVT_BUILDSTREAM_INSTALL_V012",
        "title": "Verify GitLab project visibility",
    },
    "gitlab_default_branch": {
        "id": "BSM_FVT_BUILDSTREAM_INSTALL_V013",
        "title": "Verify GitLab default branch",
    },
    "gitlab_pipeline_file_exists": {
        "id": "BSM_FVT_BUILDSTREAM_INSTALL_V014",
        "title": "Verify .gitlab-ci.yml exists in repo",
    },
    "gitlab_pipeline_variables": {
        "id": "BSM_FVT_BUILDSTREAM_INSTALL_V015",
        "title": "Verify GitLab pipeline variables configured",
    },
    "gitlab_ci_build_file_exists": {
        "id": "BSM_FVT_BUILDSTREAM_INSTALL_V016",
        "title": "Verify .gitlab-ci-build.yml exists",
    },
    "gitlab_ci_deploy_file_exists": {
        "id": "BSM_FVT_BUILDSTREAM_INSTALL_V017",
        "title": "Verify .gitlab-ci-deploy.yml exists",
    },
    "gitlab_ci_cleanup_file_exists": {
        "id": "BSM_FVT_BUILDSTREAM_INSTALL_V018",
        "title": "Verify .gitlab-ci-cleanup.yml exists",
    },
    "gitlab_deploy_child_template_exists": {
        "id": "BSM_FVT_BUILDSTREAM_INSTALL_V019",
        "title": "Verify deploy child template exists",
    },
    "gitlab_cleanup_child_template_exists": {
        "id": "BSM_FVT_BUILDSTREAM_INSTALL_V020",
        "title": "Verify cleanup child template exists",
    },
    "omnia_env_exists": {
        "id": "BSM_FVT_BUILDSTREAM_INSTALL_V021",
        "title": "Verify omnia.env exists in GitLab repo",
    },
    "domain_input_dirs_in_repo": {
        "id": "BSM_FVT_BUILDSTREAM_INSTALL_V022",
        "title": "Verify domain input directories in repo",
    },

    # --- BuildStream health verification ---
    "build_stream_enabled": {
        "id": "BSM_FVT_BUILDSTREAM_INSTALL_V023",
        "title": "Verify build_stream enabled in config",
    },
    "build_stream_health": {
        "id": "BSM_FVT_BUILDSTREAM_INSTALL_V024",
        "title": "Verify BSM API /health endpoint",
    },
    "postgres_tables": {
        "id": "BSM_FVT_BUILDSTREAM_INSTALL_V025",
        "title": "Verify Postgres tables exist",
    },
    "gitlab_server_running": {
        "id": "BSM_FVT_BUILDSTREAM_INSTALL_V026",
        "title": "Verify GitLab server running",
    },
    "gitlab_runner_running": {
        "id": "BSM_FVT_BUILDSTREAM_INSTALL_V027",
        "title": "Verify GitLab runner running",
    },
    "omnia_venv_exists": {
        "id": "BSM_FVT_BUILDSTREAM_INSTALL_V028",
        "title": "Verify shared Python venv exists",
    },
    "bsm_tls_certificate_valid": {
        "id": "BSM_FVT_BUILDSTREAM_INSTALL_V029",
        "title": "Verify BSM TLS certificate valid",
    },
    "nfs_queue_directory_accessible": {
        "id": "BSM_FVT_BUILDSTREAM_INSTALL_V030",
        "title": "Verify NFS queue directory accessible",
    },
    "playbook_watcher_running": {
        "id": "BSM_FVT_BUILDSTREAM_INSTALL_V031",
        "title": "Verify playbook watcher running",
    },

    # =================================================================
    # SECTION C: Combined BuildStream Cleanup
    # =================================================================

    "deploy_gitlab_cleanup": {
        "id": "BSM_FVT_BUILDSTREAM_CLEANUP_E001",
        "title": "Deploy build_stream --tags gitlab_cleanup",
    },
    "gitlab_packages_removed": {
        "id": "BSM_FVT_BUILDSTREAM_CLEANUP_V001",
        "title": "Verify GitLab packages removed",
    },
    "gitlab_runner_container_removed": {
        "id": "BSM_FVT_BUILDSTREAM_CLEANUP_V002",
        "title": "Verify gitlab-runner container removed",
    },
    "gitlab_runner_quadlet_removed": {
        "id": "BSM_FVT_BUILDSTREAM_CLEANUP_V003",
        "title": "Verify gitlab-runner quadlet removed",
    },
    "gitlab_runner_services_stopped": {
        "id": "BSM_FVT_BUILDSTREAM_CLEANUP_V004",
        "title": "Verify GitLab runner services stopped",
    },
    "gitlab_url_not_accessible": {
        "id": "BSM_FVT_BUILDSTREAM_CLEANUP_V005",
        "title": "Verify GitLab URL not accessible",
    },
    "gitlab_directories_removed": {
        "id": "BSM_FVT_BUILDSTREAM_CLEANUP_V006",
        "title": "Verify GitLab directories removed",
    },
    "gitlab_services_stopped": {
        "id": "BSM_FVT_BUILDSTREAM_CLEANUP_V007",
        "title": "Verify all GitLab services stopped",
    },
    "gitlab_port_free": {
        "id": "BSM_FVT_BUILDSTREAM_CLEANUP_V008",
        "title": "Verify GitLab HTTPS port free",
    },

    # =================================================================
    # SECTION C.1: BuildStream service and data cleanup
    # =================================================================

    "deploy_buildstream_cleanup": {
        "id": "BSM_FVT_BUILDSTREAM_CLEANUP_E002",
        "title": "Deploy cleanup_build_stream playbook",
    },
    "buildstream_container_stopped": {
        "id": "BSM_FVT_BUILDSTREAM_CLEANUP_V009",
        "title": "Verify omnia_build_stream container stopped",
    },
    "buildstream_container_removed": {
        "id": "BSM_FVT_BUILDSTREAM_CLEANUP_V010",
        "title": "Verify omnia_build_stream container removed",
    },
    "buildstream_quadlet_files_removed": {
        "id": "BSM_FVT_BUILDSTREAM_CLEANUP_V011",
        "title": "Verify omnia_build_stream quadlet removed",
    },
    "buildstream_services_stopped": {
        "id": "BSM_FVT_BUILDSTREAM_CLEANUP_V012",
        "title": "Verify omnia_build_stream services stopped",
    },
    "playbook_watcher_service_stopped": {
        "id": "BSM_FVT_BUILDSTREAM_CLEANUP_V013",
        "title": "Verify playbook_watcher stopped",
    },
    "playbook_watcher_service_disabled": {
        "id": "BSM_FVT_BUILDSTREAM_CLEANUP_V014",
        "title": "Verify playbook_watcher disabled",
    },
    "playbook_watcher_service_file_removed": {
        "id": "BSM_FVT_BUILDSTREAM_CLEANUP_V015",
        "title": "Verify playbook_watcher file removed",
    },
    "postgres_container_stopped": {
        "id": "BSM_FVT_BUILDSTREAM_CLEANUP_V016",
        "title": "Verify omnia_postgres container stopped",
    },
    "postgres_container_removed": {
        "id": "BSM_FVT_BUILDSTREAM_CLEANUP_V017",
        "title": "Verify omnia_postgres container removed",
    },
    "postgres_quadlet_files_removed": {
        "id": "BSM_FVT_BUILDSTREAM_CLEANUP_V018",
        "title": "Verify omnia_postgres quadlet removed",
    },
    "postgres_services_stopped": {
        "id": "BSM_FVT_BUILDSTREAM_CLEANUP_V019",
        "title": "Verify omnia_postgres services stopped",
    },
    "postgres_volumes_preserved_with_backup": {
        "id": "BSM_FVT_BUILDSTREAM_CLEANUP_V022",
        "title": "Verify Postgres volumes preserved (backup)",
    },
    "buildstream_credentials_removed": {
        "id": "BSM_FVT_BUILDSTREAM_CLEANUP_V024",
        "title": "Verify build_stream credentials removed",
    },
    "buildstream_oauth_credentials_removed": {
        "id": "BSM_FVT_BUILDSTREAM_CLEANUP_V025",
        "title": "Verify OAuth credentials removed",
    },

    # =================================================================
    # SECTION D: Build Pipeline
    #
    # Stage names match the BSM StageType enum in
    # src/build_stream/app/core/jobs/value_objects.py:
    #   create-local-repository, build-image, upload   (build pipeline)
    #   validate, restart, deploy                      (deploy pipeline)
    #
    # test_playbook.py  (deploy marker — runs with --test only)
    #   BSM_FVT_BUILD_PIPELINE_E001  Push catalog and trigger pipeline
    #
    # build_pipeline/   (verify tests — runs with --test and --verify)
    #   BSM_FVT_BUILD_PIPELINE_V001        Credentials pre-check
    #   BSM_FVT_BUILD_PIPELINE_V002 – 012  Post-execution verification
    # =================================================================

    # --- test_playbook.py (deploy) ---
    "deploy_build_pipeline": {
        "id": "BSM_FVT_BUILD_PIPELINE_E001",
        "title": "Push catalog, trigger pipeline, monitor stages",
    },

    # --- build_pipeline/ (verify) --- credentials gate ---
    "build_credentials_configured": {
        "id": "BSM_FVT_BUILD_PIPELINE_V001",
        "title": "Verify build_stream credentials configured",
    },

    # --- build_pipeline/ (verify) ---
    "build_bsm_health_check": {
        "id": "BSM_FVT_BUILD_PIPELINE_V002",
        "title": "Verify BSM API /health endpoint",
    },
    "build_oauth_auth": {
        "id": "BSM_FVT_BUILD_PIPELINE_V003",
        "title": "Verify OAuth credentials registered",
    },
    "build_job_created": {
        "id": "BSM_FVT_BUILD_PIPELINE_V004",
        "title": "Verify job created in DB",
    },
    "build_job_accessible_via_api": {
        "id": "BSM_FVT_BUILD_PIPELINE_V005",
        "title": "Verify job accessible via BSM API",
    },
    "build_stage_create_local_repository": {
        "id": "BSM_FVT_BUILD_PIPELINE_V006",
        "title": "Verify create-local-repository stage completed",
    },
    "build_stage_build_image": {
        "id": "BSM_FVT_BUILD_PIPELINE_V007",
        "title": "Verify build-image stage completed",
    },
    "build_repo_status": {
        "id": "BSM_FVT_BUILD_PIPELINE_V008",
        "title": "Verify repo_status.yml overall_status success",
    },
    "build_registry_images": {
        "id": "BSM_FVT_BUILD_PIPELINE_V009",
        "title": "Verify container images in registry",
    },
    "build_s3_boot_images": {
        "id": "BSM_FVT_BUILD_PIPELINE_V010",
        "title": "Verify boot images in S3",
    },
    "build_pipeline_result": {
        "id": "BSM_FVT_BUILD_PIPELINE_V011",
        "title": "Build pipeline final result",
    },

    # =================================================================
    # SECTION E: Deploy Pipeline
    # =================================================================

    "execute_deploy_pipeline": {
        "id": "BSM_FVT_DEPLOY_PIPELINE_E001",
        "title": "Trigger and automate deploy pipeline",
    },
    "deploy_prerequisites": {
        "id": "BSM_FVT_DEPLOY_PIPELINE_V001",
        "title": "Verify mandatory job and image-group mapping",
    },
    "deploy_gitlab_pipeline": {
        "id": "BSM_FVT_DEPLOY_PIPELINE_V002",
        "title": "Verify deploy child-pipeline jobs",
    },
    "deploy_selected_image": {
        "id": "BSM_FVT_DEPLOY_PIPELINE_V003",
        "title": "Verify mapped image group selected",
    },
    "deploy_stage_completed": {
        "id": "BSM_FVT_DEPLOY_PIPELINE_V004",
        "title": "Verify deploy stage completed",
    },
    "restart_stage_completed": {
        "id": "BSM_FVT_DEPLOY_PIPELINE_V005",
        "title": "Verify restart stage completed",
    },
    "restart_node_results": {
        "id": "BSM_FVT_DEPLOY_PIPELINE_V006",
        "title": "Verify restart node-result artifacts",
    },
    "validate_stage_completed": {
        "id": "BSM_FVT_DEPLOY_PIPELINE_V007",
        "title": "Verify validate stage completed",
    },
    "deploy_final_state": {
        "id": "BSM_FVT_DEPLOY_PIPELINE_V008",
        "title": "Verify deploy final job and image-group state",
    },
    "deploy_pipeline_summary": {
        "id": "BSM_FVT_DEPLOY_PIPELINE_V009",
        "title": "Verify deploy pipeline summary passed",
    },

}
