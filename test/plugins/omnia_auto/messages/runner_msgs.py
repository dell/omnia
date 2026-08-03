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

"""Log and assertion messages for the run_playbook utility."""

from typing import Dict

RUNNER_LOG_MSGS: Dict[str, str] = {
    "starting_playbook": "Starting playbook: {playbook} (tags: {tag})",
    "playbook_completed": (
        "Playbook completed (rc={rc}, duration={duration:.1f}s)"
    ),
    "playbook_failed": (
        "Playbook failed (rc={rc}, duration={duration:.1f}s)"
    ),
    "playbook_timeout": "Playbook timed out after {timeout}s",
    "connecting_remote": "Connecting to target: {host}:{port}",
    "connecting_local": "Running in local mode (target is localhost)",
    "streaming_output": "Streaming output live...",
}

RUNNER_ASSERT_MSGS: Dict[str, str] = {
    "playbook_failed": (
        "Playbook execution failed.\n"
        "  Playbook: {playbook}\n"
        "  Tag: {tag}\n"
        "  Exit Code: {rc}\n"
        "  Duration: {duration:.1f}s\n"
        "\n"
        "  HOW TO FIX:\n"
        "    1. Check the live output above for errors\n"
        "    2. SSH to target: ssh <user>@<host>\n"
        "    3. Check logs: ls -la {log_path}\n"
        "    4. Re-run: cd {workdir} && ansible-playbook"
        " {playbook} --tags {tag} -vvv"
    ),
    "playbook_timeout": (
        "Playbook execution timed out.\n"
        "  Playbook: {playbook}\n"
        "  Timeout: {timeout}s\n"
        "\n"
        "  HOW TO FIX:\n"
        "    1. Check if the playbook is stuck on a task\n"
        "    2. Increase timeout via configure(default_timeout=...)\n"
        "    3. SSH to target and check running ansible processes"
    ),
    "sshpass_missing": (
        "sshpass is not installed. Required for SSH password auth.\n"
        "\n"
        "  HOW TO FIX:\n"
        "    Install: dnf install -y sshpass (RHEL)"
        " or apt install -y sshpass (Ubuntu)"
    ),
    "cancelled": "Playbook cancelled by user (Ctrl+C)",
    "os_error": "Command execution encountered an OS error",
}
