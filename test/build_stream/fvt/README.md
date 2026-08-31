# Build Stream — FVT Test Cases

## Section A: BuildStream Installation & Infrastructure (22 test cases)

| TC ID | Test Function | Description |
|-------|---------------|-------------|
| TC_GI_000 | test_deploy_buildstream_install | Deploy build_stream --tags buildstream_install |
| TC_GI_001 | test_gitlab_packages_installed | Verify GitLab packages installed |
| TC_GI_002 | test_gitlab_server_reachable | Verify GitLab server reachable from OIM |
| TC_GI_003 | test_gitlab_runner_container | Verify gitlab-runner container running |
| TC_GI_004 | test_gitlab_runner_quadlet_exists | Verify gitlab-runner quadlet file exists |
| TC_GI_005 | test_gitlab_runner_services_status | Verify GitLab runner services running |
| TC_GI_006 | test_gitlab_url_accessible | Verify GitLab URL accessible from OIM |
| TC_GI_007 | test_gitlab_services_running | Verify all GitLab services running |
| TC_GI_008 | test_gitlab_resources | Verify GitLab resource requirements met |
| TC_GI_009 | test_puma_workers | Verify puma workers configured |
| TC_GI_010 | test_sidekiq_concurrency | Verify sidekiq concurrency configured |
| TC_GI_011 | test_gitlab_project_exists | Verify GitLab project exists |
| TC_GI_012 | test_gitlab_project_visibility | Verify GitLab project visibility |
| TC_GI_013 | test_gitlab_default_branch | Verify GitLab default branch |
| TC_GI_014 | test_gitlab_pipeline_file_exists | Verify .gitlab-ci.yml exists in repo |
| TC_GI_015 | test_gitlab_pipeline_variables | Verify GitLab pipeline variables |
| TC_GI_016 | test_gitlab_ci_build_file_exists | Verify .gitlab-ci-build.yml exists (2.3) |
| TC_GI_017 | test_gitlab_ci_deploy_file_exists | Verify .gitlab-ci-deploy.yml exists (2.3) |
| TC_GI_018 | test_gitlab_ci_cleanup_file_exists | Verify .gitlab-ci-cleanup.yml exists (2.3) |
| TC_GI_019 | test_gitlab_deploy_child_template_exists | Verify deploy child template (2.3) |
| TC_GI_020 | test_gitlab_cleanup_child_template_exists | Verify cleanup child template (2.3) |
| TC_GI_021 | test_omnia_env_exists | Verify omnia.env in GitLab repo (2.3) |
| TC_GI_022 | test_domain_input_dirs_in_repo | Verify domain input dirs in repo (2.3) |

## Section B: BuildStream Service Health (9 test cases)

| TC ID | Test Function | Description |
|-------|---------------|-------------|
| TC_BH_001 | test_build_stream_enabled | Verify build_stream enabled in config |
| TC_BH_002 | test_build_stream_health | Verify BSM API /health endpoint |
| TC_BH_003 | test_postgres_tables | Verify Postgres tables exist |
| TC_BH_004 | test_gitlab_server_running | Verify GitLab server running |
| TC_BH_005 | test_gitlab_runner_running | Verify GitLab runner running |
| TC_BH_006 | test_omnia_venv_exists | Verify shared venv exists (2.3) |
| TC_BH_007 | test_bsm_tls_certificate_valid | Verify BSM TLS certificate (2.3) |
| TC_BH_008 | test_nfs_queue_directory_accessible | Verify NFS queue dir (2.3) |
| TC_BH_009 | test_playbook_watcher_running | Verify watcher service (2.3) |

## Section C: Prepare BuildStream Infrastructure (12 test cases)

|| TC ID | Test Function | Description | Mode |
||-------|---------------|-------------|------|
|| TC_PREP_000 | test_deploy_prepare_buildstream | Deploy repo_manager + image_build_manager prepare | --test only |
|| TC_PREP_001 | test_pulp_container_running | Verify Pulp container is running | --test, --verify |
|| TC_PREP_002 | test_pulp_health_endpoint | Verify Pulp health endpoint is accessible | --test, --verify |
|| TC_PREP_003 | test_pulp_cli_available | Verify pulp CLI is available | --test, --verify |
|| TC_PREP_004 | test_minio_container_running | Verify MinIO container is running | --test, --verify |
|| TC_PREP_005 | test_minio_health_endpoint | Verify MinIO health endpoint is accessible | --test, --verify |
|| TC_PREP_006 | test_registry_container_running | Verify local container registry is running | --test, --verify |
|| TC_PREP_007 | test_registry_health_endpoint | Verify registry health endpoint is accessible | --test, --verify |
|| TC_PREP_008 | test_repo_manager_credentials_exist | Verify repo_manager credentials file exists | --test, --verify |
|| TC_PREP_009 | test_image_build_credentials_exist | Verify image_build_credentials.yml exists | --test, --verify |
|| TC_PREP_010 | test_repo_manager_credentials_filled | Verify repo_manager credentials are filled with valid data | --test, --verify |
|| TC_PREP_011 | test_image_build_credentials_filled | Verify image_build credentials are filled with valid data | --test, --verify |

## Section D: Build Pipeline (13 test cases)

| TC ID | Test Function | Description | Mode |
|-------|---------------|-------------|------|
| TC_BP_001 | test_deploy_build_pipeline | Push catalog, trigger pipeline, monitor stages | --test only |
| TC_BP_PRE | test_build_credentials_configured | Verify server credentials configured | --test, --verify |
| TC_BP_002 | test_build_bsm_health_check | Verify BSM API /health endpoint | --test, --verify |
| TC_BP_003 | test_build_oauth_auth | Verify OAuth credentials registered | --test, --verify |
| TC_BP_004 | test_build_job_created | Verify job created in DB | --test, --verify |
| TC_BP_005 | test_build_job_accessible_via_api | Verify job accessible via BSM API | --test, --verify |
| TC_BP_006 | test_build_stage_create_local_repository | Verify create-local-repository stage | --test, --verify |
| TC_BP_007 | test_build_stage_build_image | Verify build-image stage completed | --test, --verify |
| TC_BP_008 | test_build_repo_status | Verify repo_status.yml overall_status | --test, --verify |
| TC_BP_009 | test_build_registry_images | Verify container images in registry | --test, --verify |
| TC_BP_010 | test_build_s3_boot_images | Verify boot images in S3 | --test, --verify |
| TC_BP_011 | test_build_pipeline_result | Build pipeline final result (build stages only) | --test, --verify |

## Execution

```bash
# Setup
bash setup_env.sh
source .venv/bin/activate

# Configure
vi test_config.yml    # Set catalog_name, oim_server_ip

# Prepare buildstream infrastructure (Pulp, MinIO, Registry)
./run_validation.sh fvt_build_stream prepare_buildstream test --marker sanity

# Verify prepare_buildstream infrastructure
./run_validation.sh fvt_build_stream prepare_buildstream verify --marker sanity

# Run buildstream install verification
./run_validation.sh fvt_build_stream buildstream_install verify --marker sanity

# Run health check verification
./run_validation.sh fvt_build_stream buildstream_install verify --suite health

# Full deploy + verify
./run_validation.sh fvt_build_stream buildstream_install test

# Build pipeline — full flow (push catalog, trigger, monitor, verify)
./run_validation.sh fvt_build_stream build_pipeline test

# Build pipeline — verify only (requires job_id in test_config.yml)
./run_validation.sh fvt_build_stream build_pipeline verify
```
