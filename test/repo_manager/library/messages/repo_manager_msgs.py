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
Repo Manager — Test Messages

All test names, log messages, and assertion messages
for the repo_manager FVT automation.

Reference: src/repo_manager/playbooks/repo_manager.yml
           src/repo_manager/roles/deploy_pulp/
           src/repo_manager/playbooks/cleanup/cleanup_pulp.yml
"""

# =============================================================================
# TEST NAMES (displayed in test output header)
# =============================================================================

TEST_NAMES = {
    # Deploy
    "deploy_playbook": (
        "Deploy: repo_manager.yml --tags {tag}"
    ),
    "deploy_playbook_full": (
        "Deploy: repo_manager.yml (default: validate + deploy + download + status)"
    ),

    # Pulp container
    "pulp_container_running": (
        "Verify Pulp container is running"
    ),
    "pulp_healthy": (
        "Verify Pulp service is healthy and responding"
    ),
    "pulp_port_listening": (
        "Verify Pulp port (2225) is listening"
    ),
    "pulp_cli_configured": (
        "Verify Pulp CLI is installed and configured"
    ),
    "pulp_api_endpoint": (
        "Verify Pulp API endpoint is reachable"
    ),
    "pulp_quadlet_exists": (
        "Verify Pulp quadlet/systemd unit file exists"
    ),
    "pulp_certs": (
        "Verify Pulp SSL certificates exist"
    ),
    "pulp_directories": (
        "Verify Pulp data directories exist"
    ),

    # Input files
    "input_config_exists": (
        "Verify repo_manager_config.yml exists on target"
    ),
    "credentials_present": (
        "Verify credentials file is synced to target"
    ),
    "endpoint_config_exists": (
        "Verify repo_manager_endpoint_config.yml exists on target"
    ),
    "software_config_exists": (
        "Verify software_config.json exists on target"
    ),
    "software_config_valid": (
        "Verify software_config.json has valid JSON with required fields"
    ),

    # Repo status
    "repo_status_generated": (
        "Verify repo_status.yml exists"
    ),
    "repo_status_success": (
        "Verify repo_status.yml reports success"
    ),

    # Repos
    "repos_synced": (
        "Verify all configured repositories are synced"
    ),

    # Cleanup
    "containers_removed": (
        "Verify Pulp container removed after cleanup"
    ),
    "pulp_removed": (
        "Verify Pulp service removed after cleanup"
    ),
    "pulp_data_removed": (
        "Verify Pulp data directories removed after cleanup"
    ),
    "pulp_image_removed": (
        "Verify Pulp container image removed after cleanup"
    ),
    "pulp_quadlet_removed": (
        "Verify Pulp quadlet/systemd file removed after cleanup"
    ),
    "services_removed": (
        "Verify Pulp systemd services stopped after cleanup"
    ),
    "pulp_logs_cleaned": (
        "Verify Pulp log directories cleaned after cleanup"
    ),
    "credentials_removed": (
        "Verify credential files removed after cleanup"
    ),
}

# =============================================================================
# TEST LOG MESSAGES
# =============================================================================

TEST_LOG_MSGS = {
    # Container messages
    "container_running": "Container {container} is running",
    "container_not_running": (
        "Container {container} is NOT running"
    ),

    # Pulp health
    "pulp_healthy_ok": (
        "Pulp service is healthy and responding"
    ),
    "pulp_not_healthy": (
        "Pulp service is NOT healthy or not responding"
    ),

    # Pulp port
    "pulp_port_ok": (
        "Pulp port {port} is listening"
    ),
    "pulp_port_not_listening": (
        "Pulp port {port} is NOT listening"
    ),

    # Pulp CLI
    "pulp_cli_ok": (
        "Pulp CLI is installed and configured"
    ),
    "pulp_cli_missing": (
        "Pulp CLI is NOT installed or not configured"
    ),

    # Pulp API
    "pulp_api_ok": (
        "Pulp API endpoint reachable via {protocol}"
    ),
    "pulp_api_not_reachable": (
        "Pulp API endpoint is NOT reachable"
    ),

    # Pulp quadlet
    "pulp_quadlet_ok": (
        "Pulp quadlet/systemd unit file exists"
    ),
    "pulp_quadlet_missing": (
        "Pulp quadlet/systemd unit file NOT found"
    ),

    # Pulp certs
    "pulp_certs_ok": (
        "Pulp SSL certificates present"
    ),
    "pulp_certs_missing": (
        "Pulp SSL certificate(s) NOT found"
    ),

    # Pulp directories
    "pulp_dirs_ok": (
        "All required Pulp directories exist"
    ),
    "pulp_dirs_missing": (
        "Some required Pulp directories are missing"
    ),

    # Input config
    "input_config_ok": "repo_manager_config.yml present",
    "input_config_missing": "repo_manager_config.yml not found",

    # Credentials
    "credentials_present_ok": "Credentials file present",
    "credentials_missing": "Credentials file missing",

    # Endpoint config
    "endpoint_config_ok": (
        "repo_manager_endpoint_config.yml present"
    ),
    "endpoint_config_missing": (
        "repo_manager_endpoint_config.yml not found"
    ),

    # Software config
    "software_config_ok": "software_config.json present",
    "software_config_missing": "software_config.json not found",
    "software_config_valid_ok": "software_config.json is valid",
    "software_config_invalid": "software_config.json is invalid",

    # Repo status
    "repo_status_ok": (
        "repo_status.yml exists and overall_status is success"
    ),
    "repo_status_failed": (
        "repo_status.yml check failed"
    ),
    "repo_status_not_found": (
        "repo_status.yml not found (deploy/download tag not run yet)"
    ),

    # Repos synced
    "repos_synced_ok": (
        "All {count} configured repositories are synced"
    ),
    "repos_missing": (
        "{count} repository(ies) not synced"
    ),

    # Deploy
    "playbook_success": (
        "Playbook completed (rc=0, duration={duration:.1f}s)"
    ),
    "playbook_failed": (
        "Playbook failed (rc={rc}, duration={duration:.1f}s)"
    ),

    # Services
    "services_active_ok": "All systemd services active",
    "services_inactive": "{count} service(s) not active",

    # Cleanup
    "containers_removed_ok": (
        "Pulp container removed successfully"
    ),
    "pulp_removed_ok": (
        "Pulp service removed successfully"
    ),
    "pulp_data_removed_ok": (
        "Pulp data directories removed successfully"
    ),
    "pulp_image_removed_ok": (
        "Pulp container image removed successfully"
    ),
    "pulp_image_still_exists": (
        "Pulp container image still present"
    ),
    "pulp_quadlet_removed_ok": (
        "Pulp quadlet/systemd file removed successfully"
    ),
    "services_removed_ok": (
        "All systemd services stopped and removed"
    ),
    "pulp_logs_cleaned_ok": (
        "Pulp log directories cleaned successfully"
    ),
    "pulp_logs_not_cleaned": (
        "Pulp log directories still contain files"
    ),
    "credentials_removed_ok": (
        "Credential files removed successfully"
    ),
    "credentials_still_exist": (
        "Credential files still exist"
    ),
}

# =============================================================================
# TEST ASSERT MESSAGES (user-friendly with instructions)
# =============================================================================

_BORDER = "\u2550" * 74

TEST_ASSERT_MSGS = {
    "container_not_running": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 CONTAINER CHECK FAILED: {container}\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Status: {status}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check container: podman ps -a | grep {container}\n"
        "\u2551   2. Check logs: podman logs {container}\n"
        "\u2551   3. Restart: podman restart {container}\n"
        "\u2551   4. Re-run: ansible-playbook repo_manager.yml"
        " --tags deploy\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),

    "playbook_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 PLAYBOOK EXECUTION FAILED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Playbook: {playbook}\n"
        "\u2551 Tag: {tag}\n"
        "\u2551 Exit code: {rc}\n"
        "\u2551 Duration: {duration:.1f}s\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check the playbook output above\n"
        "\u2551   2. Check logs: /opt/omnia/log/repo_manager/\n"
        "\u2551   3. Run with increased verbosity: -vvv\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),

    "repo_status_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 REPO STATUS CHECK FAILED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 {error}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check output: cat {status_path}\n"
        "\u2551   2. Check Pulp logs: podman logs pulp\n"
        "\u2551   3. Re-run: ansible-playbook repo_manager.yml"
        " --tags download\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),

    "pulp_api_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 PULP API ENDPOINT CHECK FAILED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 {error}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check Pulp container: podman ps | grep pulp\n"
        "\u2551   2. Check Pulp logs: podman logs pulp\n"
        "\u2551   3. Check port: ss -tlnp | grep 2225\n"
        "\u2551   4. Re-deploy: ansible-playbook repo_manager.yml"
        " --tags deploy\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),

    "cleanup_data_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 CLEANUP VERIFICATION FAILED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 {error}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Re-run cleanup: ansible-playbook repo_manager.yml"
        " --tags cleanup_pulp\n"
        "\u2551   2. Manual cleanup: podman rm -f pulp && podman rmi -f"
        " docker.io/pulp/pulp:3.113\n"
        "\u2551   3. Remove data: rm -rf /opt/omnia/pulp_config\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),

    "repo_status_check_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 REPO STATUS CHECK FAILED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 {error}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check Pulp is running: podman ps | grep pulp\n"
        "\u2551   2. Re-run: ansible-playbook repo_manager.yml"
        " --tags status\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),

    "repo_status_missing_keys": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 REPO STATUS CONTENT INVALID\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Missing keys: {missing_keys}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Re-run: ansible-playbook repo_manager.yml"
        " --tags status\n"
        "\u2551   2. Check generate_local_repo_access.py output\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
}
