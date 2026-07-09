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

"""Log and assertion messages for the playbook runner."""

from typing import Dict

RUNNER_LOG_MSGS: Dict[str, str] = {
    "starting_playbook": "Starting playbook: {playbook}",
    "playbook_completed": "Playbook completed (rc={rc}, duration={duration:.1f}s)",
    "playbook_failed": "Playbook failed (rc={rc}, duration={duration:.1f}s)",
    "playbook_timeout": "Playbook timed out after {timeout}s",
    "connecting_remote": "Connecting to OIM server: {host}:{port}",
    "connecting_local": "Running in local mode (OIM is localhost)",
    "container_check": "Checking omnia_core container status",
    "container_not_running": "omnia_core container is not running",
    "streaming_output": "Streaming playbook output live...",
    "starting_shell": "Starting command: {command}",
    "sync_starting": "Syncing dataset '{dataset}' to container...",
    "sync_completed": "Dataset synced to {dest}",
    "sync_skipped": "Dataset sync skipped (sync_dataset_to_core: false)",
    "encrypt_starting": "Encrypting credentials inside container...",
    "encrypt_completed": "Credentials encrypted successfully",
}

RUNNER_ASSERT_MSGS: Dict[str, str] = {
    "playbook_failed": (
        "Playbook execution failed.\n"
        "  Playbook: {playbook}\n"
        "  Exit Code: {rc}\n"
        "  Duration: {duration:.1f}s\n"
        "\n"
        "  HOW TO FIX:\n"
        "    1. Check the live output above for errors\n"
        "    2. SSH to OIM: ssh root@<oim_ip>\n"
        "    3. Enter container: podman exec -it omnia_core bash\n"
        "    4. Check logs: ls -la /opt/omnia/log/"
    ),
    "playbook_timeout": (
        "Playbook execution timed out.\n"
        "  Playbook: {playbook}\n"
        "  Timeout: {timeout}s\n"
        "\n"
        "  HOW TO FIX:\n"
        "    1. Check if the playbook is stuck on a task\n"
        "    2. Increase timeout if the playbook is expected to run longer\n"
        "    3. SSH to OIM and check running ansible processes"
    ),
    "container_not_running": (
        "omnia_core container is not running.\n"
        "\n"
        "  HOW TO FIX:\n"
        "    1. Run: sudo ./omnia.sh --install\n"
        "    2. Check: podman ps -a | grep omnia_core"
    ),
    "ssh_failed": (
        "SSH connection to OIM server failed.\n"
        "  Host: {host}:{port}\n"
        "\n"
        "  HOW TO FIX:\n"
        "    1. Verify oim_server_ip in omnia_test_config.yml\n"
        "    2. Verify oim_ssh_password in omnia_test_credentials.yml\n"
        "    3. Ensure sshpass is installed: dnf install -y sshpass"
    ),
    "sshpass_missing": (
        "sshpass is not installed. Required for SSH password authentication.\n"
        "\n"
        "  HOW TO FIX:\n"
        "    Install: dnf install -y sshpass (RHEL) or apt install -y sshpass (Ubuntu)"
    ),
    "sync_failed": (
        "Dataset sync to omnia_core container failed.\n"
        "  Exit Code: {rc}\n"
        "  Error: {error}\n"
        "\n"
        "  HOW TO FIX:\n"
        "    1. Verify omnia_core container is running and SSH port 2222 is accessible\n"
        "    2. Check omnia_core_password in omnia_test_credentials.yml\n"
        "    3. Test: sshpass -p <password> ssh -p 2222 root@<oim_ip> ls /opt/omnia/input/"
    ),
    "encrypt_failed": (
        "Credential encryption inside container failed.\n"
        "  Error: {error}\n"
        "\n"
        "  HOW TO FIX:\n"
        "    1. Ensure ansible-vault is available inside omnia_core\n"
        "    2. Check the credentials file exists in /opt/omnia/input/project_default/"
    ),
}
