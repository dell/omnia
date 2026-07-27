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
    from main.library.functions.omnia_sh_func import (
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
        check_ssh_key_pair_exists,
        check_ssh_config_entry,
        check_authorized_key,
        check_container_image_exists,
        check_omnia_dir_in_container,
        check_log_dirs_exist,
        check_omnia_version,
        # Cleanup verification functions
        check_container_not_running,
        check_service_not_exists,
        check_fstab_entry_removed,
        check_mount_removed,
        check_ssh_key_pair_removed,
        check_ssh_config_entry_removed,
        check_known_hosts_cleaned,
    )

Author: Dell Technologies
"""

import time
from typing import Dict, Any

from ..vars.omnia_sh_vars import OMNIA_SH_VARS, TEST_VARS
from ..vars.common_vars import (
    CMDS, OMNIA_CORE_CONTAINER,
    SSH_KEY_PRIV, SSH_KEY_PUB, KNOWN_HOSTS_PATTERN,
)
from .host_func import run_on_oim, run_in_container

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
    cmd = run_on_oim(host, CMDS["podman_ps_names"])

    if cmd.rc == 0 and OMNIA_CORE_CONTAINER in cmd.stdout:
        status_cmd = run_on_oim(host, CMDS["podman_ps_detail"])
        parts = status_cmd.stdout.strip().split('|')

        return {
            "success": True,
            "details": {
                "container": parts[0] if len(parts) > 0 else OMNIA_CORE_CONTAINER,
                "status": parts[1] if len(parts) > 1 else "unknown",
                "image": parts[2] if len(parts) > 2 else "unknown",
                "ports": parts[3] if len(parts) > 3 else "none",
            },
            "error": None
        }

    exists_cmd = run_on_oim(host, CMDS["podman_ps_all_names"])
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
    check = run_on_oim(host, CMDS["file_exists"].format(path=path))

    if check.rc == 0 and "exists" in check.stdout:
        info = run_on_oim(host, CMDS["file_stat"].format(path=path)).stdout.strip()
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

    status = run_on_oim(host, CMDS["systemctl_is_active"].format(service=service_name)).stdout.strip()
    info = run_on_oim(host, CMDS["systemctl_status"].format(service=service_name)).stdout.strip()

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

    cmd = run_on_oim(host, f"ssh -o BatchMode=yes -o ConnectTimeout={timeout} {alias} 'whoami && pwd && echo SSH_OK'")
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

    cmd = run_on_oim(
        host,
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
    cmd = run_on_oim(host, CMDS["podman_ps_check"])

    if cmd.rc != 0:
        return {
            "success": True,
            "details": f"Container {OMNIA_CORE_CONTAINER} is not running",
            "error": None
        }

    return {
        "success": False,
        "details": None,
        "error": f"Container {OMNIA_CORE_CONTAINER} is still running"
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

    check = run_on_oim(host, CMDS["file_exists"].format(path=service_file))

    if check.rc != 0 or "exists" not in check.stdout:
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

    cmd = run_on_oim(host, CMDS["grep_fstab"].format(pattern=omnia_shared_path))

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

    cmd = run_on_oim(host, CMDS["mount_check"].format(path=omnia_shared_path))

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


def check_ssh_key_pair_exists(host) -> Dict[str, Any]:
    """
    Check if SSH key pair (oim_rsa + oim_rsa.pub) exists on OIM host.

    Args:
        host: testinfra host object

    Returns:
        Dict with 'success', 'details', 'error'
    """
    priv_check = run_on_oim(host, CMDS["file_exists"].format(path=SSH_KEY_PRIV))
    pub_check = run_on_oim(host, CMDS["file_exists"].format(path=SSH_KEY_PUB))

    priv_exists = priv_check.rc == 0 and "exists" in priv_check.stdout
    pub_exists = pub_check.rc == 0 and "exists" in pub_check.stdout

    if priv_exists and pub_exists:
        priv_info = run_on_oim(host, CMDS["file_stat"].format(path=SSH_KEY_PRIV)).stdout.strip()
        pub_info = run_on_oim(host, CMDS["file_stat"].format(path=SSH_KEY_PUB)).stdout.strip()
        return {
            "success": True,
            "details": f"{priv_info}\n{pub_info}",
            "error": None
        }

    missing = []
    if not priv_exists:
        missing.append(SSH_KEY_PRIV)
    if not pub_exists:
        missing.append(SSH_KEY_PUB)

    return {
        "success": False,
        "details": None,
        "error": f"SSH key files missing: {', '.join(missing)}"
    }


def check_ssh_config_entry(host) -> Dict[str, Any]:
    """
    Check if ~/.ssh/config contains a Host omnia_core entry.

    Args:
        host: testinfra host object

    Returns:
        Dict with 'success', 'details', 'error'
    """
    cmd = run_on_oim(host, CMDS["ssh_config_grep"].format(alias=OMNIA_CORE_CONTAINER))

    if cmd.rc == 0 and OMNIA_CORE_CONTAINER in cmd.stdout:
        return {
            "success": True,
            "details": cmd.stdout.strip(),
            "error": None
        }

    return {
        "success": False,
        "details": None,
        "error": f"No 'Host {OMNIA_CORE_CONTAINER}' entry in ~/.ssh/config"
    }


def check_authorized_key(host) -> Dict[str, Any]:
    """
    Check if oim_rsa.pub key is in authorized_keys.

    Args:
        host: testinfra host object

    Returns:
        Dict with 'success', 'details', 'error'
    """
    pub_check = run_on_oim(host, CMDS["file_exists"].format(path=SSH_KEY_PUB))
    if pub_check.rc != 0 or "exists" not in pub_check.stdout:
        return {
            "success": False,
            "details": None,
            "error": f"Public key file not found: {SSH_KEY_PUB}"
        }

    cmd = run_on_oim(host, CMDS["authorized_keys_grep"].format(pub_key=SSH_KEY_PUB))

    if cmd.rc == 0:
        return {
            "success": True,
            "details": "oim_rsa.pub found in authorized_keys",
            "error": None
        }

    return {
        "success": False,
        "details": None,
        "error": "oim_rsa.pub NOT found in authorized_keys"
    }


def check_container_image_exists(host) -> Dict[str, Any]:
    """
    Check if omnia_core container image exists locally.

    Args:
        host: testinfra host object

    Returns:
        Dict with 'success', 'details', 'error'
    """
    cmd = run_on_oim(host, CMDS["podman_images"])

    if cmd.rc == 0 and OMNIA_CORE_CONTAINER in cmd.stdout:
        return {
            "success": True,
            "details": cmd.stdout.strip(),
            "error": None
        }

    return {
        "success": False,
        "details": None,
        "error": f"Container image '{OMNIA_CORE_CONTAINER}' not found"
    }


def check_omnia_dir_in_container(host) -> Dict[str, Any]:
    """
    Check if /omnia/ directory exists inside the container.

    Args:
        host: testinfra host object

    Returns:
        Dict with 'success', 'details', 'error'
    """
    cmd = run_in_container(host, "test -d /omnia && ls /omnia/ | head -10")

    if cmd.rc == 0:
        return {
            "success": True,
            "details": cmd.stdout.strip(),
            "error": None
        }

    return {
        "success": False,
        "details": None,
        "error": "/omnia/ directory not found inside container"
    }


def check_log_dirs_exist(host) -> Dict[str, Any]:
    """
    Check if omnia log directories exist in the shared path.

    Args:
        host: testinfra host object

    Returns:
        Dict with 'success', 'details', 'error'
    """
    omnia_shared_path = OMNIA_SH_VARS.get("omnia_shared_path", "")

    if not omnia_shared_path:
        return {
            "success": True,
            "details": "No omnia_shared_path configured - skipping",
            "error": None
        }

    log_dirs = [
        f"{omnia_shared_path}/omnia/log/core/container",
        f"{omnia_shared_path}/omnia/log/core/playbooks",
    ]

    missing = []
    for d in log_dirs:
        check = run_on_oim(host, CMDS["dir_exists"].format(path=d))
        if check.rc != 0 or "exists" not in check.stdout:
            missing.append(d)

    if not missing:
        return {
            "success": True,
            "details": f"Log dirs exist: {', '.join(log_dirs)}",
            "error": None
        }

    return {
        "success": False,
        "details": None,
        "error": f"Missing log directories: {', '.join(missing)}"
    }


def check_omnia_version(host) -> Dict[str, Any]:
    """
    Check omnia.sh --version output.

    Args:
        host: testinfra host object

    Returns:
        Dict with 'success', 'details', 'error'
    """
    omnia_sh_path = OMNIA_SH_VARS["omnia_sh_path"]

    if not omnia_sh_path:
        return {
            "success": False,
            "details": None,
            "error": "omnia_sh_path not resolved"
        }

    cmd = run_on_oim(host, f"{omnia_sh_path} --version")

    if cmd.rc == 0 and cmd.stdout.strip():
        return {
            "success": True,
            "details": cmd.stdout.strip(),
            "error": None
        }

    return {
        "success": False,
        "details": None,
        "error": f"omnia.sh --version failed: {cmd.stderr.strip()}"
    }


def check_ssh_key_pair_removed(host) -> Dict[str, Any]:
    """
    Verify SSH key pair (oim_rsa) is removed after uninstall.

    Args:
        host: testinfra host object

    Returns:
        Dict with 'success', 'details', 'error'
    """
    still_exists = []
    priv_check = run_on_oim(host, CMDS["file_exists"].format(path=SSH_KEY_PRIV))
    if priv_check.rc == 0 and "exists" in priv_check.stdout:
        still_exists.append(SSH_KEY_PRIV)
    pub_check = run_on_oim(host, CMDS["file_exists"].format(path=SSH_KEY_PUB))
    if pub_check.rc == 0 and "exists" in pub_check.stdout:
        still_exists.append(SSH_KEY_PUB)

    if not still_exists:
        return {
            "success": True,
            "details": "SSH key pair removed",
            "error": None
        }

    return {
        "success": False,
        "details": None,
        "error": f"SSH key files still exist: {', '.join(still_exists)}"
    }


def check_ssh_config_entry_removed(host) -> Dict[str, Any]:
    """
    Verify Host omnia_core entry removed from ~/.ssh/config.

    Args:
        host: testinfra host object

    Returns:
        Dict with 'success', 'details', 'error'
    """
    cmd = run_on_oim(host, CMDS["ssh_config_grep"].format(alias=OMNIA_CORE_CONTAINER))

    if cmd.rc != 0 or OMNIA_CORE_CONTAINER not in cmd.stdout:
        return {
            "success": True,
            "details": f"Host {OMNIA_CORE_CONTAINER} entry removed from ~/.ssh/config",
            "error": None
        }

    return {
        "success": False,
        "details": None,
        "error": f"Host {OMNIA_CORE_CONTAINER} entry still in ~/.ssh/config"
    }


def check_known_hosts_cleaned(host) -> Dict[str, Any]:
    """
    Verify [localhost]:2222 entry removed from known_hosts.

    Args:
        host: testinfra host object

    Returns:
        Dict with 'success', 'details', 'error'
    """
    escaped = KNOWN_HOSTS_PATTERN.replace("[", "\\[").replace("]", "\\]")
    cmd = run_on_oim(host, CMDS["known_hosts_grep"].format(pattern=escaped))

    if cmd.rc != 0 or KNOWN_HOSTS_PATTERN not in cmd.stdout:
        return {
            "success": True,
            "details": f"{KNOWN_HOSTS_PATTERN} removed from known_hosts",
            "error": None
        }

    return {
        "success": False,
        "details": None,
        "error": f"{KNOWN_HOSTS_PATTERN} still in known_hosts"
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

    # admin_nic_ip is always required
    admin_nic_ip = OMNIA_SH_VARS["admin_nic_ip"]
    if not admin_nic_ip:
        missing.append("admin_nic_ip")

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

    check = run_on_oim(host, CMDS["file_exists"].format(path=omnia_sh_path))
    if check.rc != 0 or "exists" not in check.stdout:
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

    # Admin NIC IP (prompted after container setup starts)
    admin_nic_ip = OMNIA_SH_VARS.get("admin_nic_ip", "")
    inputs.append(admin_nic_ip)

    # Create input file
    input_content = "\n".join(inputs)
    input_file = "/tmp/omnia_sh_inputs.txt"
    run_on_oim(host, f"echo '{input_content}' > {input_file} && chmod 600 {input_file}")

    # Simple direct execution (no background)
    if not use_background:
        cmd = run_on_oim(host, f"{omnia_sh_path} --install < {input_file}")
        run_on_oim(host, f"rm -f {input_file}")  # Cleanup

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
            error_msg += "\n\nLast output lines:\n" + "\n".join(last_lines)
        return {"success": False, "output": cmd.stdout, "error": error_msg}

    # Background execution with progress (like upgrade scenario)
    log_file = "/tmp/omnia_install.log"
    pid_file = "/tmp/omnia_install.pid"
    rc_file = "/tmp/omnia_install.rc"
    wrapper = "/tmp/omnia_install.sh"

    # Write wrapper script
    run_on_oim(
        host,
        f"cat > {wrapper} << 'INSTALLEOF'\n"
        f"#!/bin/bash\n"
        f"{omnia_sh_path} --install < {input_file}\n"
        f"echo $? > {rc_file}\n"
        f"INSTALLEOF\n"
        f"chmod +x {wrapper}"
    )

    # Run wrapper in background
    run_on_oim(host, f"nohup {wrapper} > {log_file} 2>&1 & echo $! > {pid_file}")

    # Read the PID
    pid_cmd = run_on_oim(host, f"cat {pid_file}")
    pid = pid_cmd.stdout.strip()

    elapsed = 0
    while elapsed < timeout:
        time.sleep(min(poll_interval, timeout - elapsed))
        elapsed += poll_interval

        # Check if process is still running
        alive = run_on_oim(host, f"kill -0 {pid} 2>/dev/null; echo $?")
        still_running = alive.stdout.strip() == "0"

        if progress_callback:
            progress_callback(elapsed)

        if not still_running:
            break

    # If still running after timeout, kill it
    if elapsed >= timeout:
        run_on_oim(host, f"kill -9 {pid} 2>/dev/null || true")

    # Read exit code
    rc_cmd = run_on_oim(host, f"cat {rc_file} 2>/dev/null || echo 1")
    rc_str = rc_cmd.stdout.strip().split("\n")[-1]
    try:
        rc = int(rc_str)
    except ValueError:
        rc = 1

    # Get full output
    log_cmd = run_on_oim(host, f"cat {log_file} 2>/dev/null")
    output = log_cmd.stdout.strip() if log_cmd.rc == 0 else ""

    # Clean up temp files
    run_on_oim(host, f"rm -f {log_file} {pid_file} {rc_file} {input_file} {wrapper}")

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
            error_msg += "\n\nLast output lines:\n" + "\n".join(last_lines)
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
    check = run_on_oim(host, CMDS["file_exists"].format(path=omnia_sh_path))
    if check.rc != 0 or "exists" not in check.stdout:
        return {
            "success": False,
            "output": "",
            "error": f"omnia.sh not found at {omnia_sh_path}"
        }

    # Simple direct execution (no background)
    if not use_background:
        cmd = run_on_oim(host, f"echo 'y' | {omnia_sh_path} --uninstall")

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
            error_msg += "\n\nLast output lines:\n" + "\n".join(last_lines)
        return {"success": False, "output": cmd.stdout, "error": error_msg}

    # Background execution with progress (like upgrade scenario)
    log_file = "/tmp/omnia_uninstall.log"
    pid_file = "/tmp/omnia_uninstall.pid"
    rc_file = "/tmp/omnia_uninstall.rc"
    wrapper = "/tmp/omnia_uninstall.sh"

    # Write wrapper script
    run_on_oim(
        host,
        f"cat > {wrapper} << 'UNINSTALLEOF'\n"
        f"#!/bin/bash\n"
        f"echo 'y' | {omnia_sh_path} --uninstall\n"
        f"echo $? > {rc_file}\n"
        f"UNINSTALLEOF\n"
        f"chmod +x {wrapper}"
    )

    # Run wrapper in background
    run_on_oim(host, f"nohup {wrapper} > {log_file} 2>&1 & echo $! > {pid_file}")

    # Read the PID
    pid_cmd = run_on_oim(host, f"cat {pid_file}")
    pid = pid_cmd.stdout.strip()

    elapsed = 0
    while elapsed < timeout:
        time.sleep(min(poll_interval, timeout - elapsed))
        elapsed += poll_interval

        # Check if process is still running
        alive = run_on_oim(host, f"kill -0 {pid} 2>/dev/null; echo $?")
        still_running = alive.stdout.strip() == "0"

        if progress_callback:
            progress_callback(elapsed)

        if not still_running:
            break

    # If still running after timeout, kill it
    if elapsed >= timeout:
        run_on_oim(host, f"kill -9 {pid} 2>/dev/null || true")

    # Read exit code
    rc_cmd = run_on_oim(host, f"cat {rc_file} 2>/dev/null || echo 1")
    rc_str = rc_cmd.stdout.strip().split("\n")[-1]
    try:
        rc = int(rc_str)
    except ValueError:
        rc = 1

    # Get full output
    log_cmd = run_on_oim(host, f"cat {log_file} 2>/dev/null")
    output = log_cmd.stdout.strip() if log_cmd.rc == 0 else ""

    # Clean up temp files
    run_on_oim(host, f"rm -f {log_file} {pid_file} {rc_file} {wrapper}")

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
            error_msg += "\n\nLast output lines:\n" + "\n".join(last_lines)
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
