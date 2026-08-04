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
Repo Manager — Core Verification Functions.

Functions for verifying repo_manager deployment based on actual
src/repo_manager playbooks, roles, and modules:

- Pulp container checks (running, healthy, port, CLI, API endpoint)
- Pulp infrastructure checks (quadlet, certs, directories)
- Input config file presence
- repo_status.yml validation
- Repository sync verification
- Cleanup verification (container, image, data, services, logs)

All functions use testinfra host — repo_manager runs on localhost (OIM).

Reference:
    src/repo_manager/playbooks/repo_manager.yml
        (tags: validate, deploy, download, status,
         cleanup_pulp, cleanup_repos)
    src/repo_manager/roles/deploy_pulp/ (container deployment, CLI config, certs)
    src/repo_manager/roles/pulp_validation/ (health checks)
    src/repo_manager/playbooks/cleanup/cleanup_pulp.yml (full cleanup)
"""

import json
import os
from typing import Dict, Any

import yaml

from .host_func import load_test_config
from omnia_auto import read_remote_env, resolve_domain_input_path
from ..vars.common_vars import (
    DOMAIN_NAME,
    ENV_OMNIA_DATA_PATH,
    ENV_OMNIA_PROJECT_NAME,
    PULP_CONTAINER,
    PULP_IMAGE,
    PULP_PORT,
    PULP_CONFIG_BASE_DIR,
    PULP_CONFIG_DIR,
    PULP_CERTS_DIR,
    PULP_SERVER_CRT,
    PULP_SERVER_KEY,
    PULP_QUADLET_PATH,
    PULP_HA_DIR,
    PULP_CLI_CONFIG,
    PULP_LOGS_DIR,
    PULP_CLEANUP_DIRECTORIES,
    RHEL_REPO_CERTS_DIR,
    REPO_MANAGER_LOG_DIR,
    REPO_MANAGER_OFFLINE_REPO_DIR,
    OMNIA_TARGET_FILE,
    CONFIG_FILE,
    CREDENTIALS_FILE_NAME,
    CREDENTIALS_KEY_NAME,
    ENDPOINT_CONFIG_FILE,
    SOFTWARE_CONFIG_FILE,
    REPO_STATUS_PATH,
    SYSTEMD_SERVICES,
    CMDS,
)


# =============================================================================
# HELPER: LOAD CONFIG FROM TARGET
# =============================================================================

def _get_shared_path() -> str:
    """Get shared_path from test_config or default."""
    config = load_test_config()
    return config["shared_path"]


def _get_project_name() -> str:
    """Get project_name from test_config or default."""
    config = load_test_config()
    return config["project_name"]


def _get_remote_input_path(host: Any) -> str:
    """Get the deployed input path on target.

    Uses env vars to resolve::

        <OMNIA_DATA_PATH>/repo_manager/input/<project>/
    """
    return resolve_domain_input_path(
        host, DOMAIN_NAME, ENV_OMNIA_DATA_PATH, ENV_OMNIA_PROJECT_NAME,
    )


# =============================================================================
# PULP CONTAINER CHECKS
# =============================================================================

def check_pulp_container_running(host: Any) -> Dict[str, Any]:
    """Check if Pulp container is running on the target host.

    Mirrors preflight_checks.yml: checks podman container status.

    Returns:
        Dict with 'success', 'status', 'error', 'details'.
    """
    cmd = host.run(
        CMDS["podman_ps_check"].format(container=PULP_CONTAINER)
    )

    if cmd.rc == 0 and PULP_CONTAINER in cmd.stdout:
        status_cmd = host.run(
            CMDS["podman_ps"].format(container=PULP_CONTAINER)
        )
        status = status_cmd.stdout.strip() if status_cmd.rc == 0 else "running"
        return {
            "success": True,
            "status": status,
            "error": None,
            "details": f"Container '{PULP_CONTAINER}' is running",
        }

    # Check if container exists but not running
    check_all = host.run(
        CMDS["podman_ps_all"].format(container=PULP_CONTAINER)
    )
    if check_all.rc == 0 and PULP_CONTAINER in check_all.stdout:
        status = check_all.stdout.strip()
        return {
            "success": False,
            "status": status,
            "error": f"Container exists but not running: {status}",
            "details": f"Container '{PULP_CONTAINER}' exists but is not running",
        }

    return {
        "success": False,
        "status": "not_found",
        "error": f"Container '{PULP_CONTAINER}' not found",
        "details": f"Container '{PULP_CONTAINER}' not found on target",
    }


def check_pulp_healthy(host: Any) -> Dict[str, Any]:
    """Check if Pulp service is healthy and responding.

    Runs ``pulp status`` and checks database_connection.connected,
    mirroring deploy_pulp.yml Phase 2.5 health check.

    Returns:
        Dict with 'success', 'details', 'error'.
    """
    cmd = host.run(CMDS["pulp_status"])
    if cmd.rc != 0:
        return {
            "success": False,
            "details": "Pulp CLI status command failed",
            "error": f"pulp status failed (rc={cmd.rc}): {cmd.stderr.strip()}",
        }

    try:
        status_data = json.loads(cmd.stdout)
    except (json.JSONDecodeError, ValueError) as exc:
        return {
            "success": False,
            "details": "Failed to parse pulp status output",
            "error": f"JSON parse error: {exc}",
        }

    db_connected = (
        status_data.get("database_connection", {}).get("connected", False)
    )

    if db_connected:
        version = status_data.get("versions", [{}])
        version_str = ""
        if version and isinstance(version, list):
            for v in version:
                if v.get("component") == "core":
                    version_str = v.get("version", "")
                    break

        content_origin = (
            status_data
            .get("content_settings", {})
            .get("content_origin", "")
        )

        details_lines = [
            "  Database: connected",
        ]
        if version_str:
            details_lines.append(f"  Pulp core version: {version_str}")
        if content_origin:
            details_lines.append(f"  Content origin: {content_origin}")

        return {
            "success": True,
            "details": "\n".join(details_lines),
            "error": None,
            "data": status_data,
        }

    return {
        "success": False,
        "details": "Pulp database not connected",
        "error": "database_connection.connected is False",
    }


def check_pulp_port_listening(host: Any) -> Dict[str, Any]:
    """Check if Pulp port (2225) is listening.

    Returns:
        Dict with 'success', 'details', 'error'.
    """
    cmd = host.run(CMDS["ss_listen_port"].format(port=PULP_PORT))
    if cmd.rc == 0 and str(PULP_PORT) in cmd.stdout:
        return {
            "success": True,
            "details": f"  {PULP_PORT}/tcp: listening",
            "error": None,
        }

    return {
        "success": False,
        "details": f"  {PULP_PORT}/tcp: NOT LISTENING",
        "error": f"Port {PULP_PORT} is not listening",
    }


def check_pulp_cli_configured(host: Any) -> Dict[str, Any]:
    """Check if Pulp CLI is installed and configured.

    Verifies /usr/local/bin/pulp symlink and cli.toml config.
    References: deploy_pulp/tasks/setup_pulp_cli.yml

    Returns:
        Dict with 'success', 'details', 'error'.
    """
    # Check CLI binary
    which_cmd = host.run(CMDS["which_cmd"].format(binary="pulp"))
    cli_available = which_cmd.rc == 0

    if not cli_available:
        file_cmd = host.run(
            CMDS["file_exists"].format(path="/usr/local/bin/pulp")
        )
        cli_available = file_cmd.rc == 0 and "exists" in file_cmd.stdout

    # Check CLI config file
    config_cmd = host.run(
        CMDS["file_exists"].format(path=PULP_CLI_CONFIG)
    )
    config_exists = config_cmd.rc == 0 and "exists" in config_cmd.stdout

    details_lines = [
        f"  pulp binary: {'found' if cli_available else 'NOT FOUND'}",
        f"  {PULP_CLI_CONFIG}: {'exists' if config_exists else 'NOT FOUND'}",
    ]

    return {
        "success": cli_available and config_exists,
        "details": "\n".join(details_lines),
        "error": None if (cli_available and config_exists) else (
            "Pulp CLI not found" if not cli_available
            else "Pulp CLI config not found"
        ),
    }


def check_pulp_api_endpoint(host: Any) -> Dict[str, Any]:
    """Verify Pulp API endpoint is reachable.

    Mirrors deploy_pulp/tasks/verify_status.yml API verification.
    Tries HTTPS first, falls back to HTTP.

    Returns:
        Dict with 'success', 'protocol', 'details', 'error'.
    """
    for scheme, cmd_key in [
        ("https", "curl_pulp_status_https"),
        ("http", "curl_pulp_status_http"),
    ]:
        cmd = host.run(CMDS[cmd_key].format(port=PULP_PORT))
        if cmd.rc == 0 and cmd.stdout.strip():
            try:
                data = json.loads(cmd.stdout)
                if "versions" in data or "database_connection" in data:
                    return {
                        "success": True,
                        "protocol": scheme,
                        "details": f"  Pulp API reachable via {scheme.upper()} on port {PULP_PORT}",
                        "error": None,
                    }
            except (json.JSONDecodeError, ValueError):
                pass

    return {
        "success": False,
        "protocol": None,
        "details": f"  Pulp API NOT reachable on port {PULP_PORT}",
        "error": f"Cannot reach Pulp API at localhost:{PULP_PORT}",
    }


def check_pulp_quadlet_exists(host: Any) -> Dict[str, Any]:
    """Verify Pulp quadlet/systemd unit file exists.

    References: deploy_pulp/tasks/preflight_checks.yml

    Returns:
        Dict with 'success', 'details'.
    """
    cmd = host.run(CMDS["file_exists"].format(path=PULP_QUADLET_PATH))
    exists = cmd.rc == 0 and "exists" in cmd.stdout

    return {
        "success": exists,
        "details": (
            f"  {PULP_QUADLET_PATH}: present"
            if exists
            else f"  {PULP_QUADLET_PATH}: NOT FOUND"
        ),
    }


def check_pulp_certs(host: Any) -> Dict[str, Any]:
    """Verify Pulp SSL certificates exist (HTTPS mode).

    References: deploy_pulp/tasks/deploy_container_https.yml

    Returns:
        Dict with 'success', 'results', 'details'.
    """
    cert_files = {
        "server_crt": PULP_SERVER_CRT,
        "server_key": PULP_SERVER_KEY,
    }
    results = {}
    all_present = True

    for name, path in cert_files.items():
        cmd = host.run(CMDS["file_exists"].format(path=path))
        exists = cmd.rc == 0 and "exists" in cmd.stdout
        results[name] = {"path": path, "exists": exists}
        if not exists:
            all_present = False

    details_lines = []
    for name, info in results.items():
        status = "present" if info["exists"] else "NOT FOUND"
        details_lines.append(f"  {name}: {status} ({info['path']})")

    return {
        "success": all_present,
        "results": results,
        "details": "\n".join(details_lines),
    }


def check_pulp_directories(host: Any) -> Dict[str, Any]:
    """Verify required Pulp directories exist after deployment.

    References: deploy_pulp/tasks/preflight_checks.yml

    Returns:
        Dict with 'success', 'results', 'details'.
    """
    dirs_to_check = [
        PULP_CONFIG_DIR,
        PULP_LOGS_DIR,
        PULP_CERTS_DIR,
        PULP_HA_DIR,
    ]
    results = []
    all_present = True

    for dir_path in dirs_to_check:
        cmd = host.run(CMDS["dir_exists"].format(path=dir_path))
        exists = cmd.rc == 0 and "exists" in cmd.stdout
        results.append({"path": dir_path, "exists": exists})
        if not exists:
            all_present = False

    details_lines = []
    for r in results:
        status = "exists" if r["exists"] else "NOT FOUND"
        details_lines.append(f"  {r['path']}: {status}")

    return {
        "success": all_present,
        "results": results,
        "details": "\n".join(details_lines),
    }


# =============================================================================
# INPUT FILE CHECKS
# =============================================================================

def check_input_config_exists(host: Any) -> Dict[str, Any]:
    """Verify repo_manager_config.yml exists on target.

    Returns:
        Dict with 'success', 'details'.
    """
    input_dir = _get_remote_input_path(host)
    cfg_path = f"{input_dir}/{CONFIG_FILE}"

    cmd = host.run(CMDS["file_exists"].format(path=cfg_path))
    exists = cmd.rc == 0 and "exists" in cmd.stdout

    return {
        "success": exists,
        "path": cfg_path,
        "details": (
            f"  {CONFIG_FILE}: present at {cfg_path}"
            if exists
            else f"  {CONFIG_FILE}: NOT FOUND at {cfg_path}"
        ),
    }


def check_credentials_present(host: Any) -> Dict[str, Any]:
    """Verify credentials file is present on target.

    Returns:
        Dict with 'success', 'details'.
    """
    input_dir = _get_remote_input_path(host)
    cred_path = f"{input_dir}/{CREDENTIALS_FILE_NAME}"

    cmd = host.run(CMDS["file_exists"].format(path=cred_path))
    exists = cmd.rc == 0 and "exists" in cmd.stdout

    return {
        "success": exists,
        "details": (
            f"  {CREDENTIALS_FILE_NAME}: present at {cred_path}"
            if exists
            else f"  {CREDENTIALS_FILE_NAME}: NOT FOUND at {cred_path}"
        ),
    }


def check_endpoint_config_exists(host: Any) -> Dict[str, Any]:
    """Verify repo_manager_endpoint_config.yml exists on target.

    Returns:
        Dict with 'success', 'details'.
    """
    input_dir = _get_remote_input_path(host)
    cfg_path = f"{input_dir}/{ENDPOINT_CONFIG_FILE}"

    cmd = host.run(CMDS["file_exists"].format(path=cfg_path))
    exists = cmd.rc == 0 and "exists" in cmd.stdout

    return {
        "success": exists,
        "path": cfg_path,
        "details": (
            f"  {ENDPOINT_CONFIG_FILE}: present at {cfg_path}"
            if exists
            else f"  {ENDPOINT_CONFIG_FILE}: NOT FOUND at {cfg_path}"
        ),
    }


def check_software_config_exists(host: Any) -> Dict[str, Any]:
    """Verify software_config.json exists on target.

    Returns:
        Dict with 'success', 'details'.
    """
    input_dir = _get_remote_input_path(host)
    cfg_path = f"{input_dir}/{SOFTWARE_CONFIG_FILE}"

    cmd = host.run(CMDS["file_exists"].format(path=cfg_path))
    exists = cmd.rc == 0 and "exists" in cmd.stdout

    return {
        "success": exists,
        "path": cfg_path,
        "details": (
            f"  {SOFTWARE_CONFIG_FILE}: present at {cfg_path}"
            if exists
            else f"  {SOFTWARE_CONFIG_FILE}: NOT FOUND at {cfg_path}"
        ),
    }


def check_software_config_valid(host: Any) -> Dict[str, Any]:
    """Verify software_config.json is valid JSON with required fields.

    Mirrors validate/validate_config.yml Phase 2 JSON validation.

    Returns:
        Dict with 'success', 'details', 'error'.
    """
    input_dir = _get_remote_input_path(host)
    cfg_path = f"{input_dir}/{SOFTWARE_CONFIG_FILE}"

    cmd = host.run(CMDS["cat_file"].format(path=cfg_path))
    if cmd.rc != 0 or not cmd.stdout.strip():
        return {
            "success": False,
            "details": f"  {SOFTWARE_CONFIG_FILE}: not readable",
            "error": f"Cannot read {cfg_path}",
        }

    try:
        data = json.loads(cmd.stdout)
    except (json.JSONDecodeError, ValueError) as exc:
        return {
            "success": False,
            "details": f"  {SOFTWARE_CONFIG_FILE}: invalid JSON",
            "error": f"JSON parse error: {exc}",
        }

    required_keys = ["cluster_os_type", "cluster_os_version", "repo_config", "softwares"]
    missing = [k for k in required_keys if k not in data]

    if missing:
        return {
            "success": False,
            "details": f"  Missing required keys: {', '.join(missing)}",
            "error": f"software_config.json missing keys: {', '.join(missing)}",
        }

    details_lines = [
        f"  cluster_os_type: {data.get('cluster_os_type')}",
        f"  cluster_os_version: {data.get('cluster_os_version')}",
        f"  repo_config: {data.get('repo_config')}",
        f"  softwares: {len(data.get('softwares', []))} entries",
    ]

    return {
        "success": True,
        "details": "\n".join(details_lines),
        "error": None,
        "data": data,
    }


# =============================================================================
# REPO STATUS VERIFICATION
# =============================================================================

def check_repo_status_file(host: Any) -> Dict[str, Any]:
    """Verify repo_status.yml exists and reports success.

    Mirrors generate_local_repo_access.py output format.

    Returns:
        Dict with 'success', 'status', 'details', 'error'.
    """
    shared = _get_shared_path()
    project = _get_project_name()
    status_path = REPO_STATUS_PATH.format(
        shared_path=shared, project=project
    )

    cmd = host.run(CMDS["cat_file"].format(path=status_path))
    if cmd.rc != 0 or not cmd.stdout.strip():
        return {
            "success": False,
            "not_found": True,
            "status": "not_found",
            "status_path": status_path,
            "details": None,
            "error": (
                f"repo_status.yml not found at {status_path}"
            ),
        }

    try:
        data = yaml.safe_load(cmd.stdout)
    except yaml.YAMLError as exc:
        return {
            "success": False,
            "status": "parse_error",
            "status_path": status_path,
            "details": None,
            "error": f"Failed to parse repo_status.yml: {exc}",
        }

    overall = data.get("overall_status", "").lower()
    if overall == "success":
        rpm_repos = data.get("rpm_repos", {})
        repo_count = 0
        for arch_repos in rpm_repos.values():
            if isinstance(arch_repos, dict):
                repo_count += len(arch_repos)
            elif isinstance(arch_repos, list):
                repo_count += len(arch_repos)

        detail_lines = [
            "overall_status: success",
            f"cluster_os_type: {data.get('cluster_os_type', 'unknown')}",
            f"cluster_os_version: {data.get('cluster_os_version', 'unknown')}",
            f"RPM repositories: {repo_count}",
        ]

        # Report file repos if present
        file_repos = data.get("file_repos", {})
        if file_repos:
            detail_lines.append(f"File repositories: {len(file_repos)}")

        return {
            "success": True,
            "status": "success",
            "status_path": status_path,
            "details": "\n".join(detail_lines),
            "error": None,
            "data": data,
        }

    return {
        "success": False,
        "status": overall or "unknown",
        "status_path": status_path,
        "details": None,
        "error": (
            f"overall_status is '{overall}', expected 'success'"
        ),
    }


# =============================================================================
# REPOSITORY SYNC VERIFICATION
# =============================================================================

def check_repos_synced(host: Any) -> Dict[str, Any]:
    """Verify repositories are synced in Pulp.

    Queries Pulp for the list of RPM repositories.

    Returns:
        Dict with 'success', 'count', 'details', 'error'.
    """
    cmd = host.run(CMDS["pulp_repo_list"])
    if cmd.rc != 0:
        return {
            "success": False,
            "count": 0,
            "details": "Failed to query Pulp repositories",
            "error": f"pulp rpm repository list failed (rc={cmd.rc})",
        }

    try:
        repos = json.loads(cmd.stdout)
    except (json.JSONDecodeError, ValueError):
        return {
            "success": False,
            "count": 0,
            "details": "Failed to parse Pulp repository list",
            "error": "JSON parse error on pulp rpm repository list output",
        }

    if not isinstance(repos, list):
        repos = repos.get("results", []) if isinstance(repos, dict) else []

    repo_count = len(repos)
    if repo_count > 0:
        repo_names = [r.get("name", "unknown") for r in repos[:10]]
        details_lines = [f"  Synced repositories: {repo_count}"]
        for name in repo_names:
            details_lines.append(f"    - {name}")
        if repo_count > 10:
            details_lines.append(f"    ... and {repo_count - 10} more")

        return {
            "success": True,
            "count": repo_count,
            "details": "\n".join(details_lines),
            "error": None,
        }

    return {
        "success": False,
        "count": 0,
        "details": "  No repositories found in Pulp",
        "error": "No RPM repositories synced in Pulp",
    }


# =============================================================================
# CLEANUP VERIFICATION
# Mirrors cleanup_pulp.yml phases
# =============================================================================

def check_pulp_removed(host: Any) -> Dict[str, Any]:
    """Verify Pulp container is NOT running after cleanup.

    Returns:
        Dict with 'success', 'details'.
    """
    cmd = host.run(
        CMDS["podman_ps_check"].format(container=PULP_CONTAINER)
    )
    still_running = cmd.rc == 0 and PULP_CONTAINER in cmd.stdout

    return {
        "success": not still_running,
        "details": (
            f"Container '{PULP_CONTAINER}': removed"
            if not still_running
            else f"Container '{PULP_CONTAINER}': STILL RUNNING"
        ),
    }


def check_pulp_data_removed(host: Any) -> Dict[str, Any]:
    """Verify Pulp data directories are removed after cleanup.

    Checks all directories from cleanup_pulp_vars.yml:
    - pulp_config_base_dir (/opt/omnia/pulp_config)
    - rhel_repo_certs (/opt/omnia/rhel_repo_certs)
    - offline_repo (/opt/omnia/offline_repo)

    Returns:
        Dict with 'success', 'results', 'details'.
    """
    results = []
    all_removed = True

    for dir_path in PULP_CLEANUP_DIRECTORIES:
        cmd = host.run(CMDS["dir_exists"].format(path=dir_path))
        exists = cmd.rc == 0 and "exists" in cmd.stdout
        results.append({"path": dir_path, "removed": not exists})
        if exists:
            all_removed = False

    details_lines = []
    for r in results:
        status = "removed" if r["removed"] else "still exists"
        details_lines.append(f"  {r['path']}: {status}")

    return {
        "success": all_removed,
        "results": results,
        "details": "\n".join(details_lines),
    }


def check_pulp_image_removed(host: Any) -> Dict[str, Any]:
    """Verify Pulp container image is removed after cleanup.

    Mirrors cleanup_pulp.yml: ``podman rmi -f {{ pulp_image }}``

    Returns:
        Dict with 'success', 'details'.
    """
    cmd = host.run(CMDS["podman_image_exists"].format(image=PULP_IMAGE))
    still_exists = cmd.rc == 0

    return {
        "success": not still_exists,
        "details": (
            f"Image '{PULP_IMAGE}': removed"
            if not still_exists
            else f"Image '{PULP_IMAGE}': still present"
        ),
    }


def check_pulp_quadlet_removed(host: Any) -> Dict[str, Any]:
    """Verify Pulp quadlet/systemd file is removed after cleanup.

    Mirrors cleanup_pulp.yml: removal of systemd unit file.

    Returns:
        Dict with 'success', 'details'.
    """
    cmd = host.run(CMDS["file_exists"].format(path=PULP_QUADLET_PATH))
    exists = cmd.rc == 0 and "exists" in cmd.stdout

    return {
        "success": not exists,
        "details": (
            f"  {PULP_QUADLET_PATH}: removed"
            if not exists
            else f"  {PULP_QUADLET_PATH}: still exists"
        ),
    }


def check_services_removed(host: Any) -> Dict[str, Any]:
    """Verify Pulp systemd services are inactive/removed.

    Returns:
        Dict with 'success', 'results', 'details'.
    """
    results = []
    all_inactive = True

    for svc in SYSTEMD_SERVICES:
        cmd = host.run(
            CMDS["systemctl_is_active"].format(service=svc)
        )
        state = cmd.stdout.strip() if cmd.rc == 0 else "inactive"
        is_active = state == "active"
        results.append({
            "service": svc,
            "state": state,
            "removed": not is_active,
        })
        if is_active:
            all_inactive = False

    details_lines = []
    for r in results:
        status = "removed" if r["removed"] else f"still {r['state']}"
        details_lines.append(f"  {r['service']}: {status}")

    return {
        "success": all_inactive,
        "results": results,
        "details": "\n".join(details_lines),
    }


def check_containers_removed(host: Any) -> Dict[str, Any]:
    """Verify Pulp container doesn't exist (even stopped).

    Returns:
        Dict with 'success', 'details'.
    """
    cmd = host.run(
        CMDS["podman_ps_all"].format(container=PULP_CONTAINER)
    )
    still_exists = cmd.rc == 0 and PULP_CONTAINER in cmd.stdout

    return {
        "success": not still_exists,
        "details": (
            f"Container '{PULP_CONTAINER}': fully removed"
            if not still_exists
            else f"Container '{PULP_CONTAINER}': still exists (stopped)"
        ),
    }


def check_pulp_logs_cleaned(host: Any) -> Dict[str, Any]:
    """Verify Pulp log directory is cleaned after cleanup.

    Mirrors cleanup_pulp.yml Phase 4: log cleanup.

    Returns:
        Dict with 'success', 'details'.
    """
    # Check both the new log dir and legacy log dir
    log_dirs = [
        PULP_LOGS_DIR,
        REPO_MANAGER_LOG_DIR,
    ]

    results = []
    for log_dir in log_dirs:
        cmd = host.run(CMDS["dir_exists"].format(path=log_dir))
        exists = cmd.rc == 0 and "exists" in cmd.stdout
        if exists:
            # Check if directory is empty (recreated empty)
            count_cmd = host.run(
                CMDS["find_file_count"].format(path=log_dir)
            )
            file_count = int(count_cmd.stdout.strip()) if count_cmd.rc == 0 else -1
            results.append({
                "path": log_dir,
                "exists": True,
                "empty": file_count == 0,
                "file_count": file_count,
            })
        else:
            results.append({
                "path": log_dir,
                "exists": False,
                "empty": True,
                "file_count": 0,
            })

    # Success if all log dirs are either removed or empty
    all_clean = all(r["empty"] for r in results)

    details_lines = []
    for r in results:
        if not r["exists"]:
            details_lines.append(f"  {r['path']}: removed")
        elif r["empty"]:
            details_lines.append(f"  {r['path']}: exists (empty/clean)")
        else:
            details_lines.append(
                f"  {r['path']}: has {r['file_count']} log files"
            )

    return {
        "success": all_clean,
        "results": results,
        "details": "\n".join(details_lines),
    }


def check_credentials_removed(host: Any) -> Dict[str, Any]:
    """Verify credentials files are removed after cleanup.

    Returns:
        Dict with 'success', 'results', 'details'.
    """
    input_dir = _get_remote_input_path(host)

    files_to_check = [
        f"{input_dir}/{CREDENTIALS_FILE_NAME}",
        f"{input_dir}/{CREDENTIALS_KEY_NAME}",
    ]

    results = []
    all_removed = True
    for fpath in files_to_check:
        cmd = host.run(CMDS["file_exists"].format(path=fpath))
        exists = cmd.rc == 0 and "exists" in cmd.stdout
        fname = os.path.basename(fpath)
        results.append({
            "file": fname,
            "path": fpath,
            "removed": not exists,
        })
        if exists:
            all_removed = False

    details_lines = []
    for r in results:
        status = "removed" if r["removed"] else "still exists"
        details_lines.append(f"  {r['file']}: {status}")

    return {
        "success": all_removed,
        "results": results,
        "details": "\n".join(details_lines),
    }
