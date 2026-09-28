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
Discovery — Test Messages

All test names, log messages, and assertion messages
for the discovery FVT automation.
"""

from typing import Dict

# =============================================================================
TEST_NAMES: Dict[str, str] = {
    # Deploy (full run)
    "deploy_playbook": (
        "Deploy: discovery.yml -e discovery_mechanism={mechanism}"
    ),

    # Deploy (per-tag)
    "deploy_precheck": (
        "Deploy: discovery.yml --tags precheck"
    ),
    "deploy_validate": (
        "Deploy: discovery.yml --tags validate"
    ),
    "deploy_credentials": (
        "Deploy: discovery.yml --tags credentials"
    ),
    "deploy_execute": (
        "Deploy: discovery.yml --tags execute"
    ),
    "deploy_cleanup": (
        "Deploy: discovery.yml --tags cleanup (full cleanup)"
    ),
    "deploy_cleanup_preserve_credentials": (
        "Deploy: discovery.yml --tags cleanup -e cleanup_credentials=false"
    ),
    "deploy_cleanup_preserve_logs": (
        "Deploy: discovery.yml --tags cleanup -e cleanup_logs=false"
    ),
    "deploy_cleanup_idempotent": (
        "Deploy: discovery.yml --tags cleanup (idempotency test)"
    ),

    # Validate
    "input_config_exists": (
        "Verify discovery_config.yml exists on target"
    ),
    "network_spec_exists": (
        "Verify network_spec.yml exists on target"
    ),
    "credentials_present": (
        "Verify credentials file is present on target"
    ),

    # Discovery output
    "pxe_mapping_created": (
        "Verify bmc_pxe_mapping_file.csv created"
    ),
    "pxe_mapping_columns": (
        "Verify PXE mapping CSV has required columns"
    ),
    "pxe_mapping_has_rows": (
        "Verify PXE mapping CSV contains data rows"
    ),
    "discovery_report_created": (
        "Verify bmc_discovery_report.csv created"
    ),
    "pxe_mapping_symlink": (
        "Verify bmc_pxe_mapping_file.csv symlink points to latest"
    ),
    "output_dir_exists": (
        "Verify discovery output directory exists"
    ),

    # Clone / sync
    "clone_status": (
        "Verify repository is cloned and synced on target"
    ),

    # Cleanup
    "output_dir_removed": (
        "Verify output directory is empty after cleanup"
    ),
    "credentials_removed": (
        "Verify credentials file is removed after cleanup"
    ),
    "credentials_preserved": (
        "Verify credentials file is preserved when cleanup_credentials=false"
    ),
    "pxe_mapping_files_removed": (
        "Verify PXE mapping files are removed after cleanup"
    ),
    "discovery_report_files_removed": (
        "Verify discovery report files are removed after cleanup"
    ),
    "status_files_removed": (
        "Verify discovery status files are removed after cleanup"
    ),
    "log_files_removed": (
        "Verify log files are removed after cleanup"
    ),
    "log_files_preserved": (
        "Verify log files are preserved when cleanup_logs=false"
    ),
}

# =============================================================================
TEST_LOG_MSGS: Dict[str, str] = {
    # Input validation
    "input_config_ok": "discovery_config.yml present",
    "input_config_missing": "discovery_config.yml not found",
    "network_spec_ok": "network_spec.yml present",
    "network_spec_missing": "network_spec.yml not found",
    "credentials_present_ok": "Credentials file present",
    "credentials_missing": "Credentials file missing",

    # Output validation
    "pxe_mapping_ok": "PXE mapping file created successfully",
    "pxe_mapping_missing": "PXE mapping file not found",
    "pxe_mapping_columns_ok": (
        "All required columns present: {columns}"
    ),
    "pxe_mapping_columns_missing": (
        "Missing required columns: {missing}"
    ),
    "pxe_mapping_rows_ok": "{count} data rows found",
    "pxe_mapping_rows_empty": "PXE mapping file has no data rows",
    "discovery_report_ok": "Discovery report created",
    "discovery_report_missing": "Discovery report not found",
    "pxe_symlink_ok": "Symlink points to latest mapping file",
    "pxe_symlink_missing": "Symlink not found or broken",
    "output_dir_ok": "Output directory exists",
    "output_dir_missing": "Output directory not found",

    # Deploy
    "playbook_success": (
        "Playbook completed (rc=0, duration={duration:.1f}s)"
    ),
    "playbook_failed": (
        "Playbook failed (rc={rc}, duration={duration:.1f}s)"
    ),

    # Clone
    "clone_ok": "Repository cloned and synced",
    "clone_failed": "Repository clone check failed",

    # Cleanup
    "output_dir_removed_ok": "Output directory cleaned successfully",
    "output_dir_not_empty": "Output directory not empty after cleanup",
    "credentials_removed_ok": "Credentials file removed successfully",
    "credentials_not_removed": "Credentials file still exists after cleanup",
    "credentials_preserved_ok": "Credentials file preserved as expected",
    "credentials_not_preserved": "Credentials file was removed when it should have been preserved",
    "pxe_mapping_files_removed_ok": "PXE mapping files removed successfully",
    "pxe_mapping_files_not_removed": "PXE mapping files still exist after cleanup",
    "discovery_report_files_removed_ok": "Discovery report files removed successfully",
    "discovery_report_files_not_removed": "Discovery report files still exist after cleanup",
    "status_files_removed_ok": "Discovery status files removed successfully",
    "status_files_not_removed": "Discovery status files still exist after cleanup",
    "log_files_removed_ok": "Log files removed successfully",
    "log_files_not_removed": "Log files still exist after cleanup",
    "log_files_preserved_ok": "Log files preserved as expected",
    "log_files_not_preserved": "Log files were removed when they should have been preserved",
}

# =============================================================================
_BORDER = "\u2550" * 74

TEST_ASSERT_MSGS: Dict[str, str] = {
    "playbook_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 PLAYBOOK EXECUTION FAILED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Playbook: {playbook}\n"
        "\u2551 Exit code: {rc}\n"
        "\u2551 Duration: {duration:.1f}s\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check the playbook output above\n"
        "\u2551   2. Verify discovery_config.yml settings\n"
        "\u2551   3. Run with increased verbosity: -vvv\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),

    "input_config_missing": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 INPUT CONFIGURATION MISSING\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 File: discovery_config.yml\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Copy template: src/discovery/input/discovery_config.yml\n"
        "\u2551   2. Edit with your OME IP and settings\n"
        "\u2551   3. Place in /opt/omnia/discovery/input/<project>/\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),

    "network_spec_missing": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 NETWORK SPECIFICATION MISSING\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 File: network_spec.yml\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Copy template: src/discovery/input/network_spec.yml\n"
        "\u2551   2. Edit with your network topology\n"
        "\u2551   3. Place in /opt/omnia/discovery/input/<project>/\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),

    "pxe_mapping_missing": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 PXE MAPPING FILE NOT CREATED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Expected: bmc_pxe_mapping_file_<timestamp>.csv\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check discovery playbook ran successfully\n"
        "\u2551   2. Verify OME connectivity and credentials\n"
        "\u2551   3. Re-run: ansible-playbook discovery.yml\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
}
