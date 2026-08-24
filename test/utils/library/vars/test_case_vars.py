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
Utils Domain — Test Case Registry.

Central registry mapping every test to its TC ID and title.
Test files reference ``TEST_CASES["key"]`` to get a consistent
test-case identifier and display name.

Usage in test files::

    from library.vars.test_case_vars import TEST_CASES as TC

    tc = TC["deploy_collect"]
    tl = TestLogger(tc["title"], tc["id"])
"""

TEST_CASES = {
    # ══════════════════════════════════════════════════════════════════════════
    # PRECHECK SCENARIO
    # ══════════════════════════════════════════════════════════════════════════
    "target_connectivity": {
        "id": "TC_PC_001",
        "title": "Verify target host connectivity and SSH",
    },
    "env_vars_present": {
        "id": "TC_PC_002",
        "title": "Verify OMNIA env vars present on target",
    },
    "hostname_domain": {
        "id": "TC_PC_003",
        "title": "Verify hostname and domain match omnia.env",
    },
    "admin_ip_assigned": {
        "id": "TC_PC_004",
        "title": "Verify admin IP assigned to local interface",
    },
    "omnia_setup": {
        "id": "TC_PC_005",
        "title": "Verify omnia.sh setup completed on target",
    },

    # ══════════════════════════════════════════════════════════════════════════
    # COLLECT SCENARIO — Deploy Tests
    # ══════════════════════════════════════════════════════════════════════════
    "deploy_collect_setup": {
        "id": "TC_CL_001",
        "title": "Deploy collect.yml (setup stage)",
    },
    "deploy_collect_prepare": {
        "id": "TC_CL_002",
        "title": "Deploy collect.yml (prepare stage)",
    },
    "deploy_collect_bundle": {
        "id": "TC_CL_003",
        "title": "Deploy collect.yml (bundle stage)",
    },
    "deploy_collect_full": {
        "id": "TC_CL_004",
        "title": "Deploy collect.yml (full execution)",
    },

    # ══════════════════════════════════════════════════════════════════════════
    # COLLECT SCENARIO — Verification Tests
    # ══════════════════════════════════════════════════════════════════════════
    "collect_input_file_exists": {
        "id": "TC_CL_010",
        "title": "Verify collect_pxe.yml input file exists on target",
    },
    "collect_input_file_valid": {
        "id": "TC_CL_011",
        "title": "Verify collect_pxe.yml has valid YAML structure",
    },
    "collect_functional_groups_valid": {
        "id": "TC_CL_012",
        "title": "Verify collect_pxe.yml contains valid functional groups",
    },
    "collect_output_dir_exists": {
        "id": "TC_CL_020",
        "title": "Verify log collection output directory exists",
    },
    "collect_bundle_created": {
        "id": "TC_CL_021",
        "title": "Verify log bundle tar.gz file created",
    },
    "collect_metadata_exists": {
        "id": "TC_CL_022",
        "title": "Verify metadata.json file exists",
    },
    "collect_metadata_valid": {
        "id": "TC_CL_023",
        "title": "Verify metadata.json has valid structure",
    },
    "collect_metadata_sha256": {
        "id": "TC_CL_024",
        "title": "Verify metadata.json contains SHA256 checksum",
    },
    "collect_bundle_contents": {
        "id": "TC_CL_025",
        "title": "Verify log bundle contains expected directories",
    },
    "collect_env_vars_loaded": {
        "id": "TC_CL_030",
        "title": "Verify OMNIA_DATA_PATH loaded from environment",
    },
    "collect_project_name_loaded": {
        "id": "TC_CL_031",
        "title": "Verify OMNIA_PROJECT_NAME loaded from environment",
    },

    # ══════════════════════════════════════════════════════════════════════════
    # SET_PXE_BOOT SCENARIO — Deploy Tests
    # ══════════════════════════════════════════════════════════════════════════
    "deploy_pxe_credentials": {
        "id": "TC_PX_001",
        "title": "Deploy set_pxe_boot.yml (credentials tag)",
    },
    "deploy_pxe_boot": {
        "id": "TC_PX_002",
        "title": "Deploy set_pxe_boot.yml (pxe_boot tag)",
    },
    "deploy_pxe_full": {
        "id": "TC_PX_003",
        "title": "Deploy set_pxe_boot.yml (full execution)",
    },

    # ══════════════════════════════════════════════════════════════════════════
    # SET_PXE_BOOT SCENARIO — Verification Tests
    # ══════════════════════════════════════════════════════════════════════════
    "pxe_config_file_exists": {
        "id": "TC_PX_010",
        "title": "Verify set_pxe_boot_config.yml exists on target",
    },
    "pxe_config_valid": {
        "id": "TC_PX_011",
        "title": "Verify set_pxe_boot_config.yml has valid structure",
    },
    "pxe_inventory_file_exists": {
        "id": "TC_PX_012",
        "title": "Verify set_pxe_boot.ini inventory file exists",
    },
    "pxe_inventory_valid": {
        "id": "TC_PX_013",
        "title": "Verify set_pxe_boot.ini has valid INI format",
    },
    "pxe_credentials_file_exists": {
        "id": "TC_PX_014",
        "title": "Verify set_pxe_boot_credentials.yml exists",
    },
    "pxe_output_dir_exists": {
        "id": "TC_PX_020",
        "title": "Verify PXE boot output directory exists",
    },
    "pxe_failed_nodes_file": {
        "id": "TC_PX_021",
        "title": "Verify failed_nodes.json output file created",
    },
    "pxe_failed_nodes_valid": {
        "id": "TC_PX_022",
        "title": "Verify failed_nodes.json has valid structure",
    },
    "pxe_phone_home_enabled": {
        "id": "TC_PX_030",
        "title": "Verify phone-home verification is enabled",
    },
    "pxe_phone_home_config": {
        "id": "TC_PX_031",
        "title": "Verify phone-home configuration values",
    },

    # ══════════════════════════════════════════════════════════════════════════
    # INSTALL_OS SCENARIO — Deploy Tests
    # ══════════════════════════════════════════════════════════════════════════
    "deploy_install_os_validate": {
        "id": "TC_IO_001",
        "title": "Deploy install_os.yml (validate parameters)",
    },
    "deploy_install_os_fetch": {
        "id": "TC_IO_002",
        "title": "Deploy install_os.yml (fetch ISO)",
    },
    "deploy_install_os_create": {
        "id": "TC_IO_003",
        "title": "Deploy install_os.yml (create custom ISO)",
    },
    "deploy_install_os_deliver": {
        "id": "TC_IO_004",
        "title": "Deploy install_os.yml (deliver ISO via iDRAC)",
    },
    "deploy_install_os_full": {
        "id": "TC_IO_005",
        "title": "Deploy install_os.yml (full execution)",
    },

    # ══════════════════════════════════════════════════════════════════════════
    # INSTALL_OS SCENARIO — Verification Tests
    # ══════════════════════════════════════════════════════════════════════════
    "install_os_config_file_exists": {
        "id": "TC_IO_010",
        "title": "Verify iso_config.yml exists on target",
    },
    "install_os_config_valid": {
        "id": "TC_IO_011",
        "title": "Verify iso_config.yml has valid structure",
    },
    "install_os_credentials_file_exists": {
        "id": "TC_IO_012",
        "title": "Verify os_install_credentials.yml exists",
    },
    "install_os_output_dir_exists": {
        "id": "TC_IO_020",
        "title": "Verify ISO output directory exists",
    },
    "install_os_custom_iso_created": {
        "id": "TC_IO_021",
        "title": "Verify custom ISO with Kickstart created",
    },
    "install_os_iso_checksum_valid": {
        "id": "TC_IO_022",
        "title": "Verify ISO checksum matches expected value",
    },
    "install_os_kickstart_injected": {
        "id": "TC_IO_023",
        "title": "Verify Kickstart configuration injected into ISO",
    },

    # ══════════════════════════════════════════════════════════════════════════
    # NEGATIVE TEST CASES
    # ══════════════════════════════════════════════════════════════════════════
    "collect_missing_input_fails": {
        "id": "TC_NEG_001",
        "title": "Verify collect.yml fails when input file missing",
    },
    "collect_invalid_yaml_fails": {
        "id": "TC_NEG_002",
        "title": "Verify collect.yml fails with invalid YAML input",
    },
    "collect_empty_groups_succeeds": {
        "id": "TC_NEG_003",
        "title": "Verify collect.yml succeeds with empty functional groups",
    },
    "pxe_missing_inventory_fails": {
        "id": "TC_NEG_010",
        "title": "Verify set_pxe_boot.yml fails without inventory",
    },
    "pxe_invalid_bmc_ip_fails": {
        "id": "TC_NEG_011",
        "title": "Verify set_pxe_boot.yml fails with invalid BMC IP",
    },
    "install_os_missing_iso_fails": {
        "id": "TC_NEG_020",
        "title": "Verify install_os.yml fails when ISO path missing",
    },
    "install_os_invalid_params_fails": {
        "id": "TC_NEG_021",
        "title": "Verify install_os.yml fails with invalid parameters",
    },
}
