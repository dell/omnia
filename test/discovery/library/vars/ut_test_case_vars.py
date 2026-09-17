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

"""Stable test-case IDs for existing Discovery unit tests."""


def _class_cases(file_name, class_name, cases):
    """Build explicit pytest-node-to-test-case-ID mappings for one class."""
    return {
        f"{file_name}::{class_name}::{method_name}": f"DISC_UT_{sequence:03d}"
        for sequence, method_name in cases.items()
    }


def _module_cases(file_name, cases):
    """Build explicit pytest-node-to-test-case-ID mappings for module tests."""
    return {
        f"{file_name}::{function_name}": f"DISC_UT_{sequence:03d}"
        for sequence, function_name in cases.items()
    }


# Every sequence is explicit so formatting or reordering cannot renumber a
# published case. Add new cases with the next available sequence.
UT_TEST_CASE_IDS = {
    # ── Schema file existence (test_input_validation_schema.py) ──────────
    **_class_cases(
        "test_input_validation_schema.py",
        "TestDiscoveryConfigSchemaFile",
        {
            1: "test_schema_file_exists",
            2: "test_schema_is_valid_json",
            3: "test_schema_has_draft_declaration",
            4: "test_schema_requires_ome_ip",
            5: "test_credential_rules_file_exists",
            6: "test_credential_rules_is_valid_json",
        },
    ),
    # ── discovery_config.json validation ─────────────────────────────────
    **_module_cases(
        "test_input_validation_schema.py",
        {
            7: "test_valid_config_passes",
            8: "test_ome_ip_required",
            9: "test_ome_ip_rejects_invalid_addresses",
            10: "test_ome_ip_accepts_valid_addresses",
            11: "test_ome_ip_rejects_non_string_type",
            12: "test_config_allows_additional_properties",
        },
    ),
    # ── Credential rules validation ──────────────────────────────────────
    **_class_cases(
        "test_input_validation_schema.py",
        "TestCredentialRulesSchema",
        {
            13: "test_ome_username_rule_exists",
            14: "test_ome_password_rule_exists",
            15: "test_bmc_username_rule_exists",
            16: "test_bmc_password_rule_exists",
            17: "test_provision_password_rule_exists",
            18: "test_each_rule_has_min_length",
            19: "test_each_rule_has_description",
        },
    ),
    # ── L2 semantic validator (test_discovery_config_validator.py) ───────
    **_module_cases(
        "test_discovery_config_validator.py",
        {
            20: "test_valid_config_passes_l2",
            21: "test_missing_ome_ip_fails",
            22: "test_empty_ome_ip_fails",
            23: "test_loopback_ip_fails",
            24: "test_non_ipv4_string_fails",
            25: "test_valid_private_ips_pass",
            26: "test_non_string_ome_ip_fails",
            27: "test_ipv6_address_fails",
            28: "test_engine_run_validation_collects_errors",
            29: "test_engine_run_validation_passes_valid",
            30: "test_is_valid_ipv4_accepts_valid",
            31: "test_is_valid_ipv4_rejects_invalid",
            32: "test_is_valid_ipv4_rejects_ipv6",
        },
    ),
    # ── Standalone independence (test_standalone_independence.py) ─────────
    **_class_cases(
        "test_standalone_independence.py",
        "TestNoExternalDependencies",
        {
            33: "test_no_hardcoded_omnia_paths_in_ansible_cfg",
            34: "test_no_image_build_references_in_discovery",
        },
    ),
    **_class_cases(
        "test_standalone_independence.py",
        "TestRepoStructure",
        {
            35: "test_input_dir_exists",
            36: "test_discovery_config_exists",
            37: "test_network_spec_exists",
            38: "test_playbooks_dir_exists",
            39: "test_main_playbook_exists",
            40: "test_ansible_cfg_exists",
            41: "test_roles_dir_exists",
            42: "test_all_roles_have_tasks",
            43: "test_plugins_dir_exists",
            44: "test_validation_schema_dir_exists",
            45: "test_discovery_config_schema_exists",
        },
    ),
    **_class_cases(
        "test_standalone_independence.py",
        "TestInputTemplateContent",
        {
            46: "test_discovery_config_has_ome_ip",
            47: "test_network_spec_has_networks",
            48: "test_network_spec_has_admin_network",
        },
    ),
}

if len(set(UT_TEST_CASE_IDS.values())) != len(UT_TEST_CASE_IDS):
    raise ValueError("Discovery UT test-case IDs must be unique")
