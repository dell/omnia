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
Common Variables for the main module.

Shared constants used across all functions in this module.
All paths and identifiers are defined here — no hardcodes elsewhere.
"""

import os

# =============================================================================
# MODULE PATHS
# =============================================================================

# main/ directory (this module's root)
# From vars/ -> library/ -> main/
MODULE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))

# Repository root
# From main/ -> test/ -> repo root
REPO_ROOT = os.path.dirname(os.path.dirname(MODULE_ROOT))

# omnia.sh script path (resolved from repo root)
OMNIA_SH_PATH = os.path.join(REPO_ROOT, "src", "main", "omnia.sh")

# =============================================================================
# CONTAINER CONFIGURATION
# =============================================================================

OMNIA_CORE_CONTAINER = "omnia_core"
CONTAINER_SSH_PORT = 2222
PODMAN_EXEC_PREFIX = f"podman exec {OMNIA_CORE_CONTAINER} bash -lc"

# =============================================================================
# SSH OPTIONS & PATHS
# =============================================================================

SSH_OPTS = "-o StrictHostKeyChecking=no -o ConnectTimeout=10 -o BatchMode=yes"
SSH_KEY_PRIV = "/root/.ssh/oim_rsa"
SSH_KEY_PUB = "/root/.ssh/oim_rsa.pub"
SSH_CONFIG_PATH = "/root/.ssh/config"
AUTHORIZED_KEYS_PATH = "/root/.ssh/authorized_keys"
KNOWN_HOSTS_PATH = "/root/.ssh/known_hosts"

# =============================================================================
# CONFIGURATION FILES
# =============================================================================

# Test config file (non-sensitive settings — always plain text)
TEST_CONFIG_FILE = "test_config.yml"

# Credentials file (sensitive passwords — vault encrypted)
TEST_CREDENTIALS_FILE = "test_creds.yml"
TEST_CREDENTIALS_KEY = ".test_creds.key"

# =============================================================================
# REUSABLE SHELL COMMANDS
# =============================================================================

# Known hosts pattern for container SSH port
KNOWN_HOSTS_PATTERN = f"[localhost]:{CONTAINER_SSH_PORT}"


CMDS = {
    # Podman
    "podman_ps": (
        f"podman ps --filter name={OMNIA_CORE_CONTAINER}"
        " --format '{{{{.Names}}}}\t{{{{.Status}}}}\t{{{{.Image}}}}\t{{{{.Ports}}}}'"
    ),
    "podman_ps_all": (
        f"podman ps -a --filter name={OMNIA_CORE_CONTAINER}"
        " --format '{{{{.Names}}}}\t{{{{.Status}}}}'"
    ),
    "podman_ps_names": (
        "podman ps --format '{{{{.Names}}}} {{{{.Status}}}}'"
        f" | grep {OMNIA_CORE_CONTAINER}"
    ),
    "podman_ps_detail": (
        "podman ps --format '{{{{.Names}}}}|{{{{.Status}}}}|{{{{.Image}}}}|{{{{.Ports}}}}'"
        f" | grep {OMNIA_CORE_CONTAINER}"
    ),
    "podman_ps_all_names": (
        "podman ps -a --format '{{{{.Names}}}} {{{{.Status}}}}'"
        f" | grep {OMNIA_CORE_CONTAINER}"
    ),
    "podman_ps_check": (
        f"podman ps --format '{{{{.Names}}}}' | grep -q {OMNIA_CORE_CONTAINER}"
    ),
    "podman_images": (
        "podman images --format '{{{{.Repository}}}}:{{{{.Tag}}}}'"
        f" | grep '{OMNIA_CORE_CONTAINER}'"
    ),
    # Systemd
    "systemctl_is_active": "systemctl is-active {service} 2>/dev/null",
    "systemctl_status": "systemctl status {service} 2>/dev/null | head -15",
    # Network
    "ping_host": "ping -c 2 -W 3 {host} 2>/dev/null",
    # SSH
    "ssh_to_container": f"ssh {SSH_OPTS} {OMNIA_CORE_CONTAINER} '{{cmd}}'",
    "ssh_from_container": f"{PODMAN_EXEC_PREFIX} \"ssh {SSH_OPTS} {{target}} '{{cmd}}'\"",
    "ssh_key_check": "test -f {path} && echo exists",
    "ssh_config_grep": "grep -A5 'Host {alias}' /root/.ssh/config 2>/dev/null",
    "authorized_keys_grep": "grep -F \"$(cat {pub_key})\" /root/.ssh/authorized_keys",
    "known_hosts_grep": "grep '{pattern}' /root/.ssh/known_hosts 2>/dev/null",
    # Files
    "cat_metadata": f"{PODMAN_EXEC_PREFIX} 'cat {{path}}'",
    "file_stat": "stat -c '%A %U:%G %s %n' {path} 2>/dev/null",
    "file_exists": "test -f {path} && echo exists",
    "dir_exists": "test -d {path} && echo exists",
    # fstab/mount
    "grep_fstab": "grep -v '^#' /etc/fstab | grep '{pattern}'",
    "mount_check": "mountpoint -q {path}",
    # Firewall
    "firewall_add_service": "firewall-cmd --permanent --add-service={service} 2>/dev/null",
    "firewall_reload": "firewall-cmd --reload 2>/dev/null",
    "firewall_is_active": "systemctl is-active firewalld 2>/dev/null",
}
