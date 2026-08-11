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
Repo Manager — Test Case Registry.

Central registry mapping every test to its TC ID and title.
Test files reference ``TEST_CASES["key"]`` to get a consistent
test-case identifier and display name.

Usage in test files::

    from library.vars import TEST_CASES as TC

    tc = TC["deploy_validate"]
    tl = TestLogger(tc["title"], tc["id"])
"""

TEST_CASES = {
    # ── Deploy (one per scenario) ─────────────────────────────────────────
    "deploy_full": {
        "id": "TC_RM_000",
        "title": "Deploy repo_manager (default: validate + deploy + download + status)",
    },
    "deploy_validate": {
        "id": "TC_VL_000",
        "title": "Deploy repo_manager (validate)",
    },
    "deploy_deploy": {
        "id": "TC_DP_000",
        "title": "Deploy repo_manager (deploy)",
    },
    "deploy_download": {
        "id": "TC_DL_000",
        "title": "Deploy repo_manager (download)",
    },
    "deploy_status": {
        "id": "TC_ST_000",
        "title": "Deploy repo_manager (status)",
    },
    "deploy_cleanup": {
        "id": "TC_CL_000",
        "title": "Deploy repo_manager (cleanup)",
    },

    # ── Full (repo_manager) ───────────────────────────────────────────────
    "rm_pulp_container_running": {
        "id": "TC_RM_002",
        "title": "Verify Pulp container is running",
    },
    "rm_pulp_healthy": {
        "id": "TC_RM_003",
        "title": "Verify Pulp service is healthy and responding",
    },
    "rm_pulp_port_listening": {
        "id": "TC_RM_004",
        "title": "Verify Pulp port (2225) is listening",
    },
    "rm_pulp_cli_configured": {
        "id": "TC_RM_005",
        "title": "Verify Pulp CLI is installed and configured",
    },
    "rm_pulp_api_endpoint": {
        "id": "TC_RM_006",
        "title": "Verify Pulp API endpoint is reachable",
    },
    "rm_pulp_certs": {
        "id": "TC_RM_007",
        "title": "Verify Pulp SSL certificates present",
    },
    "rm_pulp_directories": {
        "id": "TC_RM_008",
        "title": "Verify Pulp data directories exist",
    },
    "rm_repo_status_file": {
        "id": "TC_RM_009",
        "title": "Verify repo_status.yml exists and reports success",
    },
    "rm_repos_synced": {
        "id": "TC_RM_010",
        "title": "Verify repositories are synced in Pulp",
    },

    # ── Validate ──────────────────────────────────────────────────────────
    "input_config_exists": {
        "id": "TC_VL_002",
        "title": "Verify repo_manager_config.yml exists on target",
    },
    "credentials_present": {
        "id": "TC_VL_003",
        "title": "Verify credentials file is present",
    },
    "endpoint_config_exists": {
        "id": "TC_VL_004",
        "title": "Verify repo_manager_endpoint_config.yml exists on target",
    },
    "software_config_exists": {
        "id": "TC_VL_005",
        "title": "Verify software_config.json exists on target",
    },

    # ── Deploy ────────────────────────────────────────────────────────────
    "dp_pulp_container_running": {
        "id": "TC_DP_002",
        "title": "Verify Pulp container running after deploy",
    },
    "dp_pulp_healthy": {
        "id": "TC_DP_003",
        "title": "Verify Pulp healthy after deploy (database connected)",
    },
    "dp_pulp_port_listening": {
        "id": "TC_DP_004",
        "title": "Verify Pulp port listening after deploy",
    },
    "dp_pulp_cli_configured": {
        "id": "TC_DP_005",
        "title": "Verify Pulp CLI configured after deploy (binary + cli.toml)",
    },
    "dp_pulp_api_endpoint": {
        "id": "TC_DP_006",
        "title": "Verify Pulp API endpoint reachable after deploy",
    },
    "dp_pulp_quadlet_exists": {
        "id": "TC_DP_007",
        "title": "Verify Pulp quadlet/systemd unit file exists",
    },
    "dp_pulp_certs": {
        "id": "TC_DP_008",
        "title": "Verify Pulp SSL certificates present (HTTPS mode)",
    },
    "dp_pulp_directories": {
        "id": "TC_DP_009",
        "title": "Verify Pulp data directories exist",
    },

    # ── Repo Operations — Download ────────────────────────────────────────
    "software_config_valid": {
        "id": "TC_DL_002",
        "title": "Verify software_config.json has valid JSON with required fields",
    },
    "dl_repos_synced": {
        "id": "TC_DL_003",
        "title": "Verify repos are synced in Pulp after download",
    },
    "dl_repo_status_generated": {
        "id": "TC_DL_004",
        "title": "Verify repo_status.yml generated after download",
    },
    "dl_repo_status_success": {
        "id": "TC_DL_005",
        "title": "Verify repo_status.yml reports success",
    },

    # ── Repo Operations — Status ──────────────────────────────────────────
    "st_pulp_running": {
        "id": "TC_ST_002",
        "title": "Verify Pulp container running (prerequisite for status)",
    },
    "st_repo_status_exists": {
        "id": "TC_ST_003",
        "title": "Verify repo_status.yml exists",
    },
    "st_repo_status_content": {
        "id": "TC_ST_004",
        "title": "Verify repo_status.yml has expected content",
    },

    # ── Cleanup ───────────────────────────────────────────────────────────
    "pulp_removed": {
        "id": "TC_CL_002",
        "title": "Verify Pulp container removed after cleanup",
    },
    "containers_removed": {
        "id": "TC_CL_003",
        "title": "Verify Pulp container fully removed (not even stopped)",
    },
    "pulp_image_removed": {
        "id": "TC_CL_004",
        "title": "Verify Pulp container image removed after cleanup",
    },
    "services_removed": {
        "id": "TC_CL_005",
        "title": "Verify Pulp systemd services stopped after cleanup",
    },
    "pulp_quadlet_removed": {
        "id": "TC_CL_006",
        "title": "Verify Pulp quadlet/systemd file removed after cleanup",
    },
    "pulp_data_removed": {
        "id": "TC_CL_007",
        "title": "Verify Pulp data directories removed after cleanup",
    },
    "pulp_logs_cleaned": {
        "id": "TC_CL_008",
        "title": "Verify Pulp log directories cleaned after cleanup",
    },
}
