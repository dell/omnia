# Repo Manager Functional Verification Tests

This document is the authoritative test-case registry for
`test/repo_manager/fvt/`. It describes what each test validates and the
condition required for the test to pass.

All test-case IDs are defined inline in each test's docstring and
`TestLogger` call. Test files must use these registered IDs; IDs and titles
must not be invented outside the established pattern.

## Test-case ID standard

IDs use `RM_FVT_<PHASE>_<TYPE><SEQ>`:

| Segment | Meaning | Values or example |
|---------|---------|-------------------|
| `RM` | Repo Manager domain | Fixed domain code |
| `FVT` | Functional Verification Test level | Fixed test-level code |
| `PHASE` | Lifecycle phase | `PRECHECK`, `PREPARE`, `EXECUTE`, `REPO_SYNC`, `STATUS`, `CLEANUP`, `CLEANUP_REPOS`, `POLICY`, `NEG`, `USER_REGISTRY`, `CATALOG_GENERATE`, `CATALOG_ADD`, `CATALOG_DELETE`, `CATALOG_VALIDATE`, or `CATALOG_NEG` |
| `TYPE` | Whether the case changes or inspects state | `E` runs a playbook; `V` verifies postconditions |
| `SEQ` | Stable sequence appended to the type | Three digits, starting at `001` |

For example, `RM_FVT_PREPARE_E001` runs the prepare playbook and
`RM_FVT_PREPARE_V001` verifies its first postcondition. The sequence is a
stable identifier, not a global execution position. Execution is controlled
first by lifecycle phase, then by suite, and finally by
`@pytest.mark.order(n)` inside that suite.

## Effective execution order

An untagged `test` runs `precheck`, `prepare`, `execute`, and `status` in
order, then verifies the non-destructive scenarios. Cleanup, negative, and
catalog and exact-mirror operations require explicit selection. Policy, negative, and user
registry scenarios are verification-only.

| Phase | Suite order |
|-------|-------------|
| precheck | `test_status` |
| prepare | `test_status` |
| execute | `test_status` |
| status | `test_status` |

## Precheck test cases

These cases confirm that the execution OIM has the required input files and
credentials. Deploy cases run only with the `test` command; `verify` runs
only the verification cases.

| Sequence | TC ID | Test | Markers | Validation | Pass criteria |
|----------|-------|------|---------|------------|---------------|
| 0 | RM_FVT_PRECHECK_E001 | `test_precheck_environment` | deploy, sanity | Runs `repo_manager.yml --tags precheck`. | Playbook exits successfully. |
| 1 | RM_FVT_PRECHECK_V001 | `test_input_config_exists` | sanity, positive | Resolves the input directory on the target. | `repo_manager_config.yml` exists at the runtime input path. |
| 2 | RM_FVT_PRECHECK_V002 | `test_endpoint_config_exists` | sanity, positive | Checks the endpoint configuration file. | `repo_manager_endpoint_config.yml` exists at the runtime input path. |
| 3 | RM_FVT_PRECHECK_V003 | `test_credentials_present` | sanity, positive | Resolves the domain-credential path on the execution OIM. | Credentials file is present. |
| 4 | RM_FVT_PRECHECK_V004 | `test_precheck_environment_no_credentials` | sanity, positive | Validates input without prompting for credentials. | Precheck completes without credential prompting. |

## Prepare test cases

These cases verify the Pulp infrastructure deployed by the `prepare` flow.

| Sequence | TC ID | Test | Markers | Validation | Pass criteria |
|----------|-------|------|---------|------------|---------------|
| 0 | RM_FVT_PREPARE_E001 | `test_prepare_pulp` | deploy, sanity | Runs `repo_manager.yml --tags prepare`. | Playbook exits successfully. |
| 1 | RM_FVT_PREPARE_V001 | `test_pulp_container_running` | sanity, positive | Inspects the Pulp container with Podman. | Pulp container is running. |
| 2 | RM_FVT_PREPARE_V002 | `test_pulp_status_healthy` | sanity, positive | Checks the Pulp health status. | Pulp status reports healthy. |
| 3 | RM_FVT_PREPARE_V003 | `test_pulp_endpoint_reachable` | sanity, positive | Calls the Pulp API status endpoint. | Pulp API endpoint is reachable. |
| 4 | RM_FVT_PREPARE_V004 | `test_pulp_cli_configured` | sanity, positive | Checks the Pulp CLI configuration. | Pulp CLI is configured and functional. |
| 5 | RM_FVT_PREPARE_V005 | `test_pulp_certificates_exist` | functional, positive | Checks Pulp SSL certificate files. | Pulp SSL certificates exist on disk. |
| 6 | RM_FVT_PREPARE_V006 | `test_pulp_cli_repository_list` | sanity, positive | Lists RPM repositories through the Pulp CLI. | Pulp CLI can list RPM repositories. |
| 7 | RM_FVT_PREPARE_V007 | `test_pulp_api_detailed_status` | sanity, positive | Checks Pulp API detailed health (DB, workers, content apps, storage). | All Pulp health components report healthy. |
| 8 | RM_FVT_PREPARE_E002 | `test_collect_credentials` | functional, positive | Verifies the `collect_repo_credentials` role functionality. | Credential collection completes successfully. |
| 9 | RM_FVT_PREPARE_E003 | `test_credential_encryption` | functional, positive | Verifies credential encryption and vault handling. | Credentials are encrypted and vault-managed. |

## Execute test cases

These cases verify the repository download and synchronization performed by
the `execute` flow.

| Sequence | TC ID | Test | Markers | Validation | Pass criteria |
|----------|-------|------|---------|------------|---------------|
| 0 | RM_FVT_EXECUTE_E001 | `test_execute_download` | deploy, sanity | Runs `repo_manager.yml --tags execute`. | Playbook exits successfully. |
| 1 | RM_FVT_EXECUTE_V001 | `test_repo_status_exists` | sanity, positive | Checks for `repo_status.yml` on the target. | `repo_status.yml` is generated. |
| 2 | RM_FVT_EXECUTE_V002 | `test_repo_status_success` | sanity, positive | Parses the overall status field. | `overall_status` is `success`. |
| 3 | RM_FVT_EXECUTE_V003 | `test_slurm_custom_repo_present` | sanity, positive | Checks for the SLURM custom repository. | `slurm_custom` repo is present if configured. |
| 4 | RM_FVT_EXECUTE_V004 | `test_epel_repo_present` | sanity, positive | Checks for the EPEL repository. | `epel` repo is present if configured. |
| 5 | RM_FVT_EXECUTE_V005 | `test_x86_64_repos_present` | sanity, positive | Checks for x86_64 `baseos` and `appstream` repositories. | x86_64 repos are present if configured. |
| 6 | RM_FVT_EXECUTE_V006 | `test_file_repos_present` | functional, positive | Checks for file repositories (tarball type). | File repos are present if configured. |
| 7 | RM_FVT_EXECUTE_V007 | `test_software_download_status` | sanity, positive | Checks `software.csv` download status per architecture. | Software download status CSV exists and reports results. |
| 8 | RM_FVT_EXECUTE_V008 | `test_per_software_package_status` | sanity, positive | Checks per-software `status.csv` for individual package download results. | Per-package status is recorded. |
| 9 | RM_FVT_EXECUTE_V009 | `test_pulp_repositories_synced` | sanity, positive | Verifies all RPM repositories have `latest_version_href`. | All RPM repositories show sync indicator. |
| 10 | RM_FVT_EXECUTE_V010 | `test_pulp_distributions_published` | sanity, positive | Verifies all RPM distributions are published with repository attachment. | All RPM distributions are published. |
| 11 | RM_FVT_EXECUTE_V011 | `test_container_repos_synced` | functional, positive | Verifies all container image repositories are synced. | Container repositories are synced. |
| 12 | RM_FVT_EXECUTE_V012 | `test_file_repos_synced` | functional, positive | Verifies all file repositories (tarball, git, etc.) are synced. | File repositories are synced. |
| 13 | RM_FVT_EXECUTE_V013 | `test_pulp_content_accessible` | sanity, positive | Verifies RPM content is reachable via HTTPS (`repomd.xml` check). | Pulp-served RPM content is accessible. |
| 14 | RM_FVT_EXECUTE_V014 | `test_software_packages_in_pulp` | sanity, positive | Verifies all RPM packages from `software_config.json` are present in Pulp. | All expected software packages are in Pulp. |

## Catalog exact-mirror test cases

These cases are explicitly selected with the `repo_resync` marker. They are
not part of the normal sanity lifecycle because the playbook deliberately
reconciles selected repositories with their current upstream contents.

| Sequence | TC ID | Test | Markers | Validation | Pass criteria |
|----------|-------|------|---------|------------|---------------|
| 0 | RM_FVT_REPO_SYNC_E001 | `test_repo_sync_playbook_reconciles_only_catalog_repositories` | deploy, repo_resync | Snapshots unreferenced Pulp repositories, runs standalone `repo_sync.yml`, and compares the snapshot. | Playbook succeeds and no unreferenced repository changes or disappears. |
| 1 | RM_FVT_REPO_SYNC_V001 | `test_repo_sync_status_is_successful` | repo_resync, positive | Reads `repo_resync_status.yml`. | Overall reconciliation and orphan cleanup report success. |
| 2 | RM_FVT_REPO_SYNC_V002 | `test_repo_sync_result_matches_catalog_scope` | repo_resync, positive | Resolves RPM sources used by active functional layers. | Result repository identities exactly match active-catalog references. |
| 3 | RM_FVT_REPO_SYNC_V003 | `test_repo_sync_repositories_have_zero_stale_packages` | repo_resync, positive | Checks every per-repository result. | Sync and cleanup succeed with zero stale packages. |
| 4 | RM_FVT_REPO_SYNC_V004 | `test_repo_sync_package_deltas_are_valid` | repo_resync, positive | Validates old/new versions and package counters. | Version and delta fields are complete, integer, and nonnegative. |
| 5 | RM_FVT_REPO_SYNC_V005 | `test_repo_sync_keeps_one_current_publication_and_version` | repo_resync, positive | Queries Pulp versions and publications. | Only Pulp's empty v0 plus one current nonzero version and one publication remain. |
| 6 | RM_FVT_REPO_SYNC_V006 | `test_repo_sync_distributions_publish_valid_metadata` | repo_resync, positive | Checks distribution publication binding and downloads `repomd.xml` with the managed CA. | Every distribution references a publication and serves valid repository metadata. |
| 7 | RM_FVT_REPO_SYNC_V007 | `test_repo_sync_slurm_user_repository_matches_input` | repo_resync, positive | Compares Slurm Pulp remote with Repo Manager input. | Script-produced Slurm URL and configured remote policy are preserved. |

## Status test cases

These cases verify the `repo_status.yml` generation performed by the
`status` flow.

| Sequence | TC ID | Test | Markers | Validation | Pass criteria |
|----------|-------|------|---------|------------|---------------|
| 0 | RM_FVT_STATUS_E001 | `test_deploy_status` | deploy, sanity | Runs `repo_manager.yml --tags status`. | Playbook exits successfully. |
| 1 | RM_FVT_STATUS_V001 | `test_repo_status_regenerated` | sanity, positive | Checks that `repo_status.yml` is regenerated. | `repo_status.yml` exists after status run. |
| 2 | RM_FVT_STATUS_V002 | `test_repo_status_success_after_status` | sanity, positive | Parses the overall status field after regeneration. | `overall_status` is `success`. |

## Cleanup test cases

These cases verify the state after the opt-in `cleanup` flow. Cleanup
requires explicit selection and is excluded from aggregate FVT execution.

| Sequence | TC ID | Test | Markers | Validation | Pass criteria |
|----------|-------|------|---------|------------|---------------|
| 100 | RM_FVT_CLEANUP_E001 | `test_deploy_cleanup` | deploy, sanity | Runs `repo_manager.yml --tags cleanup`. | Cleanup playbook exits successfully. |
| 101 | RM_FVT_CLEANUP_V001 | `test_pulp_container_removed` | sanity, positive | Searches Podman for the Pulp container. | Pulp container is removed. |
| 102 | RM_FVT_CLEANUP_V002 | `test_pulp_cli_preserved` | sanity, positive | Checks the managed Pulp CLI executable. | Managed Pulp CLI remains executable. |
| 103 | RM_FVT_CLEANUP_V003 | `test_pulp_directories_removed` | functional, positive | Checks the Pulp data directories. | Pulp directories are removed. |

## Selective cleanup test cases

These cases verify explicit, exact repository cleanup and state invalidation.
They require explicit selection with the `destructive` marker.

| Sequence | TC ID | Test | Markers | Validation | Pass criteria |
|----------|-------|------|---------|------------|---------------|
| 0 | RM_FVT_CLEANUP_REPOS_E001 | `test_deploy_exact_repository_cleanup` | deploy, destructive | Removes an explicitly authorized exact RPM repository. | Cleanup playbook exits successfully for the named repository. |
| 1 | RM_FVT_CLEANUP_REPOS_V001 | `test_exact_repository_is_absent_while_pulp_is_healthy` | destructive | Distinguishes verified absence from endpoint failure. | Target repository is absent and Pulp endpoint remains healthy. |
| 2 | RM_FVT_CLEANUP_REPOS_V002 | `test_selective_cleanup_invalidates_repo_status` | destructive | Verifies stale consumer output is invalidated. | Stale consumer URLs are removed after verified cleanup. |
| 3 | RM_FVT_CLEANUP_REPOS_V003 | `test_cleanup_status_records_exact_success` | destructive | Verifies one exact successful cleanup result. | Cleanup CSV records the requested identity successfully. |

## Policy test cases

These cases verify repository policy configurations. All policy tests are
verification-only and do not execute playbooks.

### Priority order (`test_priority_order.py`)

| Sequence | TC ID | Test | Markers | Validation | Pass criteria |
|----------|-------|------|---------|------------|---------------|
| 1 | RM_FVT_POLICY_V001 | `test_per_repo_policy_overrides_global` | sanity, positive | Per-repo policy should override global `repo_config`. | Per-repo policy wins over global setting. |
| 2 | RM_FVT_POLICY_V002 | `test_per_repo_caching_overrides_global` | sanity, positive | Per-repo caching should override global `CACHING_POLICY`. | Per-repo caching wins over global setting. |
| 3 | RM_FVT_POLICY_V003 | `test_per_repo_complete_override` | sanity, positive | Per-repo should completely override global settings. | Complete per-repo override applies. |

### Partial override (`test_partial_override.py`)

| Sequence | TC ID | Test | Markers | Validation | Pass criteria |
|----------|-------|------|---------|------------|---------------|
| 4 | RM_FVT_POLICY_V004 | `test_per_repo_policy_only` | sanity, positive | Per-repo policy only; caching from global. | Mixed policy/global resolution works. |
| 5 | RM_FVT_POLICY_V005 | `test_per_repo_caching_only` | sanity, positive | Per-repo caching only; policy from global. | Mixed caching/global resolution works. |
| 6 | RM_FVT_POLICY_V006 | `test_empty_per_repo_config` | sanity, positive | Empty per-repo config should use global settings. | Global settings apply when per-repo is empty. |

### Policy combinations (`test_policy_combinations.py`)

| Sequence | TC ID | Test | Markers | Validation | Pass criteria |
|----------|-------|------|---------|------------|---------------|
| 7 | RM_FVT_POLICY_V007 | `test_policy_always_caching_false` | sanity, positive | `policy: always + caching: false = immediate`. | Pulp policy resolves to `immediate`. |
| 8 | RM_FVT_POLICY_V008 | `test_policy_always_caching_true` | sanity, positive | `policy: always + caching: true = on_demand`. | Pulp policy resolves to `on_demand`. |
| 9 | RM_FVT_POLICY_V009 | `test_policy_partial_caching_false` | sanity, positive | `policy: partial + caching: false = streamed`. | Pulp policy resolves to `streamed`. |
| 10 | RM_FVT_POLICY_V010 | `test_policy_partial_caching_true` | sanity, positive | `policy: partial + caching: true = on_demand`. | Pulp policy resolves to `on_demand`. |

### Repo types (`test_repo_types.py`)

| Sequence | TC ID | Test | Markers | Validation | Pass criteria |
|----------|-------|------|---------|------------|---------------|
| 11 | RM_FVT_POLICY_V011 | `test_subscription_repo_per_repo_override` | sanity, positive | Subscription repos should support per-repo overrides. | Per-repo overrides apply to subscription repos. |
| 12 | RM_FVT_POLICY_V012 | `test_url_repo_per_repo_override` | sanity, positive | URL repos should support per-repo overrides. | Per-repo overrides apply to URL repos. |
| 13 | RM_FVT_POLICY_V013 | `test_subscription_and_url_identical_behavior` | sanity, positive | Subscription and URL repos should behave identically. | Identical policy resolution for both repo types. |

### Pulp mode (`test_pulp_mode.py`)

| Sequence | TC ID | Test | Markers | Validation | Pass criteria |
|----------|-------|------|---------|------------|---------------|
| 14 | RM_FVT_POLICY_V014 | `test_pulp_mode_in_repo_status` | sanity, positive | `repo_status.yml` should reflect correct Pulp mode. | Effective Pulp mode is correctly resolved. |
| 15 | RM_FVT_POLICY_V015 | `test_actual_pulp_repository_policy` | sanity, positive | Actual Pulp repository should have correct policy. | Valid Pulp policy combinations are enforced. |
| 16 | RM_FVT_POLICY_V016 | `test_disk_space_savings` | sanity, positive | On-demand repos should save disk space. | On-demand policy selection applies. |

### Integration Pulp policies (`test_integration_pulp_policies.py`)

| Sequence | TC ID | Test | Markers | Validation | Pass criteria |
|----------|-------|------|---------|------------|---------------|
| 17 | RM_FVT_POLICY_V017 | `test_pulp_remote_policy_matches_config` | sanity, positive | Actual Pulp remote policy should match resolved configuration. | Pulp remote policy matches configuration. |
| 18 | RM_FVT_POLICY_V018 | `test_pulp_remote_policy_immediate_mode` | sanity, positive | Repos with `always+false` should have `immediate` policy. | Immediate policy applies in Pulp. |
| 19 | RM_FVT_POLICY_V019 | `test_pulp_remote_policy_on_demand_mode` | sanity, positive | Repos with `partial+true` should have `on_demand` policy. | On-demand policy applies in Pulp. |
| 20 | RM_FVT_POLICY_V020 | `test_multiple_repos_policy_resolution` | sanity, positive | Multiple repos should have correct Pulp policies. | Every deployed repo has the correct Pulp policy. |
| 21 | RM_FVT_POLICY_V021 | `test_pulp_repository_exists` | sanity, positive | Pulp repositories should exist for configured repos. | Every deployed Pulp repository exists. |

## User registry test cases

### Validation tests (`test_user_registry_validation.py`)

| Sequence | TC ID | Test | Markers | Validation | Pass criteria |
|----------|-------|------|---------|------------|---------------|
| 0 | RM_FVT_USER_REGISTRY_E001 | `test_user_registry_validation_deploy` | deploy, sanity | Deploy validation playbook (includes registry checks). | Playbook exits successfully. |
| 1 | RM_FVT_USER_REGISTRY_V001 | `test_user_registry_section_exists` | sanity, positive | Verify registries section exists in config. | `registries` section exists in `repo_manager_config.yml`. |
| 2 | RM_FVT_USER_REGISTRY_V002 | `test_user_registry_structure_valid` | sanity, positive | Verify registry entries have valid structure. | Registry entries have required fields. |
| 3 | RM_FVT_USER_REGISTRY_V003 | `test_user_registry_base_url_valid` | sanity, positive | Verify `base_url` is valid HTTP(S) origin. | All registry `base_url` values are valid origins. |
| 4 | RM_FVT_USER_REGISTRY_V004 | `test_user_registry_reachable` | functional, positive | Verify configured registries are reachable. | All configured registries respond. |
| 5 | RM_FVT_USER_REGISTRY_V005 | `test_user_registry_tls_cert_paths_valid` | functional, positive | Verify TLS certificate paths exist on disk. | TLS cert paths exist on target. |
| 6 | RM_FVT_USER_REGISTRY_V006 | `test_user_registry_tls_pair_consistent` | sanity, positive | Verify client cert and key configured together. | Client cert and key are paired correctly. |
| 7 | RM_FVT_USER_REGISTRY_V007 | `test_user_registry_auth_type_valid` | sanity, positive | Verify auth type is `none` or `basic`. | Auth type is a valid value. |
| 8 | RM_FVT_USER_REGISTRY_V008 | `test_user_registry_credentials_present` | functional, positive | Verify credentials for basic auth registries. | Credentials exist for basic-auth registries. |

### Negative tests (`test_user_registry_negative.py`)

| Sequence | TC ID | Test | Markers | Validation | Pass criteria |
|----------|-------|------|---------|------------|---------------|
| 1 | RM_FVT_USER_REGISTRY_NEG_001 | `test_registry_validation_fails_missing_config` | negative | Validation fails with missing config file. | Validation fails cleanly with missing config. |
| 2 | RM_FVT_USER_REGISTRY_NEG_002 | `test_registry_validation_detects_invalid_base_url` | negative | Detects invalid `base_url`. | Invalid `base_url` is detected. |
| 3 | RM_FVT_USER_REGISTRY_NEG_003 | `test_registry_validation_detects_incomplete_tls_pair` | negative | Detects incomplete TLS cert/key pair. | Incomplete TLS pair is detected. |
| 4 | RM_FVT_USER_REGISTRY_NEG_004 | `test_registry_validation_detects_unsupported_auth_type` | negative | Detects unsupported auth type. | Unsupported auth type is detected. |
| 5 | RM_FVT_USER_REGISTRY_NEG_005 | `test_registry_validation_detects_missing_cert_paths` | negative | Detects missing cert paths on disk. | Missing cert paths are detected. |
| 6 | RM_FVT_USER_REGISTRY_NEG_006 | `test_registry_validation_detects_missing_vault_path` | negative | Detects missing `vault_path` for basic auth. | Missing `vault_path` is detected. |

## Negative test cases (`fvt/negative/error_scenarios/`)

| Sequence | TC ID | Test | Markers | Validation | Pass criteria |
|----------|-------|------|---------|------------|---------------|
| 1 | RM_FVT_NEG_001 | `test_deploy_fails_missing_credentials` | negative | Deploy fails with missing credentials. | Deployment fails cleanly. |
| 2 | RM_FVT_NEG_002 | `test_deploy_fails_invalid_endpoint_config` | negative | Deploy fails with invalid endpoint config. | Deployment fails cleanly. |
| 3 | RM_FVT_NEG_003 | `test_download_fails_invalid_repo_url` | negative | Download fails with invalid repository URL. | Download fails cleanly. |
| 4 | RM_FVT_NEG_004 | `test_status_fails_missing_repo_status` | negative | Status check fails with missing `repo_status.yml`. | Status check fails cleanly. |
| 5 | RM_FVT_NEG_005 | `test_cleanup_fails_pulp_not_running` | negative | Cleanup fails when Pulp container not running. | Cleanup fails cleanly. |
| 6 | RM_FVT_NEG_006 | `test_pulp_cli_fails_invalid_auth` | negative | Pulp CLI fails with invalid authentication. | CLI fails cleanly. |
| 7 | RM_FVT_NEG_007 | `test_repo_sync_fails_network_issues` | negative | Repository sync fails with network connectivity issues. | Sync fails cleanly. |
| 8 | RM_FVT_NEG_008 | `test_catalog_generation_fails_invalid_config` | negative | Catalog generation fails with invalid `software_config.json`. | Generation fails cleanly. |
| 9 | RM_FVT_NEG_009 | `test_validate_fails_missing_config` | negative | Validation fails with missing `repo_manager_config.yml`. | Validation fails cleanly. |
| 10 | RM_FVT_NEG_010 | `test_pulp_api_unreachable_port_closed` | negative | Pulp API unreachable when port is closed. | Unreachable state is detected cleanly. |

## Catalog test cases

Catalog lifecycle execution intentionally has no "run all" mode. Select one
operation suite so generate, add, and delete cannot run accidentally in the
same invocation.

### Catalog generate (`fvt/catalog/generate/`)

| Sequence | TC ID | Test | Markers | Validation | Pass criteria |
|----------|-------|------|---------|------------|---------------|
| 0 | RM_FVT_CATALOG_GENERATE_E001 | `test_catalog_generate_deploy` | deploy, sanity | Deploy the `catalog_generate` operation. | Playbook exits successfully. |
| 0 | RM_FVT_CATALOG_GENERATE_V001 | `test_catalog_input_dir_exists` | sanity, positive | Verify catalog input directory exists. | Input directory exists on target. |
| 1 | RM_FVT_CATALOG_GENERATE_V002 | `test_catalog_file_exists` | sanity, positive | Verify catalog file exists after generate. | Catalog JSON file is created. |
| 2 | RM_FVT_CATALOG_GENERATE_V003 | `test_catalog_structure_valid` | sanity, positive | Verify catalog structure is valid. | Catalog has valid JSON structure. |
| 3 | RM_FVT_CATALOG_GENERATE_V004 | `test_catalog_functional_layers` | sanity, positive | Verify catalog has functional layers. | Functional layers are present. |
| 4 | RM_FVT_CATALOG_GENERATE_V005 | `test_catalog_groups` | sanity, positive | Verify catalog has groups. | Groups are present. |
| 5 | RM_FVT_CATALOG_GENERATE_V006 | `test_catalog_packages` | sanity, positive | Verify catalog has packages. | Packages are present. |
| 6 | RM_FVT_CATALOG_GENERATE_V007 | `test_catalog_log_file_exists` | deploy, functional, positive | Verify catalog log file exists. | Log file is created. |

### Catalog add (`fvt/catalog/add/`)

| Sequence | TC ID | Test | Markers | Validation | Pass criteria |
|----------|-------|------|---------|------------|---------------|
| 0 | RM_FVT_CATALOG_ADD_E001 | `test_catalog_add_deploy` | deploy, sanity | Deploy `catalog_add` playbook. | Playbook exits successfully. |
| 1 | RM_FVT_CATALOG_ADD_V001 | `test_catalog_add_operation_completed` | sanity, positive | Verify catalog add operation completed successfully. | Add operation succeeds. |
| 2 | RM_FVT_CATALOG_ADD_V002 | `test_catalog_structure_valid_after_add` | functional, positive | Verify catalog structure still valid after add. | Catalog structure remains valid. |
| 3 | RM_FVT_CATALOG_ADD_V003 | `test_catalog_has_functional_layers_after_add` | functional, positive | Verify catalog has functional layers after add. | Functional layers are present. |
| 4 | RM_FVT_CATALOG_ADD_V004 | `test_catalog_has_groups_after_add` | functional, positive | Verify catalog has groups after add. | Groups are present. |
| 5 | RM_FVT_CATALOG_ADD_V005 | `test_catalog_has_packages_after_add` | functional, positive | Verify catalog has packages after add. | Packages are present. |

### Catalog delete (`fvt/catalog/delete/`)

| Sequence | TC ID | Test | Markers | Validation | Pass criteria |
|----------|-------|------|---------|------------|---------------|
| 0 | RM_FVT_CATALOG_DELETE_E001 | `test_catalog_delete_deploy` | deploy, sanity | Deploy `catalog_delete` playbook. | Playbook exits successfully. |
| 1 | RM_FVT_CATALOG_DELETE_V001 | `test_catalog_delete_operation_completed` | sanity, positive | Verify catalog delete operation completed successfully. | Delete operation succeeds. |
| 2 | RM_FVT_CATALOG_DELETE_V002 | `test_catalog_structure_valid_after_delete` | functional, positive | Verify catalog structure still valid after delete. | Catalog structure remains valid. |
| 3 | RM_FVT_CATALOG_DELETE_V003 | `test_catalog_has_functional_layers_after_delete` | functional, positive | Verify catalog still has functional layers after delete. | Functional layers are present. |
| 4 | RM_FVT_CATALOG_DELETE_V004 | `test_catalog_has_groups_after_delete` | functional, positive | Verify catalog still has groups after delete. | Groups are present. |

### Catalog validate (`fvt/catalog/validate/`)

| Sequence | TC ID | Test | Markers | Validation | Pass criteria |
|----------|-------|------|---------|------------|---------------|
| 0 | RM_FVT_CATALOG_VALIDATE_E001 | `test_catalog_validate_deploy` | deploy, sanity | Deploy `catalog_validate` playbook. | Playbook exits successfully. |
| 1 | RM_FVT_CATALOG_VALIDATE_V001 | `test_catalog_validation_completed` | sanity, positive | Verify catalog validation completed successfully. | Validation completes. |
| 2 | RM_FVT_CATALOG_VALIDATE_V002 | `test_catalog_validation_log_exists` | deploy, functional, positive | Verify catalog validation log file exists. | Log file exists. |
| 3 | RM_FVT_CATALOG_VALIDATE_V003 | `test_catalog_still_valid_after_validation` | functional, positive | Verify catalog file still valid after validation. | Catalog remains valid. |

### Catalog negative (`fvt/catalog/negative/`)

| Sequence | TC ID | Test | Markers | Validation | Pass criteria |
|----------|-------|------|---------|------------|---------------|
| 1 | RM_FVT_CATALOG_NEG_001 | `test_catalog_generate_missing_input_file` | negative | Verify `catalog_generate` fails with missing input file. | Fails cleanly. |
| 2 | RM_FVT_CATALOG_NEG_002 | `test_catalog_add_missing_input_file` | negative | Verify `catalog_add` fails with missing input file. | Fails cleanly. |
| 3 | RM_FVT_CATALOG_NEG_003 | `test_catalog_delete_missing_input_file` | negative | Verify `catalog_delete` fails with missing input file. | Fails cleanly. |
| 4 | RM_FVT_CATALOG_NEG_004 | `test_catalog_input_directory_validation` | negative | Verify catalog input directory validation. | Invalid input directory is detected. |
| 5 | RM_FVT_CATALOG_NEG_005 | `test_catalog_structure_validation` | negative | Verify catalog structure validation. | Invalid structure is detected. |
| 6 | RM_FVT_CATALOG_NEG_006 | `test_catalog_file_existence_validation` | negative | Verify catalog file existence validation. | Missing catalog is detected. |
| 7 | RM_FVT_CATALOG_NEG_007 | `test_catalog_log_file_validation` | negative | Verify catalog log file validation. | Missing log file is detected. |

## Registry summary

| Phase | Execution IDs | Verification IDs | Total | Notes |
|-------|---------------|------------------|-------|-------|
| Precheck | `RM_FVT_PRECHECK_E001` | `RM_FVT_PRECHECK_V001`--`V004` | 5 | Input and credential validation. |
| Prepare | `RM_FVT_PREPARE_E001`--`E003` | `RM_FVT_PREPARE_V001`--`V007` | 10 | Pulp infrastructure deployment. |
| Execute | `RM_FVT_EXECUTE_E001` | `RM_FVT_EXECUTE_V001`--`V014` | 15 | Repository download and sync. |
| Status | `RM_FVT_STATUS_E001` | `RM_FVT_STATUS_V001`--`V002` | 3 | Status generation. |
| Cleanup | `RM_FVT_CLEANUP_E001` | `RM_FVT_CLEANUP_V001`--`V003` | 4 | Full Pulp cleanup. |
| Selective cleanup | `RM_FVT_CLEANUP_REPOS_E001` | `RM_FVT_CLEANUP_REPOS_V001`--`V003` | 4 | Exact repository cleanup. |
| Policy | -- | `RM_FVT_POLICY_V001`--`V021` | 21 | Repository policy verification. |
| User registry | `RM_FVT_USER_REGISTRY_E001` | `RM_FVT_USER_REGISTRY_V001`--`V008`, `NEG_001`--`NEG_006` | 15 | User registry validation. |
| Negative | -- | `RM_FVT_NEG_001`--`NEG_010` | 10 | Error scenario verification. |
| Catalog generate | `RM_FVT_CATALOG_GENERATE_E001` | `RM_FVT_CATALOG_GENERATE_V001`--`V007` | 8 | Catalog generation. |
| Catalog add | `RM_FVT_CATALOG_ADD_E001` | `RM_FVT_CATALOG_ADD_V001`--`V005` | 6 | Catalog add operation. |
| Catalog delete | `RM_FVT_CATALOG_DELETE_E001` | `RM_FVT_CATALOG_DELETE_V001`--`V004` | 5 | Catalog delete operation. |
| Catalog validate | `RM_FVT_CATALOG_VALIDATE_E001` | `RM_FVT_CATALOG_VALIDATE_V001`--`V003` | 4 | Catalog validate operation. |
| Catalog negative | -- | `RM_FVT_CATALOG_NEG_001`--`NEG_007` | 7 | Catalog negative tests. |
| **Total FVT** | | | **117** | |

## Execution commands

Run from `test/repo_manager/`:

```bash
# Deploy and verify one lifecycle phase
./run_validation.sh fvt_repo_manager precheck test
./run_validation.sh fvt_repo_manager prepare test
./run_validation.sh fvt_repo_manager execute test
./run_validation.sh fvt_repo_manager status test

# Run the complete non-destructive lifecycle
./run_validation.sh fvt_repo_manager test

# Verify without running playbooks
./run_validation.sh fvt_repo_manager verify

# Focused verification
./run_validation.sh fvt_repo_manager policy verify
./run_validation.sh fvt_repo_manager user_registry test
./run_validation.sh fvt_repo_manager negative verify

# Catalog operations (one suite at a time)
./run_validation.sh fvt_repo_manager catalog test --suite generate
./run_validation.sh fvt_repo_manager catalog test --suite add
./run_validation.sh fvt_repo_manager catalog test --suite delete
./run_validation.sh fvt_repo_manager catalog test --suite validate
./run_validation.sh fvt_repo_manager catalog verify --suite negative

# Destructive flows; run only when explicit
./run_validation.sh fvt_repo_manager cleanup test --marker destructive
REPO_MANAGER_TEST_CLEANUP_REPO=x86_64_rhel_10.0_test_repo \
  ./run_validation.sh fvt_repo_manager cleanup_repos test --marker destructive
```

`verify` never executes a playbook. The untagged form excludes cleanup and
deploy cases. Cleanup scenarios run only when explicitly selected.
