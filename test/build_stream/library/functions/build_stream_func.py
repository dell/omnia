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
Build Stream — Verification Functions

Module-specific functions for verifying build_stream infrastructure:
- Container checks (BSM, PostgreSQL, GitLab, GitLab runner)
- API health check
- PostgreSQL table verification
- Port listening checks
- Input config existence
- Cleanup verification

Each function returns Dict[str, Any] with at minimum:
    {"success": bool, "error": str, ...optional details...}
"""

import json
from typing import Dict, Any, List

from omnia_auto import run_on_host

from ..vars.common_vars import (
    CMDS,
    BSM_CONTAINER,
    POSTGRES_CONTAINER,
    GITLAB_CONTAINER,
    GITLAB_RUNNER_CONTAINER,
    BSM_API_PORT,
    BSM_HEALTH_ENDPOINT,
    GITLAB_HTTP_PORT,
    POSTGRES_DB,
    EXPECTED_POSTGRES_TABLES,
    LISTENING_PORTS,
    BS_CONFIG_FILE,
    DOMAIN_NAME,
    ENV_OMNIA_DATA_PATH,
    ENV_OMNIA_PROJECT_NAME,
)


# =============================================================================
# CONTAINER CHECKS
# =============================================================================

def check_container_running(host, container_name: str) -> Dict[str, Any]:
    """Check if a container is running via podman.

    Returns:
        Dict with success, status, error, details.
    """
    cmd = CMDS["podman_inspect"].format(container=container_name)
    result = run_on_host(host, cmd)
    stdout = result.stdout.strip() if result.stdout else ""

    if result.rc == 0 and stdout == "running":
        return {
            "success": True,
            "status": stdout,
            "error": "",
            "details": f"{container_name} is running",
        }

    # Try podman ps -a for more detail
    cmd_all = CMDS["podman_ps_all"].format(container=container_name)
    result_all = run_on_host(host, cmd_all)
    status_detail = result_all.stdout.strip() if result_all.stdout else "not found"

    return {
        "success": False,
        "status": status_detail,
        "error": f"Container {container_name} is not running (status: {stdout or 'not found'})",
        "details": status_detail,
    }


def check_bsm_container(host) -> Dict[str, Any]:
    """Check if omnia_build_stream container is running."""
    return check_container_running(host, BSM_CONTAINER)


def check_postgres_container(host) -> Dict[str, Any]:
    """Check if omnia_postgres container is running."""
    return check_container_running(host, POSTGRES_CONTAINER)


def check_gitlab_container(host) -> Dict[str, Any]:
    """Check if GitLab container is running."""
    return check_container_running(host, GITLAB_CONTAINER)


def check_gitlab_runner_container(host) -> Dict[str, Any]:
    """Check if gitlab-runner container is running."""
    return check_container_running(host, GITLAB_RUNNER_CONTAINER)


# =============================================================================
# API HEALTH CHECK
# =============================================================================

def check_build_stream_health(host) -> Dict[str, Any]:
    """Check build_stream API /health endpoint.

    Returns:
        Dict with success, error, url, status, details.
    """
    url = f"http://localhost:{BSM_API_PORT}{BSM_HEALTH_ENDPOINT}"
    cmd = CMDS["curl_health"].format(
        port=BSM_API_PORT, endpoint=BSM_HEALTH_ENDPOINT,
    )
    result = run_on_host(host, cmd)
    stdout = result.stdout.strip() if result.stdout else ""

    if result.rc != 0 or not stdout:
        return {
            "success": False,
            "error": f"API not responding at {url}",
            "url": url,
            "status": "unreachable",
            "details": "",
        }

    # Try to parse JSON response
    try:
        data = json.loads(stdout)
        status = data.get("status", "unknown")
        if status in ("healthy", "ok"):
            return {
                "success": True,
                "error": "",
                "url": url,
                "status": status,
                "details": f"API healthy: {stdout}",
            }
        return {
            "success": False,
            "error": f"API returned unhealthy status: {status}",
            "url": url,
            "status": status,
            "details": stdout,
        }
    except (json.JSONDecodeError, TypeError):
        # Non-JSON response — check if it looks successful
        if "healthy" in stdout.lower() or "ok" in stdout.lower():
            return {
                "success": True,
                "error": "",
                "url": url,
                "status": "healthy",
                "details": stdout,
            }
        return {
            "success": False,
            "error": f"Unexpected API response: {stdout[:200]}",
            "url": url,
            "status": "unknown",
            "details": stdout,
        }


# =============================================================================
# POSTGRESQL CHECKS
# =============================================================================

def verify_postgres_tables(host) -> Dict[str, Any]:
    """Verify all expected tables exist in build_stream_db.

    Returns:
        Dict with success, error, missing_tables, found_tables, details.
    """
    cmd = CMDS["psql_list_tables"].format(
        container=POSTGRES_CONTAINER, db=POSTGRES_DB,
    )
    result = run_on_host(host, cmd)
    stdout = result.stdout.strip() if result.stdout else ""

    if result.rc != 0:
        return {
            "success": False,
            "error": f"Failed to query PostgreSQL (rc={result.rc})",
            "missing_tables": EXPECTED_POSTGRES_TABLES,
            "found_tables": [],
            "details": stdout,
        }

    found = [line.strip() for line in stdout.splitlines() if line.strip()]
    missing = [t for t in EXPECTED_POSTGRES_TABLES if t not in found]

    if missing:
        return {
            "success": False,
            "error": f"Missing tables: {', '.join(missing)}",
            "missing_tables": missing,
            "found_tables": found,
            "details": f"Found {len(found)} tables, missing {len(missing)}",
        }

    return {
        "success": True,
        "error": "",
        "missing_tables": [],
        "found_tables": found,
        "details": f"All {len(EXPECTED_POSTGRES_TABLES)} expected tables found",
    }


# =============================================================================
# GITLAB CHECKS
# =============================================================================

def verify_gitlab_server_running(host) -> Dict[str, Any]:
    """Verify GitLab server is running and accessible via HTTP.

    Returns:
        Dict with success, error, url, http_code, details.
    """
    cmd = CMDS["curl_gitlab"].format(port=GITLAB_HTTP_PORT)
    result = run_on_host(host, cmd)
    stdout = result.stdout.strip() if result.stdout else ""

    url = f"http://localhost:{GITLAB_HTTP_PORT}/"

    if result.rc != 0:
        return {
            "success": False,
            "error": f"GitLab not accessible at {url}",
            "url": url,
            "http_code": "",
            "details": "",
        }

    # curl -w '%{http_code}' returns the status code
    try:
        http_code = int(stdout)
    except (ValueError, TypeError):
        http_code = 0

    if http_code in (200, 301, 302):
        return {
            "success": True,
            "error": "",
            "url": url,
            "http_code": str(http_code),
            "details": f"GitLab responding (HTTP {http_code})",
        }

    return {
        "success": False,
        "error": f"GitLab returned HTTP {http_code}",
        "url": url,
        "http_code": str(http_code),
        "details": f"Expected 200/301/302, got {http_code}",
    }


def verify_gitlab_runner_running(host) -> Dict[str, Any]:
    """Verify gitlab-runner container is running.

    Returns:
        Dict with success, error, container, status, details.
    """
    result = check_container_running(host, GITLAB_RUNNER_CONTAINER)
    return {
        "success": result["success"],
        "error": result["error"],
        "container": GITLAB_RUNNER_CONTAINER,
        "status": result["status"],
        "details": result["details"],
    }


# =============================================================================
# BUILD STREAM ENABLED CHECK
# =============================================================================

def is_build_stream_enabled(host) -> bool:
    """Check if build_stream is enabled in build_stream_config.yml on target.

    Reads the config from the domain input directory on the target host.
    """
    from omnia_auto import resolve_domain_input_path
    try:
        input_path = resolve_domain_input_path(
            host, DOMAIN_NAME, ENV_OMNIA_DATA_PATH, ENV_OMNIA_PROJECT_NAME,
        )
    except Exception:
        input_path = f"/opt/omnia/{DOMAIN_NAME}/input/project_default"

    config_path = f"{input_path}/{BS_CONFIG_FILE}"
    cmd = CMDS["cat_file"].format(path=config_path)
    result = run_on_host(host, cmd)
    stdout = result.stdout.strip() if result.stdout else ""

    if not stdout:
        return False

    try:
        import yaml
        config = yaml.safe_load(stdout) or {}
        return bool(config.get("enable_build_stream", False))
    except Exception:
        return False


# =============================================================================
# INPUT CONFIG CHECK
# =============================================================================

def check_input_config_exists(host) -> Dict[str, Any]:
    """Check if build_stream_config.yml exists on target.

    Returns:
        Dict with success, error, path, details.
    """
    from omnia_auto import resolve_domain_input_path
    try:
        input_path = resolve_domain_input_path(
            host, DOMAIN_NAME, ENV_OMNIA_DATA_PATH, ENV_OMNIA_PROJECT_NAME,
        )
    except Exception:
        input_path = f"/opt/omnia/{DOMAIN_NAME}/input/project_default"

    config_path = f"{input_path}/{BS_CONFIG_FILE}"
    cmd = CMDS["file_exists"].format(path=config_path)
    result = run_on_host(host, cmd)
    stdout = result.stdout.strip() if result.stdout else ""

    if stdout == "exists":
        return {
            "success": True,
            "error": "",
            "path": config_path,
            "details": f"{BS_CONFIG_FILE} found at {config_path}",
        }
    return {
        "success": False,
        "error": f"{BS_CONFIG_FILE} not found at {config_path}",
        "path": config_path,
        "details": "",
    }


# =============================================================================
# PORT CHECKS
# =============================================================================

def check_ports_listening(host, ports: List[int] = None) -> Dict[str, Any]:
    """Check if expected service ports are listening.

    Returns:
        Dict with success, error, open_ports, closed_ports, details.
    """
    if ports is None:
        ports = LISTENING_PORTS

    open_ports = []
    closed_ports = []

    for port in ports:
        cmd = CMDS["ss_listen_port"].format(port=port)
        result = run_on_host(host, cmd)
        stdout = result.stdout.strip() if result.stdout else ""
        if stdout and str(port) in stdout:
            open_ports.append(port)
        else:
            closed_ports.append(port)

    if closed_ports:
        return {
            "success": False,
            "error": f"Ports not listening: {closed_ports}",
            "open_ports": open_ports,
            "closed_ports": closed_ports,
            "details": f"{len(open_ports)}/{len(ports)} ports open",
        }
    return {
        "success": True,
        "error": "",
        "open_ports": open_ports,
        "closed_ports": [],
        "details": f"All {len(ports)} ports listening",
    }


# =============================================================================
# CLEANUP VERIFICATION
# =============================================================================

def check_containers_removed(host) -> Dict[str, Any]:
    """Verify build_stream containers are removed after cleanup.

    Returns:
        Dict with success, error, still_running, details.
    """
    containers = [
        BSM_CONTAINER, POSTGRES_CONTAINER,
        GITLAB_CONTAINER, GITLAB_RUNNER_CONTAINER,
    ]
    still_running = []

    for container in containers:
        result = check_container_running(host, container)
        if result["success"]:
            still_running.append(container)

    if still_running:
        return {
            "success": False,
            "error": f"Containers still running: {', '.join(still_running)}",
            "still_running": still_running,
            "details": f"{len(still_running)} container(s) still running",
        }
    return {
        "success": True,
        "error": "",
        "still_running": [],
        "details": "All build_stream containers removed",
    }


def check_ports_closed(host, ports: List[int] = None) -> Dict[str, Any]:
    """Verify service ports are closed after cleanup.

    Returns:
        Dict with success, error, still_open, details.
    """
    if ports is None:
        ports = LISTENING_PORTS

    still_open = []
    for port in ports:
        cmd = CMDS["ss_listen_port"].format(port=port)
        result = run_on_host(host, cmd)
        stdout = result.stdout.strip() if result.stdout else ""
        if stdout and str(port) in stdout:
            still_open.append(port)

    if still_open:
        return {
            "success": False,
            "error": f"Ports still open: {still_open}",
            "still_open": still_open,
            "details": f"{len(still_open)} port(s) still open",
        }
    return {
        "success": True,
        "error": "",
        "still_open": [],
        "details": "All service ports closed",
    }
