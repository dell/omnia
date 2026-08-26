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

import json
from typing import Any, Dict, List

from omnia_auto import load_test_config, load_test_credentials, run_on_host

from library.vars.common_vars import (
    CMDS,
    GITLAB_API_VERSION,
    GITLAB_CI_ALL_FILES,
    GITLAB_CLEANUP_DIRECTORIES,
    GITLAB_INSTALLED_PACKAGES,
    GITLAB_PIPELINE_VARIABLES,
    GITLAB_RB_PATH,
    GITLAB_ROOT_TOKEN_FILE,
    GITLAB_RUNNER_CONTAINER,
    GITLAB_RUNNER_QUADLET_DIR,
    GITLAB_RUNNER_QUADLET_FILE,
    GITLAB_RUNNER_SERVICES,
    GITLAB_SERVICES,
    GITLAB_SUCCESS_HTTP_CODES,
    GITLAB_VISIBILITY_LEVELS,
)


def _get_gitlab_config_path() -> str:
    """Return the resolved path to build_stream_config.yml on the target host."""
    config = load_test_config()
    project = config.get("project_name", "project_default")
    data_path = config.get("shared_path", "/opt/omnia/build_stream")
    return (
        f"{data_path}/input/{project}/"
        "build_stream_config.yml"
    )


def _get_gitlab_config(host) -> Dict[str, str]:
    """Read gitlab-related values from build_stream_config.yml.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict of configuration values. Includes '_config_path' key for
        error reporting.
    """
    config_path = _get_gitlab_config_path()
    cmd = CMDS["cat_file"].format(path=config_path)
    result = run_on_host(host, cmd)

    values = {"_config_path": config_path}
    if result.rc == 0 and result.stdout.strip():
        for line in result.stdout.strip().split("\n"):
            if ":" in line and not line.strip().startswith("#"):
                key, _, val = line.partition(":")
                values[key.strip()] = val.strip().strip('"').strip("'")
    return values


def _get_gitlab_ssh_password() -> str:
    """Load gitlab_ssh_password from test_creds.yml.

    Returns:
        Password string, or empty string if not found.
    """
    try:
        creds = load_test_credentials()
        return creds.get("gitlab_ssh_password", "")
    except (ValueError, OSError):
        return ""


def _ssh_to_gitlab(host, cmd: str) -> Dict[str, Any]:
    """Run a command on the GitLab server via SSH from OIM.

    Tries key-based SSH first (BatchMode=yes). If that fails,
    falls back to sshpass with gitlab_ssh_password from test_creds.yml.

    Args:
        host: Testinfra host connection.
        cmd: Command to run on the GitLab server.

    Returns:
        Dict with keys: success, stdout, error.
    """
    gitlab_config = _get_gitlab_config(host)
    gitlab_host = gitlab_config.get("gitlab_host", "")

    if not gitlab_host:
        config_path = gitlab_config.get("_config_path", "unknown")
        return {
            "success": False,
            "stdout": "",
            "error": (
                f"gitlab_host not found or empty in {config_path}. "
                f"Set gitlab_host in build_stream_config.yml."
            ),
        }

    # Try key-based SSH first (BatchMode=yes — no password prompt)
    ssh_cmd = CMDS["ssh_to_gitlab"].format(
        gitlab_host=gitlab_host, cmd=cmd,
    )
    result = run_on_host(host, ssh_cmd)

    if result.rc == 0:
        return {
            "success": True,
            "stdout": result.stdout if result.stdout else "",
            "error": "",
        }

    # Key-based failed — try sshpass with gitlab_ssh_password
    password = _get_gitlab_ssh_password()
    if password:
        sshpass_cmd = CMDS["sshpass_to_gitlab"].format(
            password=password,
            gitlab_host=gitlab_host,
            cmd=cmd,
        )
        result = run_on_host(host, sshpass_cmd)
        if result.rc == 0:
            return {
                "success": True,
                "stdout": result.stdout if result.stdout else "",
                "error": "",
            }
        return {
            "success": False,
            "stdout": result.stdout if result.stdout else "",
            "error": (
                f"SSH to {gitlab_host} failed with sshpass (rc={result.rc}). "
                f"Verify gitlab_ssh_password in test_creds.yml and "
                f"that sshpass is installed on the OIM host."
            ),
        }

    return {
        "success": False,
        "stdout": "",
        "error": (
            f"SSH to {gitlab_host} failed (key-based auth rejected). "
            f"gitlab_ssh_password not set in test_creds.yml. "
            f"Run: setup_env.sh --set-domain-creds to set the password, "
            f"or set up SSH key-based auth: ssh-copy-id root@{gitlab_host}"
        ),
    }


def _get_gitlab_root_token(host) -> Dict[str, Any]:
    """Get the GitLab root access token from the GitLab server.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, token, error.
    """
    ssh_result = _ssh_to_gitlab(
        host,
        f"cat {GITLAB_ROOT_TOKEN_FILE} 2>/dev/null",
    )
    if ssh_result["success"] and ssh_result["stdout"].strip():
        return {
            "success": True,
            "token": ssh_result["stdout"].strip(),
            "error": "",
        }
    return {
        "success": False,
        "token": "",
        "error": "Root token not found",
    }


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
        ssh_result = _ssh_to_gitlab(
            host,
            CMDS["rpm_check"].format(package=pkg),
        )
        if ssh_result["success"] and pkg in ssh_result["stdout"]:
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
    gitlab_config = _get_gitlab_config(host)
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

    ssh_result = _ssh_to_gitlab(host, "echo REACHABLE")

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
    ssh_result = _ssh_to_gitlab(host, cmd)

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
    ssh_all = _ssh_to_gitlab(host, cmd_all)

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

    ssh_result = _ssh_to_gitlab(
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
        ssh_result = _ssh_to_gitlab(
            host,
            CMDS["systemctl_is_active"].format(service=svc_name),
        )
        status = ssh_result["stdout"].strip() if ssh_result["success"] else "unknown"
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
        config_path = gitlab_config.get("_config_path", "unknown")
        result["error"] = (
            f"gitlab_host not found or empty in {config_path}. "
            f"Set gitlab_host in build_stream_config.yml."
        )
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

    if result["http_code"] in GITLAB_SUCCESS_HTTP_CODES:
        result["success"] = True
        result["details"] = f"HTTP {result['http_code']} from {url}"
    else:
        result["error"] = (
            f"HTTP {result['http_code']} from {url}. "
            f"GitLab may not be running on {gitlab_host}:{gitlab_port}. "
            f"Check: curl -kI {url}"
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

    ssh_result = _ssh_to_gitlab(host, "gitlab-ctl status 2>/dev/null")
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
    ssh_cpu = _ssh_to_gitlab(host, CMDS["nproc_cmd"])
    if ssh_cpu["success"]:
        try:
            result["actual"]["cpu_cores"] = int(
                ssh_cpu["stdout"].strip()
            )
        except ValueError:
            pass

    # Memory
    ssh_mem = _ssh_to_gitlab(host, CMDS["free_cmd"])
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
    ssh_disk = _ssh_to_gitlab(host, CMDS["df_cmd"])
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
    gitlab_config = _get_gitlab_config(host)
    expected = int(gitlab_config.get("puma_workers", "2"))

    result = {
        "success": False,
        "expected": expected,
        "actual": 0,
        "details": "",
        "error": "",
    }

    ssh_result = _ssh_to_gitlab(
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
    gitlab_config = _get_gitlab_config(host)
    expected = int(gitlab_config.get("sidekiq_concurrency", "10"))

    result = {
        "success": False,
        "expected": expected,
        "actual": 0,
        "details": "",
        "error": "",
    }

    ssh_result = _ssh_to_gitlab(
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


def check_gitlab_project_exists(host) -> Dict[str, Any]:
    """Verify the GitLab project exists.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, project_name, project_id, details,
        error.
    """
    gitlab_config = _get_gitlab_config(host)
    project_name = gitlab_config.get("project_name", "omnia-catalog")

    result = {
        "success": False,
        "project_name": project_name,
        "project_id": None,
        "details": "",
        "error": "",
    }

    rails_cmd = CMDS["gitlab_rails_project_id"].format(
        project_name=project_name,
    )
    ssh_result = _ssh_to_gitlab(host, rails_cmd)

    if not ssh_result["success"]:
        result["error"] = f"gitlab-rails query failed: {ssh_result['error']}"
        return result

    project_id = ssh_result["stdout"].strip()
    if project_id and project_id.isdigit():
        result["project_id"] = int(project_id)
        result["success"] = True
        result["details"] = (
            f"Project '{project_name}' exists (ID: {project_id})"
        )
    else:
        result["error"] = f"Project '{project_name}' not found"
    return result


def check_gitlab_project_visibility(host) -> Dict[str, Any]:
    """Verify GitLab project visibility is configured correctly.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, expected, actual, details, error.
    """
    gitlab_config = _get_gitlab_config(host)
    project_name = gitlab_config.get("project_name", "omnia-catalog")
    expected = gitlab_config.get("project_visibility", "private")

    result = {
        "success": False,
        "expected": expected,
        "actual": "",
        "details": "",
        "error": "",
    }

    rails_cmd = CMDS["gitlab_rails_project_visibility"].format(
        project_name=project_name,
    )
    ssh_result = _ssh_to_gitlab(host, rails_cmd)

    if not ssh_result["success"]:
        result["error"] = f"Failed to query visibility: {ssh_result['error']}"
        return result

    actual_level = ssh_result["stdout"].strip()
    level_to_name = {v: k for k, v in GITLAB_VISIBILITY_LEVELS.items()}
    result["actual"] = level_to_name.get(
        actual_level, f"unknown({actual_level})"
    )

    expected_level = GITLAB_VISIBILITY_LEVELS.get(expected, "0")
    if actual_level == expected_level:
        result["success"] = True
        result["details"] = f"Visibility: {result['actual']}"
    else:
        result["error"] = (
            f"Expected {expected}, got {result['actual']}"
        )
    return result


def check_gitlab_default_branch(host) -> Dict[str, Any]:
    """Verify GitLab project default branch is configured correctly.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, expected, actual, details, error.
    """
    gitlab_config = _get_gitlab_config(host)
    project_name = gitlab_config.get("project_name", "omnia-catalog")
    expected = gitlab_config.get("default_branch", "main")

    result = {
        "success": False,
        "expected": expected,
        "actual": "",
        "details": "",
        "error": "",
    }

    rails_cmd = CMDS["gitlab_rails_project_default_branch"].format(
        project_name=project_name,
    )
    ssh_result = _ssh_to_gitlab(host, rails_cmd)

    if not ssh_result["success"]:
        result["error"] = f"Failed to query branch: {ssh_result['error']}"
        return result

    result["actual"] = ssh_result["stdout"].strip()
    if result["actual"] == expected:
        result["success"] = True
        result["details"] = f"Default branch: {result['actual']}"
    else:
        result["error"] = (
            f"Expected {expected}, got {result['actual']}"
        )
    return result


def _get_gitlab_api_context(host) -> Dict[str, str]:
    """Build GitLab API context (URL, token, project_id, branch).

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with api_url, token, project_id, branch, or error.
    """
    gitlab_config = _get_gitlab_config(host)
    gitlab_host = gitlab_config.get("gitlab_host", "")
    gitlab_port = gitlab_config.get("gitlab_https_port", "443")
    project_name = gitlab_config.get("project_name", "omnia-catalog")
    branch = gitlab_config.get("default_branch", "main")

    token_result = _get_gitlab_root_token(host)
    if not token_result["success"]:
        return {"error": "Failed to get GitLab token"}

    project_result = check_gitlab_project_exists(host)
    if not project_result["success"]:
        return {"error": f"Project {project_name} not found"}

    api_url = (
        f"https://{gitlab_host}:{gitlab_port}"
        f"/api/{GITLAB_API_VERSION}"
    )

    return {
        "api_url": api_url,
        "token": token_result["token"],
        "project_id": f"root%2F{project_name}",
        "branch": branch,
        "error": "",
    }


def check_gitlab_repo_file_exists(
    host, file_path: str
) -> Dict[str, Any]:
    """Verify a file exists in the GitLab repository.

    Args:
        host: Testinfra host connection.
        file_path: Path of the file in the repository.

    Returns:
        Dict with keys: success, file, details, error.
    """
    result = {
        "success": False,
        "file": file_path,
        "details": "",
        "error": "",
    }

    ctx = _get_gitlab_api_context(host)
    if ctx.get("error"):
        result["error"] = ctx["error"]
        return result

    encoded_path = file_path.replace("/", "%2F").replace(".", "%2E")
    cmd = CMDS["gitlab_api_file_exists"].format(
        token=ctx["token"],
        api_url=ctx["api_url"],
        project_id=ctx["project_id"],
        file_path=encoded_path,
        branch=ctx["branch"],
    )
    cmd_result = run_on_host(host, cmd)

    http_code = cmd_result.stdout.strip() if cmd_result.stdout else "0"
    if http_code == "200":
        result["success"] = True
        result["details"] = f"{file_path} exists in repo"
    else:
        result["error"] = f"{file_path} not found (HTTP {http_code})"
    return result


def check_gitlab_pipeline_variables(host) -> Dict[str, Any]:
    """Verify GitLab CI/CD pipeline variables are configured.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, found, missing, total, details, error.
    """
    result = {
        "success": False,
        "found": [],
        "missing": [],
        "total": len(GITLAB_PIPELINE_VARIABLES),
        "details": "",
        "error": "",
    }

    ctx = _get_gitlab_api_context(host)
    if ctx.get("error"):
        result["error"] = ctx["error"]
        return result

    cmd = CMDS["gitlab_api_list_variables"].format(
        token=ctx["token"],
        api_url=ctx["api_url"],
        project_id=ctx["project_id"],
    )
    cmd_result = run_on_host(host, cmd)

    if cmd_result.rc != 0 or not cmd_result.stdout.strip():
        result["error"] = "Failed to list pipeline variables"
        return result

    try:
        variables = json.loads(cmd_result.stdout.strip())
        var_keys = {v["key"] for v in variables}
    except (json.JSONDecodeError, KeyError):
        result["error"] = "Invalid JSON from variables API"
        return result

    for var_name in GITLAB_PIPELINE_VARIABLES:
        if var_name in var_keys:
            result["found"].append(var_name)
        else:
            result["missing"].append(var_name)

    result["success"] = len(result["missing"]) == 0
    result["details"] = (
        f"{len(result['found'])}/{result['total']} variables configured"
    )
    return result


def check_gitlab_repo_dir_exists(
    host, dir_path: str
) -> Dict[str, Any]:
    """Verify a directory exists in the GitLab repository.

    Args:
        host: Testinfra host connection.
        dir_path: Path of the directory in the repository.

    Returns:
        Dict with keys: success, dir, details, error.
    """
    result = {
        "success": False,
        "dir": dir_path,
        "details": "",
        "error": "",
    }

    ctx = _get_gitlab_api_context(host)
    if ctx.get("error"):
        result["error"] = ctx["error"]
        return result

    cmd = CMDS["gitlab_api_tree"].format(
        token=ctx["token"],
        api_url=ctx["api_url"],
        project_id=ctx["project_id"],
        dir_path=dir_path,
        branch=ctx["branch"],
    )
    cmd_result = run_on_host(host, cmd)

    if cmd_result.rc != 0:
        result["error"] = f"API call failed for {dir_path}"
        return result

    try:
        data = json.loads(cmd_result.stdout.strip())
        if isinstance(data, list) and len(data) > 0:
            result["success"] = True
            result["details"] = (
                f"{dir_path} exists ({len(data)} items)"
            )
        else:
            result["error"] = f"{dir_path} empty or not found"
    except json.JSONDecodeError:
        result["error"] = f"Invalid response for {dir_path}"
    return result


def check_omnia_env_in_repo(host) -> Dict[str, Any]:
    """Verify omnia.env exists in the GitLab repository.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, details, error.
    """
    file_result = check_gitlab_repo_file_exists(host, "omnia.env")
    if not file_result["success"]:
        return {
            "success": False,
            "details": "",
            "error": "omnia.env not found in GitLab repo",
        }
    return {
        "success": True,
        "details": "omnia.env exists in GitLab repo",
        "error": "",
    }


def check_domain_input_dirs(host) -> Dict[str, Any]:
    """Verify domain input directories exist in the GitLab repo.

    Checks for input/repo_manager/ and input/image_build_manager/.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, found, missing, details, error.
    """
    dirs_to_check = [
        "input/repo_manager",
        "input/image_build_manager",
    ]

    result = {
        "success": False,
        "found": [],
        "missing": [],
        "details": "",
        "error": "",
    }

    for dir_path in dirs_to_check:
        dir_result = check_gitlab_repo_dir_exists(host, dir_path)
        if dir_result["success"]:
            result["found"].append(dir_path)
        else:
            result["missing"].append(dir_path)

    result["success"] = len(result["missing"]) == 0
    result["details"] = (
        f"Found: {', '.join(result['found']) or 'none'}"
    )
    if result["missing"]:
        result["error"] = (
            f"Missing: {', '.join(result['missing'])}"
        )
    return result
