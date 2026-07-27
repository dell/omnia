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
Internal NFS Server Setup for RHEL.

Functions to create and manage an NFS server locally on the OIM host
for the ``nfs_internal`` dataset scenario. Installs nfs-utils, creates
the export directory, configures /etc/exports, and starts the NFS server.

Usage:
    from main.library.functions.nfs_func import (
        setup_internal_nfs_server,
        verify_nfs_server_running,
        cleanup_internal_nfs_server,
    )
"""

from typing import Dict, Any

from .formatting_func import TestLogger
from .host_func import run_on_oim
from ..vars.omnia_sh_vars import OMNIA_SH_VARS
from ..vars.common_vars import CMDS


def setup_internal_nfs_server(host) -> Dict[str, Any]:
    """Set up an internal NFS server on the OIM host (RHEL).

    Steps:
    1. Install nfs-utils if not already installed
    2. Create the NFS export directory
    3. Configure /etc/exports with the export path
    4. Enable and start nfs-server
    5. Apply exportfs to make the share available

    Args:
        host: Testinfra host object connected to the OIM server.

    Returns:
        Dict with ``success`` (bool), ``details`` (str), ``error`` (str|None).
    """
    log = TestLogger("Setup Internal NFS Server")
    export_path = OMNIA_SH_VARS.get("nfs_share_path", "/exports/omnia")

    if not export_path:
        return {
            "success": False,
            "details": None,
            "error": (
                "nfs_server_share_path is not set in the dataset install_config.yml.\n"
                "  Set nfs_server_share_path to the directory to be exported via NFS."
            ),
        }

    # Step 1: Install nfs-utils
    log.check("Installing nfs-utils...")
    install_cmd = run_on_oim(host, "dnf install -y nfs-utils 2>&1")
    if install_cmd.rc != 0:
        return {
            "success": False,
            "details": install_cmd.stdout.strip(),
            "error": f"Failed to install nfs-utils (rc={install_cmd.rc}): {install_cmd.stderr.strip()}",
        }
    log.passed("nfs-utils installed")

    # Step 2: Create export directory
    log.check(f"Creating NFS export directory: {export_path}")
    mkdir_cmd = run_on_oim(host, f"mkdir -p {export_path}")
    if mkdir_cmd.rc != 0:
        return {
            "success": False,
            "details": None,
            "error": f"Failed to create directory {export_path}: {mkdir_cmd.stderr.strip()}",
        }
    run_on_oim(host, f"chmod 755 {export_path}")
    log.passed(f"Directory created: {export_path}")

    # Step 3: Configure /etc/exports
    log.check("Configuring /etc/exports...")
    export_line = f"{export_path} *(rw,sync,no_subtree_check,no_root_squash)"

    # Check if already exported
    check_exports = run_on_oim(host, f"grep -F '{export_path}' /etc/exports 2>/dev/null")
    if check_exports.rc != 0:
        add_cmd = run_on_oim(host, f"echo '{export_line}' >> /etc/exports")
        if add_cmd.rc != 0:
            return {
                "success": False,
                "details": None,
                "error": f"Failed to update /etc/exports: {add_cmd.stderr.strip()}",
            }
    log.passed("NFS export configured in /etc/exports")

    # Step 4: Enable and start nfs-server
    log.check("Enabling and starting nfs-server...")
    enable_cmd = run_on_oim(host, "systemctl enable --now nfs-server 2>&1")
    if enable_cmd.rc != 0:
        return {
            "success": False,
            "details": enable_cmd.stdout.strip(),
            "error": f"Failed to start nfs-server: {enable_cmd.stderr.strip()}",
        }
    log.passed("nfs-server started and enabled")

    # Step 5: Apply exports
    log.check("Applying NFS exports...")
    exportfs_cmd = run_on_oim(host, "exportfs -rav 2>&1")
    if exportfs_cmd.rc != 0:
        return {
            "success": False,
            "details": exportfs_cmd.stdout.strip(),
            "error": f"Failed to apply exports: {exportfs_cmd.stderr.strip()}",
        }
    log.passed("NFS exports applied")

    # Step 6: Open firewall (if firewalld is running)
    firewall_status = run_on_oim(host, CMDS["firewall_is_active"])
    if firewall_status.rc == 0:
        log.check("Opening firewall for NFS...")
        for svc in ("nfs", "rpc-bind", "mountd"):
            run_on_oim(host, CMDS["firewall_add_service"].format(service=svc))
        run_on_oim(host, CMDS["firewall_reload"])
        log.passed("Firewall opened for NFS")

    return {
        "success": True,
        "details": f"Internal NFS server configured at {export_path}",
        "error": None,
    }


def verify_nfs_server_running(host) -> Dict[str, Any]:
    """Verify the internal NFS server is running and exporting.

    Args:
        host: Testinfra host object connected to the OIM server.

    Returns:
        Dict with ``success`` (bool), ``details`` (dict), ``error`` (str|None).
    """
    log = TestLogger("Verify Internal NFS Server")
    export_path = OMNIA_SH_VARS.get("nfs_share_path", "/exports/omnia")

    # Check nfs-server service
    log.check("Checking nfs-server service...")
    status = run_on_oim(host, CMDS["systemctl_is_active"].format(service="nfs-server")).stdout.strip()
    if status != "active":
        return {
            "success": False,
            "details": {"service_status": status},
            "error": f"nfs-server is not active (status: {status})",
        }
    log.passed(f"nfs-server is {status}")

    # Check exports
    log.check("Checking NFS exports...")
    exports_cmd = run_on_oim(host, "exportfs -v")
    if export_path not in exports_cmd.stdout:
        return {
            "success": False,
            "details": {"exports": exports_cmd.stdout.strip()},
            "error": f"Export path {export_path} not found in active exports",
        }
    log.passed(f"Export path {export_path} is active")

    # Check export directory exists
    log.check(f"Checking export directory: {export_path}")
    dir_check = run_on_oim(host, CMDS["dir_exists"].format(path=export_path))
    dir_exists = dir_check.rc == 0 and "exists" in dir_check.stdout
    if not dir_exists:
        return {
            "success": False,
            "details": None,
            "error": f"Export directory does not exist: {export_path}",
        }
    log.passed(f"Export directory exists: {export_path}")

    return {
        "success": True,
        "details": {
            "service_status": status,
            "export_path": export_path,
            "exports": exports_cmd.stdout.strip(),
        },
        "error": None,
    }


def cleanup_internal_nfs_server(host) -> Dict[str, Any]:
    """Clean up the internal NFS server configuration.

    Removes the export entry from /etc/exports and stops nfs-server.
    Does NOT remove the export directory or its contents.

    Args:
        host: Testinfra host object connected to the OIM server.

    Returns:
        Dict with ``success`` (bool), ``details`` (str), ``error`` (str|None).
    """
    log = TestLogger("Cleanup Internal NFS Server")
    export_path = OMNIA_SH_VARS.get("nfs_share_path", "/exports/omnia")

    # Remove export entry
    log.check("Removing NFS export entry...")
    escaped_path = export_path.replace("/", "\\/")
    run_on_oim(host, f"sed -i '/{escaped_path}/d' /etc/exports")
    run_on_oim(host, "exportfs -rav 2>/dev/null")
    log.passed("NFS export entry removed")

    # Stop nfs-server (only if no other exports remain)
    remaining = run_on_oim(host, "grep -v '^#' /etc/exports | grep -v '^$'").stdout.strip()
    if not remaining:
        log.check("No remaining exports, stopping nfs-server...")
        run_on_oim(host, "systemctl stop nfs-server")
        run_on_oim(host, "systemctl disable nfs-server")
        log.passed("nfs-server stopped and disabled")
    else:
        log.info("Other NFS exports exist, keeping nfs-server running")

    return {
        "success": True,
        "details": f"Internal NFS server cleanup complete for {export_path}",
        "error": None,
    }
