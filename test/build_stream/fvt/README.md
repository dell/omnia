# Build Stream — FVT Test Cases

## Section A: BuildStream Installation & Infrastructure (23 test cases)

| TC ID | Test Function | Description |
|-------|---------------|-------------|
| BSM_FVT_BUILDSTREAM_INSTALL_E001 | test_deploy_buildstream_install | Deploy build_stream --tags buildstream_install |
| BSM_FVT_BUILDSTREAM_INSTALL_V001 | test_gitlab_packages_installed | Verify GitLab packages installed |
| BSM_FVT_BUILDSTREAM_INSTALL_V002 | test_gitlab_server_reachable | Verify GitLab server reachable from OIM |
| BSM_FVT_BUILDSTREAM_INSTALL_V003 | test_gitlab_runner_container | Verify gitlab-runner container running |
| BSM_FVT_BUILDSTREAM_INSTALL_V004 | test_gitlab_runner_quadlet_exists | Verify gitlab-runner quadlet file exists |
| BSM_FVT_BUILDSTREAM_INSTALL_V005 | test_gitlab_runner_services_status | Verify GitLab runner services running |
| BSM_FVT_BUILDSTREAM_INSTALL_V006 | test_gitlab_url_accessible | Verify GitLab URL accessible from OIM |
| BSM_FVT_BUILDSTREAM_INSTALL_V007 | test_gitlab_services_running | Verify all GitLab services running |
| BSM_FVT_BUILDSTREAM_INSTALL_V008 | test_gitlab_resources | Verify GitLab resource requirements met |
| BSM_FVT_BUILDSTREAM_INSTALL_V009 | test_puma_workers | Verify puma workers configured |
| BSM_FVT_BUILDSTREAM_INSTALL_V010 | test_sidekiq_concurrency | Verify sidekiq concurrency configured |
| BSM_FVT_BUILDSTREAM_INSTALL_V011 | test_gitlab_project_exists | Verify GitLab project exists |
| BSM_FVT_BUILDSTREAM_INSTALL_V012 | test_gitlab_project_visibility | Verify GitLab project visibility |
| BSM_FVT_BUILDSTREAM_INSTALL_V013 | test_gitlab_default_branch | Verify GitLab default branch |
| BSM_FVT_BUILDSTREAM_INSTALL_V014 | test_gitlab_pipeline_file_exists | Verify .gitlab-ci.yml exists in repo |
| BSM_FVT_BUILDSTREAM_INSTALL_V015 | test_gitlab_pipeline_variables | Verify GitLab pipeline variables |
| BSM_FVT_BUILDSTREAM_INSTALL_V016 | test_gitlab_ci_build_file_exists | Verify .gitlab-ci-build.yml exists (2.3) |
| BSM_FVT_BUILDSTREAM_INSTALL_V017 | test_gitlab_ci_deploy_file_exists | Verify .gitlab-ci-deploy.yml exists (2.3) |
| BSM_FVT_BUILDSTREAM_INSTALL_V018 | test_gitlab_ci_cleanup_file_exists | Verify .gitlab-ci-cleanup.yml exists (2.3) |
| BSM_FVT_BUILDSTREAM_INSTALL_V019 | test_gitlab_deploy_child_template_exists | Verify deploy child template (2.3) |
| BSM_FVT_BUILDSTREAM_INSTALL_V020 | test_gitlab_cleanup_child_template_exists | Verify cleanup child template (2.3) |
| BSM_FVT_BUILDSTREAM_INSTALL_V021 | test_omnia_env_exists | Verify omnia.env in GitLab repo (2.3) |
| BSM_FVT_BUILDSTREAM_INSTALL_V022 | test_domain_input_dirs_in_repo | Verify domain input dirs in repo (2.3) |

## Section B: BuildStream Service Health (9 test cases)

| TC ID | Test Function | Description |
|-------|---------------|-------------|
| BSM_FVT_BUILDSTREAM_INSTALL_V023 | test_build_stream_enabled | Verify build_stream enabled in config |
| BSM_FVT_BUILDSTREAM_INSTALL_V024 | test_build_stream_health | Verify BSM API /health endpoint |
| BSM_FVT_BUILDSTREAM_INSTALL_V025 | test_postgres_tables | Verify Postgres tables exist |
| BSM_FVT_BUILDSTREAM_INSTALL_V026 | test_gitlab_server_running | Verify GitLab server running |
| BSM_FVT_BUILDSTREAM_INSTALL_V027 | test_gitlab_runner_running | Verify GitLab runner running |
| BSM_FVT_BUILDSTREAM_INSTALL_V028 | test_omnia_venv_exists | Verify shared venv exists (2.3) |
| BSM_FVT_BUILDSTREAM_INSTALL_V029 | test_bsm_tls_certificate_valid | Verify BSM TLS certificate (2.3) |
| BSM_FVT_BUILDSTREAM_INSTALL_V030 | test_nfs_queue_directory_accessible | Verify NFS queue dir (2.3) |
| BSM_FVT_BUILDSTREAM_INSTALL_V031 | test_playbook_watcher_running | Verify watcher service (2.3) |

## Section C: Combined BuildStream Cleanup (24 test cases)

The `buildstream_cleanup` scenario runs GitLab cleanup first, followed by the
BuildStream service and data cleanup. Verification then checks both areas.

| TC ID | Test Function | Description |
|-------|---------------|-------------|
| BSM_FVT_BUILDSTREAM_CLEANUP_E001 | test_deploy_gitlab_cleanup | Execute GitLab cleanup |
| BSM_FVT_BUILDSTREAM_CLEANUP_E002 | test_deploy_buildstream_cleanup | Execute BuildStream cleanup |
| BSM_FVT_BUILDSTREAM_CLEANUP_V001–V008 | GitLab cleanup verification tests | Verify GitLab packages, runner, services, directories, URL, and port cleanup |
| BSM_FVT_BUILDSTREAM_CLEANUP_V009–V019, V022, V024–V025 | BuildStream cleanup verification tests | Verify BSM, watcher, PostgreSQL backup preservation, and credential cleanup |

## Section D: Build Pipeline (12 test cases)

| TC ID | Test Function | Description | Mode |
|-------|---------------|-------------|------|
| BSM_FVT_BUILD_PIPELINE_E001 | test_deploy_build_pipeline | Push catalog, trigger pipeline, monitor stages | --test only |
| BSM_FVT_BUILD_PIPELINE_V001 | test_build_credentials_configured | Verify server credentials configured | --test, --verify |
| BSM_FVT_BUILD_PIPELINE_V002 | test_build_bsm_health_check | Verify BSM API /health endpoint | --test, --verify |
| BSM_FVT_BUILD_PIPELINE_V003 | test_build_oauth_auth | Verify OAuth credentials registered | --test, --verify |
| BSM_FVT_BUILD_PIPELINE_V004 | test_build_job_created | Verify job created in DB | --test, --verify |
| BSM_FVT_BUILD_PIPELINE_V005 | test_build_job_accessible_via_api | Verify job accessible via BSM API | --test, --verify |
| BSM_FVT_BUILD_PIPELINE_V006 | test_build_stage_create_local_repository | Verify create-local-repository stage | --test, --verify |
| BSM_FVT_BUILD_PIPELINE_V007 | test_build_stage_build_image | Verify build-image stage completed | --test, --verify |
| BSM_FVT_BUILD_PIPELINE_V008 | test_build_repo_status | Verify repo_status.yml overall_status | --test, --verify |
| BSM_FVT_BUILD_PIPELINE_V009 | test_build_registry_images | Verify container images in registry | --test, --verify |
| BSM_FVT_BUILD_PIPELINE_V010 | test_build_s3_boot_images | Verify boot images in S3 | --test, --verify |
| BSM_FVT_BUILD_PIPELINE_V011 | test_build_pipeline_result | Build pipeline final result (build stages only) | --test, --verify |

## Section E: Deploy Pipeline (10 test cases)

| TC ID | Test Function | Description | Mode |
|-------|---------------|-------------|------|
| BSM_FVT_DEPLOY_PIPELINE_E001 | test_execute_deploy_pipeline | Swap PXE rows, select mapped image, run deploy | --test/--exec |
| BSM_FVT_DEPLOY_PIPELINE_V001 | test_deploy_prerequisites | Verify unique job/image-group mapping | --test/--verify |
| BSM_FVT_DEPLOY_PIPELINE_V002 | test_deploy_gitlab_pipeline | Verify child-pipeline jobs succeeded | --test/--verify |
| BSM_FVT_DEPLOY_PIPELINE_V003 | test_deploy_selected_image | Verify mapped image was selected | --test/--verify |
| BSM_FVT_DEPLOY_PIPELINE_V004 | test_deploy_stage_completed | Verify deploy stage completed | --test/--verify |
| BSM_FVT_DEPLOY_PIPELINE_V005 | test_restart_stage_completed | Verify restart stage completed | --test/--verify |
| BSM_FVT_DEPLOY_PIPELINE_V006 | test_restart_node_results | Verify node results; missing failed-nodes is valid | --test/--verify |
| BSM_FVT_DEPLOY_PIPELINE_V007 | test_validate_stage_completed | Verify validate stage completed | --test/--verify |
| BSM_FVT_DEPLOY_PIPELINE_V008 | test_deploy_final_state | Verify job COMPLETED and image group PASSED | --test/--verify |
| BSM_FVT_DEPLOY_PIPELINE_V009 | test_deploy_pipeline_summary | Verify summary reports PASSED | --test/--verify |

## Execution

```bash
# Setup
bash setup_env.sh
source .venv/bin/activate

# Configure
vi test_config.yml    # Set catalog_path, oim_server_ip

# Run buildstream install verification
./run_validation.sh fvt_build_stream buildstream_install verify --marker sanity

# Run health check verification
./run_validation.sh fvt_build_stream buildstream_install verify --suite health

# Full execution + verification
./run_validation.sh fvt_build_stream buildstream_install test

# Build pipeline — full flow (push catalog, trigger, monitor, verify)
./run_validation.sh fvt_build_stream build_pipeline test

# exec/test always replaces GitLab's canonical catalog with the catalog_path
# selected below src/main/samples/catalogs/ and waits for the new pipeline.

# Build pipeline — verify only (requires job_id in test_config.yml)
./run_validation.sh fvt_build_stream build_pipeline verify

# Build pipeline exec/test overwrites job_id with the newly created build job;
# verify reads the existing job_id without changing it.

# Complete sanity lifecycle: install -> build -> deploy
./run_validation.sh fvt_build_stream test --marker sanity

# Cleanup is explicit and is not included in the untagged lifecycle
./run_validation.sh fvt_build_stream buildstream_cleanup test --marker sanity

# Deploy only (job_id is mandatory and resolves the image group)
./run_validation.sh fvt_build_stream deploy_pipeline test --marker sanity
```
