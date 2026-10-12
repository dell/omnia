# Build Stream — FVT Test Cases

## Section A: BuildStream Installation & Infrastructure (24 test cases)

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
| BSM_FVT_BUILDSTREAM_INSTALL_V032 | test_gitlab_ci_cadence_file_exists | Verify .gitlab-ci-cadence.yml exists (2.3) |

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

## Section C: Explicit cleanup suites (26 test cases)

Cleanup is not part of the default lifecycle. Select exactly one suite so an
operation cannot remove GitLab, BuildStream, and image artifacts in the same
run accidentally.

| TC ID | Test Function | Description |
|-------|---------------|-------------|
| BSM_FVT_BUILDSTREAM_CLEANUP_E001 | test_deploy_gitlab_cleanup | Execute GitLab cleanup |
| BSM_FVT_BUILDSTREAM_CLEANUP_E002 | test_deploy_buildstream_cleanup | Execute BuildStream cleanup |
| BSM_FVT_BUILDSTREAM_CLEANUP_V001–V008 | GitLab cleanup verification tests | Verify GitLab packages, runner, services, directories, URL, and port cleanup |
| BSM_FVT_BUILDSTREAM_CLEANUP_V009–V020, V022, V024–V025 | BuildStream cleanup verification tests | Verify BSM, watcher, PostgreSQL backup preservation, runtime directory cleanup, and credential cleanup |
| BSM_FVT_BUILDSTREAM_CLEANUP_V021 | test_buildstream_runtime_caches_removed | Verify application source and project input remain while generated Python caches are removed |

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

## Section E.1: Unified Cadence Pipeline (24 test cases)

The cadence action signals the running watcher. The watcher runs
`repo_sync.yml`, validates the exact-mirror result, bumps
`cadence_catalog_rhel.json`, and pushes the commit that starts the unified
pipeline. The action then persists its exact `job_id`. Verification never
falls back to the latest job or image group.

| TC ID | Test Function | Description | Mode |
|-------|---------------|-------------|------|
| BSM_FVT_CADENCE_PIPELINE_E001 | test_execute_cadence_pipeline | Trigger the watcher cadence cycle and wait for the pipeline | --test/--exec |
| BSM_FVT_CADENCE_PIPELINE_V017 | test_cadence_gitlab_jobs | Verify all eight GitLab jobs succeeded | --test/--verify |
| BSM_FVT_CADENCE_PIPELINE_V018 | test_cadence_catalog_identity | Verify job and composite image-group identity | --test/--verify |
| BSM_FVT_CADENCE_PIPELINE_V019 | test_cadence_build_stages | Verify parse, repository, and build DB stages | --test/--verify |
| BSM_FVT_CADENCE_PIPELINE_V020 | test_cadence_registry_artifacts | Verify registry artifacts for requested roles | --test/--verify |
| BSM_FVT_CADENCE_PIPELINE_V021 | test_cadence_job_accessible | Verify BSM health and exact job access | --test/--verify |
| BSM_FVT_CADENCE_PIPELINE_V022 | test_cadence_repo_resync_status | Verify pre-pipeline repo_resync_status.yml exact-mirror contract | --test/--verify |
| BSM_FVT_CADENCE_PIPELINE_V023 | test_cadence_deploy_stage | Verify deploy DB stage completed | --test/--verify |
| BSM_FVT_CADENCE_PIPELINE_V024 | test_cadence_restart_stage | Verify restart DB stage completed | --test/--verify |
| BSM_FVT_CADENCE_PIPELINE_V025 | test_cadence_validate_stage | Verify validate DB stage completed | --test/--verify |
| BSM_FVT_CADENCE_PIPELINE_V026 | test_cadence_restart_results | Verify restart node-result artifacts | --test/--verify |
| BSM_FVT_CADENCE_PIPELINE_V027 | test_cadence_final_state | Verify successful job and image-group states | --test/--verify |
| BSM_FVT_CADENCE_PIPELINE_V028 | test_cadence_summary | Verify DB and GitLab summary completion | --test/--verify |
| BSM_FVT_CADENCE_PIPELINE_V029 | test_cadence_local_repo_status | Verify pipeline repo_status.yml matches the cadence catalog | --test/--verify |
| BSM_FVT_CADENCE_PIPELINE_V030 | test_cadence_build_status | Verify versioned and latest build_status.yml contracts | --test/--verify |
| BSM_FVT_CADENCE_PIPELINE_V031 | test_cadence_s3_artifacts | Verify all S3 boot artifacts for requested roles | --test/--verify |
| BSM_FVT_CADENCE_PIPELINE_V032 | test_cadence_catalog_commit_integrity | Verify one catalog version increment and matching pipeline commit | --test/--verify |
| BSM_FVT_CADENCE_PIPELINE_V033 | test_cadence_expected_functional_groups | Verify catalog, database, and build-status roles match | --test/--verify |
| BSM_FVT_CADENCE_PIPELINE_V034 | test_cadence_artifact_identity | Verify versioned status and engine-specific artifact identity | --test/--verify |
| BSM_FVT_CADENCE_PIPELINE_V035 | test_cadence_validate_report | Verify validation executed tests with no failures or errors | --test/--verify |
| BSM_FVT_CADENCE_PIPELINE_V036 | test_cadence_validation_feature_selection | Verify Slurm/Kubernetes selection follows the PXE mapping | --test/--verify |
| BSM_FVT_CADENCE_PIPELINE_V037 | test_cadence_restart_node_coverage | Verify every PXE node has one successful restart result | --test/--verify |
| BSM_FVT_CADENCE_PIPELINE_V038 | test_cadence_uploaded_input_snapshot | Verify canonical catalog and required domain inputs | --test/--verify |
| BSM_FVT_CADENCE_PIPELINE_V039 | test_cadence_stage_attempt_freshness | Verify stage timestamps and logs belong to the current job | --test/--verify |

## Execution

## Manual pipeline tests

The API-triggered build and deploy cases are available under the `manual`
marker and the `manual` suite. They do not carry the `sanity` marker and are
therefore excluded from the default lifecycle. First confirm that BuildStream
installation sanity passes. Set `catalog_path` in `test_config.yml`; manual
build stages that catalog with `[skip ci]`, triggers only through
`PIPELINE_TYPE=build`, and overwrites `job_id` with the newly created job.
Manual deploy uses that exact `job_id` and triggers with
`PIPELINE_TYPE=deploy`.

```bash
# Required prerequisite
./run_validation.sh fvt_build_stream buildstream_install verify --marker sanity

# Manual build: trigger only, verify only, or both
./run_validation.sh fvt_build_stream build_pipeline exec \
  --suite manual --marker manual
./run_validation.sh fvt_build_stream build_pipeline verify \
  --suite manual --marker manual
./run_validation.sh fvt_build_stream build_pipeline test \
  --suite manual --marker manual

# Manual deploy: trigger only, verify only, or both
./run_validation.sh fvt_build_stream deploy_pipeline exec \
  --suite manual --marker manual
./run_validation.sh fvt_build_stream deploy_pipeline verify \
  --suite manual --marker manual
./run_validation.sh fvt_build_stream deploy_pipeline test \
  --suite manual --marker manual
```

## Cadence pipeline sanity suite

BuildStream installation and the cadence configuration must already be
deployed. `exec`/`test` signals the watcher, which performs repository sync and
commits the catalog version bump that triggers a real unified pipeline.
`verify` is read-only and uses the exact `job_id` recorded in
`test_config.yml`.

The action requires `cadence.enabled: true` in deployed
`build_stream_config.yml`, plus active watcher and Pulp services, the configured
Git worktree, and a registered `repo_sync.yml`. Every successful repository
reconciliation triggers cadence, including syncs with no package-count delta.

The cadence catalog is always `cadence_catalog_rhel.json`; `catalog_path` is
only for the separate build-pipeline tests. Cadence `exec` and `test` save the
new JobID automatically. Before a standalone cadence `verify`, `job_id` must
contain the JobID from the cadence pipeline being checked.

```bash
./run_validation.sh fvt_build_stream cadence_pipeline exec --marker sanity
./run_validation.sh fvt_build_stream cadence_pipeline verify --marker sanity
./run_validation.sh fvt_build_stream cadence_pipeline test --marker sanity
```

`generate-input-files` is retained as an explicit compatibility case but is
skipped on 2.3 because that stage was retired.

## Automatic cadence timing coverage

The product configuration keeps `cadence.interval_days` as an integer with a
minimum of one day. The cadence FVT uses the supported one-shot watcher signal
to exercise the complete repository-sync and GitLab pipeline path without a
one-day wait. The NFT cadence timer test separately loads the integer setting,
lets the timer wait expire without setting the manual-trigger event, and
verifies that `interval_days: 1` produces a `86400` second timeout and one
automatic cycle. A real wall-clock automatic FVT would necessarily take at
least one day and is intentionally not part of sanity or either lifecycle.

```bash
./run_validation.sh nft_build_stream test --marker nft
```

## Automatic cleanup sanity suite

Automatic cleanup is an explicit destructive FVT and is never part of the
default or named lifecycle. Set `automatic_cleanup_job_id` to a dedicated Job
whose ImageGroup is `FAILED`. Execution is refused unless that Job owns the
only `FAILED` ImageGroup, because the production cron processes every failed
group. Set `automatic_cleanup_allow_execution: true` only after checking this
precondition. `exec` runs the production cleanup cron, `verify` is read-only,
and `test` runs both phases.

```bash
./run_validation.sh fvt_build_stream automatic_cleanup exec \
  --suite automatic_cleanup --marker sanity
./run_validation.sh fvt_build_stream automatic_cleanup verify \
  --suite automatic_cleanup --marker sanity
./run_validation.sh fvt_build_stream automatic_cleanup test \
  --suite automatic_cleanup --marker sanity
```

The suite verifies integer retention settings, active BuildStream/watcher
services, `type=auto` log evidence, the final `CLEANED` state, and removal of
S3 and registry artifacts for the exact configured Job.

## Cleanup pipeline sanity suite

The API-triggered cleanup pipeline is an explicit sanity suite. It is not part
of the default lifecycle because it deletes the selected image group's S3 and
registry artifacts. The seven ordered cases check GitLab prerequisites, select
the image group for the configured `job_id`, trigger `PIPELINE_TYPE=cleanup`,
and verify database, S3, and registry cleanup in the same pytest session.

```bash
./run_validation.sh fvt_build_stream buildstream_cleanup test \
  --suite cleanup_pipeline --marker sanity
```

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

# Default sanity lifecycle: install -> cadence
./run_validation.sh fvt_build_stream test --marker sanity

# Alternate sanity lifecycle: install -> build -> deploy
./run_validation.sh fvt_build_stream build_deploy_lifecycle test \
  --marker sanity

# Cleanup is explicit and requires exactly one selected suite
./run_validation.sh fvt_build_stream buildstream_cleanup test \
  --suite buildstream_cleanup --marker sanity
./run_validation.sh fvt_build_stream buildstream_cleanup test \
  --suite gitlab_cleanup --marker sanity
./run_validation.sh fvt_build_stream buildstream_cleanup test \
  --suite cleanup_pipeline --marker sanity

# Deploy only (job_id is mandatory and resolves the image group)
./run_validation.sh fvt_build_stream deploy_pipeline test --marker sanity
```

The default lifecycle collects 57 sanity cases: 33 installation cases and 24
cadence cases. The alternate lifecycle collects 55: 33 installation, 12 build,
and 10 deploy cases. Manual, cleanup, and NFT cases are excluded from both.
