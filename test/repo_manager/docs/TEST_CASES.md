# Repo Manager — Test Case Registry

> All functional and deterministic contract tests for Repo Manager.

## Test Case ID Convention

| Area | Prefix | Description |
|------|--------|-------------|
| Precheck | `TC_RM_PC_` | Input and environment validation tests |
| Prepare | `TC_RM_PR_` | Pulp deployment tests |
| Execute | `TC_RM_EX_` | Repository download/sync tests |
| Status | `TC_RM_ST_` | repo_status.yml generation tests |
| Cleanup | `TC_RM_CL_` | Cleanup verification tests |
| Selective cleanup | `TC_RM_SCL_` | Exact repository cleanup tests |
| Policy | `TC_RM_PL_` | Repository policy tests |
| Negative | `TC_RM_NG_` | Error scenario tests |

---

## Precheck Scenario (`fvt/precheck/`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| TC_RM_PC_000 | `test_precheck_environment` | Execute the precheck playbook tag | deploy, sanity |
| TC_RM_PC_001 | `test_input_config_exists` | Verify repo_manager_config.yml exists | sanity |
| TC_RM_PC_002 | `test_endpoint_config_exists` | Verify endpoint config exists | sanity |
| TC_RM_PC_003 | `test_credentials_present` | Verify credentials file present | sanity |
| TC_RM_PC_004 | `test_precheck_environment_no_credentials` | Precheck without credential prompting | sanity |

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
| TC_RM_CL_000 | `test_deploy_cleanup` | Deploy full cleanup playbook | deploy, destructive |
| TC_RM_CL_001 | `test_pulp_container_removed` | Verify Pulp container removed | destructive |
| TC_RM_CL_002 | `test_pulp_cli_preserved` | Verify managed Pulp CLI remains executable | destructive |
| TC_RM_CL_003 | `test_pulp_directories_removed` | Verify Pulp directories removed | destructive |

## Selective Cleanup Scenario (`fvt/cleanup_repos/`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| TC_RM_SCL_000 | `test_deploy_exact_repository_cleanup` | Remove an explicitly authorized exact RPM repository | deploy, destructive |
| TC_RM_SCL_001 | `test_exact_repository_is_absent_while_pulp_is_healthy` | Verify absence independently from endpoint health | destructive |
| TC_RM_SCL_002 | `test_selective_cleanup_invalidates_repo_status` | Verify stale consumer output is invalidated | destructive |
| TC_RM_SCL_003 | `test_cleanup_status_records_exact_success` | Verify one exact successful cleanup result | destructive |

## Deterministic Unit/Contract Tests (`ut/`)

| Suite | Count | Coverage |
|-------|------:|----------|
| `test_cleanup_contract.py` | 24 | Cases 1-6 scope, exact identities, fail-closed state, idempotency and ordering |
| `test_container_reconciliation.py` | 8 | Ready/incomplete/unknown state and tag union |
| `test_dnf_retry.py` | 7 | Transient-only bounded retries and integrity failures |
| `test_fvt_policy_helpers.py` | 6 | Policy config keys, Pulp JSON parsing, catalog-selected repos and repo source types |
| `test_framework_contract.py` | 26 | Commands, public tags, suites, entrypoint imports, filtering and dispatch |
| `test_mirror_state.py` | 9 | Rerun selection, ambiguity, corruption and atomic replacement |
| `test_pulp_command_contract.py` | 13 | Central structured argv and allowlisted grammar |
| `test_repo_file_state.py` | 3 | Atomic, read-only and symlink-safe DNF repo files |
| `test_repo_settings.py` | 7 | Configuration precedence and typed environment values |
| `test_status_contract.py` | 8 | Multi-version aggregation and fail-closed publication |

---

## Policy Tests (`fvt/policy/`)

### Repo Types (`test_repo_types.py`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| TC_RM_PO_011 | `test_subscription_repo_per_repo_override` | Test subscription repo override | sanity, positive |
| TC_RM_PO_012 | `test_url_repo_per_repo_override` | Test URL repo override | sanity, positive |
| TC_RM_PO_013 | `test_subscription_and_url_identical_behavior` | Test identical policy resolution | sanity, positive |

### Partial Override (`test_partial_override.py`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| TC_RM_PO_004 | `test_per_repo_policy_only` | Test per-repo policy only | sanity, positive |
| TC_RM_PO_005 | `test_per_repo_caching_only` | Test per-repo caching only | sanity, positive |
| TC_RM_PO_006 | `test_empty_per_repo_config` | Test empty per-repo config | sanity, positive |

### Integration Pulp Policies (`test_integration_pulp_policies.py`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| TC_RM_PO_017 | `test_pulp_remote_policy_matches_config` | Test Pulp remote policy matches | sanity, positive |
| TC_RM_PO_018 | `test_pulp_remote_policy_immediate_mode` | Test immediate mode | sanity, positive |
| TC_RM_PO_019 | `test_pulp_remote_policy_on_demand_mode` | Test on-demand mode | sanity, positive |
| TC_RM_PO_020 | `test_multiple_repos_policy_resolution` | Test every deployed repo policy | sanity, positive |
| TC_RM_PO_021 | `test_pulp_repository_exists` | Test every deployed Pulp repository exists | sanity, positive |

### Priority Order (`test_priority_order.py`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| TC_RM_PO_001 | `test_per_repo_policy_overrides_global` | Test per-repo overrides global | sanity, positive |
| TC_RM_PO_002 | `test_per_repo_caching_overrides_global` | Test per-repo caching overrides | sanity, positive |
| TC_RM_PO_003 | `test_per_repo_complete_override` | Test complete override | sanity, positive |

### Pulp Mode (`test_pulp_mode.py`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| TC_RM_PO_014 | `test_pulp_mode_in_repo_status` | Test effective Pulp mode resolution | sanity, positive |
| TC_RM_PO_015 | `test_actual_pulp_repository_policy` | Test valid Pulp policy combinations | sanity, positive |
| TC_RM_PO_016 | `test_disk_space_savings` | Test on-demand policy selection | sanity, positive |

### Policy Combinations (`test_policy_combinations.py`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| TC_RM_PO_007 | `test_policy_always_caching_false` | Test always caching false | sanity, positive |
| TC_RM_PO_008 | `test_policy_always_caching_true` | Test always caching true | sanity, positive |
| TC_RM_PO_009 | `test_policy_partial_caching_false` | Test partial caching false | sanity, positive |
| TC_RM_PO_010 | `test_policy_partial_caching_true` | Test partial caching true | sanity, positive |

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

## User Registry Tests (`fvt/user_registry/`)

### Validation Tests (`test_user_registry_validation.py`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| TC_RM_UR_000 | `test_user_registry_validation_deploy` | Deploy validation playbook (includes registry checks) | deploy, sanity |
| TC_RM_UR_001 | `test_user_registry_section_exists` | Verify registries section exists in config | sanity, positive |
| TC_RM_UR_002 | `test_user_registry_structure_valid` | Verify registry entries have valid structure | sanity, positive |
| TC_RM_UR_003 | `test_user_registry_base_url_valid` | Verify base_url is valid HTTP(S) origin | sanity, positive |
| TC_RM_UR_004 | `test_user_registry_reachable` | Verify configured registries are reachable | functional, positive |
| TC_RM_UR_005 | `test_user_registry_tls_cert_paths_valid` | Verify TLS cert paths exist on disk | functional, positive |
| TC_RM_UR_006 | `test_user_registry_tls_pair_consistent` | Verify client cert and key configured together | sanity, positive |
| TC_RM_UR_007 | `test_user_registry_auth_type_valid` | Verify auth type is none or basic | sanity, positive |
| TC_RM_UR_008 | `test_user_registry_credentials_present` | Verify credentials for basic auth registries | functional, positive |

### Negative Tests (`test_user_registry_negative.py`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| TC_RM_UR_NEG_001 | `test_registry_validation_fails_missing_config` | Validation fails with missing config | negative |
| TC_RM_UR_NEG_002 | `test_registry_validation_detects_invalid_base_url` | Detects invalid base_url | negative |
| TC_RM_UR_NEG_003 | `test_registry_validation_detects_incomplete_tls_pair` | Detects incomplete TLS cert/key pair | negative |
| TC_RM_UR_NEG_004 | `test_registry_validation_detects_unsupported_auth_type` | Detects unsupported auth type | negative |
| TC_RM_UR_NEG_005 | `test_registry_validation_detects_missing_cert_paths` | Detects missing cert paths on disk | negative |
| TC_RM_UR_NEG_006 | `test_registry_validation_detects_missing_vault_path` | Detects missing vault_path for basic auth | negative |

---

## Test Summary

**Total Test Cases: 228**

| Category | Count |
|----------|-------|
| Precheck Tests | 5 |
| Prepare Tests | 10 |
| Execute Tests | 15 |
| Status Tests | 3 |
| Cleanup Tests | 4 |
| Selective Cleanup Tests | 4 |
| Policy Tests | 21 |
| Negative Tests | 10 |
| User Registry Tests | 15 |
| Catalog Tests | 30 |
| Unit/Contract Tests | 111 |
| **Total** | **228** |
