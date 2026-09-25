# Repo Manager Deterministic Unit Tests

This document is the authoritative test-case registry for
`test/repo_manager/ut/`. These tests exercise Repo Manager source and
orchestration contracts without a live Pulp service, registry, subscription
or destructive cleanup.

All test-case IDs are defined in `library/vars/ut_test_case_vars.py`. IDs
use the format `RM_UT_<SEQ>` where `SEQ` is a stable three-digit sequence.

## Running

Run with the Python standard library:

```bash
python3 -m unittest discover -s test/repo_manager/ut -p 'test_*.py' -v
```

After installing `test/repo_manager/requirements.txt`, the shared runner can
also execute them:

```bash
test/repo_manager/run_validation.sh ut_repo_manager test
```

Expected-failure tests record confirmed production gaps. They must be removed
from `expectedFailure` when the corresponding source behavior is corrected;
they are not permission to weaken the required invariant.

The `cleanup` and `cleanup_repos` FVT suites are separate, destructive and
explicitly excluded from aggregate FVT execution.

## Test cases

### Cleanup contract (`test_cleanup_contract.py`) -- 24 tests

#### CleanupContextTests

| TC ID | Test | Description |
|-------|------|-------------|
| RM_UT_001 | `test_bare_file_request_expands_to_exact_context_matches` | A bare file identity excludes prefix/suffix near matches. |
| RM_UT_002 | `test_cases_one_to_four_use_target_version_log` | Single-context RPM cleanup logs under its exact minor version. |
| RM_UT_003 | `test_content_directory_cleanup_preserves_other_contexts` | Local cleanup removes only the selected OS/version/architecture path. |
| RM_UT_004 | `test_cross_version_cleanup_uses_aggregate_log` | Shared or multi-version cleanup cannot be attributed to one version. |
| RM_UT_005 | `test_dual_architecture_shared_artifact_uses_version_log` | A shared artifact within one version stays version-scoped. |
| RM_UT_006 | `test_group_status_update_is_version_scoped` | Marking one context partial does not contaminate another version. |
| RM_UT_007 | `test_malformed_python_cleanup_identity_is_rejected` | Malformed version syntax cannot become a cleanup target. |
| RM_UT_008 | `test_pinned_python_request_expands_to_exact_versions` | Pinned Python cleanup retains package-version identity. |
| RM_UT_009 | `test_repository_removal_is_version_and_architecture_scoped` | An exact RPM cleanup cannot erase a near context match. |
| RM_UT_010 | `test_shared_container_is_invalidated_in_every_owning_context` | An exact shared tag is removed from every matching context only. |

#### CleanupStateTests

| TC ID | Test | Description |
|-------|------|-------------|
| RM_UT_011 | `test_already_absent_object_is_unchanged` | Repeated cleanup reports success without a false change. |
| RM_UT_012 | `test_configuration_cleanup_invalidates_before_stopping_pulp` | Configuration-only cleanup follows the same dependency order. |
| RM_UT_013 | `test_credential_cleanup_default_and_preserve_values_are_documented` | Default deletion and explicit preservation spellings remain stable. |
| RM_UT_014 | `test_full_cleanup_invalidates_consumers_before_stopping_pulp` | Public and DNF consumer state is removed before endpoint teardown. |
| RM_UT_015 | `test_full_cleanup_preserves_managed_cli_chain` | Cleanup removes CLI configuration but retains launcher and backend. |
| RM_UT_016 | `test_not_found_query_is_confirmed_absence` | Only an explicit Pulp not-found response proves absence. |
| RM_UT_017 | `test_operational_query_error_is_unknown` | Authentication or transport failures never become absence. |
| RM_UT_018 | `test_orphan_timeout_exceeds_general_command_timeout` | Storage reclamation has a dedicated long-running timeout. |
| RM_UT_019 | `test_pulp_cli_uses_fixed_system_path` | Selective cleanup cannot select an alternate executable implicitly. |
| RM_UT_020 | `test_pulp_repo_stanza_removal_is_idempotent` | A DNF stanza is changed once and remains absent on rerun. |
| RM_UT_021 | `test_repo_status_invalidation_is_idempotent` | The first cleanup removes stale consumer state; the second is a no-op. |
| RM_UT_022 | `test_repo_status_outside_runtime_root_is_rejected` | A cleanup path cannot escape the configured runtime root. |
| RM_UT_023 | `test_unknown_object_state_does_not_trigger_deletion` | Cleanup fails closed when object presence cannot be established. |
| RM_UT_024 | `test_verified_object_deletion_is_changed` | A confirmed present-to-absent transition reports changed. |

### Common vars (`test_common_vars.py`) -- 3 tests

#### CommonVarsTests

| TC ID | Test | Description |
|-------|------|-------------|
| RM_UT_025 | `test_blank_catalog_path_uses_default` | A blank override is never treated as a usable file path. |
| RM_UT_026 | `test_catalog_path_falls_back_below_omnia_data_path` | Legacy environments retain their data-root-derived default. |
| RM_UT_027 | `test_catalog_path_uses_explicit_catalog_file` | The selected versioned catalog takes precedence over defaults. |

### Container reconciliation (`test_container_reconciliation.py`) -- 8 tests

#### ContainerReconciliationTests

| TC ID | Test | Description |
|-------|------|-------------|
| RM_UT_030 | `test_distribution_must_reference_current_repository_state` | Existence alone does not prove the distribution is current. (expectedFailure) |
| RM_UT_031 | `test_distribution_query_error_does_not_trigger_mutation` | Unknown distribution state must fail without create/update. (expectedFailure) |
| RM_UT_032 | `test_missing_distribution_is_incomplete` | Content without a pullable distribution is not ready. |
| RM_UT_033 | `test_missing_tag_is_incomplete` | An existing repository without the requested tag needs repair. |
| RM_UT_034 | `test_new_tag_is_union_with_existing_tags` | Adding one tag preserves all tags already configured on the remote. |
| RM_UT_035 | `test_ready_tag_and_distribution_are_reused` | A tag with a serving distribution performs no repair. |
| RM_UT_036 | `test_remote_tag_query_error_does_not_become_empty_tag_set` | Unknown tags must not overwrite the existing tag union. (expectedFailure) |
| RM_UT_037 | `test_repository_query_error_is_not_treated_as_absent` | Unknown repository state must not trigger create. (expectedFailure) |

### Dataset generator (`test_dataset_generator.py`) -- 6 tests

#### DatasetGeneratorTests

| TC ID | Test | Description |
|-------|------|-------------|
| RM_UT_038 | `test_dataset_name_accepts_portable_identifier` | Normal dataset identifiers resolve directly below datasets/. |
| RM_UT_039 | `test_dataset_name_rejects_path_traversal` | Dataset names cannot escape the datasets directory. |
| RM_UT_040 | `test_declared_non_secret_override_is_allowed` | Known operational variables remain configurable. |
| RM_UT_041 | `test_from_src_copies_only_public_input_allowlist` | Source-copy mode never sweeps credentials or unrelated YAML files. |
| RM_UT_042 | `test_secret_like_override_is_rejected` | Credentials cannot be written into a generated dataset via --var. |
| RM_UT_043 | `test_unknown_override_is_rejected` | Typos cannot silently create unused profile variables. |

### DNF retry (`test_dnf_retry.py`) -- 7 tests

#### DnfRetryTests

| TC ID | Test | Description |
|-------|------|-------------|
| RM_UT_044 | `test_checksum_failure_is_not_retried` | Integrity failures are never hidden by availability retries. |
| RM_UT_045 | `test_non_retryable_marker_wins_over_transient_marker` | A mixed integrity/transport error remains non-retryable. |
| RM_UT_046 | `test_package_not_found_is_not_retried` | A catalog/package error fails immediately. |
| RM_UT_047 | `test_success_runs_once_without_sleep` | A successful command returns immediately. |
| RM_UT_048 | `test_transient_failure_retries_then_succeeds` | Temporary repository availability failures are retried. |
| RM_UT_049 | `test_transient_failure_stops_after_configured_attempts` | A persistent transient error cannot retry indefinitely. |
| RM_UT_050 | `test_warning_reports_next_attempt_numbers` | Retry logs expose bounded progress without raw command data. |

### Framework contract (`test_framework_contract.py`) -- 30 tests

#### FrameworkContractTests

| TC ID | Test | Description |
|-------|------|-------------|
| RM_UT_051 | `test_batch_commands_use_the_shared_runner_vocabulary` | Batch entries use only exec, verify, or test. |
| RM_UT_052 | `test_batch_fvt_scenarios_match_registered_tags` | Every configured scenario is accepted by the domain runner. |
| RM_UT_053 | `test_batch_test_targets_have_a_deploy_trigger` | Every configured full-flow target can execute before verifying. |
| RM_UT_054 | `test_catalog_lifecycle_requires_one_real_suite` | Catalog lifecycle execution cannot fan out across operations. |
| RM_UT_055 | `test_catalog_lifecycle_suites_call_their_public_tags` | Every executable catalog suite owns its matching playbook tag. |
| RM_UT_056 | `test_catalog_lifecycle_without_exact_suite_fails_closed` | Ambiguous or verify-only catalog execution is rejected. |
| RM_UT_057 | `test_catalog_suite_dispatches_one_full_flow` | An exact catalog suite reaches the shared test flow unchanged. |
| RM_UT_058 | `test_declared_suites_are_real_immediate_directories` | Every advertised suite resolves directly beneath its FVT tag. |
| RM_UT_059 | `test_declared_tc_id_wins_over_nested_logger_state` | A test's registered ID cannot be replaced by nested logger state. |
| RM_UT_060 | `test_destructive_cleanup_scenarios_are_excluded_from_all` | Cleanup can run only through an explicitly selected scenario. |
| RM_UT_061 | `test_entrypoint_forwards_the_lifecycle_contract` | Repo Manager passes every domain lifecycle rule to the runner. |
| RM_UT_062 | `test_full_cleanup_fvt_matches_preserved_cli_contract` | Full cleanup no longer depends on obsolete input or CLI deletion. |
| RM_UT_063 | `test_lifecycle_scenarios_call_the_intended_public_tags` | Scenario names resolve to the intended Repo Manager playbook tags. |
| RM_UT_064 | `test_nonfunctional_category_is_registered_and_present` | The advertised NFT category owns real tests and marker metadata. |
| RM_UT_065 | `test_playbook_callers_use_supported_verbosity_keyword` | FVT callers cannot pass the removed `verbose` keyword. |
| RM_UT_066 | `test_playbook_wrapper_uses_supported_verbosity_keyword` | The domain wrapper matches the shared runner API. |
| RM_UT_067 | `test_pytest_entrypoint_can_import_shared_ut_loader` | ValidationRunner's absolute UT path can resolve source_loader.py. |
| RM_UT_068 | `test_pytest_reporting_hooks_are_defined_once` | Later definitions cannot silently override result reporting. |
| RM_UT_069 | `test_runner_entrypoint_dependencies_are_importable` | The CLI dependency graph has no missing domain constants. |
| RM_UT_070 | `test_selected_suite_is_forwarded_to_execution` | A full flow executes only the selected operation suite. |
| RM_UT_071 | `test_shell_entrypoint_prefers_the_local_virtual_environment` | The public wrapper uses installed local dependencies when available. |
| RM_UT_072 | `test_suite_execution_keeps_deploy_scope_exact` | Suite execution includes only its suite and any root trigger. |
| RM_UT_073 | `test_suite_execution_preserves_image_builder_root_trigger` | Shared suite filtering keeps Image Builder's deploy-test layout. |
| RM_UT_074 | `test_unit_category_is_registered_in_batch_config` | The runner registers every deterministic test with a stable ID. |
| RM_UT_075 | `test_unit_startup_does_not_connect_or_sync` | Deterministic unit execution bypasses FVT host setup and reporting. |
| RM_UT_076 | `test_untagged_execution_uses_ordered_lifecycle_paths` | The real runner receives each safe lifecycle directory in order. |
| RM_UT_077 | `test_untagged_lifecycle_is_ordered_and_non_destructive` | An untagged exec/test has an explicit safe lifecycle. |
| RM_UT_078 | `test_untagged_verification_excludes_negative_markers` | Aggregate verification cannot collect co-located negative cases. |
| RM_UT_079 | `test_verify_only_targets_are_not_configured_for_execution` | Targets without deploy triggers fail closed at configuration time. |
| RM_UT_126 | `test_report_names_are_isolated_by_category` | FVT, NFT, and UT runs cannot overwrite one another's reports. |

### FVT policy helpers (`test_fvt_policy_helpers.py`) -- 6 tests

#### FvtPolicyHelperTests

| TC ID | Test | Description |
|-------|------|-------------|
| RM_UT_080 | `test_deployed_repos_come_from_catalog_status` | Policy integration checks only catalog-selected repositories. |
| RM_UT_081 | `test_global_caching_uses_lowercase_key` | Global helper follows the production caching_policy spelling. |
| RM_UT_082 | `test_pulp_repository_list_counts_json_entries` | Pulp's JSON list output is counted without relying on table labels. |
| RM_UT_083 | `test_pulp_repository_list_rejects_non_list_json` | A valid but incompatible Pulp response fails closed. |
| RM_UT_084 | `test_repo_caching_uses_lowercase_global_key` | Per-repo fallback reads caching_policy and defaults to true. |
| RM_UT_085 | `test_repository_source_type_uses_configured_url` | Source-type checks distinguish URL and subscription repositories. |

### Mirror state (`test_mirror_state.py`) -- 9 tests

#### MirrorStateTests

| TC ID | Test | Description |
|-------|------|-------------|
| RM_UT_086 | `test_ambiguous_name_match_does_not_select_an_identity` | A name-only collision cannot update the wrong mirror entry. |
| RM_UT_087 | `test_corrupt_index_is_not_treated_as_confirmed_absence` | Corrupt state must fail rather than schedule everything as new. (expectedFailure) |
| RM_UT_088 | `test_failed_mirror_replacement_removes_temporary_file` | Interrupted mirror writes must not leave PID temp files. (expectedFailure) |
| RM_UT_089 | `test_filter_processes_only_actionable_states` | Skipped artifacts are excluded from the worker task list. |
| RM_UT_090 | `test_global_index_replacement_failure_cleans_temporary_file` | The hardened global-index writer preserves and cleans on failure. |
| RM_UT_091 | `test_mirror_replacement_failure_preserves_previous_file` | An interrupted replacement leaves the last complete index intact. |
| RM_UT_092 | `test_missing_index_starts_with_current_empty_schema` | Confirmed absence of local state creates a valid empty index. |
| RM_UT_093 | `test_rerun_classifies_absent_failed_pending_and_mirrored` | The persisted-state matrix selects new, retry and skip work exactly. |
| RM_UT_094 | `test_save_updates_summary_and_schema` | A complete write publishes deterministic status counts. |

### Pulp command contract (`test_pulp_command_contract.py`) -- 13 tests

#### PulpCommandBuilderTests

| TC ID | Test | Description |
|-------|------|-------------|
| RM_UT_095 | `test_cleanup_tokens_are_allowlisted` | Cleanup accepts only known Pulp plugins, resources and actions. |
| RM_UT_096 | `test_compatibility_exports_remain_valid` | Established config imports remain available to callers. |
| RM_UT_097 | `test_container_password_cannot_add_arguments` | Shell punctuation in a password remains one opaque argument. |
| RM_UT_098 | `test_every_static_template_is_structured` | Every static template is immutable and begins with one executable. |
| RM_UT_099 | `test_executable_override_changes_only_argv_zero` | A configured executable override preserves command grammar. |
| RM_UT_100 | `test_file_path_with_spaces_remains_one_argument` | File paths containing spaces cannot alter command structure. |
| RM_UT_101 | `test_name_and_href_are_mutually_exclusive` | An entity command cannot contain two conflicting identities. |
| RM_UT_102 | `test_task_filters_are_built_centrally` | Exact task correlation retains the established CLI ordering. |
| RM_UT_103 | `test_task_state_is_allowlisted` | An unknown task state cannot become dynamic Pulp grammar. |
| RM_UT_104 | `test_template_returns_fresh_structured_argv` | Templates use the configured executable and never share argv. |

#### PulpCommandSourceBoundaryTests

| TC ID | Test | Description |
|-------|------|-------------|
| RM_UT_105 | `test_pulp_command_module_does_not_own_dnf` | DNF command construction remains outside the Pulp boundary. |
| RM_UT_106 | `test_pulp_commands_are_not_defined_at_python_call_sites` | Production Python callers cannot reintroduce Pulp grammar. |
| RM_UT_107 | `test_yaml_common_commands_have_one_definition` | YAML owns only the status and version command suffixes. |

### Repo file state (`test_repo_file_state.py`) -- 3 tests

#### RepoFileUtilityTests

| TC ID | Test | Description |
|-------|------|-------------|
| RM_UT_108 | `test_atomic_write_is_idempotent` | An identical complete file is reported unchanged. |
| RM_UT_109 | `test_read_only_destination_is_rejected_before_write` | A read-only filesystem is reported without creating a file. |
| RM_UT_110 | `test_symbolic_link_target_is_rejected` | A symlink cannot redirect repository-file replacement. |

### Repo settings (`test_repo_settings.py`) -- 7 tests

#### RepoSettingsTests

| TC ID | Test | Description |
|-------|------|-------------|
| RM_UT_111 | `test_default_is_used_for_missing_key` | A missing environment and YAML key uses the defensive default. |
| RM_UT_112 | `test_false_boolean_environment_override_is_typed` | Bool/int subclass ordering currently returns a string. (expectedFailure) |
| RM_UT_113 | `test_invalid_boolean_environment_override_is_rejected` | Arbitrary boolean spellings must fail closed. (expectedFailure) |
| RM_UT_114 | `test_invalid_integer_environment_override_is_rejected` | Malformed numeric inputs must not become strings. (expectedFailure) |
| RM_UT_115 | `test_true_boolean_environment_override_is_typed` | Valid true values must return bool rather than text. (expectedFailure) |
| RM_UT_116 | `test_valid_integer_environment_override` | A valid numeric override is returned as an integer. |
| RM_UT_117 | `test_yaml_value_is_used_when_environment_is_absent` | Declarative configuration takes precedence over the fallback. |

### Status contract (`test_status_contract.py`) -- 8 tests

#### StatusBuilderTests

| TC ID | Test | Description |
|-------|------|-------------|
| RM_UT_118 | `test_context_summary_contains_only_public_stable_fields` | Internal catalog data cannot leak through execution contexts. |
| RM_UT_119 | `test_failure_keeps_later_context_pending` | A failed active version cannot make an unexecuted version successful. |
| RM_UT_120 | `test_first_context_resets_stale_selected_version_status` | A new pass cannot retain success from an earlier selected version. |
| RM_UT_121 | `test_success_requires_every_selected_context` | A partially completed multi-version run remains in progress. |
| RM_UT_122 | `test_version_mapping_removes_unselected_versions` | Changing catalog selection removes obsolete version output. |

#### StatusPublicationTests

| TC ID | Test | Description |
|-------|------|-------------|
| RM_UT_123 | `test_atomic_write_preserves_previous_status_on_replace_failure` | An interrupted publication retains the last complete public status. |
| RM_UT_124 | `test_failed_status_contains_no_consumable_repository_urls` | A failed run publishes empty repository maps and legacy URLs. |
| RM_UT_125 | `test_removed_file_repos_by_version_field_is_not_reintroduced` | The current output contract owns only the common file_repos field. |

### Dataset contract (`test_dataset_contract.py`) -- 17 tests

#### DatasetContractTests

| TC ID | Test | Description |
|-------|------|-------------|
| RM_UT_127 | `test_atomic_publication_restores_previous_dataset` | A failed staged rename restores the previous published dataset. |
| RM_UT_128 | `test_batch_scenarios_expose_dataset_controls` | Every FVT batch scenario can select and synchronize a dataset. |
| RM_UT_129 | `test_check_mode_detects_dataset_drift` | Check mode succeeds for current output and fails after modification. |
| RM_UT_130 | `test_checked_in_dataset_is_current` | The committed default dataset remains reproducible from its profile. |
| RM_UT_131 | `test_credential_like_dataset_file_fails_closed` | Datasets cannot become a plaintext credential transport. |
| RM_UT_132 | `test_dataset_symlink_fails_closed` | A named dataset cannot redirect consumers outside the dataset root. |
| RM_UT_133 | `test_dry_run_generates_without_publishing` | Dry-run validates all artifacts and leaves no dataset behind. |
| RM_UT_134 | `test_empty_dataset_validates_canonical_source_fallback` | Empty dataset mode validates the same public source contract. |
| RM_UT_135 | `test_host_resolution_rejects_unsafe_or_missing_datasets` | Runtime consumers enforce the same contained dataset selection. |
| RM_UT_136 | `test_incomplete_named_dataset_fails_closed` | Both public Repo Manager input files are mandatory. |
| RM_UT_137 | `test_invalid_dataset_yaml_fails_closed` | Malformed YAML cannot reach target synchronization. |
| RM_UT_138 | `test_invalid_sync_override_fails_closed` | Boolean environment overrides are parsed strictly. |
| RM_UT_139 | `test_manifest_records_provenance_and_artifact_hashes` | Published datasets contain deterministic source and artifact hashes. |
| RM_UT_140 | `test_missing_named_dataset_fails_closed` | A selected dataset must exist before test startup can continue. |
| RM_UT_141 | `test_repeated_generation_is_reproducible` | Force regeneration produces byte-identical checked artifacts. |
| RM_UT_142 | `test_sync_staging_copies_only_public_input_allowlist` | Defense in depth prevents extra files from entering sync staging. |
| RM_UT_143 | `test_named_dataset_reaches_remote_sync_staging` | The selected dataset supplies the exact files sent to the target. |

### Exact-mirror reconciliation (`test_exact_mirror_reconciliation.py`) -- 11 tests

| TC ID | Test | Description |
|-------|------|-------------|
| RM_UT_144 | `test_exact_and_normal_sync_commands_remain_separate` | Exact mirror remains an explicit operation and cannot alter normal synchronization. |
| RM_UT_145 | `test_exact_sync_uses_mirror_content_only` | Exact synchronization passes Pulp's `mirror_content_only` policy. |
| RM_UT_146 | `test_nested_content_summary_reports_package_delta` | Current Pulp response data yields accurate RPM additions and removals. |
| RM_UT_147 | `test_normal_sync_does_not_change_policy` | Existing Repo Manager downloads keep their established additive command. |
| RM_UT_148 | `test_duplicate_catalog_repository_identity_fails_closed` | Duplicate selected repository identities are rejected before mutation. |
| RM_UT_149 | `test_empty_catalog_repository_list_fails_closed` | Empty selection cannot broaden to all Pulp repositories. |
| RM_UT_150 | `test_failed_metadata_validation_restores_old_publication` | Failed replacement metadata restores the last-known-good publication. |
| RM_UT_151 | `test_orphan_cleanup_runs_only_after_every_repo_succeeds` | Orphan cleanup follows successful repository reconciliation. |
| RM_UT_152 | `test_pruning_occurs_after_replacement_validation` | Superseded state is pruned only after replacement metadata is validated. |
| RM_UT_153 | `test_pruning_preserves_empty_and_current_versions` | Cleanup preserves Pulp v0 and the current repository version. |
| RM_UT_154 | `test_repository_failure_blocks_orphan_cleanup_and_later_repos` | One failure stops pending repositories and aggregate cleanup. |

## Registry summary

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
| `test_exact_mirror_reconciliation.py` | 11 | Exact sync policy, metrics, failure safety, rollback and cleanup gating |
| **Total** | **152** | |
