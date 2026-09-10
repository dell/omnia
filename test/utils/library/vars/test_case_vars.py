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

"""
Utils Domain - Test Case Registry.

Central registry mapping every test to its TC ID and title.
Test files reference ``TEST_CASES["key"]`` to get a consistent
test-case identifier and display name.

ID Format: UTILS_FVT_<PHASE>_<TYPE><SEQ>
- UTILS: Domain code
- FVT: Functional Verification Test
- PHASE: PRECHECK, SETUP, COLLECT, INSTALL_OS, CLEANUP_LOGS, CLEANUP_INSTALL_OS, CLEANUP
- TYPE: E (execution/deploy), V (verification)
- SEQ: Three-digit sequence number

Usage in test files::

    from library.vars.test_case_vars import TEST_CASES as TC

    tc = TC["deploy_collect"]
    tl = TestLogger(tc["title"], tc["id"])
"""

TEST_CASES = {
    # ══════════════════════════════════════════════════════════════════════════
    # PRECHECK SCENARIO
    # ══════════════════════════════════════════════════════════════════════════
    "deploy_precheck": {
        "id": "UTILS_FVT_PRECHECK_E001",
        "title": "Deploy utils.yml (precheck)",
    },
    "target_connectivity": {
        "id": "UTILS_FVT_PRECHECK_V001",
        "title": "Verify target host connectivity and SSH",
    },
    "env_vars_present": {
        "id": "UTILS_FVT_PRECHECK_V002",
        "title": "Verify OMNIA env vars present on target",
    },
    "hostname_domain": {
        "id": "UTILS_FVT_PRECHECK_V003",
        "title": "Verify hostname and domain match omnia.env",
    },
    "admin_ip_assigned": {
        "id": "UTILS_FVT_PRECHECK_V004",
        "title": "Verify admin IP assigned to local interface",
    },
    "omnia_setup": {
        "id": "UTILS_FVT_PRECHECK_V005",
        "title": "Verify omnia.sh setup completed on target",
    },

    # ══════════════════════════════════════════════════════════════════════════
    # SETUP SCENARIO
    # ══════════════════════════════════════════════════════════════════════════
    "deploy_setup": {
        "id": "UTILS_FVT_SETUP_E001",
        "title": "Deploy utils.yml (setup)",
    },
    "setup_omnia_data_path_set": {
        "id": "UTILS_FVT_SETUP_V001",
        "title": "Verify OMNIA_DATA_PATH fact is set",
    },
    "setup_project_paths_set": {
        "id": "UTILS_FVT_SETUP_V002",
        "title": "Verify project input/output paths are set",
    },
    "setup_output_dir_created": {
        "id": "UTILS_FVT_SETUP_V003",
        "title": "Verify output directory is created",
    },
    "setup_domain_ready_fact": {
        "id": "UTILS_FVT_SETUP_V004",
        "title": "Verify utils domain ready fact is true",
    },

    # ══════════════════════════════════════════════════════════════════════════
    # COLLECT SCENARIO - Deploy Tests
    # ══════════════════════════════════════════════════════════════════════════
    "deploy_collect": {
        "id": "UTILS_FVT_COLLECT_E000",
        "title": "Deploy collect.yml (full stack based on OMNIA_DEPLOY_TAG)",
    },
    "deploy_collect_setup": {
        "id": "UTILS_FVT_COLLECT_E001",
        "title": "Deploy collect.yml (setup stage)",
    },
    "deploy_collect_prepare": {
        "id": "UTILS_FVT_COLLECT_E002",
        "title": "Deploy collect.yml (prepare stage)",
    },
    "deploy_collect_bundle": {
        "id": "UTILS_FVT_COLLECT_E003",
        "title": "Deploy collect.yml (bundle stage)",
    },
    "deploy_collect_full": {
        "id": "UTILS_FVT_COLLECT_E004",
        "title": "Deploy collect.yml (full execution)",
    },

    # ══════════════════════════════════════════════════════════════════════════
    # COLLECT SCENARIO - Verification Tests
    # ══════════════════════════════════════════════════════════════════════════
    "collect_input_file_exists": {
        "id": "UTILS_FVT_COLLECT_V001",
        "title": "Verify collect_pxe.yml input file exists on target",
    },
    "collect_input_file_valid": {
        "id": "UTILS_FVT_COLLECT_V002",
        "title": "Verify collect_pxe.yml has valid YAML structure",
    },
    "collect_functional_groups_valid": {
        "id": "UTILS_FVT_COLLECT_V003",
        "title": "Verify collect_pxe.yml contains valid functional groups",
    },
    "collect_output_dir_exists": {
        "id": "UTILS_FVT_COLLECT_V004",
        "title": "Verify log collection output directory exists",
    },
    "collect_bundle_created": {
        "id": "UTILS_FVT_COLLECT_V005",
        "title": "Verify log bundle tar.gz file created",
    },
    "collect_metadata_exists": {
        "id": "UTILS_FVT_COLLECT_V006",
        "title": "Verify metadata.json file exists",
    },
    "collect_metadata_valid": {
        "id": "UTILS_FVT_COLLECT_V007",
        "title": "Verify metadata.json has valid structure",
    },
    "collect_metadata_sha256": {
        "id": "UTILS_FVT_COLLECT_V008",
        "title": "Verify metadata.json contains SHA256 checksum",
    },
    "collect_bundle_contents": {
        "id": "UTILS_FVT_COLLECT_V009",
        "title": "Verify log bundle contains expected directories",
    },
    "collect_env_vars_loaded": {
        "id": "UTILS_FVT_COLLECT_V010",
        "title": "Verify OMNIA_DATA_PATH loaded from environment",
    },
    "collect_project_name_loaded": {
        "id": "UTILS_FVT_COLLECT_V011",
        "title": "Verify OMNIA_PROJECT_NAME loaded from environment",
    },
    "collect_bundle_log_files_content": {
        "id": "UTILS_FVT_COLLECT_V012",
        "title": "Verify log bundle contains log files with content",
    },

    # ══════════════════════════════════════════════════════════════════════════
    # INSTALL_OS SCENARIO - Deploy Tests
    # ══════════════════════════════════════════════════════════════════════════
    "deploy_install_os": {
        "id": "UTILS_FVT_INSTALL_OS_E000",
        "title": "Deploy install_os.yml (full stack based on OMNIA_DEPLOY_TAG)",
    },
    "deploy_install_os_credentials": {
        "id": "UTILS_FVT_INSTALL_OS_E001",
        "title": "Deploy install_os.yml (credentials tag)",
    },
    "deploy_install_os_build_iso": {
        "id": "UTILS_FVT_INSTALL_OS_E002",
        "title": "Deploy install_os.yml (build_iso tag)",
    },
    "deploy_install_os_deploy": {
        "id": "UTILS_FVT_INSTALL_OS_E003",
        "title": "Deploy install_os.yml (deploy tag)",
    },
    "deploy_install_os_generate_ks": {
        "id": "UTILS_FVT_INSTALL_OS_E004",
        "title": "Deploy install_os.yml (generate_ks tag)",
    },
    "deploy_install_os_full": {
        "id": "UTILS_FVT_INSTALL_OS_E005",
        "title": "Deploy install_os.yml (full execution)",
    },

    # ══════════════════════════════════════════════════════════════════════════
    # INSTALL_OS SCENARIO - Verification Tests
    # ══════════════════════════════════════════════════════════════════════════
    "install_os_config_file_exists": {
        "id": "UTILS_FVT_INSTALL_OS_V001",
        "title": "Verify install_os_config.yml exists on target",
    },
    "install_os_config_valid": {
        "id": "UTILS_FVT_INSTALL_OS_V002",
        "title": "Verify install_os_config.yml has valid structure",
    },
    "install_os_credentials_file_exists": {
        "id": "UTILS_FVT_INSTALL_OS_V003",
        "title": "Verify install_os_credentials.yml exists",
    },
    "install_os_output_dir_exists": {
        "id": "UTILS_FVT_INSTALL_OS_V004",
        "title": "Verify install_os output directory exists",
    },
    "install_os_status_file_exists": {
        "id": "UTILS_FVT_INSTALL_OS_V005",
        "title": "Verify install_os_status.yml output file created",
    },
    "install_os_status_valid": {
        "id": "UTILS_FVT_INSTALL_OS_V006",
        "title": "Verify install_os_status.yml has valid structure",
    },
    "install_os_custom_iso_created": {
        "id": "UTILS_FVT_INSTALL_OS_V007",
        "title": "Verify custom ISO with Kickstart created",
    },
    "install_os_kickstart_generated": {
        "id": "UTILS_FVT_INSTALL_OS_V008",
        "title": "Verify kickstart.ks file generated",
    },

    # ══════════════════════════════════════════════════════════════════════════
    # CLEANUP_LOGS SCENARIO
    # ══════════════════════════════════════════════════════════════════════════
    "deploy_cleanup_logs": {
        "id": "UTILS_FVT_CLEANUP_LOGS_E001",
        "title": "Deploy utils.yml (cleanup_logs)",
    },
    "cleanup_logs_old_bundles_removed": {
        "id": "UTILS_FVT_CLEANUP_LOGS_V001",
        "title": "Verify old log bundles removed (retention-based)",
    },
    "cleanup_logs_empty_dirs_removed": {
        "id": "UTILS_FVT_CLEANUP_LOGS_V002",
        "title": "Verify empty log directories removed",
    },
    "cleanup_logs_temp_dirs_cleaned": {
        "id": "UTILS_FVT_CLEANUP_LOGS_V003",
        "title": "Verify temp directories (k8s, slurm) cleaned",
    },

    # ══════════════════════════════════════════════════════════════════════════
    # CLEANUP_INSTALL_OS SCENARIO
    # ══════════════════════════════════════════════════════════════════════════
    "deploy_cleanup_install_os": {
        "id": "UTILS_FVT_CLEANUP_INSTALL_OS_E001",
        "title": "Deploy utils.yml (cleanup_install_os)",
    },
    "cleanup_install_os_temp_iso_removed": {
        "id": "UTILS_FVT_CLEANUP_INSTALL_OS_V001",
        "title": "Verify /tmp/install_os directory removed",
    },
    "cleanup_install_os_nfs_unmounted": {
        "id": "UTILS_FVT_CLEANUP_INSTALL_OS_V002",
        "title": "Verify /tmp/install_os_nfs unmounted and removed",
    },
    "cleanup_install_os_credentials_removed": {
        "id": "UTILS_FVT_CLEANUP_INSTALL_OS_V003",
        "title": "Verify credential files removed (when cleanup_credentials=true)",
    },

    # ══════════════════════════════════════════════════════════════════════════
    # CLEANUP (COMBINED) SCENARIO
    # ══════════════════════════════════════════════════════════════════════════
    "deploy_cleanup": {
        "id": "UTILS_FVT_CLEANUP_E001",
        "title": "Deploy utils.yml (cleanup - combined)",
    },
    "cleanup_all_logs_cleaned": {
        "id": "UTILS_FVT_CLEANUP_V001",
        "title": "Verify all log collection artifacts cleaned",
    },
    "cleanup_all_install_os_cleaned": {
        "id": "UTILS_FVT_CLEANUP_V002",
        "title": "Verify all install_os artifacts cleaned",
    },

    # ══════════════════════════════════════════════════════════════════════════
    # NEGATIVE TEST CASES - COLLECT
    # ══════════════════════════════════════════════════════════════════════════
    "collect_missing_input_fails": {
        "id": "UTILS_FVT_COLLECT_NEG001",
        "title": "Verify collect.yml fails when input file missing",
    },
    "collect_invalid_yaml_fails": {
        "id": "UTILS_FVT_COLLECT_NEG002",
        "title": "Verify collect.yml fails with invalid YAML input",
    },
    "collect_empty_groups_succeeds": {
        "id": "UTILS_FVT_COLLECT_NEG003",
        "title": "Verify collect.yml succeeds with empty functional groups",
    },

    # ══════════════════════════════════════════════════════════════════════════
    # NEGATIVE TEST CASES - INSTALL_OS
    # ══════════════════════════════════════════════════════════════════════════
    "install_os_missing_config_fails": {
        "id": "UTILS_FVT_INSTALL_OS_NEG001",
        "title": "Verify install_os.yml fails when config file missing",
    },
    "install_os_invalid_config_params_fails": {
        "id": "UTILS_FVT_INSTALL_OS_NEG002",
        "title": "Verify install_os.yml fails with invalid configuration parameters",
    },
    "install_os_missing_iso_path_fails": {
        "id": "UTILS_FVT_INSTALL_OS_NEG003",
        "title": "Verify install_os.yml fails when source ISO path missing",
    },
    "install_os_missing_bmc_ip_fails": {
        "id": "UTILS_FVT_INSTALL_OS_NEG004",
        "title": "Verify install_os.yml fails when BMC IP missing for deploy",
    },
}

# Legacy ID mapping for backward compatibility with existing reports
LEGACY_ID_MAP = {
    "TC_PC_001": "UTILS_FVT_PRECHECK_V001",
    "TC_PC_002": "UTILS_FVT_PRECHECK_V002",
    "TC_PC_003": "UTILS_FVT_PRECHECK_V003",
    "TC_PC_004": "UTILS_FVT_PRECHECK_V004",
    "TC_PC_005": "UTILS_FVT_PRECHECK_V005",
    "TC_CL_001": "UTILS_FVT_COLLECT_E001",
    "TC_CL_002": "UTILS_FVT_COLLECT_E002",
    "TC_CL_003": "UTILS_FVT_COLLECT_E003",
    "TC_CL_004": "UTILS_FVT_COLLECT_E004",
    "TC_CL_010": "UTILS_FVT_COLLECT_V001",
    "TC_CL_011": "UTILS_FVT_COLLECT_V002",
    "TC_CL_012": "UTILS_FVT_COLLECT_V003",
    "TC_CL_020": "UTILS_FVT_COLLECT_V004",
    "TC_CL_021": "UTILS_FVT_COLLECT_V005",
    "TC_CL_022": "UTILS_FVT_COLLECT_V006",
    "TC_CL_023": "UTILS_FVT_COLLECT_V007",
    "TC_CL_024": "UTILS_FVT_COLLECT_V008",
    "TC_CL_025": "UTILS_FVT_COLLECT_V009",
    "TC_CL_030": "UTILS_FVT_COLLECT_V010",
    "TC_CL_031": "UTILS_FVT_COLLECT_V011",
    "TC_CL_032": "UTILS_FVT_COLLECT_V012",
    "TC_IO_001": "UTILS_FVT_INSTALL_OS_E001",
    "TC_IO_002": "UTILS_FVT_INSTALL_OS_E002",
    "TC_IO_003": "UTILS_FVT_INSTALL_OS_E003",
    "TC_IO_004": "UTILS_FVT_INSTALL_OS_E004",
    "TC_IO_005": "UTILS_FVT_INSTALL_OS_E005",
    "TC_IO_010": "UTILS_FVT_INSTALL_OS_V001",
    "TC_IO_011": "UTILS_FVT_INSTALL_OS_V002",
    "TC_IO_012": "UTILS_FVT_INSTALL_OS_V003",
    "TC_IO_020": "UTILS_FVT_INSTALL_OS_V004",
    "TC_IO_021": "UTILS_FVT_INSTALL_OS_V005",
    "TC_IO_022": "UTILS_FVT_INSTALL_OS_V006",
    "TC_IO_030": "UTILS_FVT_INSTALL_OS_V007",
    "TC_IO_031": "UTILS_FVT_INSTALL_OS_V008",
    "TC_NEG_001": "UTILS_FVT_COLLECT_NEG001",
    "TC_NEG_002": "UTILS_FVT_COLLECT_NEG002",
    "TC_NEG_003": "UTILS_FVT_COLLECT_NEG003",
    "TC_NEG_020": "UTILS_FVT_INSTALL_OS_NEG001",
    "TC_NEG_021": "UTILS_FVT_INSTALL_OS_NEG002",
    "TC_NEG_022": "UTILS_FVT_INSTALL_OS_NEG003",
    "TC_NEG_023": "UTILS_FVT_INSTALL_OS_NEG004",
}
