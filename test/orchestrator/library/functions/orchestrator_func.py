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
Orchestrator — Domain-Specific Verification Functions

All verification functions return a dict with keys:
  success (bool), details (str), error (str), and optionally skipped (bool).
"""

from typing import Any, Dict, List

from omnia_auto import load_test_config, run_on_host
from ..vars.common_vars import (
    CMDS,
    ORCHESTRATOR_CONFIG_FILE,
    OMNIA_CONFIG_FILE,
    NETWORK_SPEC_FILE,
    CREDENTIALS_FILE_NAME,
    INPUT_PATH_TEMPLATE,
    REPO_MANAGER_OUTPUT_TEMPLATE,
    OPENCHAMI_CONTAINERS,
    SYSTEMD_SERVICES,
    FIREWALL_PORTS,
)


def _get_input_path() -> str:
    """Return the orchestrator input path for the configured project."""
    config = load_test_config()
    project = config.get("project_name", "project_default")
    return INPUT_PATH_TEMPLATE.format(project=project)


def check_input_config_exists(host) -> Dict[str, Any]:
    """Verify orchestrator_config.yml exists on target.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success (bool), details (str), error (str).
    """
    input_path = _get_input_path()
    path = f"{input_path}/{ORCHESTRATOR_CONFIG_FILE}"
    cmd = CMDS["file_exists"].format(path=path)
    result = run_on_host(host, cmd)
    if result.rc == 0 and "exists" in result.stdout:
        return {
            "success": True,
            "details": f"{ORCHESTRATOR_CONFIG_FILE} found at {path}",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Checked path: {path}",
        "error": f"{ORCHESTRATOR_CONFIG_FILE} not found at {path}",
    }


def check_omnia_config_exists(host) -> Dict[str, Any]:
    """Verify omnia_config.yml exists on target.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success (bool), details (str), error (str).
    """
    input_path = _get_input_path()
    path = f"{input_path}/{OMNIA_CONFIG_FILE}"
    cmd = CMDS["file_exists"].format(path=path)
    result = run_on_host(host, cmd)
    if result.rc == 0 and "exists" in result.stdout:
        return {
            "success": True,
            "details": f"{OMNIA_CONFIG_FILE} found at {path}",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Checked path: {path}",
        "error": f"{OMNIA_CONFIG_FILE} not found at {path}",
    }


def check_network_spec_exists(host) -> Dict[str, Any]:
    """Verify network_spec.yml exists on target.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success (bool), details (str), error (str).
    """
    input_path = _get_input_path()
    path = f"{input_path}/{NETWORK_SPEC_FILE}"
    cmd = CMDS["file_exists"].format(path=path)
    result = run_on_host(host, cmd)
    if result.rc == 0 and "exists" in result.stdout:
        return {
            "success": True,
            "details": f"{NETWORK_SPEC_FILE} found at {path}",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Checked path: {path}",
        "error": f"{NETWORK_SPEC_FILE} not found at {path}",
    }


def check_credentials_present(host) -> Dict[str, Any]:
    """Verify credentials file is present on target.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success (bool), details (str), error (str).
    """
    config = load_test_config()
    project = config.get("project_name", "project_default")
    cred_path = f"/opt/omnia/input/{project}/{CREDENTIALS_FILE_NAME}"
    cmd = CMDS["file_exists"].format(path=cred_path)
    result = run_on_host(host, cmd)
    if result.rc == 0 and "exists" in result.stdout:
        return {
            "success": True,
            "details": f"{CREDENTIALS_FILE_NAME} found at {cred_path}",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Checked path: {cred_path}",
        "error": f"{CREDENTIALS_FILE_NAME} not found at {cred_path}",
    }


def check_repo_status_exists(host) -> Dict[str, Any]:
    """Verify repo_status.yml exists on target.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success (bool), details (str), error (str).
    """
    config = load_test_config()
    project = config.get("project_name", "project_default")
    path = REPO_MANAGER_OUTPUT_TEMPLATE.format(project=project)
    cmd = CMDS["file_exists"].format(path=path)
    result = run_on_host(host, cmd)
    if result.rc == 0 and "exists" in result.stdout:
        return {
            "success": True,
            "details": f"repo_status.yml found at {path}",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Checked path: {path}",
        "error": f"repo_status.yml not found at {path}",
    }


def check_container_running(host, container_name: str) -> Dict[str, Any]:
    """Check if a container is running on the target host.

    Args:
        host: Testinfra host connection.
        container_name: Name of the container to check.

    Returns:
        Dict with keys: success (bool), details (str), error (str).
    """
    cmd = CMDS["podman_ps_check"].format(container=container_name)
    result = run_on_host(host, cmd)
    if result.rc == 0 and container_name in result.stdout:
        return {
            "success": True,
            "details": f"Container {container_name} is running",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Container {container_name} not found in podman ps",
        "error": f"Container {container_name} is not running",
    }


def check_openchami_containers(host) -> Dict[str, Any]:
    """Check all OpenCHAMI containers are running.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success (bool), details (str), error (str).
    """
    missing: List[str] = []
    running: List[str] = []
    for container in OPENCHAMI_CONTAINERS:
        result = check_container_running(host, container)
        if result["success"]:
            running.append(container)
        else:
            missing.append(container)

    if not missing:
        return {
            "success": True,
            "details": f"All {len(running)} OpenCHAMI containers running",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Running: {running}, Missing: {missing}",
        "error": f"{len(missing)} container(s) not running: {missing}",
    }


def check_services_active(host) -> Dict[str, Any]:
    """Verify systemd services are active.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success (bool), details (str), error (str).
    """
    inactive: List[str] = []
    for service in SYSTEMD_SERVICES:
        cmd = CMDS["systemctl_is_active"].format(service=service)
        result = run_on_host(host, cmd)
        if result.rc != 0 or "active" not in result.stdout:
            inactive.append(service)

    if not inactive:
        return {
            "success": True,
            "details": f"All {len(SYSTEMD_SERVICES)} services active",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Inactive: {inactive}",
        "error": f"{len(inactive)} service(s) not active",
    }


def check_openchami_api_reachable(host) -> Dict[str, Any]:
    """Verify OpenCHAMI API endpoint is reachable.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success (bool), details (str), error (str).
    """
    cmd = CMDS["curl_check"].format(host="localhost", port=8443)
    result = run_on_host(host, cmd)
    if result.rc == 0:
        return {
            "success": True,
            "details": "OpenCHAMI API reachable on port 8443",
            "error": "",
        }
    return {
        "success": False,
        "details": "curl to localhost:8443 failed",
        "error": "OpenCHAMI API not reachable",
    }


def check_containers_removed(host) -> Dict[str, Any]:
    """Verify OpenCHAMI containers are removed after cleanup.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success (bool), details (str), error (str).
    """
    still_running: List[str] = []
    for container in OPENCHAMI_CONTAINERS:
        cmd = CMDS["podman_ps_all"].format(container=container)
        result = run_on_host(host, cmd)
        if container in result.stdout:
            still_running.append(container)

    if not still_running:
        return {
            "success": True,
            "details": "All OpenCHAMI containers removed",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Still present: {still_running}",
        "error": f"{len(still_running)} container(s) still exist",
    }


def check_services_removed(host) -> Dict[str, Any]:
    """Verify systemd services are stopped after cleanup.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success (bool), details (str), error (str).
    """
    still_active: List[str] = []
    for service in SYSTEMD_SERVICES:
        cmd = CMDS["systemctl_is_active"].format(service=service)
        result = run_on_host(host, cmd)
        if result.rc == 0 and "active" in result.stdout:
            still_active.append(service)

    if not still_active:
        return {
            "success": True,
            "details": "All systemd services stopped",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Still active: {still_active}",
        "error": f"{len(still_active)} service(s) still active",
    }


def check_firewall_ports_closed(host) -> Dict[str, Any]:
    """Verify firewall ports are closed after cleanup.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success (bool), details (str), error (str).
    """
    cmd = CMDS["firewall_list_ports"]
    result = run_on_host(host, cmd)
    if result.rc != 0:
        return {
            "success": True,
            "skipped": True,
            "details": "firewalld not active — skipping port check",
            "error": "",
        }

    open_ports = result.stdout.strip()
    still_open: List[str] = []
    for port in FIREWALL_PORTS:
        if port in open_ports:
            still_open.append(port)

    if not still_open:
        return {
            "success": True,
            "details": "All orchestrator firewall ports closed",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Still open: {still_open}",
        "error": f"{len(still_open)} port(s) still open",
    }


def check_clone_status(host) -> Dict[str, Any]:
    """Verify repository is cloned on target.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success (bool), details (str), error (str).
    """
    config = load_test_config()
    clone_path = config.get("clone_path", "/root/omnia")
    cmd = CMDS["dir_exists"].format(path=clone_path)
    result = run_on_host(host, cmd)
    if result.rc == 0 and "exists" in result.stdout:
        return {
            "success": True,
            "details": f"Repository found at {clone_path}",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Checked: {clone_path}",
        "error": f"Repository not found at {clone_path}",
    }
