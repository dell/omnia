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

TEST_CASES: Dict[str, Dict[str, str]] = {
    # =================================================================
    # Execute: GitLab server, runner and project
    # =================================================================
    "gitlab_packages_installed": {
        "id": "BSM_FVT_EXECUTE_V001",
        "title": "Verify GitLab packages installed",
    },
    "gitlab_server_reachable": {
        "id": "BSM_FVT_EXECUTE_V002",
        "title": "Verify GitLab server reachable from OIM",
    },
    "gitlab_runner_container": {
        "id": "BSM_FVT_EXECUTE_V009",
        "title": "Verify gitlab-runner container running",
    },
    "gitlab_runner_quadlet_exists": {
        "id": "BSM_FVT_EXECUTE_V010",
        "title": "Verify gitlab-runner quadlet file exists",
    },
    "gitlab_runner_services_status": {
        "id": "BSM_FVT_EXECUTE_V011",
        "title": "Verify GitLab runner services running",
    },
    "gitlab_url_accessible": {
        "id": "BSM_FVT_EXECUTE_V003",
        "title": "Verify GitLab URL accessible from OIM",
    },
    "gitlab_services_running": {
        "id": "BSM_FVT_EXECUTE_V005",
        "title": "Verify all GitLab services running",
    },
    "gitlab_resources": {
        "id": "BSM_FVT_EXECUTE_V006",
        "title": "Verify GitLab resource requirements met",
    },
    "puma_workers": {
        "id": "BSM_FVT_EXECUTE_V007",
        "title": "Verify puma workers configured",
    },
    "sidekiq_concurrency": {
        "id": "BSM_FVT_EXECUTE_V008",
        "title": "Verify sidekiq concurrency configured",
    },
    "gitlab_project_exists": {
        "id": "BSM_FVT_EXECUTE_V013",
        "title": "Verify GitLab project exists",
    },
    "gitlab_project_visibility": {
        "id": "BSM_FVT_EXECUTE_V014",
        "title": "Verify GitLab project visibility",
    },
    "gitlab_default_branch": {
        "id": "BSM_FVT_EXECUTE_V015",
        "title": "Verify GitLab default branch",
    },
    "gitlab_pipeline_file_exists": {
        "id": "BSM_FVT_EXECUTE_V017",
        "title": "Verify .gitlab-ci.yml exists in repo",
    },
    "gitlab_pipeline_variables": {
        "id": "BSM_FVT_EXECUTE_V016",
        "title": "Verify GitLab pipeline variables configured",
    },
    "gitlab_ci_build_file_exists": {
        "id": "BSM_FVT_EXECUTE_V018",
        "title": "Verify .gitlab-ci-build.yml exists",
    },
    "gitlab_ci_deploy_file_exists": {
        "id": "BSM_FVT_EXECUTE_V019",
        "title": "Verify .gitlab-ci-deploy.yml exists",
    },
    "gitlab_ci_cleanup_file_exists": {
        "id": "BSM_FVT_EXECUTE_V020",
        "title": "Verify .gitlab-ci-cleanup.yml exists",
    },
    "gitlab_deploy_child_template_exists": {
        "id": "BSM_FVT_EXECUTE_V022",
        "title": "Verify deploy child template exists",
    },
    "gitlab_cleanup_child_template_exists": {
        "id": "BSM_FVT_EXECUTE_V023",
        "title": "Verify cleanup child template exists",
    },
    "omnia_env_exists": {
        "id": "BSM_FVT_EXECUTE_V024",
        "title": "Verify omnia.env exists in GitLab repo",
    },
    "domain_input_dirs_in_repo": {
        "id": "BSM_FVT_EXECUTE_V025",
        "title": ("Verify domain input files in repo: repo_manager, "
                  "image_build_manager, orchestrator"),
    },

    # --- Prepare: BuildStream service health ---
    "build_stream_enabled": {
        "id": "BSM_FVT_PREPARE_V001",
        "title": "Verify build_stream enabled in config",
    },
    "build_stream_health": {
        "id": "BSM_FVT_PREPARE_V004",
        "title": "Verify BSM API /health endpoint",
    },
    "postgres_tables": {
        "id": "BSM_FVT_PREPARE_V005",
        "title": "Verify Postgres tables exist",
    },
    "gitlab_server_running": {
        "id": "BSM_FVT_EXECUTE_V004",
        "title": "Verify GitLab server running",
    },
    "gitlab_runner_running": {
        "id": "BSM_FVT_EXECUTE_V012",
        "title": "Verify GitLab runner running",
    },
    "omnia_venv_exists": {
        "id": "BSM_FVT_PREPARE_V007",
        "title": "Verify shared Python venv exists",
    },
    "bsm_tls_certificate_valid": {
        "id": "BSM_FVT_PREPARE_V008",
        "title": "Verify BSM TLS certificate valid",
    },
    "nfs_queue_directory_accessible": {
        "id": "BSM_FVT_PREPARE_V009",
        "title": "Verify NFS queue directory accessible",
    },
    "playbook_watcher_running": {
        "id": "BSM_FVT_PREPARE_V006",
        "title": "Verify playbook watcher running",
    },
    "gitlab_ci_cadence_file_exists": {
        "id": "BSM_FVT_EXECUTE_V021",
        "title": "Verify .gitlab-ci-cadence.yml exists",
    },

    # =================================================================
    # Cleanup: GitLab
    # =================================================================
    "gitlab_packages_removed": {
        "id": "BSM_FVT_CLEANUP_V001",
        "title": "Verify GitLab packages removed",
    },
    "gitlab_runner_container_removed": {
        "id": "BSM_FVT_CLEANUP_V002",
        "title": "Verify gitlab-runner container removed",
    },
    "gitlab_runner_quadlet_removed": {
        "id": "BSM_FVT_CLEANUP_V003",
        "title": "Verify gitlab-runner quadlet removed",
    },
    "gitlab_runner_services_stopped": {
        "id": "BSM_FVT_CLEANUP_V004",
        "title": "Verify GitLab runner services stopped",
    },
    "gitlab_url_not_accessible": {
        "id": "BSM_FVT_CLEANUP_V005",
        "title": "Verify GitLab URL not accessible",
    },
    "gitlab_directories_removed": {
        "id": "BSM_FVT_CLEANUP_V006",
        "title": "Verify GitLab directories removed",
    },
    "gitlab_services_stopped": {
        "id": "BSM_FVT_CLEANUP_V007",
        "title": "Verify all GitLab services stopped",
    },
    "gitlab_port_free": {
        "id": "BSM_FVT_CLEANUP_V008",
        "title": "Verify GitLab HTTPS port free",
    },

    # =================================================================
    # Cleanup: BuildStream service and data
    # =================================================================
    "buildstream_container_stopped": {
        "id": "BSM_FVT_CLEANUP_V009",
        "title": "Verify omnia_build_stream container stopped",
    },
    "buildstream_container_removed": {
        "id": "BSM_FVT_CLEANUP_V010",
        "title": "Verify omnia_build_stream container removed",
    },
    "buildstream_quadlet_files_removed": {
        "id": "BSM_FVT_CLEANUP_V011",
        "title": "Verify omnia_build_stream quadlet files removed",
    },
    "buildstream_services_stopped": {
        "id": "BSM_FVT_CLEANUP_V012",
        "title": "Verify omnia_build_stream services stopped",
    },
    "playbook_watcher_service_stopped": {
        "id": "BSM_FVT_CLEANUP_V013",
        "title": "Verify playbook-watcher stopped",
    },
    "playbook_watcher_service_disabled": {
        "id": "BSM_FVT_CLEANUP_V029",
        "title": "Verify playbook-watcher disabled",
    },
    "playbook_watcher_service_file_removed": {
        "id": "BSM_FVT_CLEANUP_V015",
        "title": "Verify playbook-watcher file removed",
    },
    "postgres_container_stopped": {
        "id": "BSM_FVT_CLEANUP_V016",
        "title": "Verify omnia_postgres container stopped",
    },
    "postgres_container_removed": {
        "id": "BSM_FVT_CLEANUP_V017",
        "title": "Verify omnia_postgres container removed",
    },
    "postgres_quadlet_files_removed": {
        "id": "BSM_FVT_CLEANUP_V018",
        "title": "Verify omnia_postgres quadlet files removed",
    },
    "postgres_services_stopped": {
        "id": "BSM_FVT_CLEANUP_V019",
        "title": "Verify omnia_postgres services stopped",
    },
    "buildstream_directories_removed": {
        "id": "BSM_FVT_CLEANUP_V020",
        "title": "Verify BuildStream runtime directories removed",
    },
    "buildstream_runtime_caches_removed": {
        "id": "BSM_FVT_CLEANUP_V021",
        "title": "Verify runtime preserved and Python caches removed",
    },

    # =================================================================
    # NFT: resilience and security
    # =================================================================
    "gitlab_cancel_then_create_new_job": {
        "id": "BSM_NFT_RESILIENCE_001",
        "title": "Cancel GitLab pipeline and create an independent BSM job",
    },
    "bsm_container_restart_recovery": {
        "id": "BSM_NFT_RESILIENCE_002",
        "title": "Verify BSM container and persisted job recover after restart",
    },
    "bsm_restart_during_active_stage": {
        "id": "BSM_NFT_RESILIENCE_003",
        "title": "Verify active BSM job survives API container restart",
    },
    "watcher_restart_during_queued_request": {
        "id": "BSM_NFT_RESILIENCE_004",
        "title": "Verify watcher restart preserves queued job isolation",
    },
    "protected_endpoints_reject_invalid_tokens": {
        "id": "BSM_NFT_SECURITY_001",
        "title": "Verify protected endpoints reject invalid bearer tokens",
    },
    "scope_authorization_enforced": {
        "id": "BSM_NFT_SECURITY_002",
        "title": "Verify read-only OAuth scope cannot mutate jobs",
    },
    "upload_path_and_filename_protection": {
        "id": "BSM_NFT_SECURITY_003",
        "title": "Verify upload whitelist blocks path traversal",
    },
    "oversized_upload_rejected_without_partial_state": {
        "id": "BSM_NFT_SECURITY_004",
        "title": "Verify oversized upload leaves no partial artifact",
    },
    "secret_redaction_in_logs_and_responses": {
        "id": "BSM_NFT_SECURITY_005",
        "title": "Verify authentication secrets are absent from logs",
    },
    "postgres_quadlet_permissions": {
        "id": "BSM_NFT_SECURITY_006",
        "title": "Verify omnia_postgres quadlet is 0600 root:root",
    },
    "build_stream_quadlet_permissions": {
        "id": "BSM_NFT_SECURITY_007",
        "title": "Verify omnia_build_stream quadlet is 0600 root:root",
    },

    # =========================================================================
    # Prepare Base (./omnia.sh --prepare-base prerequisites)
    # =========================================================================
    "precheck_prepare_base": {
        "id": "BSM_FVT_PREPARE_BASE_E001",
        "title": "Precheck: omnia.env, venv, omnia.sh and base domain credentials",
    },
    "deploy_prepare_base": {
        "id": "BSM_FVT_PREPARE_BASE_E002",
        "title": "Deploy ./omnia.sh --prepare-base",
    },
    "repo_manager_ready": {
        "id": "BSM_FVT_PREPARE_BASE_V001",
        "title": "Verify repo_manager ready: Pulp quadlet, service and container",
    },
    "image_build_manager_ready": {
        "id": "BSM_FVT_PREPARE_BASE_V002",
        "title": "Verify image_build_manager ready: MinIO and registry serving",
    },
    "orchestrator_ready": {
        "id": "BSM_FVT_PREPARE_BASE_V003",
        "title": "Verify orchestrator ready: OpenCHAMI units, containers, volumes, OpenLDAP",
    },

    # =========================================================================
    # Precheck (build_stream.yml --tags precheck)
    # =========================================================================
    "deploy_precheck": {
        "id": "BSM_FVT_PRECHECK_E001",
        "title": "Deploy build_stream.yml --tags precheck",
    },
    "precheck_environment_variables": {
        "id": "BSM_FVT_PRECHECK_V001",
        "title": "Verify omnia.env sets SYSTEM_*, OMNIA_DATA_PATH and OMNIA_PROJECT_NAME",
    },
    "precheck_oim_identity": {
        "id": "BSM_FVT_PRECHECK_V002",
        "title": "Verify hostname -s and hostname -d match omnia.env",
    },
    "precheck_admin_ipv4": {
        "id": "BSM_FVT_PRECHECK_V003",
        "title": "Verify SYSTEM_ADMIN_NIC_IPV4 is assigned to an OIM interface",
    },
    "precheck_data_path_export": {
        "id": "BSM_FVT_PRECHECK_V004",
        "title": "Verify no NFS export lets remote root write OMNIA_DATA_PATH",
    },
    "precheck_containers": {
        "id": "BSM_FVT_PRECHECK_V005",
        "title": "Verify pulp, minio-server and registry containers are running",
    },
    "precheck_credentials": {
        "id": "BSM_FVT_PRECHECK_V006",
        "title": "Verify repo_manager and image_build_manager credential stores exist",
    },
    "precheck_repo_manager_files": {
        "id": "BSM_FVT_PRECHECK_V007",
        "title": "Verify repo_manager credential store, vault key and GitLab input files",
    },
    "precheck_image_build_manager_files": {
        "id": "BSM_FVT_PRECHECK_V008",
        "title": "Verify image_build_manager credential store, vault key and GitLab input files",
    },
    "precheck_orchestrator_files": {
        "id": "BSM_FVT_PRECHECK_V009",
        "title": "Verify orchestrator credential store, vault key and GitLab input files",
    },

    # =========================================================================
    # Prepare (build_stream.yml --tags prepare)
    # =========================================================================
    "deploy_prepare": {
        "id": "BSM_FVT_PREPARE_E001",
        "title": "Deploy build_stream.yml --tags prepare",
    },
    "prepare_containers": {
        "id": "BSM_FVT_PREPARE_V002",
        "title": "Verify omnia_build_stream and omnia_postgres containers and quadlets",
    },
    "prepare_services": {
        "id": "BSM_FVT_PREPARE_V003",
        "title": "Verify omnia_postgres, omnia_build_stream and playbook-watcher services",
    },
    "prepare_status_file": {
        "id": "BSM_FVT_PREPARE_V010",
        "title": "Verify build_stream_status.yml reports prepared with all endpoints",
    },
    "buildstream_directories_present": {
        "id": "BSM_FVT_PREPARE_V011",
        "title": "Verify BuildStream runtime directories exist (ssl, build_stream_root, "
                 "playbook_queue, postgres)",
    },

    # =========================================================================
    # Execute (build_stream.yml --tags execute)
    # =========================================================================
    "deploy_execute": {
        "id": "BSM_FVT_EXECUTE_E001",
        "title": "Deploy build_stream.yml --tags execute",
    },
    # --- Execute: build/deploy (automatic + manual), cadence, image cleanup ---
    "build_trigger_pipeline": {
        "id": "BSM_FVT_EXECUTE_V026",
        "title": ("Automatic build: commit the selected catalog (next unused version); "
                  "verify the push started build_pipeline and a job"),
    },
    "build_upload_stage": {
        "id": "BSM_FVT_EXECUTE_V027",
        "title": ("Automatic build: verify upload stage (DB, API) and the committed "
                  "catalog on the host"),
    },
    "build_parse_catalog_stage": {
        "id": "BSM_FVT_EXECUTE_V028",
        "title": "Automatic build: verify parse-catalog stage (DB, API, stage log)",
    },
    "build_create_local_repository_stage": {
        "id": "BSM_FVT_EXECUTE_V029",
        "title": ("Automatic build: verify create-local-repository stage (DB, API, "
                  "stage log)"),
    },
    "build_build_image_stage": {
        "id": "BSM_FVT_EXECUTE_V030",
        "title": "Automatic build: verify build-image stage (DB, API, stage log)",
    },
    "build_repo_manager_status": {
        "id": "BSM_FVT_EXECUTE_V031",
        "title": ("Automatic build: verify Repo Manager repo_status.yml overall_status "
                  "success"),
    },
    "build_image_build_manager_artifacts": {
        "id": "BSM_FVT_EXECUTE_V032",
        "title": ("Automatic build: verify registry image (regctl) and S3 boot files "
                  "for every role"),
    },
    "build_pipeline_records": {
        "id": "BSM_FVT_EXECUTE_V033",
        "title": ("Automatic build: verify GitLab pipeline result and jobs, "
                  "image_groups, images rows"),
    },
    "build_oauth_client_registered": {
        "id": "BSM_FVT_EXECUTE_V077",
        "title": ("Automatic build: verify the OAuth client is registered (BSM_CLIENT_ID, "
                  "BSM_CLIENT_SECRET in GitLab) and created the job"),
    },
    "build_manual_trigger_pipeline": {
        "id": "BSM_FVT_EXECUTE_V034",
        "title": ("Manual build: commit the selected catalog with [skip ci], trigger "
                  "PIPELINE_TYPE=build through the API; verify the pipeline and job "
                  "started"),
    },
    "build_manual_upload_stage": {
        "id": "BSM_FVT_EXECUTE_V035",
        "title": ("Manual build: verify upload stage (DB, API) and the committed "
                  "catalog on the host"),
    },
    "build_manual_parse_catalog_stage": {
        "id": "BSM_FVT_EXECUTE_V036",
        "title": "Manual build: verify parse-catalog stage (DB, API, stage log)",
    },
    "build_manual_create_local_repository_stage": {
        "id": "BSM_FVT_EXECUTE_V037",
        "title": ("Manual build: verify create-local-repository stage (DB, API, stage "
                  "log)"),
    },
    "build_manual_build_image_stage": {
        "id": "BSM_FVT_EXECUTE_V038",
        "title": "Manual build: verify build-image stage (DB, API, stage log)",
    },
    "build_manual_repo_manager_status": {
        "id": "BSM_FVT_EXECUTE_V039",
        "title": ("Manual build: verify Repo Manager repo_status.yml overall_status "
                  "success"),
    },
    "build_manual_image_build_manager_artifacts": {
        "id": "BSM_FVT_EXECUTE_V040",
        "title": ("Manual build: verify registry image (regctl) and S3 boot files for "
                  "every role"),
    },
    "build_manual_pipeline_records": {
        "id": "BSM_FVT_EXECUTE_V041",
        "title": ("Manual build: verify GitLab pipeline result and jobs, image_groups, "
                  "images rows"),
    },
    "build_manual_oauth_client_registered": {
        "id": "BSM_FVT_EXECUTE_V078",
        "title": ("Manual build: verify the OAuth client is registered (BSM_CLIENT_ID, "
                  "BSM_CLIENT_SECRET in GitLab) and created the job"),
    },
    "deploy_trigger_pxe_change": {
        "id": "BSM_FVT_EXECUTE_V042",
        "title": ("Automatic deploy: swap PXE mapping rows in GitLab; verify the push "
                  "started deploy_pipeline"),
    },
    "deploy_select_image": {
        "id": "BSM_FVT_EXECUTE_V043",
        "title": ("Automatic deploy: select the image group; verify the select_image "
                  "job chose it"),
    },
    "deploy_deploy_stage": {
        "id": "BSM_FVT_EXECUTE_V044",
        "title": ("Automatic deploy: play the deploy job; verify deploy stage (DB, API, "
                  "stage log)"),
    },
    "deploy_restart_stage": {
        "id": "BSM_FVT_EXECUTE_V045",
        "title": "Automatic deploy: verify restart stage (DB, API, stage log)",
    },
    "deploy_restart_node_results": {
        "id": "BSM_FVT_EXECUTE_V046",
        "title": ("Automatic deploy: verify restart node-results and failed-nodes "
                  "artifacts"),
    },
    "deploy_validate_stage": {
        "id": "BSM_FVT_EXECUTE_V047",
        "title": "Automatic deploy: verify validate stage (DB, API, stage log)",
    },
    "deploy_pipeline_records": {
        "id": "BSM_FVT_EXECUTE_V048",
        "title": ("Automatic deploy: verify pipeline result, summary PASSED, image "
                  "group PASSED, deploy_count"),
    },
    "deploy_job_image_group_mapping": {
        "id": "BSM_FVT_EXECUTE_V079",
        "title": ("Automatic deploy: verify the job maps to exactly one image group, the "
                  "deployed one"),
    },
    "deploy_manual_trigger_pipeline": {
        "id": "BSM_FVT_EXECUTE_V049",
        "title": ("Manual deploy: trigger PIPELINE_TYPE=deploy through the API for the "
                  "image group; verify the deploy pipeline started"),
    },
    "deploy_manual_select_image": {
        "id": "BSM_FVT_EXECUTE_V050",
        "title": ("Manual deploy: select the image group; verify the select_image job "
                  "chose it"),
    },
    "deploy_manual_deploy_stage": {
        "id": "BSM_FVT_EXECUTE_V051",
        "title": ("Manual deploy: play the deploy job; verify deploy stage (DB, API, "
                  "stage log)"),
    },
    "deploy_manual_restart_stage": {
        "id": "BSM_FVT_EXECUTE_V052",
        "title": "Manual deploy: verify restart stage (DB, API, stage log)",
    },
    "deploy_manual_restart_node_results": {
        "id": "BSM_FVT_EXECUTE_V053",
        "title": "Manual deploy: verify restart node-results and failed-nodes artifacts",
    },
    "deploy_manual_validate_stage": {
        "id": "BSM_FVT_EXECUTE_V054",
        "title": "Manual deploy: verify validate stage (DB, API, stage log)",
    },
    "deploy_manual_pipeline_records": {
        "id": "BSM_FVT_EXECUTE_V055",
        "title": ("Manual deploy: verify pipeline result, summary PASSED, image group "
                  "PASSED, deploy_count"),
    },
    "deploy_manual_job_image_group_mapping": {
        "id": "BSM_FVT_EXECUTE_V080",
        "title": ("Manual deploy: verify the job maps to exactly one image group, the "
                  "deployed one"),
    },
    "cadence_pipeline_trigger_cycle": {
        "id": "BSM_FVT_EXECUTE_V056",
        "title": ("Cadence: build a new image first, upload the selected catalog ([skip "
                  "ci]), trigger a cycle; verify repo sync, bump, commit, pipeline and "
                  "job"),
    },
    "cadence_pipeline_upload_stage": {
        "id": "BSM_FVT_EXECUTE_V057",
        "title": "Cadence: verify upload stage (DB, API, stage log)",
    },
    "cadence_pipeline_parse_catalog_stage": {
        "id": "BSM_FVT_EXECUTE_V058",
        "title": "Cadence: verify parse-catalog stage (DB, API, stage log)",
    },
    "cadence_pipeline_create_local_repository_stage": {
        "id": "BSM_FVT_EXECUTE_V059",
        "title": "Cadence: verify create-local-repository stage (DB, API, stage log)",
    },
    "cadence_pipeline_build_image_stage": {
        "id": "BSM_FVT_EXECUTE_V060",
        "title": "Cadence: verify build-image stage (DB, API, stage log)",
    },
    "cadence_pipeline_deploy_stage": {
        "id": "BSM_FVT_EXECUTE_V061",
        "title": "Cadence: verify deploy stage (DB, API, stage log)",
    },
    "cadence_pipeline_restart_stage": {
        "id": "BSM_FVT_EXECUTE_V062",
        "title": "Cadence: verify restart stage (DB, API, stage log)",
    },
    "cadence_pipeline_validate_stage": {
        "id": "BSM_FVT_EXECUTE_V063",
        "title": "Cadence: verify validate stage (DB, API, stage log)",
    },
    "cadence_pipeline_records": {
        "id": "BSM_FVT_EXECUTE_V064",
        "title": "Cadence: verify GitLab pipeline result, image group PASSED and API job",
    },
    "cadence_pipeline_artifacts": {
        "id": "BSM_FVT_EXECUTE_V081",
        "title": ("Cadence: verify registry image and S3 boot files for every role "
                  "of the cadence image"),
    },
    "cadence_pipeline_restart_node_results": {
        "id": "BSM_FVT_EXECUTE_V082",
        "title": "Cadence: verify restart node-results and failed-nodes artifacts",
    },
    "cadence_disable_takes_effect_live": {
        "id": "BSM_FVT_EXECUTE_V065",
        "title": ("Disable cadence (no restart); trigger a cycle; verify it is skipped "
                  "and no cadence commit or pipeline reaches GitLab"),
    },
    "cadence_reenable_resumes_cycle": {
        "id": "BSM_FVT_EXECUTE_V066",
        "title": ("Re-enable cadence (no restart); trigger a cycle; verify it completes "
                  "and starts the cadence pipeline and a BuildStream job"),
    },
    "pipeline_cleanup_trigger_select": {
        "id": "BSM_FVT_EXECUTE_V067",
        "title": ("Cleanup pipeline: pick the image group (config or newest), trigger "
                  "PIPELINE_TYPE=cleanup; verify the select_image job chose it"),
    },
    "pipeline_cleanup_run_cleanup_job": {
        "id": "BSM_FVT_EXECUTE_V068",
        "title": ("Cleanup pipeline: play the cleanup job; verify the image group goes "
                  "CLEANING -> CLEANED and the summary reports SUCCESS"),
    },
    "pipeline_cleanup_db_cleaned": {
        "id": "BSM_FVT_EXECUTE_V069",
        "title": ("Cleanup pipeline: verify image_groups CLEANED, job tombstoned and "
                  "cleanup audit events"),
    },
    "pipeline_cleanup_s3_deleted": {
        "id": "BSM_FVT_EXECUTE_V070",
        "title": ("Cleanup pipeline: verify no s3://boot-images object of the image "
                  "group is left"),
    },
    "pipeline_cleanup_registry_deleted": {
        "id": "BSM_FVT_EXECUTE_V071",
        "title": "Cleanup pipeline: verify no registry tag of the image group is left",
    },
    "pipeline_cleanup_nfs_removed": {
        "id": "BSM_FVT_EXECUTE_V072",
        "title": "Cleanup pipeline: verify the job's NFS artifact directory is removed",
    },
    "auto_cleanup_precheck": {
        "id": "BSM_FVT_EXECUTE_V073",
        "title": ("Automated cleanup: verify retention settings, BuildStream container "
                  "and playbook-watcher"),
    },
    "auto_cleanup_run_pass": {
        "id": "BSM_FVT_EXECUTE_V074",
        "title": ("Automated cleanup: mark the cadence build image FAILED, run one "
                  "cleanup_cron pass; wait until none is CLEANING"),
    },
    "auto_cleanup_db_updated": {
        "id": "BSM_FVT_EXECUTE_V075",
        "title": ("Automated cleanup: verify build_stream_db (cleaned groups CLEANED, "
                  "tombstoned, audited; others kept)"),
    },
    "auto_cleanup_artifacts_removed": {
        "id": "BSM_FVT_EXECUTE_V076",
        "title": ("Automated cleanup: verify S3 objects, registry tags (regctl) and NFS "
                  "artifacts of cleaned groups removed, others untouched"),
    },

    # =========================================================================
    # Cleanup (build_stream.yml --tags cleanup)
    # =========================================================================
    "deploy_cleanup": {
        "id": "BSM_FVT_CLEANUP_E001",
        "title": "Deploy build_stream.yml --tags cleanup",
    },
    "buildstream_api_port_closed": {
        "id": "BSM_FVT_CLEANUP_V025",
        "title": "Verify nothing listens on the BuildStream API port after cleanup",
    },
    "postgres_data_per_backup_flag": {
        "id": "BSM_FVT_CLEANUP_V026",
        "title": "Verify Postgres data and volumes deleted (postgres_backup: false) or "
                 "preserved (true)",
    },
    "buildstream_credentials_per_flag": {
        "id": "BSM_FVT_CLEANUP_V027",
        "title": "Verify build_stream credentials deleted (cleanup_credentials: true) or "
                 "kept (false)",
    },

}
