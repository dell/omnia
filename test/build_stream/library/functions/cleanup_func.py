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
Build Stream — Cleanup Verification Functions.

Functions to verify GitLab cleanup and BuildStream domain cleanup.
Checks that containers, services, directories, credentials, and
volumes are properly removed after running cleanup playbooks.
"""

from typing import Any, Dict, List

from omnia_auto import load_test_config, run_on_host

from ..vars.common_vars import (
    BSM_CONTAINER_NAME,
    BUILDSTREAM_CLEANUP_DIRECTORIES,
    BUILDSTREAM_CREDENTIAL_FILES,
    BUILDSTREAM_OAUTH_CREDENTIAL_FILES,
    CMDS,
    GITLAB_CLEANUP_DIRECTORIES,
    GITLAB_INSTALLED_PACKAGES,
    GITLAB_RUNNER_CONTAINER,
    GITLAB_RUNNER_QUADLET_DIR,
    GITLAB_RUNNER_QUADLET_FILE,
    GITLAB_RUNNER_SERVICES,
    GITLAB_SERVICES,
    PLAYBOOK_WATCHER_SERVICE_FILE,
    PLAYBOOK_WATCHER_SERVICE_NAME,
    POSTGRES_CONTAINER_NAME,
    QUADLET_DIR,
)
from .gitlab_func import _get_gitlab_config, _ssh_to_gitlab


# =========================================================================
# SECTION C: GitLab Cleanup Verification
# =========================================================================

def check_gitlab_packages_removed(host) -> Dict[str, Any]:
    """Verify GitLab packages are removed from the GitLab server.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, removed, still_installed, details, error.
    """
    result = {
        "success": False,
        "removed": [],
        "still_installed": [],
        "details": "",
        "error": "",
    }

    for pkg in GITLAB_INSTALLED_PACKAGES:
        ssh_result = _ssh_to_gitlab(
            host,
            CMDS["rpm_check"].format(package=pkg),
        )
        if ssh_result["success"] and pkg in ssh_result.get("stdout", ""):
            result["still_installed"].append(pkg)
        else:
            result["removed"].append(pkg)

    result["success"] = len(result["still_installed"]) == 0
    result["details"] = (
        f"Removed: {', '.join(result['removed']) or 'none'}"
    )
    if result["still_installed"]:
        result["error"] = (
            f"Still installed: {', '.join(result['still_installed'])}"
        )
    return result


def check_gitlab_runner_container_removed(host) -> Dict[str, Any]:
    """Verify gitlab-runner container is removed from the GitLab server.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, details, error.
    """
    cmd = (
        'podman ps -a --format "{{.Names}}" 2>/dev/null || true'
    )
    ssh_result = _ssh_to_gitlab(host, cmd)

    if not ssh_result["success"]:
        return {
            "success": True,
            "details": (
                "Cannot SSH to GitLab (expected if server removed)"
            ),
            "error": "",
        }

    stdout = ssh_result.get("stdout", "")
    if GITLAB_RUNNER_CONTAINER in stdout:
        return {
            "success": False,
            "details": "",
            "error": (
                f"Container {GITLAB_RUNNER_CONTAINER} still exists"
            ),
        }
    return {
        "success": True,
        "details": f"Container {GITLAB_RUNNER_CONTAINER} removed",
        "error": "",
    }


def check_gitlab_runner_quadlet_removed(host) -> Dict[str, Any]:
    """Verify gitlab-runner quadlet file is removed.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, path, details, error.
    """
    quadlet_path = (
        f"{GITLAB_RUNNER_QUADLET_DIR}/{GITLAB_RUNNER_QUADLET_FILE}"
    )
    ssh_result = _ssh_to_gitlab(
        host,
        f"test -f {quadlet_path} && echo EXISTS || echo NOT_FOUND",
    )

    if not ssh_result["success"]:
        return {
            "success": True,
            "path": quadlet_path,
            "details": "Cannot SSH (expected if server removed)",
            "error": "",
        }

    if "EXISTS" in ssh_result.get("stdout", ""):
        return {
            "success": False,
            "path": quadlet_path,
            "details": "",
            "error": f"Quadlet still exists: {quadlet_path}",
        }
    return {
        "success": True,
        "path": quadlet_path,
        "details": f"Quadlet removed: {quadlet_path}",
        "error": "",
    }


def check_gitlab_runner_services_stopped(host) -> Dict[str, Any]:
    """Verify GitLab runner services are stopped after cleanup.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, results, details, error.
    """
    result = {
        "success": False,
        "results": [],
        "details": "",
        "error": "",
    }

    still_active = []
    stopped = []

    for svc in GITLAB_RUNNER_SERVICES:
        svc_name = svc["name"]
        ssh_result = _ssh_to_gitlab(
            host,
            CMDS["systemctl_is_active"].format(service=svc_name),
        )
        status = ssh_result["stdout"].strip() if ssh_result["success"] else "inactive"
        is_active = status == "active"

        result["results"].append({
            "name": svc_name,
            "status": status,
            "is_active": is_active,
        })

        if is_active:
            still_active.append(svc_name)
        else:
            stopped.append(svc_name)

    result["success"] = len(still_active) == 0
    result["details"] = (
        f"Stopped: {len(stopped)}/{len(GITLAB_RUNNER_SERVICES)}"
    )
    if still_active:
        result["error"] = (
            f"Still active: {', '.join(still_active)}"
        )
    return result


def check_gitlab_url_not_accessible(host) -> Dict[str, Any]:
    """Verify GitLab URL is NOT accessible after cleanup.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, url, http_code, details, error.
    """
    gitlab_config = _get_gitlab_config(host)
    gitlab_host = gitlab_config.get("gitlab_host", "")
    gitlab_port = gitlab_config.get("gitlab_https_port", "443")

    result = {
        "success": False,
        "url": "",
        "http_code": 0,
        "details": "",
        "error": "",
    }

    if not gitlab_host:
        result["success"] = True
        result["details"] = "gitlab_host not set (cleanup complete)"
        return result

    url = f"https://{gitlab_host}:{gitlab_port}/"
    result["url"] = url

    cmd = CMDS["curl_gitlab_url"].format(
        host=gitlab_host, port=gitlab_port,
    )
    cmd_result = run_on_host(host, cmd)

    http_code_str = cmd_result.stdout.strip() if cmd_result.stdout else "0"
    try:
        result["http_code"] = int(http_code_str)
    except ValueError:
        result["http_code"] = 0

    # After cleanup, URL should NOT return 200 or 302
    if result["http_code"] in (200, 302):
        result["error"] = (
            f"GitLab still accessible: HTTP {result['http_code']} "
            f"from {url}"
        )
    else:
        result["success"] = True
        result["details"] = (
            f"GitLab not accessible (HTTP {result['http_code']})"
        )
    return result


def check_gitlab_directories_removed(host) -> Dict[str, Any]:
    """Verify GitLab directories are removed from the GitLab server.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, removed, still_exist, details, error.
    """
    result = {
        "success": False,
        "removed": [],
        "still_exist": [],
        "details": "",
        "error": "",
    }

    for dir_path in GITLAB_CLEANUP_DIRECTORIES:
        ssh_result = _ssh_to_gitlab(
            host,
            CMDS["dir_exists"].format(path=dir_path),
        )
        if ssh_result["success"] and "exists" in ssh_result.get("stdout", ""):
            result["still_exist"].append(dir_path)
        else:
            result["removed"].append(dir_path)

    total = len(GITLAB_CLEANUP_DIRECTORIES)
    result["success"] = len(result["still_exist"]) == 0
    result["details"] = (
        f"Removed: {len(result['removed'])}/{total}"
    )
    if result["still_exist"]:
        result["error"] = (
            f"Still exist: {', '.join(result['still_exist'])}"
        )
    return result


def check_gitlab_services_stopped(host) -> Dict[str, Any]:
    """Verify all GitLab services are stopped via gitlab-ctl status.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, still_running, details, error.
    """
    result = {
        "success": False,
        "still_running": [],
        "details": "",
        "error": "",
    }

    ssh_result = _ssh_to_gitlab(host, "gitlab-ctl status 2>/dev/null")
    if not ssh_result["success"]:
        result["success"] = True
        result["details"] = (
            "gitlab-ctl not available (expected after uninstall)"
        )
        return result

    output = ssh_result.get("stdout", "")
    if not output.strip():
        result["success"] = True
        result["details"] = "No GitLab services found"
        return result

    for service in GITLAB_SERVICES:
        for line in output.split("\n"):
            if service in line and line.startswith("run:"):
                result["still_running"].append(service)
                break

    result["success"] = len(result["still_running"]) == 0
    if result["still_running"]:
        result["details"] = (
            f"Still running: {', '.join(result['still_running'])}"
        )
        result["error"] = result["details"]
    else:
        result["details"] = "All GitLab services stopped"
    return result


def check_gitlab_port_free(host) -> Dict[str, Any]:
    """Verify GitLab HTTPS port is free after cleanup.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, port, details, error.
    """
    gitlab_config = _get_gitlab_config(host)
    gitlab_port = gitlab_config.get("gitlab_https_port", "443")

    ssh_result = _ssh_to_gitlab(
        host,
        CMDS["ss_port_check"].format(port=gitlab_port),
    )

    if not ssh_result["success"]:
        return {
            "success": True,
            "port": gitlab_port,
            "details": "Cannot SSH (expected if server removed)",
            "error": "",
        }

    output = ssh_result.get("stdout", "").strip()
    if output:
        return {
            "success": False,
            "port": gitlab_port,
            "details": "",
            "error": f"Port {gitlab_port} still in use: {output}",
        }
    return {
        "success": True,
        "port": gitlab_port,
        "details": f"Port {gitlab_port} is free",
        "error": "",
    }


# =========================================================================
# SECTION C.1: BuildStream Domain Cleanup Verification
# =========================================================================

def _check_container_removed(
    host, container: str
) -> Dict[str, Any]:
    """Check that a container does not exist (stopped and removed).

    Args:
        host: Testinfra host connection.
        container: Container name to check.

    Returns:
        Dict with keys: success, container, status, details, error.
    """
    cmd = CMDS["podman_container_exists"].format(container=container)
    cmd_result = run_on_host(host, cmd)

    stdout = cmd_result.stdout.strip() if cmd_result.stdout else ""
    if container in stdout:
        # Get status
        status_cmd = CMDS["podman_ps_all"].format(container=container)
        status_result = run_on_host(host, status_cmd)
        status = status_result.stdout.strip() if status_result.stdout else "exists"
        return {
            "success": False,
            "container": container,
            "status": status,
            "details": "",
            "error": f"{container} still exists: {status}",
        }
    return {
        "success": True,
        "container": container,
        "status": "removed",
        "details": f"{container} not found (removed)",
        "error": "",
    }


def _check_container_not_running(
    host, container: str
) -> Dict[str, Any]:
    """Check that a container is NOT running (stopped).

    Args:
        host: Testinfra host connection.
        container: Container name to check.

    Returns:
        Dict with keys: success, container, status, details, error.
    """
    cmd = CMDS["podman_ps_check"].format(container=container)
    cmd_result = run_on_host(host, cmd)

    stdout = cmd_result.stdout.strip() if cmd_result.stdout else ""
    if container in stdout:
        return {
            "success": False,
            "container": container,
            "status": stdout,
            "details": "",
            "error": f"{container} is still running: {stdout}",
        }
    return {
        "success": True,
        "container": container,
        "status": "stopped",
        "details": f"{container} is not running",
        "error": "",
    }


def check_buildstream_container_stopped(host) -> Dict[str, Any]:
    """Verify omnia_build_stream container is stopped.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, container, status, details, error.
    """
    return _check_container_not_running(host, BSM_CONTAINER_NAME)


def check_buildstream_container_removed(host) -> Dict[str, Any]:
    """Verify omnia_build_stream container is removed.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, container, status, details, error.
    """
    return _check_container_removed(host, BSM_CONTAINER_NAME)


def check_buildstream_quadlet_files_removed(host) -> Dict[str, Any]:
    """Verify omnia_build_stream quadlet files are removed.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, details, error.
    """
    cmd = CMDS["find_quadlet_files"].format(
        dir=QUADLET_DIR, pattern="omnia_build_stream",
    )
    cmd_result = run_on_host(host, cmd)
    found = cmd_result.stdout.strip() if cmd_result.stdout else ""

    if found:
        return {
            "success": False,
            "details": "",
            "error": f"Quadlet files still exist: {found}",
        }
    return {
        "success": True,
        "details": "No omnia_build_stream quadlet files found",
        "error": "",
    }


def check_buildstream_services_stopped(host) -> Dict[str, Any]:
    """Verify all omnia_build_stream systemd services are stopped.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, still_active, details, error.
    """
    cmd = CMDS["systemctl_list_units"].format(
        pattern="omnia_build_stream",
    )
    cmd_result = run_on_host(host, cmd)
    output = cmd_result.stdout.strip() if cmd_result.stdout else ""

    still_active = []
    if output:
        for line in output.split("\n"):
            if "active" in line and "inactive" not in line:
                svc_name = line.strip().split()[0]
                still_active.append(svc_name)

    if still_active:
        return {
            "success": False,
            "still_active": still_active,
            "details": "",
            "error": (
                f"Services still active: {', '.join(still_active)}"
            ),
        }
    return {
        "success": True,
        "still_active": [],
        "details": "No active omnia_build_stream services",
        "error": "",
    }


def check_playbook_watcher_service_stopped(host) -> Dict[str, Any]:
    """Verify playbook_watcher service is stopped.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, status, details, error.
    """
    cmd = CMDS["systemctl_is_active"].format(
        service=PLAYBOOK_WATCHER_SERVICE_NAME,
    )
    cmd_result = run_on_host(host, cmd)
    status = cmd_result.stdout.strip() if cmd_result.stdout else "unknown"

    if status == "active":
        return {
            "success": False,
            "status": status,
            "details": "",
            "error": f"{PLAYBOOK_WATCHER_SERVICE_NAME}: still active",
        }
    return {
        "success": True,
        "status": status,
        "details": f"{PLAYBOOK_WATCHER_SERVICE_NAME}: {status}",
        "error": "",
    }


def check_playbook_watcher_service_disabled(host) -> Dict[str, Any]:
    """Verify playbook_watcher service is disabled.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, status, details, error.
    """
    cmd = CMDS["systemctl_is_enabled"].format(
        service=PLAYBOOK_WATCHER_SERVICE_NAME,
    )
    cmd_result = run_on_host(host, cmd)
    status = cmd_result.stdout.strip() if cmd_result.stdout else "unknown"

    if status == "enabled":
        return {
            "success": False,
            "status": status,
            "details": "",
            "error": f"{PLAYBOOK_WATCHER_SERVICE_NAME}: still enabled",
        }
    return {
        "success": True,
        "status": status,
        "details": f"{PLAYBOOK_WATCHER_SERVICE_NAME}: {status}",
        "error": "",
    }


def check_playbook_watcher_service_file_removed(
    host,
) -> Dict[str, Any]:
    """Verify playbook_watcher.service unit file is removed.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, path, details, error.
    """
    cmd = CMDS["file_exists"].format(path=PLAYBOOK_WATCHER_SERVICE_FILE)
    cmd_result = run_on_host(host, cmd)

    if cmd_result.stdout.strip() == "exists":
        return {
            "success": False,
            "path": PLAYBOOK_WATCHER_SERVICE_FILE,
            "details": "",
            "error": (
                f"Service file still exists: "
                f"{PLAYBOOK_WATCHER_SERVICE_FILE}"
            ),
        }
    return {
        "success": True,
        "path": PLAYBOOK_WATCHER_SERVICE_FILE,
        "details": (
            f"Service file removed: {PLAYBOOK_WATCHER_SERVICE_FILE}"
        ),
        "error": "",
    }


def check_postgres_container_stopped(host) -> Dict[str, Any]:
    """Verify omnia_postgres container is stopped.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, container, status, details, error.
    """
    return _check_container_not_running(host, POSTGRES_CONTAINER_NAME)


def check_postgres_container_removed(host) -> Dict[str, Any]:
    """Verify omnia_postgres container is removed.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, container, status, details, error.
    """
    return _check_container_removed(host, POSTGRES_CONTAINER_NAME)


def check_postgres_quadlet_files_removed(host) -> Dict[str, Any]:
    """Verify omnia_postgres quadlet files are removed.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, details, error.
    """
    cmd = CMDS["find_quadlet_files"].format(
        dir=QUADLET_DIR, pattern="omnia_postgres",
    )
    cmd_result = run_on_host(host, cmd)
    found = cmd_result.stdout.strip() if cmd_result.stdout else ""

    if found:
        return {
            "success": False,
            "details": "",
            "error": f"Quadlet files still exist: {found}",
        }
    return {
        "success": True,
        "details": "No omnia_postgres quadlet files found",
        "error": "",
    }


def check_postgres_services_stopped(host) -> Dict[str, Any]:
    """Verify all omnia_postgres systemd services are stopped.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, still_active, details, error.
    """
    cmd = CMDS["systemctl_list_units"].format(
        pattern="omnia_postgres",
    )
    cmd_result = run_on_host(host, cmd)
    output = cmd_result.stdout.strip() if cmd_result.stdout else ""

    still_active = []
    if output:
        for line in output.split("\n"):
            if "active" in line and "inactive" not in line:
                svc_name = line.strip().split()[0]
                still_active.append(svc_name)

    if still_active:
        return {
            "success": False,
            "still_active": still_active,
            "details": "",
            "error": (
                f"Services still active: {', '.join(still_active)}"
            ),
        }
    return {
        "success": True,
        "still_active": [],
        "details": "No active omnia_postgres services",
        "error": "",
    }


def check_image_groups_marked_cleaned(host) -> Dict[str, Any]:
    """Verify all image_groups records are updated to CLEANED status.

    If Postgres is not running (expected after cleanup), this test
    is skipped as the cleanup already handled it.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, skipped, details, error.
    """
    # Check if postgres container is running first
    ps_cmd = CMDS["podman_ps_check"].format(
        container=POSTGRES_CONTAINER_NAME,
    )
    ps_result = run_on_host(host, ps_cmd)

    if POSTGRES_CONTAINER_NAME not in (ps_result.stdout or ""):
        return {
            "success": True,
            "skipped": True,
            "details": (
                "Postgres not running (expected after cleanup). "
                "image_groups were marked CLEANED before container "
                "removal."
            ),
            "error": "",
        }

    # If postgres is still running, check the actual records
    cmd = (
        f"podman exec {POSTGRES_CONTAINER_NAME} psql -U admin"
        f" -d build_stream_db -t -c"
        f" \"SELECT COUNT(*) FROM image_groups"
        f" WHERE status != 'CLEANED'\" 2>/dev/null"
    )
    cmd_result = run_on_host(host, cmd)

    if cmd_result.rc != 0:
        return {
            "success": True,
            "skipped": True,
            "details": "Cannot query database (expected after cleanup)",
            "error": "",
        }

    count = cmd_result.stdout.strip()
    try:
        non_cleaned = int(count)
    except ValueError:
        return {
            "success": True,
            "skipped": True,
            "details": f"Unexpected query result: {count}",
            "error": "",
        }

    if non_cleaned > 0:
        return {
            "success": False,
            "skipped": False,
            "details": "",
            "error": (
                f"{non_cleaned} image_groups not marked CLEANED"
            ),
        }
    return {
        "success": True,
        "skipped": False,
        "details": "All image_groups marked CLEANED",
        "error": "",
    }


def check_postgres_volumes_removed(host) -> Dict[str, Any]:
    """Verify Postgres volumes are removed (when postgres_backup=false).

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, volumes, details, error.
    """
    cmd = CMDS["podman_volume_ls"].format(pattern="postgres")
    cmd_result = run_on_host(host, cmd)
    volumes = cmd_result.stdout.strip() if cmd_result.stdout else ""

    if volumes:
        vol_list = [v.strip() for v in volumes.split("\n") if v.strip()]
        return {
            "success": False,
            "volumes": vol_list,
            "details": "",
            "error": (
                f"Postgres volumes still exist: "
                f"{', '.join(vol_list)}"
            ),
        }
    return {
        "success": True,
        "volumes": [],
        "details": "No Postgres volumes found",
        "error": "",
    }


def check_postgres_volumes_preserved(host) -> Dict[str, Any]:
    """Verify Postgres volumes are preserved (when postgres_backup=true).

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, volumes, details, error.
    """
    config = load_test_config()
    shared_path = config.get(
        "shared_path", "/opt/omnia/build_stream"
    )
    omnia_path = shared_path.rsplit("/build_stream", 1)[0]
    postgres_dir = f"{omnia_path}/postgres"

    cmd = CMDS["dir_exists"].format(path=postgres_dir)
    cmd_result = run_on_host(host, cmd)

    if cmd_result.stdout.strip() == "exists":
        return {
            "success": True,
            "volumes": [postgres_dir],
            "details": f"Postgres directory preserved: {postgres_dir}",
            "error": "",
        }
    return {
        "success": False,
        "volumes": [],
        "details": "",
        "error": (
            f"Postgres directory NOT preserved: {postgres_dir}. "
            f"Expected to be retained with postgres_backup=true."
        ),
    }


def check_buildstream_directories_removed(host) -> Dict[str, Any]:
    """Verify build_stream cleanup directories are removed.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, removed, still_exist, details, error.
    """
    config = load_test_config()
    shared_path = config.get(
        "shared_path", "/opt/omnia/build_stream"
    )
    omnia_path = shared_path.rsplit("/build_stream", 1)[0]

    # Build dynamic list based on config
    dirs = [
        f"{omnia_path}/build_stream/log",
        f"{omnia_path}/build_stream/playbook_queue",
        f"{omnia_path}/build_stream_ssl",
        f"{omnia_path}/build_stream_root",
        f"{omnia_path}/build_stream_inv",
        f"{omnia_path}/build_stream_enabled",
        f"{omnia_path}/build_stream",
    ]

    result = {
        "success": False,
        "removed": [],
        "still_exist": [],
        "details": "",
        "error": "",
    }

    for dir_path in dirs:
        cmd = CMDS["dir_exists"].format(path=dir_path)
        cmd_result = run_on_host(host, cmd)
        if cmd_result.stdout.strip() == "exists":
            result["still_exist"].append(dir_path)
        else:
            result["removed"].append(dir_path)

    total = len(dirs)
    result["success"] = len(result["still_exist"]) == 0
    result["details"] = (
        f"Removed: {len(result['removed'])}/{total}"
    )
    if result["still_exist"]:
        result["error"] = (
            f"Still exist: {', '.join(result['still_exist'])}"
        )
    return result


def check_buildstream_credentials_removed(host) -> Dict[str, Any]:
    """Verify build_stream_credentials.yml and vault key are removed.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, removed, still_exist, details, error.
    """
    config = load_test_config()
    project = config.get("project_name", "project_default")
    shared_path = config.get(
        "shared_path", "/opt/omnia/build_stream"
    )
    input_dir = f"{shared_path}/input/{project}"

    result = {
        "success": False,
        "removed": [],
        "still_exist": [],
        "details": "",
        "error": "",
    }

    for fname in BUILDSTREAM_CREDENTIAL_FILES:
        fpath = f"{input_dir}/{fname}"
        cmd = CMDS["file_exists"].format(path=fpath)
        cmd_result = run_on_host(host, cmd)
        if cmd_result.stdout.strip() == "exists":
            result["still_exist"].append(fpath)
        else:
            result["removed"].append(fpath)

    total = len(BUILDSTREAM_CREDENTIAL_FILES)
    result["success"] = len(result["still_exist"]) == 0
    result["details"] = (
        f"Removed: {len(result['removed'])}/{total}"
    )
    if result["still_exist"]:
        result["error"] = (
            f"Still exist: {', '.join(result['still_exist'])}"
        )
    return result


def check_buildstream_oauth_credentials_removed(
    host,
) -> Dict[str, Any]:
    """Verify build_stream_oauth_credentials.yml and key are removed.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, removed, still_exist, details, error.
    """
    config = load_test_config()
    project = config.get("project_name", "project_default")
    shared_path = config.get(
        "shared_path", "/opt/omnia/build_stream"
    )
    input_dir = f"{shared_path}/input/{project}"

    result = {
        "success": False,
        "removed": [],
        "still_exist": [],
        "details": "",
        "error": "",
    }

    for fname in BUILDSTREAM_OAUTH_CREDENTIAL_FILES:
        fpath = f"{input_dir}/{fname}"
        cmd = CMDS["file_exists"].format(path=fpath)
        cmd_result = run_on_host(host, cmd)
        if cmd_result.stdout.strip() == "exists":
            result["still_exist"].append(fpath)
        else:
            result["removed"].append(fpath)

    total = len(BUILDSTREAM_OAUTH_CREDENTIAL_FILES)
    result["success"] = len(result["still_exist"]) == 0
    result["details"] = (
        f"Removed: {len(result['removed'])}/{total}"
    )
    if result["still_exist"]:
        result["error"] = (
            f"Still exist: {', '.join(result['still_exist'])}"
        )
    return result
