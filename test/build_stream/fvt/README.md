# Build Stream — FVT Test Cases

## Section A: GitLab Installation & Infrastructure (22 test cases)

| TC ID | Test Function | Description |
|-------|---------------|-------------|
| TC_GI_000 | test_deploy_gitlab_install | Deploy build_stream --tags gitlab_install |
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

## Section B: BuildStream Service Health (11 test cases)

| TC ID | Test Function | Description |
|-------|---------------|-------------|
| TC_BH_001 | test_build_stream_enabled | Verify build_stream enabled in config |
| TC_BH_002 | test_build_stream_health | Verify BSM API /health endpoint |
| TC_BH_003 | test_postgres_tables | Verify Postgres tables exist |
| TC_BH_004 | test_gitlab_server_running | Verify GitLab server running |
| TC_BH_005 | test_gitlab_runner_running | Verify GitLab runner running |
| TC_BH_006 | test_playbook_paths_yml_exists | Verify playbook_paths.yml (2.3) |
| TC_BH_007 | test_playbook_paths_resolvable | Verify playbook paths resolve (2.3) |
| TC_BH_008 | test_omnia_venv_exists | Verify shared venv exists (2.3) |
| TC_BH_009 | test_bsm_tls_certificate_valid | Verify BSM TLS certificate (2.3) |
| TC_BH_010 | test_nfs_queue_directory_accessible | Verify NFS queue dir (2.3) |
| TC_BH_011 | test_playbook_watcher_running | Verify watcher service (2.3) |

## Execution

```bash
# Setup
bash setup_env.sh
source .venv/bin/activate

# Configure
vi test_config.yml

# Run GitLab install verification
./run_validation.sh gitlab_install verify --marker sanity

# Run health check verification
./run_validation.sh gitlab_install verify --suite health

# Full deploy + verify
./run_validation.sh gitlab_install test
```
