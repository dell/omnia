# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Stable test-case IDs for Repo Manager unit tests."""


def _class_cases(file_name, class_name, cases):
    """Build explicit pytest-node-to-test-case-ID mappings for one class."""
    return {
        f"{file_name}::{class_name}::{method_name}": f"RM_UT_{sequence:03d}"
        for sequence, method_name in cases.items()
    }


# Every sequence is explicit so formatting or test collection order cannot
# renumber a published case. Add new cases with the next available sequence.
UT_TEST_CASE_IDS = {
    **_class_cases(
        "test_cleanup_contract.py",
        "CleanupContextTests",
        {
            1: "test_bare_file_request_expands_to_exact_context_matches",
            2: "test_cases_one_to_four_use_target_version_log",
            3: "test_content_directory_cleanup_preserves_other_contexts",
            4: "test_cross_version_cleanup_uses_aggregate_log",
            5: "test_dual_architecture_shared_artifact_uses_version_log",
            6: "test_group_status_update_is_version_scoped",
            7: "test_malformed_python_cleanup_identity_is_rejected",
            8: "test_pinned_python_request_expands_to_exact_versions",
            9: "test_repository_removal_is_version_and_architecture_scoped",
            10: "test_shared_container_is_invalidated_in_every_owning_context",
        },
    ),
    **_class_cases(
        "test_cleanup_contract.py",
        "CleanupStateTests",
        {
            11: "test_already_absent_object_is_unchanged",
            12: "test_configuration_cleanup_invalidates_before_stopping_pulp",
            13: "test_credential_cleanup_default_and_preserve_values_are_documented",
            14: "test_full_cleanup_invalidates_consumers_before_stopping_pulp",
            15: "test_full_cleanup_preserves_managed_cli_chain",
            16: "test_not_found_query_is_confirmed_absence",
            17: "test_operational_query_error_is_unknown",
            18: "test_orphan_timeout_exceeds_general_command_timeout",
            19: "test_pulp_cli_uses_fixed_system_path",
            20: "test_pulp_repo_stanza_removal_is_idempotent",
            21: "test_repo_status_invalidation_is_idempotent",
            22: "test_repo_status_outside_runtime_root_is_rejected",
            23: "test_unknown_object_state_does_not_trigger_deletion",
            24: "test_verified_object_deletion_is_changed",
        },
    ),
    **_class_cases(
        "test_common_vars.py",
        "CommonVarsTests",
        {
            25: "test_blank_catalog_path_uses_default",
            26: "test_catalog_path_falls_back_below_omnia_data_path",
            27: "test_catalog_path_uses_explicit_catalog_file",
        },
    ),
    **_class_cases(
        "test_container_reconciliation.py",
        "ContainerReconciliationTests",
        {
            30: "test_distribution_must_reference_current_repository_state",
            31: "test_distribution_query_error_does_not_trigger_mutation",
            32: "test_missing_distribution_is_incomplete",
            33: "test_missing_tag_is_incomplete",
            34: "test_new_tag_is_union_with_existing_tags",
            35: "test_ready_tag_and_distribution_are_reused",
            36: "test_remote_tag_query_error_does_not_become_empty_tag_set",
            37: "test_repository_query_error_is_not_treated_as_absent",
        },
    ),
    **_class_cases(
        "test_dataset_generator.py",
        "DatasetGeneratorTests",
        {
            38: "test_dataset_name_accepts_portable_identifier",
            39: "test_dataset_name_rejects_path_traversal",
            40: "test_declared_non_secret_override_is_allowed",
            41: "test_from_src_copies_only_public_input_allowlist",
            42: "test_secret_like_override_is_rejected",
            43: "test_unknown_override_is_rejected",
        },
    ),
    **_class_cases(
        "test_dataset_contract.py",
        "DatasetContractTests",
        {
            127: "test_atomic_publication_restores_previous_dataset",
            128: "test_batch_scenarios_expose_dataset_controls",
            129: "test_check_mode_detects_dataset_drift",
            130: "test_checked_in_dataset_is_current",
            131: "test_credential_like_dataset_file_fails_closed",
            132: "test_dataset_symlink_fails_closed",
            133: "test_dry_run_generates_without_publishing",
            134: "test_empty_dataset_validates_canonical_source_fallback",
            135: "test_host_resolution_rejects_unsafe_or_missing_datasets",
            136: "test_incomplete_named_dataset_fails_closed",
            137: "test_invalid_dataset_yaml_fails_closed",
            138: "test_invalid_sync_override_fails_closed",
            139: "test_manifest_records_provenance_and_artifact_hashes",
            140: "test_missing_named_dataset_fails_closed",
            141: "test_repeated_generation_is_reproducible",
            142: "test_sync_staging_copies_only_public_input_allowlist",
            143: "test_named_dataset_reaches_remote_sync_staging",
        },
    ),
    **_class_cases(
        "test_dnf_retry.py",
        "DnfRetryTests",
        {
            44: "test_checksum_failure_is_not_retried",
            45: "test_non_retryable_marker_wins_over_transient_marker",
            46: "test_package_not_found_is_not_retried",
            47: "test_success_runs_once_without_sleep",
            48: "test_transient_failure_retries_then_succeeds",
            49: "test_transient_failure_stops_after_configured_attempts",
            50: "test_warning_reports_next_attempt_numbers",
        },
    ),
    **_class_cases(
        "test_framework_contract.py",
        "FrameworkContractTests",
        {
            51: "test_batch_commands_use_the_shared_runner_vocabulary",
            52: "test_batch_fvt_scenarios_match_registered_tags",
            53: "test_batch_test_targets_have_a_deploy_trigger",
            54: "test_catalog_lifecycle_requires_one_real_suite",
            55: "test_catalog_lifecycle_suites_call_their_public_tags",
            56: "test_catalog_lifecycle_without_exact_suite_fails_closed",
            57: "test_catalog_suite_dispatches_one_full_flow",
            58: "test_declared_suites_are_real_immediate_directories",
            59: "test_declared_tc_id_wins_over_nested_logger_state",
            60: "test_destructive_cleanup_scenarios_are_excluded_from_all",
            61: "test_entrypoint_forwards_the_lifecycle_contract",
            62: "test_full_cleanup_fvt_matches_preserved_cli_contract",
            63: "test_lifecycle_scenarios_call_the_intended_public_tags",
            64: "test_nonfunctional_category_is_registered_and_present",
            65: "test_playbook_callers_use_supported_verbosity_keyword",
            66: "test_playbook_wrapper_uses_supported_verbosity_keyword",
            67: "test_pytest_entrypoint_can_import_shared_ut_loader",
            68: "test_pytest_reporting_hooks_are_defined_once",
            69: "test_runner_entrypoint_dependencies_are_importable",
            70: "test_selected_suite_is_forwarded_to_execution",
            71: "test_shell_entrypoint_prefers_the_local_virtual_environment",
            72: "test_suite_execution_keeps_deploy_scope_exact",
            73: "test_suite_execution_preserves_image_builder_root_trigger",
            74: "test_unit_category_is_registered_in_batch_config",
            75: "test_unit_startup_does_not_connect_or_sync",
            76: "test_untagged_execution_uses_ordered_lifecycle_paths",
            77: "test_untagged_lifecycle_is_ordered_and_non_destructive",
            78: "test_untagged_verification_excludes_negative_markers",
            79: "test_verify_only_targets_are_not_configured_for_execution",
            126: "test_report_names_are_isolated_by_category",
        },
    ),
    **_class_cases(
        "test_fvt_policy_helpers.py",
        "FvtPolicyHelperTests",
        {
            80: "test_deployed_repos_come_from_catalog_status",
            81: "test_global_caching_uses_lowercase_key",
            82: "test_pulp_repository_list_counts_json_entries",
            83: "test_pulp_repository_list_rejects_non_list_json",
            84: "test_repo_caching_uses_lowercase_global_key",
            85: "test_repository_source_type_uses_configured_url",
        },
    ),
    **_class_cases(
        "test_mirror_state.py",
        "MirrorStateTests",
        {
            86: "test_ambiguous_name_match_does_not_select_an_identity",
            87: "test_corrupt_index_is_not_treated_as_confirmed_absence",
            88: "test_failed_mirror_replacement_removes_temporary_file",
            89: "test_filter_processes_only_actionable_states",
            90: "test_global_index_replacement_failure_cleans_temporary_file",
            91: "test_mirror_replacement_failure_preserves_previous_file",
            92: "test_missing_index_starts_with_current_empty_schema",
            93: "test_rerun_classifies_absent_failed_pending_and_mirrored",
            94: "test_save_updates_summary_and_schema",
        },
    ),
    **_class_cases(
        "test_pulp_command_contract.py",
        "PulpCommandBuilderTests",
        {
            95: "test_cleanup_tokens_are_allowlisted",
            96: "test_compatibility_exports_remain_valid",
            97: "test_container_password_cannot_add_arguments",
            98: "test_every_static_template_is_structured",
            99: "test_executable_override_changes_only_argv_zero",
            100: "test_file_path_with_spaces_remains_one_argument",
            101: "test_name_and_href_are_mutually_exclusive",
            102: "test_task_filters_are_built_centrally",
            103: "test_task_state_is_allowlisted",
            104: "test_template_returns_fresh_structured_argv",
        },
    ),
    **_class_cases(
        "test_pulp_command_contract.py",
        "PulpCommandSourceBoundaryTests",
        {
            105: "test_pulp_command_module_does_not_own_dnf",
            106: "test_pulp_commands_are_not_defined_at_python_call_sites",
            107: "test_yaml_common_commands_have_one_definition",
        },
    ),
    **_class_cases(
        "test_repo_file_state.py",
        "RepoFileUtilityTests",
        {
            108: "test_atomic_write_is_idempotent",
            109: "test_read_only_destination_is_rejected_before_write",
            110: "test_symbolic_link_target_is_rejected",
        },
    ),
    **_class_cases(
        "test_repo_settings.py",
        "RepoSettingsTests",
        {
            111: "test_default_is_used_for_missing_key",
            112: "test_false_boolean_environment_override_is_typed",
            113: "test_invalid_boolean_environment_override_is_rejected",
            114: "test_invalid_integer_environment_override_is_rejected",
            115: "test_true_boolean_environment_override_is_typed",
            116: "test_valid_integer_environment_override",
            117: "test_yaml_value_is_used_when_environment_is_absent",
        },
    ),
    **_class_cases(
        "test_status_contract.py",
        "StatusBuilderTests",
        {
            118: "test_context_summary_contains_only_public_stable_fields",
            119: "test_failure_keeps_later_context_pending",
            120: "test_first_context_resets_stale_selected_version_status",
            121: "test_success_requires_every_selected_context",
            122: "test_version_mapping_removes_unselected_versions",
        },
    ),
    **_class_cases(
        "test_status_contract.py",
        "StatusPublicationTests",
        {
            123: "test_atomic_write_preserves_previous_status_on_replace_failure",
            124: "test_failed_status_contains_no_consumable_repository_urls",
            125: "test_removed_file_repos_by_version_field_is_not_reintroduced",
        },
    ),
    **_class_cases(
        "test_exact_mirror_reconciliation.py",
        "ExactMirrorCommandTests",
        {
            144: "test_exact_and_normal_sync_commands_remain_separate",
            145: "test_exact_sync_uses_mirror_content_only",
            146: "test_nested_content_summary_reports_package_delta",
            147: "test_normal_sync_does_not_change_policy",
        },
    ),
    **_class_cases(
        "test_exact_mirror_reconciliation.py",
        "ExactMirrorSafetyTests",
        {
            148: "test_duplicate_catalog_repository_identity_fails_closed",
            149: "test_empty_catalog_repository_list_fails_closed",
            150: "test_failed_metadata_validation_restores_old_publication",
            151: "test_orphan_cleanup_runs_only_after_every_repo_succeeds",
            152: "test_pruning_occurs_after_replacement_validation",
            153: "test_pruning_preserves_empty_and_current_versions",
            154: "test_repository_failure_blocks_orphan_cleanup_and_later_repos",
        },
    ),
}


if len(set(UT_TEST_CASE_IDS.values())) != len(UT_TEST_CASE_IDS):
    raise ValueError("Duplicate Repo Manager unit-test case ID")
