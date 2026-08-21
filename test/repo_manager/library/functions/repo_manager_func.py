# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
Repo Manager — Domain-specific verification functions.

All verification functions return a dict with keys:
  success (bool), details (str), error (str), and optionally skipped (bool).
"""

from typing import Any, Dict
import os
import yaml

from omnia_auto import load_test_config, run_on_host, run_playbook as _run_playbook
from ..vars.common_vars import (
    PLAYBOOK_ENTRY_POINT,
    PLAYBOOK_WORKDIR,
    CMDS,
    INPUT_FILES,
    OUTPUT_FILES,
    PULP_CONTAINER_NAME,
    PULP_PORT,
    PULP_CLI_SYMLINK,
    PULP_CERTS_DIR,
    PULP_SYSTEMD_UNIT,
    PULP_YUM_REPO_FILE,
)


def run_playbook(tag=None, **kwargs):
    """Wrapper around omnia_auto.run_playbook with repo_manager defaults."""
    return _run_playbook(
        playbook=kwargs.pop("playbook", PLAYBOOK_ENTRY_POINT),
        playbook_workdir=kwargs.pop("playbook_workdir", PLAYBOOK_WORKDIR),
        tag=tag,
        **kwargs,
    )


def _get_input_path() -> str:
    """Return the repo_manager input path for the configured project."""
    config = load_test_config()
    project = config.get("project_name", "project_default")
    return f"/opt/omnia/repo_manager/input/{project}"


def _get_output_path() -> str:
    """Return the repo_manager output path for the configured project."""
    config = load_test_config()
    project = config.get("project_name", "project_default")
    return f"/opt/omnia/repo_manager/output/{project}"


def _get_base_path() -> str:
    """Return the repo_manager base data path."""
    return "/opt/omnia/repo_manager"


def _cmd_file_exists(host, path: str) -> str:
    """Run a file-existence check on the target."""
    cmd = CMDS["file_exists"].format(path=path)
    return run_on_host(host, cmd)


def _cmd_dir_exists(host, path: str) -> str:
    """Run a directory-existence check on the target."""
    cmd = CMDS["dir_exists"].format(path=path)
    return run_on_host(host, cmd)


def check_input_config_exists(host) -> Dict[str, Any]:
    """Verify repo_manager_config.yml exists on target."""
    input_path = _get_input_path()
    path = f"{input_path}/{INPUT_FILES['repo_manager_config']}"
    result = _cmd_file_exists(host, path)
    if result.rc == 0 and "exists" in result.stdout:
        return {
            "success": True,
            "details": f"{INPUT_FILES['repo_manager_config']} found at {path}",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Checked path: {path}",
        "error": f"{INPUT_FILES['repo_manager_config']} not found at {path}",
    }


def check_endpoint_config_exists(host) -> Dict[str, Any]:
    """Verify repo_manager_endpoint_config.yml exists on target."""
    input_path = _get_input_path()
    path = f"{input_path}/{INPUT_FILES['repo_manager_endpoint_config']}"
    result = _cmd_file_exists(host, path)
    if result.rc == 0 and "exists" in result.stdout:
        return {
            "success": True,
            "details": f"{INPUT_FILES['repo_manager_endpoint_config']} found at {path}",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Checked path: {path}",
        "error": f"{INPUT_FILES['repo_manager_endpoint_config']} not found at {path}",
    }


def check_credentials_present(host) -> Dict[str, Any]:
    """Verify credentials file is present on target."""
    input_path = _get_input_path()
    path = f"{input_path}/{INPUT_FILES['repo_manager_credentials']}"
    result = _cmd_file_exists(host, path)
    if result.rc == 0 and "exists" in result.stdout:
        return {
            "success": True,
            "details": f"{INPUT_FILES['repo_manager_credentials']} found at {path}",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Checked path: {path}",
        "error": f"{INPUT_FILES['repo_manager_credentials']} not found at {path}",
    }


def check_pulp_container_running(host) -> Dict[str, Any]:
    """Verify Pulp container is running."""
    cmd = CMDS["container_running"].format(name=PULP_CONTAINER_NAME)
    result = run_on_host(host, cmd)
    if result.rc == 0 and "running" in result.stdout:
        return {
            "success": True,
            "details": f"Pulp container is running",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Container status: {result.stdout.strip()}",
        "error": "Pulp container is not running",
    }


def check_pulp_status_healthy(host) -> Dict[str, Any]:
    """Verify Pulp status command succeeds and reports healthy."""
    result = run_on_host(host, CMDS["pulp_status"])
    if result.rc == 0 and result.stdout.strip():
        return {
            "success": True,
            "details": "pulp status returned successfully",
            "error": "",
        }
    return {
        "success": False,
        "details": f"pulp status exit code: {result.rc}",
        "error": "pulp status command failed or returned empty output",
    }


def check_pulp_endpoint_reachable(host) -> Dict[str, Any]:
    """Verify Pulp endpoint responds with HTTP 200."""
    # Use 127.0.0.1 for local Pulp endpoint health check
    cmd = (
        f"curl -k -s -o /dev/null -w '%{{http_code}}' "
        f"https://127.0.0.1:{PULP_PORT}/pulp/api/v3/status/ "
        f"|| echo '000'"
    )
    result = run_on_host(host, cmd)
    status = result.stdout.strip()
    if status == "200":
        return {
            "success": True,
            "details": f"Pulp endpoint returned HTTP {status}",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Pulp endpoint HTTP status: {status}",
        "error": "Pulp endpoint is not reachable",
    }


def check_pulp_cli_configured(host) -> Dict[str, Any]:
    """Verify Pulp CLI symlink and version work."""
    result = run_on_host(host, CMDS["pulp_version"])
    if result.rc == 0:
        return {
            "success": True,
            "details": f"Pulp CLI version: {result.stdout.strip()}",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Pulp CLI exit code: {result.rc}",
        "error": "Pulp CLI is not configured at /usr/local/bin/pulp",
    }


def check_pulp_certificates_exist(host) -> Dict[str, Any]:
    """Verify Pulp SSL certificates exist for HTTPS."""
    crt_path = f"{PULP_CERTS_DIR}/pulp_webserver.crt"
    key_path = f"{PULP_CERTS_DIR}/pulp_webserver.key"
    crt_result = _cmd_file_exists(host, crt_path)
    key_result = _cmd_file_exists(host, key_path)
    if "exists" in crt_result.stdout and "exists" in key_result.stdout:
        return {
            "success": True,
            "details": f"Pulp certificates found at {PULP_CERTS_DIR}",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Checked crt: {crt_path}, key: {key_path}",
        "error": "Pulp SSL certificates are missing",
    }


def _read_repo_status(host) -> Dict[str, Any]:
    """Read repo_status.yml from the target and parse as YAML."""
    output_path = _get_output_path()
    path = f"{output_path}/{OUTPUT_FILES['repo_status']}"
    result = run_on_host(host, f"cat {path}")
    if result.rc != 0:
        return {"success": False, "details": f"Could not read {path}", "error": result.stderr}
    try:
        data = yaml.safe_load(result.stdout)
        return {"success": True, "details": data, "error": ""}
    except yaml.YAMLError as exc:
        return {
            "success": False,
            "details": f"Invalid YAML in {path}",
            "error": str(exc),
        }


def check_repo_status_exists(host) -> Dict[str, Any]:
    """Verify repo_status.yml exists."""
    output_path = _get_output_path()
    path = f"{output_path}/{OUTPUT_FILES['repo_status']}"
    result = _cmd_file_exists(host, path)
    if result.rc == 0 and "exists" in result.stdout:
        return {
            "success": True,
            "details": f"{OUTPUT_FILES['repo_status']} found at {path}",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Checked path: {path}",
        "error": f"{OUTPUT_FILES['repo_status']} not found",
    }


def check_repo_status_success(host) -> Dict[str, Any]:
    """Verify repo_status.yml reports overall_status = success."""
    result = _read_repo_status(host)
    if not result["success"]:
        return result
    data = result["details"]
    overall_status = data.get("overall_status", "").lower()
    if overall_status == "success":
        return {
            "success": True,
            "details": f"overall_status is '{overall_status}'",
            "error": "",
        }
    return {
        "success": False,
        "details": f"overall_status is '{overall_status}'",
        "error": "repo_status.yml does not report success",
    }


def check_repo_status_has_repo(host, repo_name: str, arch: str = "x86_64", os_version: str = "10.0") -> Dict[str, Any]:
    """Verify a specific RPM repository is present in repo_status.yml."""
    result = _read_repo_status(host)
    if not result["success"]:
        return result
    data = result["details"]
    try:
        url = data["repositories"][os_version][arch][repo_name]["url"]
        if url:
            return {
                "success": True,
                "details": f"Repository '{repo_name}' ({arch}) URL: {url}",
                "error": "",
            }
    except (KeyError, TypeError):
        pass
    return {
        "success": False,
        "details": f"Searched repositories.{os_version}.{arch}.{repo_name}",
        "error": f"Repository '{repo_name}' ({arch}) not found in repo_status.yml",
    }


def check_repo_status_has_file_repo(host, repo_name: str, arch: str = "x86_64") -> Dict[str, Any]:
    """Verify a specific file repository (tarball) is present in repo_status.yml."""
    result = _read_repo_status(host)
    if not result["success"]:
        return result
    data = result["details"]
    try:
        url = data["file_repos"][arch]["tarball"][repo_name]
        if url:
            return {
                "success": True,
                "details": f"File repo '{repo_name}' ({arch}) URL: {url}",
                "error": "",
            }
    except (KeyError, TypeError):
        pass
    return {
        "success": False,
        "details": f"Searched file_repos.{arch}.tarball.{repo_name}",
        "error": f"File repo '{repo_name}' not found in repo_status.yml",
    }


def check_pulp_container_removed(host) -> Dict[str, Any]:
    """Verify Pulp container is removed."""
    cmd = f"podman container exists {PULP_CONTAINER_NAME} && echo 'exists' || echo 'missing'"
    result = run_on_host(host, cmd)
    if "missing" in result.stdout:
        return {
            "success": True,
            "details": "Pulp container is removed",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Container check output: {result.stdout.strip()}",
        "error": "Pulp container still exists",
    }


def check_pulp_cli_removed(host) -> Dict[str, Any]:
    """Verify Pulp CLI symlink is removed."""
    result = _cmd_file_exists(host, PULP_CLI_SYMLINK)
    if "missing" in result.stdout:
        return {
            "success": True,
            "details": f"Pulp CLI symlink removed: {PULP_CLI_SYMLINK}",
            "error": "",
        }
    return {
        "success": False,
        "details": f"Pulp CLI symlink still exists: {PULP_CLI_SYMLINK}",
        "error": "Pulp CLI symlink not removed",
    }


def check_pulp_directories_removed(host) -> Dict[str, Any]:
    """Verify Pulp config directories are removed."""
    base_path = _get_base_path()
    dirs = [
        f"{base_path}/pulp_config",
        f"{base_path}/log/pulp",
    ]
    for d in dirs:
        result = _cmd_dir_exists(host, d)
        if "exists" in result.stdout:
            return {
                "success": False,
                "details": f"Directory still exists: {d}",
                "error": "Pulp directories not fully removed",
            }
    return {
        "success": True,
        "details": f"Pulp directories removed: {', '.join(dirs)}",
        "error": "",
    }
