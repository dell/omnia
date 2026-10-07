#!/bin/bash
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
#
# Manually trigger a cadence polling cycle.
#
# Sends SIGUSR1 to the playbook-watcher service, which wakes up the
# CadenceTimerThread and executes a cadence cycle immediately
# (repo_sync -> catalog version bump -> GitLab pipeline trigger).
#
# Prerequisites:
#   - playbook-watcher.service must be running
#   - Cadence polling must be enabled in build_stream_config.yml
#
# Usage:
#   /opt/omnia/build_stream/playbook-watcher/trigger_cadence.sh
#
# The script exits 0 on success, 1 if the watcher is not running.

set -euo pipefail

SERVICE="playbook-watcher.service"

# Verify the service is running
if ! systemctl is-active --quiet "${SERVICE}"; then
    echo "ERROR: ${SERVICE} is not running."
    echo "Start it with: systemctl start ${SERVICE}"
    exit 1
fi

# Get the main PID of the service
PID=$(systemctl show --property=MainPID --value "${SERVICE}")

if [ -z "${PID}" ] || [ "${PID}" = "0" ]; then
    echo "ERROR: Could not determine PID for ${SERVICE}."
    exit 1
fi

# Send SIGUSR1 to trigger cadence cycle
kill -USR1 "${PID}"

echo "Cadence trigger sent to playbook-watcher (PID ${PID})."
echo "Monitor progress with: journalctl -u ${SERVICE} -f"
