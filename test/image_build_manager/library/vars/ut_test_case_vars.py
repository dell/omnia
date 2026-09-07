# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Stable test-case IDs for existing Image Build Manager unit tests."""


def _class_cases(file_name, class_name, cases):
    """Build explicit pytest-node-to-test-case-ID mappings for one class."""
    return {
        f"{file_name}::{class_name}::{method_name}": f"IMGBM_UT_{sequence:03d}"
        for sequence, method_name in cases.items()
    }


def _module_cases(file_name, cases):
    """Build explicit pytest-node-to-test-case-ID mappings for module tests."""
    return {
        f"{file_name}::{function_name}": f"IMGBM_UT_{sequence:03d}"
        for sequence, function_name in cases.items()
    }


# Every sequence is explicit so formatting or reordering cannot renumber a
# published case. Add new cases with the next available sequence.
UT_TEST_CASE_IDS = {
    **_class_cases(
        "test_catalog_validation.py",
        "TestCatalogSchemaFile",
        {
            1: "test_schema_file_exists",
            2: "test_schema_is_valid_json",
            3: "test_schema_requires_catalog_root",
            4: "test_schema_requires_functionallayer",
            5: "test_schema_requires_groups",
            6: "test_schema_requires_packages",
        },
    ),
    **_class_cases(
        "test_catalog_validation.py",
        "TestSampleCatalogStructure",
        {
            7: "test_sample_catalog_exists",
            8: "test_sample_catalog_is_valid_json",
            9: "test_sample_has_required_keys",
            10: "test_sample_functionallayer_not_empty",
            11: "test_sample_groups_reference_valid_packages",
            12: "test_sample_layers_reference_valid_groups",
            13: "test_sample_has_baseos_group",
            14: "test_sample_packages_have_sources",
        },
    ),
    **_class_cases(
        "test_driver_group_skip.py",
        "TestIsDriverGroup",
        {
            15: "test_nvidia_driver_group",
            16: "test_infiniband_driver_group",
            17: "test_vast_driver_group",
            18: "test_regular_group_not_driver",
            19: "test_baseos_not_driver",
            20: "test_empty_string",
            21: "test_driver_group_substring_anywhere",
            22: "test_partial_match_no_false_positive",
        },
    ),
    **_class_cases(
        "test_driver_group_skip.py",
        "TestCollectDriverGroups",
        {
            23: "test_finds_driver_groups_at_top_level",
            24: "test_no_driver_groups",
            25: "test_does_not_include_standard_keys",
        },
    ),
    **_class_cases(
        "test_driver_group_skip.py",
        "TestResolveCatalogDriverSkip",
        {
            26: "test_driver_components_excluded_from_compute_packages",
            27: "test_non_driver_packages_still_present",
            28: "test_skipped_driver_groups_reported",
            29: "test_base_packages_unaffected_by_driver_skip",
        },
    ),
    **_class_cases(
        "test_driver_group_skip.py",
        "TestSampleCatalogDriverGroups",
        {
            30: "test_sample_catalog_has_driver_groups",
            31: "test_sample_driver_groups_defined_in_groups",
            32: "test_sample_driver_groups_excluded_from_resolution",
        },
    ),
    **_class_cases(
        "test_functional_group_packages.py",
        "TestFunctionalGroupPackagesStructure",
        {
            33: "test_base_packages_exists",
            34: "test_functional_groups_exists",
            35: "test_each_group_has_packages_key",
            36: "test_group_names_have_arch_suffix",
            37: "test_base_packages_are_strings",
            38: "test_group_packages_are_strings",
            39: "test_no_duplicate_base_packages",
            40: "test_no_duplicate_group_packages",
        },
    ),
    **_class_cases(
        "test_functional_group_packages.py",
        "TestFunctionalGroupPackagesContent",
        {
            41: "test_base_has_essential_packages",
            42: "test_os_x86_64_exists",
            43: "test_slurm_groups_have_munge",
        },
    ),
    **_class_cases(
        "test_functional_group_packages.py",
        "TestConfigConsistency",
        {
            44: "test_functional_groups_have_arch_suffix_in_mapping",
        },
    ),
    **_class_cases(
        "test_standalone_independence.py",
        "TestNoExternalDependencies",
        {
            45: "test_no_software_config_json_reference_in_active_code",
            46: "test_no_metadata_file_path_in_active_code",
            47: "test_no_provision_config_reference",
            48: "test_ansible_cfg_no_omnia_paths",
        },
    ),
    **_class_cases(
        "test_standalone_independence.py",
        "TestRepoStructure",
        {
            49: "test_input_dir_exists",
            50: "test_image_build_config_exists",
            51: "test_package_groups_exists",
            52: "test_samples_dir_exists",
            53: "test_sample_repo_status_exists",
            54: "test_package_groups_in_input",
            55: "test_ansible_cfg_exists",
            56: "test_main_playbook_exists",
            57: "test_all_roles_have_tasks",
        },
    ),
    **_class_cases(
        "test_validate_image_build_config.py",
        "TestImageBuildConfigSchema",
        {
            58: "test_schema_file_exists",
            59: "test_schema_is_valid_json",
            60: "test_schema_has_functional_groups_source",
            61: "test_config_has_required_fields",
            62: "test_s3_provider_valid",
            63: "test_functional_groups_source_valid",
        },
    ),
    **_class_cases(
        "test_validate_image_build_config.py",
        "TestRepoStatus",
        {
            64: "test_has_overall_status",
            65: "test_has_cluster_os_type",
            66: "test_has_repositories_or_rpm_repos",
            67: "test_repositories_have_x86_64",
            68: "test_x86_64_has_baseos",
        },
    ),
    **_class_cases(
        "test_validate_image_build_config.py",
        "TestInputFilesExist",
        {
            69: "test_image_build_config_exists",
            70: "test_repo_status_exists",
            71: "test_package_groups_exists",
            72: "test_certs_dir_exists",
        },
    ),
    **_class_cases(
        "test_validate_image_build_config.py",
        "TestNoHardcodedOmniaPaths",
        {
            73: "test_role_vars_no_omnia_defaults",
        },
    ),
    **_module_cases(
        "test_input_validation_schema.py",
        {
            74: "test_valid_boolean_values_pass",
            75: "test_top_level_required_values_must_exist",
            76: "test_quoted_boolean_values_fail",
            77: "test_empty_scalar_values_fail",
            78: "test_optional_arm_host_may_be_empty",
            79: "test_optional_arm_host_must_be_ipv4_when_set",
            80: "test_minio_requires_empty_endpoint",
            81: "test_minio_endpoint_key_is_required",
            82: "test_powerscale_requires_nonempty_endpoint",
            83: "test_powerscale_accepts_valid_endpoint",
            84: "test_arm_host_requires_nonempty_ssh_user",
            85: "test_all_build_controls_are_required",
            86: "test_package_groups_schema_rejects_blank_package",
            87: "test_valid_repo_status_passes_schema_and_logic",
            88: "test_repo_status_requires_success",
            89: "test_repo_status_requires_repo_manager_contract",
            90: "test_repo_status_allows_empty_internet_repo_manager_values",
            91: "test_repo_status_checks_repo_manager_structure_only",
            92: "test_repo_status_requires_certificate_structure",
            93: "test_repo_status_rejects_invalid_port_type_or_range",
            94: "test_repo_status_requires_certificate_values_to_be_strings",
            95: "test_repo_status_rejects_blank_url",
            96: "test_repo_status_requires_usable_x86_repository",
            97: "test_repo_status_boolean_priority_fails",
            98: "test_internet_repo_status_sample_passes_contract",
            99: "test_repo_contract_runs_in_build_setup_not_general_validation",
        },
    ),
}

if len(set(UT_TEST_CASE_IDS.values())) != len(UT_TEST_CASE_IDS):
    raise ValueError("Image Build Manager UT test-case IDs must be unique")
