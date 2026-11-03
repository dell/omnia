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
Build Stream — GitLab Installation Verification Functions.

Functions to verify GitLab server, runner, services, project,
pipeline files, and CI/CD variables.
"""

from typing import Any, Dict


# GitLab project/repository checks live in gitlab_project_func; they are
# re-exported here so existing ``gitlab_func`` imports keep working.
from library.functions.gitlab_project_func import (
    check_domain_input_dirs,
    check_gitlab_default_branch,
    check_gitlab_pipeline_variables,
    check_gitlab_project_exists,
    check_gitlab_project_visibility,
    check_gitlab_repo_file_exists,
    check_omnia_env_in_repo,
)
from library.functions.gitlab_ssh_func import (
    get_gitlab_config,
    gitlab_package_installed,
    gitlab_service_state,
    probe_gitlab_url,
    ssh_to_gitlab,
)
from library.vars.common_vars import (
    CMDS,
    GITLAB_INSTALLED_PACKAGES,
    GITLAB_RB_PATH,
    GITLAB_RUNNER_CONTAINER,
    GITLAB_RUNNER_QUADLET_DIR,
    GITLAB_RUNNER_QUADLET_FILE,
    GITLAB_RUNNER_SERVICES,
    GITLAB_SERVICES,
    GITLAB_SUCCESS_HTTP_CODES,
)

__all__ = [
    "check_domain_input_dirs",
    "check_gitlab_default_branch",
    "check_gitlab_packages_installed",
    "check_gitlab_pipeline_variables",
    "check_gitlab_project_exists",
    "check_gitlab_project_visibility",
    "check_gitlab_repo_file_exists",
    "check_gitlab_resources",
    "check_gitlab_runner_container",
    "check_gitlab_runner_quadlet",
    "check_gitlab_runner_services",
    "check_gitlab_server_reachable",
    "check_gitlab_services_running",
    "check_gitlab_url_accessible",
    "check_omnia_env_in_repo",
    "check_puma_workers",
    "check_sidekiq_concurrency",
    "get_gitlab_config",
    "ssh_to_gitlab",
]


# =========================================================================
# SECTION A: GitLab Installation Verification
# =========================================================================

def check_gitlab_packages_installed(host) -> Dict[str, Any]:
    """Verify GitLab packages are installed on the GitLab server.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, installed, missing, details, error.
    """
    result = {
        "success": False,
        "installed": [],
        "missing": [],
        "details": "",
        "error": "",
    }

    for pkg in GITLAB_INSTALLED_PACKAGES:
        if gitlab_package_installed(host, pkg):
            result["installed"].append(pkg)
        else:
            result["missing"].append(pkg)

    result["success"] = len(result["missing"]) == 0
    result["details"] = (
        f"Installed: {', '.join(result['installed']) or 'none'}"
    )
    return result


def check_gitlab_server_reachable(host) -> Dict[str, Any]:
    """Verify GitLab server is reachable from OIM via SSH.

    In 2.3, this is checked directly from the OIM host
    (no omnia_core container).

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, gitlab_host, details, error.
    """
    gitlab_config = get_gitlab_config(host)
    gitlab_host = gitlab_config.get("gitlab_host", "")

    result = {
        "success": False,
        "gitlab_host": gitlab_host,
        "details": "",
        "error": "",
    }

    if not gitlab_host:
        config_path = gitlab_config.get("_config_path", "unknown")
        result["error"] = (
            f"gitlab_host not found or empty in {config_path}. "
            f"Set gitlab_host in build_stream_config.yml."
        )
        return result

    ssh_result = ssh_to_gitlab(host, "echo REACHABLE")

    if ssh_result["success"] and "REACHABLE" in ssh_result["stdout"]:
        result["success"] = True
        result["details"] = f"GitLab server reachable at {gitlab_host}"
    else:
        result["error"] = (
            f"GitLab server {gitlab_host} not reachable via SSH. "
            f"Error: {ssh_result['error']}. "
            f"Verify: ssh root@{gitlab_host} from OIM host."
        )
    return result


def check_gitlab_runner_container(host) -> Dict[str, Any]:
    """Verify gitlab-runner container is running on the GitLab server.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, container, status, details, error.
    """
    result = {
        "success": False,
        "container": GITLAB_RUNNER_CONTAINER,
        "status": "",
        "details": "",
        "error": "",
    }

    cmd = (
        'podman ps --format "{{.Names}} {{.Status}}" 2>/dev/null'
        " || true"
    )
    ssh_result = ssh_to_gitlab(host, cmd)

    if GITLAB_RUNNER_CONTAINER in ssh_result.get("stdout", ""):
        for line in ssh_result["stdout"].strip().split("\n"):
            if GITLAB_RUNNER_CONTAINER in line:
                result["status"] = line.strip()
                result["success"] = True
                result["details"] = f"Container running: {line.strip()}"
                return result

    # Check if it exists but is stopped
    cmd_all = (
        'podman ps -a --format "{{.Names}} {{.Status}}" 2>/dev/null'
        " || true"
    )
    ssh_all = ssh_to_gitlab(host, cmd_all)

    if GITLAB_RUNNER_CONTAINER in ssh_all.get("stdout", ""):
        for line in ssh_all["stdout"].strip().split("\n"):
            if GITLAB_RUNNER_CONTAINER in line:
                result["status"] = line.strip()
                result["error"] = (
                    f"Container exists but not running: {line.strip()}"
                )
                return result

    result["error"] = f"Container {GITLAB_RUNNER_CONTAINER} not found"
    return result


def check_gitlab_runner_quadlet(host) -> Dict[str, Any]:
    """Verify gitlab-runner quadlet file exists on the GitLab server.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, path, details, error.
    """
    quadlet_path = (
        f"{GITLAB_RUNNER_QUADLET_DIR}/{GITLAB_RUNNER_QUADLET_FILE}"
    )
    result = {
        "success": False,
        "path": quadlet_path,
        "details": "",
        "error": "",
    }

    ssh_result = ssh_to_gitlab(
        host,
        f"test -f {quadlet_path} && echo EXISTS || echo NOT_FOUND",
    )

    if ssh_result["success"] and "EXISTS" in ssh_result["stdout"]:
        result["success"] = True
        result["details"] = f"Quadlet file exists: {quadlet_path}"
    else:
        result["error"] = f"Quadlet file not found: {quadlet_path}"
    return result


def check_gitlab_runner_services(host) -> Dict[str, Any]:
    """Verify all GitLab runner services are running.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, results, passed, failed, total,
        details, error.
    """
    result = {
        "success": False,
        "results": [],
        "passed": 0,
        "failed": 0,
        "total": 0,
        "details": "",
        "error": "",
    }

    passed = 0
    failed = 0
    svc_results = []

    for svc in GITLAB_RUNNER_SERVICES:
        svc_name = svc["name"]
        status = gitlab_service_state(host, svc_name, "unknown")
        is_active = status == "active"

        if is_active:
            passed += 1
        else:
            failed += 1

        svc_results.append({
            "name": svc_name,
            "description": svc["description"],
            "status": status,
            "is_active": is_active,
        })

    total = passed + failed
    result["results"] = svc_results
    result["passed"] = passed
    result["failed"] = failed
    result["total"] = total
    result["success"] = failed == 0
    result["details"] = f"Services: {passed}/{total} running"

    if failed > 0:
        failed_names = [
            s["name"] for s in svc_results if not s["is_active"]
        ]
        result["error"] = f"Not running: {', '.join(failed_names)}"
    return result


def check_gitlab_url_accessible(host) -> Dict[str, Any]:
    """Verify GitLab URL is accessible from the OIM server.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, url, http_code, details, error.
    """
    probe = probe_gitlab_url(host)
    url = probe["url"]
    result = {"success": False, "url": url, "http_code": probe["http_code"],
              "details": "", "error": ""}
    if not probe["host"]:
        result["error"] = (
            f"gitlab_host not found or empty in {probe['config_path']}. "
            f"Set gitlab_host in build_stream_config.yml."
        )
        return result

    if result["http_code"] in GITLAB_SUCCESS_HTTP_CODES:
        result["success"] = True
        result["details"] = f"HTTP {result['http_code']} from {url}"
    else:
        result["error"] = (
            f"HTTP {result['http_code']} from {url}. "
            f"GitLab may not be running on {probe['address']}. "
            f"Check from the OIM: curl --cacert <GitLab CA> -I {url} "
            "(the CA is /root/gitlab-certs/ca.crt on the GitLab host)"
        )
    return result


def check_gitlab_services_running(host) -> Dict[str, Any]:
    """Verify all GitLab services are running via gitlab-ctl status.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, running, not_running, total, details,
        error.
    """
    result = {
        "success": False,
        "running": [],
        "not_running": [],
        "total": 0,
        "details": "",
        "error": "",
    }

    ssh_result = ssh_to_gitlab(host, "gitlab-ctl status 2>/dev/null")
    if not ssh_result["success"]:
        result["error"] = f"gitlab-ctl status failed: {ssh_result['error']}"
        return result

    output = ssh_result["stdout"]
    lines = output.split("\n") if output else []

    for service in GITLAB_SERVICES:
        found = False
        for line in lines:
            if service in line:
                if line.startswith("run:"):
                    result["running"].append(service)
                else:
                    result["not_running"].append(service)
                found = True
                break
        if not found:
            result["not_running"].append(service)

    result["total"] = len(GITLAB_SERVICES)
    result["success"] = len(result["not_running"]) == 0
    result["details"] = (
        f"{len(result['running'])}/{result['total']} services running"
    )
    if result["not_running"]:
        result["error"] = (
            f"Not running: {', '.join(result['not_running'])}"
        )
    return result


def check_gitlab_resources(host) -> Dict[str, Any]:
    """Verify GitLab server meets minimum resource requirements.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, actual, required, checks, details,
        error.
    """
    result = {
        "success": False,
        "actual": {"cpu_cores": 0, "memory_gb": 0, "storage_gb": 0},
        "required": {"min_cpu_cores": 4, "min_memory_gb": 8, "min_storage_gb": 50},
        "checks": {"cpu": False, "memory": False, "storage": False},
        "details": "",
        "error": "",
    }

    # CPU
    ssh_cpu = ssh_to_gitlab(host, CMDS["nproc_cmd"])
    if ssh_cpu["success"]:
        try:
            result["actual"]["cpu_cores"] = int(
                ssh_cpu["stdout"].strip()
            )
        except ValueError:
            pass

    # Memory
    ssh_mem = ssh_to_gitlab(host, CMDS["free_cmd"])
    if ssh_mem["success"]:
        for line in ssh_mem["stdout"].split("\n"):
            if "Mem:" in line:
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        result["actual"]["memory_gb"] = int(parts[1])
                    except ValueError:
                        pass
                break

    # Storage
    ssh_disk = ssh_to_gitlab(host, CMDS["df_cmd"])
    if ssh_disk["success"]:
        lines = ssh_disk["stdout"].strip().split("\n")
        if len(lines) >= 2:
            parts = lines[1].split()
            if len(parts) >= 4:
                try:
                    result["actual"]["storage_gb"] = int(
                        parts[3].replace("G", "")
                    )
                except ValueError:
                    pass

    req = result["required"]
    result["checks"]["cpu"] = (
        result["actual"]["cpu_cores"] >= req["min_cpu_cores"]
    )
    result["checks"]["memory"] = (
        result["actual"]["memory_gb"] >= req["min_memory_gb"]
    )
    result["checks"]["storage"] = (
        result["actual"]["storage_gb"] >= req["min_storage_gb"]
    )

    result["success"] = all(result["checks"].values())
    result["details"] = (
        f"CPU: {result['actual']['cpu_cores']}, "
        f"MEM: {result['actual']['memory_gb']}G, "
        f"DISK: {result['actual']['storage_gb']}G"
    )
    if not result["success"]:
        failed = [k for k, v in result["checks"].items() if not v]
        result["error"] = f"Requirements not met: {', '.join(failed)}"
    return result


def check_puma_workers(host) -> Dict[str, Any]:
    """Verify puma workers configured correctly in gitlab.rb.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, expected, actual, details, error.
    """
    gitlab_config = get_gitlab_config(host)
    expected = int(gitlab_config.get("puma_workers", "2"))

    result = {
        "success": False,
        "expected": expected,
        "actual": 0,
        "details": "",
        "error": "",
    }

    ssh_result = ssh_to_gitlab(
        host,
        CMDS["grep_gitlab_rb"].format(
            pattern="worker_processes", path=GITLAB_RB_PATH,
        ),
    )

    if not ssh_result["success"]:
        result["error"] = "Failed to read puma config from gitlab.rb"
        return result

    for line in ssh_result["stdout"].split("\n"):
        if "worker_processes" in line and "=" in line:
            try:
                result["actual"] = int(line.split("=")[1].strip())
            except (ValueError, IndexError):
                pass
            break

    if result["actual"] == expected:
        result["success"] = True
        result["details"] = f"Puma workers: {result['actual']}"
    else:
        result["error"] = (
            f"Expected {expected}, got {result['actual']}"
        )
    return result


def check_sidekiq_concurrency(host) -> Dict[str, Any]:
    """Verify sidekiq concurrency configured correctly in gitlab.rb.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, expected, actual, details, error.
    """
    gitlab_config = get_gitlab_config(host)
    expected = int(gitlab_config.get("sidekiq_concurrency", "10"))

    result = {
        "success": False,
        "expected": expected,
        "actual": 0,
        "details": "",
        "error": "",
    }

    ssh_result = ssh_to_gitlab(
        host,
        CMDS["grep_gitlab_rb"].format(
            pattern="max_concurrency", path=GITLAB_RB_PATH,
        ),
    )

    if not ssh_result["success"]:
        result["error"] = "Failed to read sidekiq config from gitlab.rb"
        return result

    for line in ssh_result["stdout"].split("\n"):
        if "max_concurrency" in line and "=" in line:
            try:
                result["actual"] = int(line.split("=")[1].strip())
            except (ValueError, IndexError):
                pass
            break

    if result["actual"] == expected:
        result["success"] = True
        result["details"] = f"Sidekiq concurrency: {result['actual']}"
    else:
        result["error"] = (
            f"Expected {expected}, got {result['actual']}"
        )
    return result
