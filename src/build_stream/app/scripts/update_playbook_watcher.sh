#!/bin/bash

# Script to update and restart the playbook watcher service

set -e

echo "=== Updating Playbook Watcher Service ==="

# Define paths
SERVICE_DIR="/opt/omnia/build_stream/playbook-watcher"
SERVICE_NAME="playbook-watcher"
LOCAL_DIR="/root/Documents/omnia/src/build_stream/playbook-watcher"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "This script must be run as root. Use sudo."
    exit 1
fi

# Create directory if it doesn't exist
echo "Creating service directory..."
mkdir -p /opt/omnia/build_stream/playbook-watcher
mkdir -p /opt/omnia/build_stream/logs

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
