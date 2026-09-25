# Repo Manager -- Test Case Registry

> All functional, non-functional, and deterministic contract tests for Repo Manager.

## Test Case ID Convention

| Level | Prefix | Description |
|-------|--------|-------------|
| FVT | `RM_FVT_<PHASE>_<TYPE><SEQ>` | Functional verification tests |
| NFT | `RM_NFT_<SEQ>` | Non-functional tests |
| UT | `RM_UT_<SEQ>` | Deterministic unit/contract tests |

### FVT Phase Codes

| Phase | Prefix | Description |
|-------|--------|-------------|
| Precheck | `RM_FVT_PRECHECK_` | Input and environment validation tests |
| Prepare | `RM_FVT_PREPARE_` | Pulp deployment tests |
| Execute | `RM_FVT_EXECUTE_` | Repository download/sync tests |
| Catalog exact mirror | `RM_FVT_REPO_SYNC_` | Standalone active-catalog RPM reconciliation tests |
| Status | `RM_FVT_STATUS_` | repo_status.yml generation tests |
| Cleanup | `RM_FVT_CLEANUP_` | Cleanup verification tests |
| Selective cleanup | `RM_FVT_CLEANUP_REPOS_` | Exact repository cleanup tests |
| Policy | `RM_FVT_POLICY_` | Repository policy tests |
| Negative | `RM_FVT_NEG_` | Error scenario tests |
| User registry | `RM_FVT_USER_REGISTRY_` | User registry tests |
| Catalog generate | `RM_FVT_CATALOG_GENERATE_` | Catalog generation tests |
| Catalog add | `RM_FVT_CATALOG_ADD_` | Catalog add tests |
| Catalog delete | `RM_FVT_CATALOG_DELETE_` | Catalog delete tests |
| Catalog validate | `RM_FVT_CATALOG_VALIDATE_` | Catalog validate tests |
| Catalog negative | `RM_FVT_CATALOG_NEG_` | Catalog negative tests |

---

## Precheck Scenario (`fvt/precheck/`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| RM_FVT_PRECHECK_E001 | `test_precheck_environment` | Execute the precheck playbook tag | deploy, sanity |
| RM_FVT_PRECHECK_V001 | `test_input_config_exists` | Verify repo_manager_config.yml exists | sanity, positive |
| RM_FVT_PRECHECK_V002 | `test_endpoint_config_exists` | Verify endpoint config exists | sanity, positive |
| RM_FVT_PRECHECK_V003 | `test_credentials_present` | Verify credentials file present | sanity, positive |
| RM_FVT_PRECHECK_V004 | `test_precheck_environment_no_credentials` | Precheck without credential prompting | sanity, positive |

---

## Prepare Scenario (`fvt/prepare/`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| RM_FVT_PREPARE_E001 | `test_prepare_pulp` | Deploy Pulp server | deploy, sanity |
| RM_FVT_PREPARE_V001 | `test_pulp_container_running` | Verify Pulp container running | sanity, positive |
| RM_FVT_PREPARE_V002 | `test_pulp_status_healthy` | Verify Pulp status healthy | sanity, positive |
| RM_FVT_PREPARE_V003 | `test_pulp_endpoint_reachable` | Verify Pulp API reachable | sanity, positive |
| RM_FVT_PREPARE_V004 | `test_pulp_cli_configured` | Verify Pulp CLI configured | sanity, positive |
| RM_FVT_PREPARE_V005 | `test_pulp_certificates_exist` | Verify Pulp certificates exist | functional, positive |
| RM_FVT_PREPARE_V006 | `test_pulp_cli_repository_list` | Verify Pulp CLI can list repos | sanity, positive |
| RM_FVT_PREPARE_V007 | `test_pulp_api_detailed_status` | Verify Pulp API detailed status | sanity, positive |
| RM_FVT_PREPARE_E002 | `test_collect_credentials` | Verify credential collection | functional, positive |
| RM_FVT_PREPARE_E003 | `test_credential_encryption` | Verify credential encryption | functional, positive |

---

## Execute Scenario (`fvt/execute/`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| RM_FVT_EXECUTE_E001 | `test_execute_download` | Execute repository download | deploy, sanity |
| RM_FVT_EXECUTE_V001 | `test_repo_status_exists` | Verify repo_status.yml exists | sanity, positive |
| RM_FVT_EXECUTE_V002 | `test_repo_status_success` | Verify repo_status success | sanity, positive |
| RM_FVT_EXECUTE_V003 | `test_slurm_custom_repo_present` | Verify SLURM custom repo present | sanity, positive |
| RM_FVT_EXECUTE_V004 | `test_epel_repo_present` | Verify EPEL repo present | sanity, positive |
| RM_FVT_EXECUTE_V005 | `test_x86_64_repos_present` | Verify x86_64 repos present | sanity, positive |
| RM_FVT_EXECUTE_V006 | `test_file_repos_present` | Verify file repos present | functional, positive |
| RM_FVT_EXECUTE_V007 | `test_software_download_status` | Verify software download status | sanity, positive |
| RM_FVT_EXECUTE_V008 | `test_per_software_package_status` | Verify per-package status | sanity, positive |
| RM_FVT_EXECUTE_V009 | `test_pulp_repositories_synced` | Verify Pulp repos synced | sanity, positive |
| RM_FVT_EXECUTE_V010 | `test_pulp_distributions_published` | Verify Pulp distributions published | sanity, positive |
| RM_FVT_EXECUTE_V011 | `test_container_repos_synced` | Verify container repos synced | functional, positive |
| RM_FVT_EXECUTE_V012 | `test_file_repos_synced` | Verify file repos synced | functional, positive |
| RM_FVT_EXECUTE_V013 | `test_pulp_content_accessible` | Verify Pulp content accessible | sanity, positive |
| RM_FVT_EXECUTE_V014 | `test_software_packages_in_pulp` | Verify software packages in Pulp | sanity, positive |

---

## Catalog Exact-Mirror Scenario (`fvt/repo_sync/`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| RM_FVT_REPO_SYNC_E001 | `test_repo_sync_playbook_reconciles_only_catalog_repositories` | Run standalone sync and prove unreferenced repositories are unchanged | deploy, repo_resync |
| RM_FVT_REPO_SYNC_V001 | `test_repo_sync_status_is_successful` | Verify aggregate and orphan-cleanup success | repo_resync, positive |
| RM_FVT_REPO_SYNC_V002 | `test_repo_sync_result_matches_catalog_scope` | Verify result scope exactly matches catalog RPM references | repo_resync, positive |
| RM_FVT_REPO_SYNC_V003 | `test_repo_sync_repositories_have_zero_stale_packages` | Verify successful cleanup and zero stale packages | repo_resync, positive |
| RM_FVT_REPO_SYNC_V004 | `test_repo_sync_package_deltas_are_valid` | Verify version and package-delta fields | repo_resync, positive |
| RM_FVT_REPO_SYNC_V005 | `test_repo_sync_keeps_one_current_publication_and_version` | Verify superseded Pulp state was pruned | repo_resync, positive |
| RM_FVT_REPO_SYNC_V006 | `test_repo_sync_distributions_publish_valid_metadata` | Verify publication binding and served repomd.xml | repo_resync, positive |
| RM_FVT_REPO_SYNC_V007 | `test_repo_sync_slurm_user_repository_matches_input` | Verify Slurm user-repo URL and policy are preserved | repo_resync, positive |

---

## Status Scenario (`fvt/status/`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| RM_FVT_STATUS_E001 | `test_deploy_status` | Deploy status playbook | deploy, sanity |
| RM_FVT_STATUS_V001 | `test_repo_status_regenerated` | Verify repo_status regenerated | sanity, positive |
| RM_FVT_STATUS_V002 | `test_repo_status_success_after_status` | Verify success after status | sanity, positive |

---

## Cleanup Scenario (`fvt/cleanup/`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| RM_FVT_CLEANUP_E001 | `test_deploy_cleanup` | Deploy full cleanup playbook | deploy, sanity |
| RM_FVT_CLEANUP_V001 | `test_pulp_container_removed` | Verify Pulp container removed | sanity, positive |
| RM_FVT_CLEANUP_V002 | `test_pulp_cli_preserved` | Verify managed Pulp CLI remains executable | sanity, positive |
| RM_FVT_CLEANUP_V003 | `test_pulp_directories_removed` | Verify Pulp directories removed | functional, positive |

## Selective Cleanup Scenario (`fvt/cleanup_repos/`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| RM_FVT_CLEANUP_REPOS_E001 | `test_deploy_exact_repository_cleanup` | Remove an explicitly authorized exact RPM repository | deploy, destructive |
| RM_FVT_CLEANUP_REPOS_V001 | `test_exact_repository_is_absent_while_pulp_is_healthy` | Verify absence independently from endpoint health | destructive |
| RM_FVT_CLEANUP_REPOS_V002 | `test_selective_cleanup_invalidates_repo_status` | Verify stale consumer output is invalidated | destructive |
| RM_FVT_CLEANUP_REPOS_V003 | `test_cleanup_status_records_exact_success` | Verify one exact successful cleanup result | destructive |

---

## Policy Tests (`fvt/policy/`)

### Priority Order (`test_priority_order.py`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| RM_FVT_POLICY_V001 | `test_per_repo_policy_overrides_global` | Test per-repo overrides global | sanity, positive |
| RM_FVT_POLICY_V002 | `test_per_repo_caching_overrides_global` | Test per-repo caching overrides | sanity, positive |
| RM_FVT_POLICY_V003 | `test_per_repo_complete_override` | Test complete override | sanity, positive |

### Partial Override (`test_partial_override.py`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| RM_FVT_POLICY_V004 | `test_per_repo_policy_only` | Test per-repo policy only | sanity, positive |
| RM_FVT_POLICY_V005 | `test_per_repo_caching_only` | Test per-repo caching only | sanity, positive |
| RM_FVT_POLICY_V006 | `test_empty_per_repo_config` | Test empty per-repo config | sanity, positive |

### Policy Combinations (`test_policy_combinations.py`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| RM_FVT_POLICY_V007 | `test_policy_always_caching_false` | Test always caching false | sanity, positive |
| RM_FVT_POLICY_V008 | `test_policy_always_caching_true` | Test always caching true | sanity, positive |
| RM_FVT_POLICY_V009 | `test_policy_partial_caching_false` | Test partial caching false | sanity, positive |
| RM_FVT_POLICY_V010 | `test_policy_partial_caching_true` | Test partial caching true | sanity, positive |

### Repo Types (`test_repo_types.py`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| RM_FVT_POLICY_V011 | `test_subscription_repo_per_repo_override` | Test subscription repo override | sanity, positive |
| RM_FVT_POLICY_V012 | `test_url_repo_per_repo_override` | Test URL repo override | sanity, positive |
| RM_FVT_POLICY_V013 | `test_subscription_and_url_identical_behavior` | Test identical policy resolution | sanity, positive |

### Pulp Mode (`test_pulp_mode.py`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| RM_FVT_POLICY_V014 | `test_pulp_mode_in_repo_status` | Test effective Pulp mode resolution | sanity, positive |
| RM_FVT_POLICY_V015 | `test_actual_pulp_repository_policy` | Test valid Pulp policy combinations | sanity, positive |
| RM_FVT_POLICY_V016 | `test_disk_space_savings` | Test on-demand policy selection | sanity, positive |

### Integration Pulp Policies (`test_integration_pulp_policies.py`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| RM_FVT_POLICY_V017 | `test_pulp_remote_policy_matches_config` | Test Pulp remote policy matches | sanity, positive |
| RM_FVT_POLICY_V018 | `test_pulp_remote_policy_immediate_mode` | Test immediate mode | sanity, positive |
| RM_FVT_POLICY_V019 | `test_pulp_remote_policy_on_demand_mode` | Test on-demand mode | sanity, positive |
| RM_FVT_POLICY_V020 | `test_multiple_repos_policy_resolution` | Test every deployed repo policy | sanity, positive |
| RM_FVT_POLICY_V021 | `test_pulp_repository_exists` | Test every deployed Pulp repository exists | sanity, positive |

---

## Negative Tests (`fvt/negative/error_scenarios/`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| RM_FVT_NEG_001 | `test_deploy_fails_missing_credentials` | Test deploy fails without credentials | negative |
| RM_FVT_NEG_002 | `test_deploy_fails_invalid_endpoint_config` | Test deploy fails with invalid endpoint | negative |
| RM_FVT_NEG_003 | `test_download_fails_invalid_repo_url` | Test download fails with invalid URL | negative |
| RM_FVT_NEG_004 | `test_status_fails_missing_repo_status` | Test status fails without repo_status | negative |
| RM_FVT_NEG_005 | `test_cleanup_fails_pulp_not_running` | Test cleanup fails when Pulp not running | negative |
| RM_FVT_NEG_006 | `test_pulp_cli_fails_invalid_auth` | Test Pulp CLI fails with invalid auth | negative |
| RM_FVT_NEG_007 | `test_repo_sync_fails_network_issues` | Test repo sync fails with network issues | negative |
| RM_FVT_NEG_008 | `test_catalog_generation_fails_invalid_config` | Test catalog generation fails with invalid config | negative |
| RM_FVT_NEG_009 | `test_validate_fails_missing_config` | Test validate fails without config | negative |
| RM_FVT_NEG_010 | `test_pulp_api_unreachable_port_closed` | Test Pulp API unreachable when port closed | negative |

---

## User Registry Tests (`fvt/user_registry/`)

### Validation Tests (`test_user_registry_validation.py`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| RM_FVT_USER_REGISTRY_E001 | `test_user_registry_validation_deploy` | Deploy validation playbook (includes registry checks) | deploy, sanity |
| RM_FVT_USER_REGISTRY_V001 | `test_user_registry_section_exists` | Verify registries section exists in config | sanity, positive |
| RM_FVT_USER_REGISTRY_V002 | `test_user_registry_structure_valid` | Verify registry entries have valid structure | sanity, positive |
| RM_FVT_USER_REGISTRY_V003 | `test_user_registry_base_url_valid` | Verify base_url is valid HTTP(S) origin | sanity, positive |
| RM_FVT_USER_REGISTRY_V004 | `test_user_registry_reachable` | Verify configured registries are reachable | functional, positive |
| RM_FVT_USER_REGISTRY_V005 | `test_user_registry_tls_cert_paths_valid` | Verify TLS cert paths exist on disk | functional, positive |
| RM_FVT_USER_REGISTRY_V006 | `test_user_registry_tls_pair_consistent` | Verify client cert and key configured together | sanity, positive |
| RM_FVT_USER_REGISTRY_V007 | `test_user_registry_auth_type_valid` | Verify auth type is none or basic | sanity, positive |
| RM_FVT_USER_REGISTRY_V008 | `test_user_registry_credentials_present` | Verify credentials for basic auth registries | functional, positive |

### Negative Tests (`test_user_registry_negative.py`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| RM_FVT_USER_REGISTRY_NEG_001 | `test_registry_validation_fails_missing_config` | Validation fails with missing config | negative |
| RM_FVT_USER_REGISTRY_NEG_002 | `test_registry_validation_detects_invalid_base_url` | Detects invalid base_url | negative |
| RM_FVT_USER_REGISTRY_NEG_003 | `test_registry_validation_detects_incomplete_tls_pair` | Detects incomplete TLS cert/key pair | negative |
| RM_FVT_USER_REGISTRY_NEG_004 | `test_registry_validation_detects_unsupported_auth_type` | Detects unsupported auth type | negative |
| RM_FVT_USER_REGISTRY_NEG_005 | `test_registry_validation_detects_missing_cert_paths` | Detects missing cert paths on disk | negative |
| RM_FVT_USER_REGISTRY_NEG_006 | `test_registry_validation_detects_missing_vault_path` | Detects missing vault_path for basic auth | negative |

---

## Catalog Tests (`fvt/catalog/`)

### Catalog Generate (`fvt/catalog/generate/`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| RM_FVT_CATALOG_GENERATE_E001 | `test_catalog_generate_deploy` | Deploy catalog_generate playbook | deploy, sanity |
| RM_FVT_CATALOG_GENERATE_V001 | `test_catalog_input_dir_exists` | Verify catalog input directory exists | sanity, positive |
| RM_FVT_CATALOG_GENERATE_V002 | `test_catalog_file_exists` | Verify catalog file exists after generate | sanity, positive |
| RM_FVT_CATALOG_GENERATE_V003 | `test_catalog_structure_valid` | Verify catalog structure is valid | sanity, positive |
| RM_FVT_CATALOG_GENERATE_V004 | `test_catalog_functional_layers` | Verify catalog has functional layers | sanity, positive |
| RM_FVT_CATALOG_GENERATE_V005 | `test_catalog_groups` | Verify catalog has groups | sanity, positive |
| RM_FVT_CATALOG_GENERATE_V006 | `test_catalog_packages` | Verify catalog has packages | sanity, positive |
| RM_FVT_CATALOG_GENERATE_V007 | `test_catalog_log_file_exists` | Verify catalog log file exists | deploy, functional, positive |

### Catalog Add (`fvt/catalog/add/`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| RM_FVT_CATALOG_ADD_E001 | `test_catalog_add_deploy` | Deploy catalog_add playbook | deploy, sanity |
| RM_FVT_CATALOG_ADD_V001 | `test_catalog_add_operation_completed` | Verify add operation completed | sanity, positive |
| RM_FVT_CATALOG_ADD_V002 | `test_catalog_structure_valid_after_add` | Verify catalog structure valid after add | functional, positive |
| RM_FVT_CATALOG_ADD_V003 | `test_catalog_has_functional_layers_after_add` | Verify functional layers after add | functional, positive |
| RM_FVT_CATALOG_ADD_V004 | `test_catalog_has_groups_after_add` | Verify groups after add | functional, positive |
| RM_FVT_CATALOG_ADD_V005 | `test_catalog_has_packages_after_add` | Verify packages after add | functional, positive |

### Catalog Delete (`fvt/catalog/delete/`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| RM_FVT_CATALOG_DELETE_E001 | `test_catalog_delete_deploy` | Deploy catalog_delete playbook | deploy, sanity |
| RM_FVT_CATALOG_DELETE_V001 | `test_catalog_delete_operation_completed` | Verify delete operation completed | sanity, positive |
| RM_FVT_CATALOG_DELETE_V002 | `test_catalog_structure_valid_after_delete` | Verify catalog structure valid after delete | functional, positive |
| RM_FVT_CATALOG_DELETE_V003 | `test_catalog_has_functional_layers_after_delete` | Verify functional layers after delete | functional, positive |
| RM_FVT_CATALOG_DELETE_V004 | `test_catalog_has_groups_after_delete` | Verify groups after delete | functional, positive |

### Catalog Validate (`fvt/catalog/validate/`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| RM_FVT_CATALOG_VALIDATE_E001 | `test_catalog_validate_deploy` | Deploy catalog_validate playbook | deploy, sanity |
| RM_FVT_CATALOG_VALIDATE_V001 | `test_catalog_validation_completed` | Verify validation completed | sanity, positive |
| RM_FVT_CATALOG_VALIDATE_V002 | `test_catalog_validation_log_exists` | Verify validation log file exists | deploy, functional, positive |
| RM_FVT_CATALOG_VALIDATE_V003 | `test_catalog_still_valid_after_validation` | Verify catalog still valid after validation | functional, positive |

### Catalog Negative (`fvt/catalog/negative/`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| RM_FVT_CATALOG_NEG_001 | `test_catalog_generate_missing_input_file` | Verify catalog_generate fails with missing input | negative |
| RM_FVT_CATALOG_NEG_002 | `test_catalog_add_missing_input_file` | Verify catalog_add fails with missing input | negative |
| RM_FVT_CATALOG_NEG_003 | `test_catalog_delete_missing_input_file` | Verify catalog_delete fails with missing input | negative |
| RM_FVT_CATALOG_NEG_004 | `test_catalog_input_directory_validation` | Verify catalog input directory validation | negative |
| RM_FVT_CATALOG_NEG_005 | `test_catalog_structure_validation` | Verify catalog structure validation | negative |
| RM_FVT_CATALOG_NEG_006 | `test_catalog_file_existence_validation` | Verify catalog file existence validation | negative |
| RM_FVT_CATALOG_NEG_007 | `test_catalog_log_file_validation` | Verify catalog log file validation | negative |

---

## Non-Functional Tests (`nft/`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| RM_NFT_001 | `test_status_is_semantically_idempotent` | Repeated status generation preserves its published contract | nft, idempotency |
| RM_NFT_002 | `test_pulp_status_response_time` | Pulp health command completes promptly | nft, performance |
| RM_NFT_003 | `test_credentials_are_encrypted_and_private` | Credentials are vaulted and private | nft, security |
| RM_NFT_004 | `test_private_keys_and_log_directories_are_restricted` | Pulp keys and logs deny public access | nft, security |
| RM_NFT_005 | `test_pulp_tls_certificate_is_current` | TLS certificate remains valid | nft, security |

---

## Deterministic Unit/Contract Tests (`ut/`)

| Suite | Count | Coverage |
|-------|------:|----------|
| `test_cleanup_contract.py` | 24 | Cases 1-6 scope, exact identities, fail-closed state, idempotency and ordering |
| `test_common_vars.py` | 3 | Environment-derived path resolution and fallback |
| `test_container_reconciliation.py` | 8 | Ready/incomplete/unknown state and tag union |
| `test_dataset_generator.py` | 6 | Contained output, explicit inputs, and secret-free overrides |
| `test_dataset_contract.py` | 17 | Consumer, generator, publication, and sync contracts |
| `test_dnf_retry.py` | 7 | Transient-only bounded retries and integrity failures |
| `test_framework_contract.py` | 30 | Commands, public tags, suites, entrypoint imports, filtering and dispatch |
| `test_fvt_policy_helpers.py` | 6 | Policy config keys, Pulp JSON parsing, catalog-selected repos and repo source types |
| `test_mirror_state.py` | 9 | Rerun selection, ambiguity, corruption and atomic replacement |
| `test_pulp_command_contract.py` | 13 | Central structured argv and allowlisted grammar |
| `test_repo_file_state.py` | 3 | Atomic, read-only and symlink-safe DNF repo files |
| `test_repo_settings.py` | 7 | Configuration precedence and typed environment values |
| `test_status_contract.py` | 8 | Multi-version aggregation and fail-closed publication |

See [ut/README.md](../ut/README.md) for the full UT test-case registry with individual test IDs
(`RM_UT_001` through `RM_UT_143`).

---

## Test Summary

**Total Test Cases: 263**

| Category | Count |
|----------|-------|
| Precheck Tests | 5 |
| Prepare Tests | 10 |
| Execute Tests | 15 |
| Status Tests | 3 |
| Cleanup Tests | 4 |
| Selective Cleanup Tests | 4 |
| Policy Tests | 21 |
| User Registry Tests | 15 |
| Negative Tests | 10 |
| Catalog Tests | 30 |
| Non-Functional Tests | 5 |
| Unit/Contract Tests | 141 |
| **Total** | **263** |
