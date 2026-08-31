# Repo Manager — Test Case Registry

> All test cases for the repo_manager domain FVT automation.

## Test Case ID Convention

| Area | Prefix | Description |
|------|--------|-------------|
| Validate | `TC_RM_VL_` | Input validation tests |
| Prepare | `TC_RM_PR_` | Pulp deployment tests |
| Execute | `TC_RM_EX_` | Repository download/sync tests |
| Status | `TC_RM_ST_` | repo_status.yml generation tests |
| Cleanup | `TC_RM_CL_` | Cleanup verification tests |
| Policy | `TC_RM_PL_` | Repository policy tests |
| Negative | `TC_RM_NG_` | Error scenario tests |

---

## Validate Scenario (`fvt/validate/`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| TC_RM_VL_001 | `test_precheck_environment` | Precheck environment validates config | sanity |
| TC_RM_VL_002 | `test_input_config_exists` | Verify repo_manager_config.yml exists | sanity |
| TC_RM_VL_003 | `test_endpoint_config_exists` | Verify endpoint config exists | sanity |
| TC_RM_VL_004 | `test_credentials_present` | Verify credentials file present | sanity |
| TC_RM_VL_005 | `test_precheck_environment_no_credentials` | Precheck without credentials | sanity |

---

## Prepare Scenario (`fvt/prepare/`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| TC_RM_PR_001 | `test_prepare_pulp` | Deploy Pulp server | deploy, sanity |
| TC_RM_PR_002 | `test_pulp_container_running` | Verify Pulp container running | sanity |
| TC_RM_PR_003 | `test_pulp_status_healthy` | Verify Pulp status healthy | sanity |
| TC_RM_PR_004 | `test_pulp_endpoint_reachable` | Verify Pulp API reachable | functional |
| TC_RM_PR_005 | `test_pulp_cli_configured` | Verify Pulp CLI configured | sanity |
| TC_RM_PR_006 | `test_pulp_certificates_exist` | Verify Pulp certificates exist | sanity |
| TC_RM_PR_007 | `test_pulp_cli_repository_list` | Verify Pulp CLI can list repos | functional |
| TC_RM_PR_008 | `test_pulp_api_detailed_status` | Verify Pulp API detailed status | functional |
| TC_RM_PR_009 | `test_collect_credentials` | Collect credentials for deployment | deploy |
| TC_RM_PR_010 | `test_credential_encryption` | Verify credential encryption | deploy |

---

## Execute Scenario (`fvt/execute/`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| TC_RM_EX_001 | `test_execute_download` | Execute repository download | deploy, sanity |
| TC_RM_EX_002 | `test_repo_status_exists` | Verify repo_status.yml exists | sanity |
| TC_RM_EX_003 | `test_repo_status_success` | Verify repo_status success | sanity |
| TC_RM_EX_004 | `test_slurm_custom_repo_present` | Verify SLURM custom repo present | functional |
| TC_RM_EX_005 | `test_epel_repo_present` | Verify EPEL repo present | functional |
| TC_RM_EX_006 | `test_x86_64_repos_present` | Verify x86_64 repos present | x86_64 |
| TC_RM_EX_007 | `test_file_repos_present` | Verify file repos present | functional |
| TC_RM_EX_008 | `test_software_download_status` | Verify software download status | functional |
| TC_RM_EX_009 | `test_per_software_package_status` | Verify per-package status | functional |
| TC_RM_EX_010 | `test_pulp_repositories_synced` | Verify Pulp repos synced | functional |
| TC_RM_EX_011 | `test_pulp_distributions_published` | Verify Pulp distributions published | functional |
| TC_RM_EX_012 | `test_container_repos_synced` | Verify container repos synced | functional |
| TC_RM_EX_013 | `test_file_repos_synced` | Verify file repos synced | functional |
| TC_RM_EX_014 | `test_pulp_content_accessible` | Verify Pulp content accessible | functional |
| TC_RM_EX_015 | `test_software_packages_in_pulp` | Verify software packages in Pulp | functional |

---

## Status Scenario (`fvt/status/`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| TC_RM_ST_001 | `test_deploy_status` | Deploy status playbook | deploy, sanity |
| TC_RM_ST_002 | `test_repo_status_regenerated` | Verify repo_status regenerated | sanity |
| TC_RM_ST_003 | `test_repo_status_success_after_status` | Verify success after status | sanity |

---

## Cleanup Scenario (`fvt/cleanup/`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| TC_RM_CL_001 | `test_deploy_cleanup` | Deploy cleanup playbook | deploy, sanity |
| TC_RM_CL_002 | `test_pulp_container_removed` | Verify Pulp container removed | sanity |
| TC_RM_CL_003 | `test_pulp_cli_removed` | Verify Pulp CLI removed | sanity |
| TC_RM_CL_004 | `test_pulp_directories_removed` | Verify Pulp directories removed | sanity |

---

## Policy Tests (`fvt/policy/`)

### Repo Types (`test_repo_types.py`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| TC_RM_PL_001 | `test_subscription_repo_per_repo_override` | Test subscription repo override | functional |
| TC_RM_PL_002 | `test_url_repo_per_repo_override` | Test URL repo override | functional |
| TC_RM_PL_003 | `test_subscription_and_url_identical_behavior` | Test identical behavior | functional |

### Partial Override (`test_partial_override.py`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| TC_RM_PL_004 | `test_per_repo_policy_only` | Test per-repo policy only | functional |
| TC_RM_PL_005 | `test_per_repo_caching_only` | Test per-repo caching only | functional |
| TC_RM_PL_006 | `test_empty_per_repo_config` | Test empty per-repo config | functional |

### Integration Pulp Policies (`test_integration_pulp_policies.py`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| TC_RM_PL_007 | `test_pulp_remote_policy_matches_config` | Test Pulp remote policy matches | functional |
| TC_RM_PL_008 | `test_pulp_remote_policy_immediate_mode` | Test immediate mode | functional |
| TC_RM_PL_009 | `test_pulp_remote_policy_on_demand_mode` | Test on-demand mode | functional |
| TC_RM_PL_010 | `test_multiple_repos_policy_resolution` | Test multiple repos policy | functional |
| TC_RM_PL_011 | `test_pulp_repository_exists` | Test Pulp repository exists | functional |

### Priority Order (`test_priority_order.py`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| TC_RM_PL_012 | `test_per_repo_policy_overrides_global` | Test per-repo overrides global | functional |
| TC_RM_PL_013 | `test_per_repo_caching_overrides_global` | Test per-repo caching overrides | functional |
| TC_RM_PL_014 | `test_per_repo_complete_override` | Test complete override | functional |

### Pulp Mode (`test_pulp_mode.py`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| TC_RM_PL_015 | `test_pulp_mode_in_repo_status` | Test pulp mode in repo_status | functional |
| TC_RM_PL_016 | `test_actual_pulp_repository_policy` | Test actual Pulp repository policy | functional |
| TC_RM_PL_017 | `test_disk_space_savings` | Test disk space savings | functional |

### Policy Combinations (`test_policy_combinations.py`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| TC_RM_PL_018 | `test_policy_always_caching_false` | Test always caching false | functional |
| TC_RM_PL_019 | `test_policy_always_caching_true` | Test always caching true | functional |
| TC_RM_PL_020 | `test_policy_partial_caching_false` | Test partial caching false | functional |
| TC_RM_PL_021 | `test_policy_partial_caching_true` | Test partial caching true | functional |

---

## Negative Tests (`fvt/negative/error_scenarios/`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| TC_RM_NG_001 | `test_deploy_fails_missing_credentials` | Test deploy fails without credentials | negative |
| TC_RM_NG_002 | `test_deploy_fails_invalid_endpoint_config` | Test deploy fails with invalid endpoint | negative |
| TC_RM_NG_003 | `test_download_fails_invalid_repo_url` | Test download fails with invalid URL | negative |
| TC_RM_NG_004 | `test_status_fails_missing_repo_status` | Test status fails without repo_status | negative |
| TC_RM_NG_005 | `test_cleanup_fails_pulp_not_running` | Test cleanup fails when Pulp not running | negative |
| TC_RM_NG_006 | `test_pulp_cli_fails_invalid_auth` | Test Pulp CLI fails with invalid auth | negative |
| TC_RM_NG_007 | `test_repo_sync_fails_network_issues` | Test repo sync fails with network issues | negative |
| TC_RM_NG_008 | `test_catalog_generation_fails_invalid_config` | Test catalog generation fails with invalid config | negative |
| TC_RM_NG_009 | `test_validate_fails_missing_config` | Test validate fails without config | negative |
| TC_RM_NG_010 | `test_pulp_api_unreachable_port_closed` | Test Pulp API unreachable when port closed | negative |

---

## Test Summary

**Total Test Cases: 68**

| Category | Count |
|----------|-------|
| Validate Tests | 5 |
| Prepare Tests | 10 |
| Execute Tests | 15 |
| Status Tests | 3 |
| Cleanup Tests | 4 |
| Policy Tests | 21 |
| Negative Tests | 10 |
| **Total** | **68** |
