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
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied
# See the License for the specific language governing permissions and
# limitations under the License.

# Script to update and restart the playbook watcher service

set -e

echo "=== Updating Playbook Watcher Service ==="

# Define paths
OMNIA_DATA_PATH="${OMNIA_DATA_PATH:-/opt/omnia}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_DIR="${OMNIA_DATA_PATH}/build_stream/playbook-watcher"
SERVICE_NAME="playbook-watcher"
LOCAL_DIR="${SCRIPT_DIR}/../playbook-watcher"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "This script must be run as root. Use sudo."
    exit 1
fi

# Create directory if it doesn't exist
echo "Creating service directory..."
mkdir -p "${SERVICE_DIR}"
mkdir -p "${OMNIA_DATA_PATH}/build_stream/logs"

# Copy updated files
echo "Copying updated service files..."
cp "$LOCAL_DIR/playbook_watcher_service.py" "$SERVICE_DIR/"
cp "$LOCAL_DIR/playbook-watcher.service" /etc/systemd/system/

# Set permissions
echo "Setting permissions..."
chmod +x "$SERVICE_DIR/playbook_watcher_service.py"
chown root:root "$SERVICE_DIR/playbook_watcher_service.py"

# Reload systemd
echo "Reloading systemd daemon..."
systemctl daemon-reload

# Restart the service
echo "Restarting playbook-watcher service..."
systemctl restart playbook-watcher

# Check service status
echo "Checking service status..."
sleep 2
systemctl status playbook-watcher --no-pager

# Show recent logs
echo ""
echo "Recent service logs:"
journalctl -u playbook-watcher -n 10 --no-pager

echo ""
echo "=== Update Complete ==="
echo "Service is running with the new configuration."
