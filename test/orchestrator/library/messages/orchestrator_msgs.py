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
Orchestrator — Test Messages

All test names, log messages, and assertion messages
for the orchestrator FVT automation.
"""

from typing import Dict

# =============================================================================
TEST_NAMES: Dict[str, str] = {
    # Deploy
    "deploy_playbook": (
        "Deploy: orchestrator.yml --tags {tag}"
    ),
    "deploy_playbook_full": (
        "Deploy: orchestrator.yml (full provisioning)"
    ),
    "deploy_validate": (
        "Deploy: orchestrator.yml (validate)"
    ),

    # Validate
    "input_config_exists": (
        "Verify orchestrator_config.yml exists on target"
    ),
    "omnia_config_exists": (
        "Verify omnia_config.yml exists on target"
    ),
    "network_spec_exists": (
        "Verify network_spec.yml exists on target"
    ),
    "credentials_present": (
        "Verify credentials file is present on target"
    ),
    "repo_status_exists": (
        "Verify repo_status.yml exists on target"
    ),

    # Prepare — OpenCHAMI
    "openchami_container_running": (
        "Verify OpenCHAMI container {container} is running"
    ),
    "openchami_services_active": (
        "Verify OpenCHAMI systemd services are active"
    ),
    "openchami_api_reachable": (
        "Verify OpenCHAMI API is reachable"
    ),

    # Provision — Nodes
    "nodes_provisioned": (
        "Verify nodes are provisioned and reachable"
    ),
    "k8s_nodes_ready": (
        "Verify Kubernetes nodes are in Ready state"
    ),
    "slurm_nodes_idle": (
        "Verify Slurm nodes are in idle state"
    ),

    # Cleanup
    "containers_removed": (
        "Verify OpenCHAMI containers removed after cleanup"
    ),
    "services_removed": (
        "Verify systemd services stopped after cleanup"
    ),
    "firewall_ports_closed": (
        "Verify firewall ports closed after cleanup"
    ),

    # Clone / sync
    "clone_status": (
        "Verify repository is cloned and synced on target"
    ),
}

# =============================================================================
TEST_LOG_MSGS: Dict[str, str] = {
    # Input validation
    "input_config_ok": "orchestrator_config.yml present",
    "input_config_missing": "orchestrator_config.yml not found",
    "omnia_config_ok": "omnia_config.yml present",
    "omnia_config_missing": "omnia_config.yml not found",
    "network_spec_ok": "network_spec.yml present",
    "network_spec_missing": "network_spec.yml not found",
    "credentials_present_ok": "Credentials file present",
    "credentials_missing": "Credentials file missing",
    "repo_status_ok": "repo_status.yml present",
    "repo_status_missing": "repo_status.yml not found",

    # Container messages
    "container_running": "Container {container} is running",
    "container_not_running": (
        "Container {container} is NOT running"
    ),

    # Services
    "services_active_ok": "All systemd services active",
    "services_inactive": "{count} service(s) not active",
    "services_removed_ok": (
        "All systemd services stopped and removed"
    ),
    "services_still_active": (
        "{count} service(s) still active"
    ),

    # Firewall
    "firewall_ports_closed_ok": (
        "All firewall ports closed"
    ),
    "firewall_ports_still_open": (
        "{count} port(s) still open"
    ),

    # API
    "api_reachable_ok": "OpenCHAMI API reachable",
    "api_not_reachable": "OpenCHAMI API not reachable",

    # Nodes
    "nodes_ok": "All {count} nodes provisioned",
    "nodes_failed": "{count} node(s) not reachable",
    "k8s_nodes_ok": "All Kubernetes nodes Ready",
    "k8s_nodes_not_ready": "{count} node(s) not Ready",
    "slurm_nodes_ok": "All Slurm nodes idle",
    "slurm_nodes_not_idle": "{count} node(s) not idle",

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
}

# =============================================================================
_BORDER = "\u2550" * 74

TEST_ASSERT_MSGS: Dict[str, str] = {
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
        "\u2551   2. Verify orchestrator_config.yml settings\n"
        "\u2551   3. Run with increased verbosity: -vvv\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),

    "input_config_missing": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 INPUT CONFIGURATION MISSING\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 File: orchestrator_config.yml\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Copy template: src/orchestrator/input/orchestrator_config.yml\n"
        "\u2551   2. Edit with your cluster settings\n"
        "\u2551   3. Place in /opt/omnia/orchestrator/input/<project>/\n"
        "\u2551   4. Or run: omnia.sh --setup-venv (copies input templates)\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),

    "container_not_running": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 CONTAINER CHECK FAILED: {container}\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Status: {status}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check container: podman ps -a | grep {container}\n"
        "\u2551   2. Check logs: podman logs {container}\n"
        "\u2551   3. Restart target: systemctl restart openchami.target\n"
        "\u2551   4. Re-run: cd src/orchestrator/playbooks && ansible-playbook orchestrator.yml\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),

    "repo_status_missing": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 REPO STATUS FILE MISSING\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 File: repo_status.yml\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Run repo_manager domain first\n"
        "\u2551   2. Verify output at /opt/omnia/repo_manager/output/<project>/\n"
        "\u2551   3. Check orchestrator_config.yml repo_manager_output_path\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
}
