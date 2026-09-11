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
Discovery — Test Case Registry

Central registry mapping every test to its TC ID and title.
Test files reference ``TEST_CASES["key"]`` to get a consistent
test-case identifier and display name.

Usage in test files::

    from library.vars.test_case_vars import TEST_CASES as TC

    tc = TC["deploy_precheck"]
    tl = TestLogger(tc["title"], tc["id"])
"""

from typing import Dict

TEST_CASES: Dict[str, Dict[str, str]] = {
    # ── Precheck ───────────────────────────────────────────────────────────
    "deploy_precheck": {
        "id": "DISCOVERY_FVT_PRECHECK_E001",
        "title": "Deploy discovery.yml --tags precheck",
    },

    # ── Validate ───────────────────────────────────────────────────────────
    "deploy_validate": {
        "id": "DISCOVERY_FVT_VALIDATE_E001",
        "title": "Deploy discovery.yml --tags validate",
    },
    "input_config_exists": {
        "id": "DISCOVERY_FVT_VALIDATE_V001",
        "title": "Verify discovery_config.yml exists on target",
    },
    "network_spec_exists": {
        "id": "DISCOVERY_FVT_VALIDATE_V002",
        "title": "Verify network_spec.yml exists on target",
    },
    "credentials_present": {
        "id": "DISCOVERY_FVT_VALIDATE_V003",
        "title": "Verify credentials file present on target",
    },

    # ── Credentials ────────────────────────────────────────────────────────
    "deploy_credentials": {
        "id": "DISCOVERY_FVT_CREDENTIALS_E001",
        "title": "Deploy discovery.yml --tags credentials",
    },

    # ── Execute ─────────────────────────────────────────────────────────────
    "deploy_execute": {
        "id": "DISCOVERY_FVT_EXECUTE_E001",
        "title": "Deploy discovery.yml --tags execute (OME discovery)",
    },
    "output_dir_exists": {
        "id": "DISCOVERY_FVT_EXECUTE_V001",
        "title": "Verify output directory exists",
    },
    "pxe_mapping_created": {
        "id": "DISCOVERY_FVT_EXECUTE_V002",
        "title": "Verify PXE mapping CSV created",
    },
    "pxe_mapping_columns": {
        "id": "DISCOVERY_FVT_EXECUTE_V003",
        "title": "Verify PXE mapping CSV has required columns",
    },
    "pxe_mapping_has_rows": {
        "id": "DISCOVERY_FVT_EXECUTE_V004",
        "title": "Verify PXE mapping CSV has data rows",
    },
    "pxe_mapping_symlink": {
        "id": "DISCOVERY_FVT_EXECUTE_V005",
        "title": "Verify PXE mapping symlink points to latest",
    },
    "discovery_report_created": {
        "id": "DISCOVERY_FVT_EXECUTE_V006",
        "title": "Verify discovery report CSV created",
    },

    # ── Discovery (Full Run) ────────────────────────────────────────────────
    "deploy_discovery": {
        "id": "DISCOVERY_FVT_DISCOVERY_E001",
        "title": "Deploy discovery.yml (full run)",
    },

    # ── Cleanup ────────────────────────────────────────────────────────────
    "deploy_cleanup": {
        "id": "DISCOVERY_FVT_CLEANUP_E001",
        "title": "Deploy discovery.yml --tags cleanup",
    },
}
