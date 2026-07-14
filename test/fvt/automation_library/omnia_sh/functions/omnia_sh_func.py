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
Omnia.sh Test - Core Functions.

This module contains all functions for running and verifying omnia.sh via
testinfra. All install/uninstall operations run the omnia.sh source resolved
from the core ``OMNIA_SH_PATH`` (``src/main/omnia.sh``). Test functions call
these functions - all logic resides here.

Usage:
    from automation_library.omnia_sh.functions.omnia_sh_func import (
        # Deploy (install / uninstall) - testinfra based
        check_omnia_sh_exists,
        validate_nfs_config,
        setup_internal_nfs_server,
        run_omnia_sh_install_testinfra,
        run_omnia_sh_uninstall_testinfra,
        # Verification functions
        check_container_running,
        check_file_exists,
        check_service_running,
        check_ssh_to_container,
        check_ssh_from_container,
        check_metadata_file,
        # Cleanup verification functions
        check_container_not_running,
        check_service_not_exists,
        check_fstab_entry_removed,
        check_mount_removed,
    )

Author: Dell Technologies
"""

import time
from typing import Dict, Any

from ..vars.omnia_sh_vars import OMNIA_SH_VARS, TEST_VARS
from ...core import run_in_container

# =============================================================================
# TEST VERIFICATION FUNCTIONS (for pytest/testinfra)
# =============================================================================
# These functions are called by test_omnia_sh.py to verify installation.
# They return structured results that the test file uses for assertions.

def check_container_running(host) -> Dict[str, Any]:
    """
    Check if omnia_core container is running.

    Args:
        host: testinfra host object

    Returns:
        Dict with 'success', 'details', 'error'
    """
    container_name = OMNIA_SH_VARS["container_name"]

    cmd = host.run(f"podman ps --format '{{{{.Names}}}} {{{{.Status}}}}' | grep {container_name}")

    if cmd.rc == 0 and container_name in cmd.stdout:
        # Get detailed info
        status_cmd = host.run(
            f"podman ps --format '{{{{.Names}}}}|{{{{.Status}}}}|{{{{.Image}}}}|{{{{.Ports}}}}' | grep {container_name}"
        )
        parts = status_cmd.stdout.strip().split('|')

        return {
            "success": True,
            "details": {
                "container": parts[0] if len(parts) > 0 else container_name,
                "status": parts[1] if len(parts) > 1 else "unknown",
                "image": parts[2] if len(parts) > 2 else "unknown",
                "ports": parts[3] if len(parts) > 3 else "none",
            },
            "error": None
        }

    # Check if exists but not running
    exists_cmd = host.run(f"podman ps -a --format '{{{{.Names}}}} {{{{.Status}}}}' | grep {container_name}")
    if exists_cmd.rc == 0:
        return {
            "success": False,
            "details": None,
            "error": f"Container exists but not running: {exists_cmd.stdout.strip()}"
        }

    return {
        "success": False,
        "details": None,
        "error": "Container does not exist"
    }


def check_file_exists(host, path: str) -> Dict[str, Any]:
    """
    Check if a file exists on the remote host.

    Args:
        host: testinfra host object
        path: file path to check

    Returns:
        Dict with 'success', 'details', 'error'
    """
    f = host.file(path)

    if f.exists:
        info = host.run(f"ls -la {path}").stdout.strip()
        return {
            "success": True,
            "details": info,
            "error": None
        }

    return {
        "success": False,
        "details": None,
        "error": f"File not found: {path}"
    }


def check_service_running(host, service_name: str = None) -> Dict[str, Any]:
    """
    Check if a systemd service is running.

    Args:
        host: testinfra host object
        service_name: service name (default: omnia_core.service)

    Returns:
        Dict with 'success', 'status', 'details', 'error'
    """
    service_name = service_name or TEST_VARS["service_name"]

    status = host.run(f"systemctl is-active {service_name}").stdout.strip()
    info = host.run(f"systemctl status {service_name} --no-pager -l 2>/dev/null | head -10").stdout.strip()

    if status == "active":
        return {
            "success": True,
            "status": status,
            "details": info,
            "error": None
        }

    return {
        "success": False,
        "status": status,
        "details": info,
        "error": f"Service is {status}"
    }


def check_ssh_to_container(host, timeout: int = 5) -> Dict[str, Any]:
    """
    Check passwordless SSH from OIM server to omnia_core container.

    Args:
        host: testinfra host object
        timeout: SSH connection timeout

    Returns:
        Dict with 'success', 'details', 'error'
    """
    alias = TEST_VARS["ssh_alias"]

    cmd = host.run(f"ssh -o BatchMode=yes -o ConnectTimeout={timeout} {alias} 'whoami && pwd && echo SSH_OK'")
    output = cmd.stdout.strip()

    if cmd.rc == 0 and "SSH_OK" in output:
        lines = output.split('\n')
        return {
            "success": True,
            "details": {
                "user": lines[0] if len(lines) > 0 else "unknown",
                "workdir": lines[1] if len(lines) > 1 else "unknown",
                "connection": "passwordless (no password prompt)"
            },
            "error": None
        }

    return {
        "success": False,
        "details": None,
        "error": cmd.stderr.strip() or "SSH connection failed"
    }


def check_ssh_from_container(host, oim_ip: str, timeout: int = 5) -> Dict[str, Any]:
    """
    Check passwordless SSH from omnia_core container back to OIM server.

    Args:
        host: testinfra host object
        oim_ip: OIM server IP address
        timeout: SSH connection timeout

    Returns:
        Dict with 'success', 'details', 'error'
    """
    alias = TEST_VARS["ssh_alias"]

    cmd = host.run(
        f"ssh -o BatchMode=yes -o ConnectTimeout={timeout} {alias} "
        f"'ssh -o BatchMode=yes -o StrictHostKeyChecking=no -o ConnectTimeout={timeout} {oim_ip} "
        f"whoami && echo SSH_REVERSE_OK'"
    )
    output = cmd.stdout.strip()

    if cmd.rc == 0 and "SSH_REVERSE_OK" in output:
        lines = output.split('\n')
        return {
            "success": True,
            "details": {
                "user": lines[0] if len(lines) > 0 else "unknown",
                "target": oim_ip,
                "connection": "passwordless (key-based auth)"
            },
            "error": None
        }

    return {
        "success": False,
        "details": None,
        "error": cmd.stderr.strip() or "Reverse SSH connection failed"
    }


def check_metadata_file(host) -> Dict[str, Any]:
    """
    Check if oim_metadata.yml file exists inside the container and return its content.

    Args:
        host: testinfra host object

    Returns:
        Dict with 'success', 'details', 'error'
    """
    path = TEST_VARS["metadata_file"]

    # Check inside the container (file is at /opt/omnia/.data/ inside container)
    check_cmd = run_in_container(host, f"test -f {path} && echo exists")
    if "exists" in check_cmd.stdout:
        content_cmd = run_in_container(host, f"head -15 {path}")
        return {
            "success": True,
            "details": content_cmd.stdout.strip(),
            "error": None
        }

    return {
        "success": False,
        "details": None,
        "error": f"Metadata file not found inside container: {path}"
    }


# =============================================================================
# CLEANUP VERIFICATION FUNCTIONS (for pytest/testinfra)
# =============================================================================
# These functions verify that cleanup was successful.

def check_container_not_running(host) -> Dict[str, Any]:
    """
    Verify omnia_core container is NOT running (cleanup verification).

    Args:
        host: testinfra host object

    Returns:
        Dict with 'success', 'details', 'error'
    """
    container_name = OMNIA_SH_VARS["container_name"]

    # Check if container is running
    cmd = host.run(f"podman ps --format '{{{{.Names}}}}' | grep -q {container_name}")

    if cmd.rc != 0:
        # Container not running - good
        return {
            "success": True,
            "details": f"Container {container_name} is not running",
            "error": None
        }

    return {
        "success": False,
        "details": None,
        "error": f"Container {container_name} is still running"
    }


def check_service_not_exists(host) -> Dict[str, Any]:
    """
    Verify omnia_core.service file does NOT exist (cleanup verification).

    Args:
        host: testinfra host object

    Returns:
        Dict with 'success', 'details', 'error'
    """
    service_file = TEST_VARS["container_file"]  # /etc/containers/systemd/omnia_core.container

    f = host.file(service_file)

    if not f.exists:
        return {
            "success": True,
            "details": f"Service file {service_file} removed",
            "error": None
        }

    return {
        "success": False,
        "details": None,
        "error": f"Service file still exists: {service_file}"
    }


def check_fstab_entry_removed(host, omnia_shared_path: str = None) -> Dict[str, Any]:
    """
    Verify fstab entry for omnia_shared_path is removed (cleanup verification).

    Args:
        host: testinfra host object
        omnia_shared_path: path to check in fstab (default from config)

    Returns:
        Dict with 'success', 'details', 'error'
    """
    if omnia_shared_path is None:
        omnia_shared_path = OMNIA_SH_VARS["omnia_shared_path"]

    # If omnia_shared_path is not configured, skip check
    if not omnia_shared_path:
        return {
            "success": True,
            "details": "No omnia_shared_path configured - skipping fstab check",
            "error": None
        }

    cmd = host.run(f"grep -E '\\s+{omnia_shared_path}\\s+' /etc/fstab")

    if cmd.rc != 0:
        # No entry found - good
        return {
            "success": True,
            "details": f"No fstab entry for {omnia_shared_path}",
            "error": None
        }

    return {
        "success": False,
        "details": None,
        "error": f"fstab entry still exists: {cmd.stdout.strip()}"
    }


def check_mount_removed(host, omnia_shared_path: str = None) -> Dict[str, Any]:
    """
    Verify omnia_shared_path is NOT mounted (cleanup verification).

    Args:
        host: testinfra host object
        omnia_shared_path: path to check (default from config)

    Returns:
        Dict with 'success', 'details', 'error'
    """
    if omnia_shared_path is None:
        omnia_shared_path = OMNIA_SH_VARS["omnia_shared_path"]

    # If omnia_shared_path is not configured, skip check
    if not omnia_shared_path:
        return {
            "success": True,
            "details": "No omnia_shared_path configured - skipping mount check",
            "error": None
        }

    cmd = host.run(f"mountpoint -q {omnia_shared_path}")

    if cmd.rc != 0:
        # Not a mount point - good
        return {
            "success": True,
            "details": f"{omnia_shared_path} is not mounted",
            "error": None
        }

    return {
        "success": False,
        "details": None,
        "error": f"{omnia_shared_path} is still mounted"
    }


# =============================================================================
# NFS VALIDATION FUNCTIONS (for pytest/testinfra)
# =============================================================================

def validate_nfs_config() -> Dict[str, Any]:
    """
    Validate NFS configuration in omnia_test_config.yml.

    Validates required fields based on share_option and nfs_type:
    - NFS external: nfs_server_ip, nfs_share_path, omnia_shared_path, omnia_core_password required
    - NFS internal: nfs_share_path, omnia_core_password required (oim_server_ip optional - uses localhost)
    - Local: omnia_shared_path, omnia_core_password required

    Returns:
        Dict with 'success', 'share_option', 'nfs_type', 'missing_fields', 'error'
    """
    share_option = OMNIA_SH_VARS["share_option"]
    nfs_type = OMNIA_SH_VARS["nfs_type"]
    nfs_server_ip = OMNIA_SH_VARS["nfs_server_ip"]
    nfs_share_path = OMNIA_SH_VARS["nfs_share_path"]
    omnia_shared_path = OMNIA_SH_VARS["omnia_shared_path"]
    omnia_core_password = OMNIA_SH_VARS["omnia_core_password"]
    oim_server_ip = OMNIA_SH_VARS["oim_server_ip"]

    missing = []

    # share_option is always required
    if not share_option:
        missing.append("share_option")
        return {
            "success": False,
            "share_option": share_option,
            "nfs_type": nfs_type,
            "missing_fields": missing,
            "error": "share_option not configured in omnia_test_config.yml"
        }

    # omnia_core_password is always required
    if not omnia_core_password:
        missing.append("omnia_core_password")

    if share_option == "NFS":
        # nfs_type is required for NFS
        if not nfs_type:
            missing.append("nfs_type")

        if nfs_type == "external":
            # External NFS requires: nfs_server_ip, nfs_share_path, omnia_shared_path
            if not nfs_server_ip:
                missing.append("nfs_server_ip")
            if not nfs_share_path:
                missing.append("nfs_share_path")
            if not omnia_shared_path:
                missing.append("omnia_shared_path")
        elif nfs_type == "internal":
            # Internal NFS requires: oim_server_ip, nfs_share_path
            # oim_server_ip is mandatory for internal NFS setup
            if not oim_server_ip:
                missing.append("oim_server_ip")
            if not nfs_share_path:
                missing.append("nfs_share_path")
        else:
            missing.append(f"nfs_type (invalid value: {nfs_type})")

    elif share_option == "Local":
        # Local requires only omnia_shared_path
        if not omnia_shared_path:
            missing.append("omnia_shared_path")
    else:
        missing.append(f"share_option (invalid value: {share_option})")

    if missing:
        # Separate config vs credentials fields for better error message
        config_fields = [f for f in missing if f not in ["omnia_core_password"]]
        creds_fields = [f for f in missing if f == "omnia_core_password"]

        error_parts = []
        if config_fields:
            error_parts.append(f"Config fields missing in omnia_test_config.yml: {', '.join(config_fields)}")
        if creds_fields:
            error_parts.append(f"Credential fields missing in omnia_test_credentials.yml: {', '.join(creds_fields)}")

        return {
            "success": False,
            "share_option": share_option,
            "nfs_type": nfs_type,
            "missing_fields": missing,
            "error": "; ".join(error_parts)
        }

    return {
        "success": True,
        "share_option": share_option,
        "nfs_type": nfs_type,
        "missing_fields": [],
        "error": ""
    }


# =============================================================================
# TESTINFRA-BASED INSTALL/UNINSTALL FUNCTIONS
# =============================================================================

def check_omnia_sh_exists(host) -> Dict[str, Any]:
    """
    Verify omnia.sh script exists at the local repo path.

    Args:
        host: testinfra host object

    Returns:
        Dict with 'success', 'path', 'error'
    """
    omnia_sh_path = OMNIA_SH_VARS["omnia_sh_path"]

    if not omnia_sh_path:
        return {
            "success": False,
            "path": "",
            "error": "omnia_sh_path not resolved"
        }

    check = host.run(f"test -f {omnia_sh_path}")
    if check.rc != 0:
        return {
            "success": False,
            "path": omnia_sh_path,
            "error": f"omnia.sh not found at {omnia_sh_path}"
        }

    return {
        "success": True,
        "path": omnia_sh_path,
        "ref_type": "local",
        "error": ""
    }


def run_omnia_sh_install_testinfra(host, progress_callback=None, use_background=True) -> Dict[str, Any]:
    """
    Run omnia.sh --install using testinfra host with optional progress output.

    Args:
        host: testinfra host object
        progress_callback: Optional callable(elapsed_seconds: int) for progress output
        use_background: If True, runs in background with progress (like upgrade).
                       If False, runs directly (simpler but no progress updates).

    Returns:
        Dict with 'success', 'output', 'error'
    """
    omnia_sh_path = OMNIA_SH_VARS["omnia_sh_path"]
    timeout = OMNIA_SH_VARS["install_timeout"]
    poll_interval = OMNIA_SH_VARS["poll_interval"]

    if not omnia_sh_path:
        return {
            "success": False,
            "output": "",
            "error": "omnia_sh_path not resolved"
        }

    # Validate NFS config first
    nfs_result = validate_nfs_config()
    if not nfs_result["success"]:
        return {
            "success": False,
            "output": "",
            "error": nfs_result["error"]
        }

    # Get all values from vars (no fallbacks)
    share_option = OMNIA_SH_VARS["share_option"]
    nfs_type = OMNIA_SH_VARS["nfs_type"]
    nfs_server_ip = OMNIA_SH_VARS["nfs_server_ip"]
    nfs_share_path = OMNIA_SH_VARS["nfs_share_path"]
    omnia_shared_path = OMNIA_SH_VARS["omnia_shared_path"]
    omnia_core_password = OMNIA_SH_VARS["omnia_core_password"]
    oim_server_ip = OMNIA_SH_VARS["oim_server_ip"]

    inputs = []
    if share_option == "NFS":
        inputs.append("1")  # Select NFS
        if nfs_type == "external":
            inputs.append("1")  # Select External
            inputs.append(nfs_server_ip)
            inputs.append(nfs_share_path)
            inputs.append(omnia_shared_path)
        else:  # internal
            inputs.append("2")  # Select Internal
            server_ip = oim_server_ip if oim_server_ip else "localhost"
            inputs.append(server_ip)
            inputs.append(nfs_share_path)
    else:  # Local
        inputs.append("2")  # Select Local
        inputs.append(omnia_shared_path)

    inputs.append(omnia_core_password)
    inputs.append(omnia_core_password)  # Confirm password

    # Create input file
    input_content = "\n".join(inputs)
    input_file = "/tmp/omnia_sh_inputs.txt"
    host.run(f"echo '{input_content}' > {input_file} && chmod 600 {input_file}")

    # Simple direct execution (no background)
    if not use_background:
        cmd = host.run(f"{omnia_sh_path} --install < {input_file}")
        host.run(f"rm -f {input_file}")  # Cleanup

        if cmd.rc == 0:
            return {"success": True, "output": cmd.stdout, "error": ""}
        
        # Include detailed error output
        error_msg = f"omnia.sh --install failed (exit code {cmd.rc})"
        if cmd.stderr:
            error_msg += f"\n\nError output:\n{cmd.stderr}"
        if cmd.stdout:
            # Show last few lines of stdout for context
            lines = cmd.stdout.strip().split('\n')
            last_lines = lines[-5:] if len(lines) > 5 else lines
            error_msg += f"\n\nLast output lines:\n" + "\n".join(last_lines)
        return {"success": False, "output": cmd.stdout, "error": error_msg}

    # Background execution with progress (like upgrade scenario)
    log_file = "/tmp/omnia_install.log"
    pid_file = "/tmp/omnia_install.pid"
    rc_file = "/tmp/omnia_install.rc"
    wrapper = "/tmp/omnia_install.sh"

    # Write wrapper script
    host.run(
        f"cat > {wrapper} << 'INSTALLEOF'\n"
        f"#!/bin/bash\n"
        f"{omnia_sh_path} --install < {input_file}\n"
        f"echo $? > {rc_file}\n"
        f"INSTALLEOF\n"
        f"chmod +x {wrapper}"
    )

    # Run wrapper in background
    host.run(f"nohup {wrapper} > {log_file} 2>&1 & echo $! > {pid_file}")

    # Read the PID
    pid_cmd = host.run(f"cat {pid_file}")
    pid = pid_cmd.stdout.strip()

    elapsed = 0
    while elapsed < timeout:
        time.sleep(min(poll_interval, timeout - elapsed))
        elapsed += poll_interval

        # Check if process is still running
        alive = host.run(f"kill -0 {pid} 2>/dev/null; echo $?")
        still_running = alive.stdout.strip() == "0"

        if progress_callback:
            progress_callback(elapsed)

        if not still_running:
            break

    # If still running after timeout, kill it
    if elapsed >= timeout:
        host.run(f"kill -9 {pid} 2>/dev/null || true")

    # Read exit code
    rc_cmd = host.run(f"cat {rc_file} 2>/dev/null || echo 1")
    rc_str = rc_cmd.stdout.strip().split("\n")[-1]
    try:
        rc = int(rc_str)
    except ValueError:
        rc = 1

    # Get full output
    log_cmd = host.run(f"cat {log_file} 2>/dev/null")
    output = log_cmd.stdout.strip() if log_cmd.rc == 0 else ""

    # Clean up temp files
    host.run(f"rm -f {log_file} {pid_file} {rc_file} {input_file} {wrapper}")

    if rc != 0 and elapsed >= timeout:
        return {
            "success": False,
            "output": output,
            "error": f"omnia.sh --install timed out after {timeout}s"
        }

    if rc != 0:
        # Include actual error output for debugging
        error_msg = f"omnia.sh --install failed (exit code {rc})"
        if output:
            # Show last few lines of output for context
            lines = output.strip().split('\n')
            last_lines = lines[-5:] if len(lines) > 5 else lines
            error_msg += f"\n\nLast output lines:\n" + "\n".join(last_lines)
        return {
            "success": False,
            "output": output,
            "error": error_msg
        }

    return {
        "success": True,
        "output": output,
        "error": ""
    }


def run_omnia_sh_uninstall_testinfra(host, progress_callback=None, use_background=True) -> Dict[str, Any]:
    """
    Run omnia.sh --uninstall using testinfra host with optional progress output.

    Args:
        host: testinfra host object
        progress_callback: Optional callable(elapsed_seconds: int) for progress output
        use_background: If True, runs in background with progress (like upgrade).
                       If False, runs directly (simpler but no progress updates).

    Returns:
        Dict with 'success', 'output', 'error'
    """
    omnia_sh_path = OMNIA_SH_VARS["omnia_sh_path"]
    timeout = OMNIA_SH_VARS["uninstall_timeout"]
    poll_interval = OMNIA_SH_VARS["poll_interval"]

    if not omnia_sh_path:
        return {
            "success": False,
            "output": "",
            "error": "omnia_sh_path not resolved"
        }

    # Check if omnia.sh exists
    check = host.run(f"test -f {omnia_sh_path}")
    if check.rc != 0:
        return {
            "success": False,
            "output": "",
            "error": f"omnia.sh not found at {omnia_sh_path}"
        }

    # Simple direct execution (no background)
    if not use_background:
        cmd = host.run(f"echo 'y' | {omnia_sh_path} --uninstall")

        if cmd.rc == 0:
            return {"success": True, "output": cmd.stdout, "error": ""}
        
        # Include detailed error output
        error_msg = f"omnia.sh --uninstall failed (exit code {cmd.rc})"
        if cmd.stderr:
            error_msg += f"\n\nError output:\n{cmd.stderr}"
        if cmd.stdout:
            # Show last few lines of stdout for context
            lines = cmd.stdout.strip().split('\n')
            last_lines = lines[-5:] if len(lines) > 5 else lines
            error_msg += f"\n\nLast output lines:\n" + "\n".join(last_lines)
        return {"success": False, "output": cmd.stdout, "error": error_msg}

    # Background execution with progress (like upgrade scenario)
    log_file = "/tmp/omnia_uninstall.log"
    pid_file = "/tmp/omnia_uninstall.pid"
    rc_file = "/tmp/omnia_uninstall.rc"
    wrapper = "/tmp/omnia_uninstall.sh"

    # Write wrapper script
    host.run(
        f"cat > {wrapper} << 'UNINSTALLEOF'\n"
        f"#!/bin/bash\n"
        f"echo 'y' | {omnia_sh_path} --uninstall\n"
        f"echo $? > {rc_file}\n"
        f"UNINSTALLEOF\n"
        f"chmod +x {wrapper}"
    )

    # Run wrapper in background
    host.run(f"nohup {wrapper} > {log_file} 2>&1 & echo $! > {pid_file}")

    # Read the PID
    pid_cmd = host.run(f"cat {pid_file}")
    pid = pid_cmd.stdout.strip()

    elapsed = 0
    while elapsed < timeout:
        time.sleep(min(poll_interval, timeout - elapsed))
        elapsed += poll_interval

        # Check if process is still running
        alive = host.run(f"kill -0 {pid} 2>/dev/null; echo $?")
        still_running = alive.stdout.strip() == "0"

        if progress_callback:
            progress_callback(elapsed)

        if not still_running:
            break

    # If still running after timeout, kill it
    if elapsed >= timeout:
        host.run(f"kill -9 {pid} 2>/dev/null || true")

    # Read exit code
    rc_cmd = host.run(f"cat {rc_file} 2>/dev/null || echo 1")
    rc_str = rc_cmd.stdout.strip().split("\n")[-1]
    try:
        rc = int(rc_str)
    except ValueError:
        rc = 1

    # Get full output
    log_cmd = host.run(f"cat {log_file} 2>/dev/null")
    output = log_cmd.stdout.strip() if log_cmd.rc == 0 else ""

    # Clean up temp files
    host.run(f"rm -f {log_file} {pid_file} {rc_file} {wrapper}")

    if rc != 0 and elapsed >= timeout:
        return {
            "success": False,
            "output": output,
            "error": f"omnia.sh --uninstall timed out after {timeout}s"
        }

    if rc != 0:
        # Include actual error output for debugging
        error_msg = f"omnia.sh --uninstall failed (exit code {rc})"
        if output:
            # Show last few lines of output for context
            lines = output.strip().split('\n')
            last_lines = lines[-5:] if len(lines) > 5 else lines
            error_msg += f"\n\nLast output lines:\n" + "\n".join(last_lines)
        return {
            "success": False,
            "output": output,
            "error": error_msg
        }

    return {
        "success": True,
        "output": output,
        "error": ""
    }


def setup_internal_nfs_server(host) -> Dict[str, Any]:
    """
    Setup internal NFS server on OIM when nfs_type is internal.

    Installs nfs-utils, creates share directory, configures exports with *, and starts services.
    If oim_server_ip is blank, runs on localhost.

    Args:
        host: testinfra host object

    Returns:
        Dict with 'success', 'details', 'error'
    """
    nfs_share_path = OMNIA_SH_VARS["nfs_share_path"]

    if not nfs_share_path:
        return {
            "success": False,
            "details": None,
            "error": "nfs_share_path not configured in omnia_test_config.yml"
        }

    # Check if NFS server is already configured
    check_exports = host.run(f"grep -q '{nfs_share_path}' /etc/exports 2>/dev/null")
    if check_exports.rc == 0:
        return {
            "success": False,
            "details": None,
            "error": f"NFS export already configured for {nfs_share_path}. Remove existing config first."
        }

    # Install nfs-utils
    install_cmd = host.run("dnf install -y nfs-utils")
    if install_cmd.rc != 0:
        return {
            "success": False,
            "details": None,
            "error": f"Failed to install nfs-utils: {install_cmd.stderr}"
        }

    # Create share directory
    mkdir_cmd = host.run(f"mkdir -p {nfs_share_path}")
    if mkdir_cmd.rc != 0:
        return {
            "success": False,
            "details": None,
            "error": f"Failed to create directory: {mkdir_cmd.stderr}"
        }

    # Add export entry with * (allow all)
    export_line = f"{nfs_share_path} *(rw,sync,no_root_squash,no_subtree_check)"
    add_export = host.run(f"echo '{export_line}' >> /etc/exports")
    if add_export.rc != 0:
        return {
            "success": False,
            "details": None,
            "error": f"Failed to add export: {add_export.stderr}"
        }

    # Export and start services
    host.run("exportfs -a")
    host.run("systemctl enable --now nfs-server")
    host.run("systemctl enable --now rpcbind")

    # Verify
    verify = host.run(f"exportfs -v | grep -q '{nfs_share_path}'")
    if verify.rc == 0:
        return {
            "success": True,
            "details": f"NFS server configured with export: {nfs_share_path} *(rw,sync,no_root_squash,no_subtree_check)",
            "error": ""
        }

    return {
        "success": False,
        "details": None,
        "error": "NFS export not found after configuration"
    }
