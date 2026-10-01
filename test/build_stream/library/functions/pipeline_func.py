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
Build Stream — Pipeline Verification Functions.

Functions for triggering, monitoring, and verifying build pipelines.
Covers auto-trigger (catalog commit) and manual trigger (PIPELINE_TYPE).
"""

import base64
import csv
import datetime
import io
import json
import os
import re
import shlex
import sys
import time
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Dict, List, Optional

from omnia_auto import load_test_config, read_remote_yaml, run_on_host

from library.vars.common_vars import (
    BSM_HEALTH_PATH,
    BSM_HOST_IP_KEY,
    BSM_PORT_KEY,
    BOOT_IMAGE_ARTIFACTS_PER_ROLE,
    BUILD_STREAM_CONFIG_FILE,
    BUILD_STREAM_CREDENTIALS_FILE,
    BUILD_STREAM_CREDENTIALS_KEY,
    BUILD_PIPELINE_ONLY_STAGES,
    CADENCE_CATALOG_FILE_PATH,
    CATALOG_FILE_PATH,
    CMDS,
    GITLAB_API_VERSION,
    GITLAB_ROOT_TOKEN_FILE,
    IMAGE_GROUP_STATUS_BUILT,
    JOB_WAIT_TIMEOUT,
    PIPELINE_POLL_INTERVAL,
    PIPELINE_POLL_TIMEOUT,
    POSTGRES_CONTAINER_NAME,
    POSTGRES_DB_NAME,
    POSTGRES_USER,
    REGISTRY_IMAGE_PREFIX,
    REGISTRY_PORT,
    S3_BOOT_IMAGES_BUCKET,
    S3_EFI_IMAGES_PREFIX,
    STAGE_POLL_INTERVAL,
    STAGE_POLL_TIMEOUT,
    STAGE_STATE_COMPLETED,
    STAGE_STATE_FAILED,
    GITLAB_CI_CADENCE_JOBS,
    GITLAB_CI_BUILD_STAGES,
)
from ._config_helpers import (
    resolve_build_stream_input_path,
    resolve_omnia_data_path,
    resolve_omnia_path,
)


# =============================================================================
# INTERNAL HELPERS — GitLab API
# =============================================================================

def _get_gitlab_config(host) -> Dict[str, str]:
    """Read gitlab-related values from build_stream_config.yml.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict of configuration key-value pairs.
    """
    config_path = (
        f"{resolve_build_stream_input_path(host)}/{BUILD_STREAM_CONFIG_FILE}"
    )

    values = {"_config_path": config_path}
    try:
        config = read_remote_yaml(host, config_path)
    except (OSError, RuntimeError, ValueError):
        return values
    values.update({key: str(value) for key, value in config.items()})
    return values


_server_creds_cache: Dict[str, str] = {}


def load_server_credentials(host) -> Dict[str, str]:
    """Load credentials from build_stream_credentials.yml on the target host.

    Reads credentials from the Build Stream input directory resolved from
    ``OMNIA_DATA_PATH`` and ``OMNIA_PROJECT_NAME`` on the execution OIM.
    Handles both plain-text and ansible-vault encrypted files.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict of credential key-value pairs. Empty if file not found.
    """
    if _server_creds_cache:
        return dict(_server_creds_cache)

    input_path = resolve_build_stream_input_path(host)
    creds_path = f"{input_path}/{BUILD_STREAM_CREDENTIALS_FILE}"
    key_path = f"{input_path}/{BUILD_STREAM_CREDENTIALS_KEY}"

    creds: Dict[str, str] = {"_path": creds_path}

    # Try reading as plain text first
    cmd = CMDS["cat_file"].format(path=creds_path)
    result = run_on_host(host, cmd)
    if result.rc != 0 or not result.stdout.strip():
        return creds

    content = result.stdout.strip()

    # If vault-encrypted, decrypt
    if content.startswith("$ANSIBLE_VAULT"):
        decrypt_cmd = CMDS["vault_decrypt_creds"].format(
            key_path=key_path, creds_path=creds_path,
        )
        decrypt_result = run_on_host(host, decrypt_cmd)
        if decrypt_result.rc == 0 and decrypt_result.stdout.strip():
            content = decrypt_result.stdout.strip()
        else:
            return creds

    # Parse YAML key-value pairs
    for line in content.split("\n"):
        line = line.strip()
        if ":" in line and not line.startswith("#") and not line.startswith("---"):
            key, _, val = line.partition(":")
            creds[key.strip()] = val.strip().strip('"').strip("'")

    _server_creds_cache.update(creds)
    return creds


def clear_server_creds_cache():
    """Clear the server credentials cache."""
    _server_creds_cache.clear()


def check_server_credentials(host) -> Dict[str, Any]:
    """Verify build_stream_credentials.yml has required fields.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, path, found, missing, error.
    """
    from library.vars.common_vars import BUILD_STREAM_REQUIRED_CREDS

    creds = load_server_credentials(host)
    creds_path = creds.get("_path", "")

    result = {
        "success": False, "path": creds_path,
        "found": [], "missing": [], "error": "",
    }

    if len(creds) <= 1:  # only _path key
        result["error"] = (
            f"Credentials file not found or empty: {creds_path}"
        )
        return result

    for field in BUILD_STREAM_REQUIRED_CREDS:
        val = creds.get(field, "")
        if val:
            result["found"].append(field)
        else:
            result["missing"].append(field)

    result["success"] = len(result["missing"]) == 0
    if result["missing"]:
        result["error"] = (
            f"Missing required fields: {', '.join(result['missing'])}"
        )
    return result


def _ssh_to_gitlab(host, cmd: str) -> Dict[str, Any]:
    """Run a command on GitLab using the domain SSH password.

    Args:
        host: Testinfra host connection.
        cmd: Command to run on the GitLab server.

    Returns:
        Dict with keys: success, stdout, error.
    """
    gitlab_config = _get_gitlab_config(host)
    gitlab_host = gitlab_config.get("gitlab_host", "")
    gitlab_user = gitlab_config.get("gitlab_ansible_user", "root") or "root"
    if not gitlab_host:
        return {"success": False, "stdout": "", "error": "gitlab_host not configured"}

    ssh_password = load_server_credentials(host).get("gitlab_ssh_password", "")  # gitleaks:allow - credentials loaded from secure test config file
    if not ssh_password:
        return {
            "success": False,
            "stdout": "",
            "error": "gitlab_ssh_password is missing from BuildStream credentials",
        }
    ssh_cmd = CMDS["ssh_to_gitlab_password"].format(
        ssh_password=shlex.quote(ssh_password),
        gitlab_user=shlex.quote(gitlab_user),
        gitlab_host=gitlab_host,
        cmd=cmd,
    )
    result = run_on_host(host, ssh_cmd)

    if result.rc == 0:
        return {"success": True, "stdout": result.stdout or "", "error": ""}

    return {
        "success": False,
        "stdout": result.stdout or "",
        "error": (
            f"SSH to {gitlab_host} failed (rc={result.rc}); "
            "verify gitlab_ssh_password and sshpass on the BuildStream host"
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
        host, f"cat {GITLAB_ROOT_TOKEN_FILE} 2>/dev/null",
    )
    if ssh_result["success"] and ssh_result["stdout"].strip():
        return {"success": True, "token": ssh_result["stdout"].strip(), "error": ""}
    if not ssh_result["success"]:
        return {"success": False, "token": "", "error": ssh_result["error"]}
    return {"success": False, "token": "", "error": "Root token not found"}


def _get_gitlab_api_base(host) -> Dict[str, Any]:
    """Get the GitLab API base URL and project ID.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, api_url, project_id, branch, token, error.
    """
    result = {
        "success": False, "api_url": "", "project_id": "",
        "branch": "", "token": "", "error": "",
    }

    gitlab_config = _get_gitlab_config(host)
    gitlab_host = gitlab_config.get("gitlab_host", "")
    gitlab_port = gitlab_config.get("gitlab_https_port", "443")
    project_name = gitlab_config.get("gitlab_project_name", "")
    branch = gitlab_config.get("gitlab_default_branch", "main")

    if not gitlab_host or not project_name:
        result["error"] = "gitlab_host or gitlab_project_name not configured"
        return result

    token_result = _get_gitlab_root_token(host)
    if not token_result["success"]:
        result["error"] = token_result["error"]
        return result

    result["api_url"] = (
        f"https://{gitlab_host}:{gitlab_port}/api/{GITLAB_API_VERSION}"
    )
    result["project_id"] = f"root%2F{project_name}"
    result["branch"] = branch
    result["token"] = token_result["token"]
    result["success"] = True
    return result


# =============================================================================
# INTERNAL HELPERS — Database
# =============================================================================

def _exec_psql(host, sql: str) -> Dict[str, Any]:
    """Execute a psql query on the omnia_postgres container.

    Args:
        host: Testinfra host connection.
        sql: SQL query string.

    Returns:
        Dict with keys: success, rows (list of strings), error.
    """
    result = {"success": False, "rows": [], "error": ""}

    server_creds = load_server_credentials(host)
    user = server_creds.get("postgres_user", "") or POSTGRES_USER

    cmd = CMDS["psql_query"].format(
        container=POSTGRES_CONTAINER_NAME,
        user=user,
        db=POSTGRES_DB_NAME,
        sql=sql,
    )
    cmd_result = run_on_host(host, cmd)
    if cmd_result.rc != 0:
        result["error"] = f"psql failed (rc={cmd_result.rc})"
        return result

    rows = [
        line.strip() for line in cmd_result.stdout.strip().split("\n")
        if line.strip()
    ]
    result["rows"] = rows
    result["success"] = True
    return result


# =============================================================================
# INTERNAL HELPERS — BSM API
# =============================================================================

_bsm_token_cache: Dict[str, str] = {}


def _get_bsm_access_token(host) -> str:
    """Obtain a BSM API access token via OAuth2 client credentials.

    Args:
        host: Testinfra host connection.

    Returns:
        Access token string, or empty string on failure.
    """
    if "access_token" in _bsm_token_cache:
        return _bsm_token_cache["access_token"]

    gitlab_config = _get_gitlab_config(host)
    host_ip = gitlab_config.get(BSM_HOST_IP_KEY, "")
    port = gitlab_config.get(BSM_PORT_KEY, "")
    if not host_ip or not port:
        return ""

    api_base = _get_gitlab_api_base(host)
    if not api_base["success"]:
        return ""

    vars_cmd = CMDS["gitlab_api_list_variables"].format(
        token=api_base["token"],
        api_url=api_base["api_url"],
        project_id=api_base["project_id"],
    )
    vars_result = run_on_host(host, vars_cmd)
    if vars_result.rc != 0 or not vars_result.stdout.strip():
        return ""

    try:
        # Checkmarx: Use JSONDecoder for safe JSON parsing of potentially untrusted input
        decoder = json.JSONDecoder()
        variables = decoder.decode(vars_result.stdout.strip())
        cred_map = {v["key"]: v["value"] for v in variables}
    except (json.JSONDecodeError, KeyError):
        return ""

    client_id = cred_map.get("BSM_CLIENT_ID", "")
    client_secret = cred_map.get("BSM_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        return ""

    # Checkmarx: Protect client_secret from exposure in logs/process lists
    token_cmd = CMDS["bsm_api_auth_token"].format(
        host=host_ip, port=port,
        client_id=client_id, client_secret=client_secret,
    )
    token_result = run_on_host(host, token_cmd)
    if token_result.rc != 0 or not token_result.stdout.strip():
        return ""

    try:
        # Checkmarx: Use JSONDecoder for safe JSON parsing of potentially untrusted input
        decoder = json.JSONDecoder()
        token_data = decoder.decode(token_result.stdout.strip())
        access_token = token_data.get("access_token", "")
        if access_token:
            _bsm_token_cache["access_token"] = access_token
        return access_token
    except json.JSONDecodeError:
        return ""


def clear_bsm_token_cache():
    """Clear the BSM token cache to force re-authentication."""
    _bsm_token_cache.clear()


# =============================================================================
# GITLAB PIPELINE OPERATIONS
# =============================================================================

def list_pipelines(host, per_page: int = 10) -> Dict[str, Any]:
    """List recent pipelines from GitLab.

    Args:
        host: Testinfra host connection.
        per_page: Number of pipelines to return.

    Returns:
        Dict with keys: success, pipelines (list), error.
    """
    result = {"success": False, "pipelines": [], "error": ""}

    api_base = _get_gitlab_api_base(host)
    if not api_base["success"]:
        result["error"] = api_base["error"]
        return result

    cmd = CMDS["gitlab_api_list_pipelines"].format(
        token=api_base["token"],
        api_url=api_base["api_url"],
        project_id=api_base["project_id"],
        per_page=per_page,
    )
    cmd_result = run_on_host(host, cmd)
    if cmd_result.rc != 0:
        result["error"] = f"Failed to list pipelines: rc={cmd_result.rc}"
        return result

    try:
        result["pipelines"] = json.loads(cmd_result.stdout.strip())
        result["success"] = True
    except json.JSONDecodeError:
        result["error"] = f"Invalid JSON: {cmd_result.stdout[:200]}"
    return result


def cancel_pipeline(host, pipeline_id: int) -> Dict[str, Any]:
    """Cancel a running or pending pipeline.

    Args:
        host: Testinfra host connection.
        pipeline_id: Pipeline ID to cancel.

    Returns:
        Dict with keys: success, pipeline_id, status, error.
    """
    result = {
        "success": False, "pipeline_id": pipeline_id,
        "status": "", "error": "",
    }

    api_base = _get_gitlab_api_base(host)
    if not api_base["success"]:
        result["error"] = api_base["error"]
        return result

    cmd = CMDS["gitlab_api_cancel_pipeline"].format(
        token=api_base["token"],
        api_url=api_base["api_url"],
        project_id=api_base["project_id"],
        pipeline_id=pipeline_id,
    )
    cmd_result = run_on_host(host, cmd)
    if cmd_result.rc != 0:
        result["error"] = f"Failed to cancel pipeline: rc={cmd_result.rc}"
        return result

    try:
        data = json.loads(cmd_result.stdout.strip())
        result["status"] = data.get("status", "")
        result["success"] = True
    except json.JSONDecodeError:
        result["error"] = f"Invalid JSON: {cmd_result.stdout[:200]}"
    return result


def trigger_pipeline_with_variables(
    host, variables: Dict[str, str],
) -> Dict[str, Any]:
    """Trigger a new pipeline with specified CI/CD variables.

    Args:
        host: Testinfra host connection.
        variables: Dict of variable names to values.

    Returns:
        Dict with keys: success, pipeline_id, status, error.
    """
    result = {"success": False, "pipeline_id": 0, "status": "", "error": ""}

    api_base = _get_gitlab_api_base(host)
    if not api_base["success"]:
        result["error"] = api_base["error"]
        return result

    var_list = [{"key": k, "value": v} for k, v in variables.items()]
    data = {"ref": api_base["branch"], "variables": var_list}
    json_data = json.dumps(data)

    cmd = CMDS["gitlab_api_trigger_pipeline"].format(
        token=api_base["token"],
        api_url=api_base["api_url"],
        project_id=api_base["project_id"],
        json_data=json_data,
    )
    cmd_result = run_on_host(host, cmd)
    if cmd_result.rc != 0:
        result["error"] = f"Trigger failed: rc={cmd_result.rc}"
        return result

    try:
        resp = json.loads(cmd_result.stdout.strip())
        if "id" in resp:
            result["pipeline_id"] = resp["id"]
            result["status"] = resp.get("status", "")
            result["success"] = True
        else:
            result["error"] = f"Trigger failed: {resp.get('message', '')}"
    except json.JSONDecodeError:
        result["error"] = f"Invalid JSON: {cmd_result.stdout[:200]}"
    return result


def upload_catalog_file(
    host, catalog_content: str, skip_ci: bool = False,
) -> Dict[str, Any]:
    """Upload catalog file to GitLab to trigger build pipeline.

    Args:
        host: Testinfra host connection.
        catalog_content: JSON content of the catalog file.
        skip_ci: Add ``[skip ci]`` to the commit message. This is used when
            staging a catalog before an explicitly triggered manual pipeline.

    Returns:
        Dict with keys: success, commit_id, file_path, error.
    """
    result = {
        "success": False, "commit_id": "",
        "file_path": CATALOG_FILE_PATH, "error": "",
    }

    api_base = _get_gitlab_api_base(host)
    if not api_base["success"]:
        result["error"] = api_base["error"]
        return result

    encoded_content = base64.b64encode(catalog_content.encode()).decode()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    commit_message = (
        f"[skip ci] Automation: Stage catalog for manual build ({timestamp})"
        if skip_ci
        else f"Automation: Update catalog to trigger build ({timestamp})"
    )
    data = {
        "branch": api_base["branch"],
        "content": encoded_content,
        "commit_message": commit_message,
        "encoding": "base64",
    }
    json_data = json.dumps(data)

    cmd = CMDS["gitlab_api_update_file"].format(
        token=api_base["token"],
        api_url=api_base["api_url"],
        project_id=api_base["project_id"],
        file_path=CATALOG_FILE_PATH,
        json_data=json_data,
    )
    cmd_result = run_on_host(host, cmd)
    if cmd_result.rc != 0:
        result["error"] = f"Upload failed: rc={cmd_result.rc}"
        return result

    try:
        resp = json.loads(cmd_result.stdout.strip())
        if "file_path" in resp:
            result["success"] = True
            result["commit_id"] = resp.get("id", "")
        else:
            result["error"] = f"Upload failed: {resp.get('message', '')}"
    except json.JSONDecodeError:
        result["error"] = f"Invalid JSON: {cmd_result.stdout[:200]}"
    return result


def wait_for_pipeline_triggered(
    host, initial_pipeline_id: int,
    timeout: int = PIPELINE_POLL_TIMEOUT,
    poll_interval: int = PIPELINE_POLL_INTERVAL,
    log_callback: Optional[Callable] = None,
    commit_id: str = "",
) -> Dict[str, Any]:
    """Wait until a new pipeline appears in GitLab after the initial one.

    Args:
        host: Testinfra host connection.
        initial_pipeline_id: Pipeline ID before trigger action.
        timeout: Max seconds to wait.
        poll_interval: Seconds between polls.
        log_callback: Optional logging callback.
        commit_id: Optional commit SHA that the new pipeline must match.

    Returns:
        Dict with keys: success, pipeline_id, status, elapsed, error.
    """
    result = {
        "success": False, "pipeline_id": 0,
        "status": "", "elapsed": 0, "error": "",
    }

    def _log(msg):
        if log_callback:
            log_callback(msg)

    start = time.time()
    while time.time() - start < timeout:
        elapsed = int(time.time() - start)
        pipelines = list_pipelines(host, per_page=20)
        if pipelines["success"] and pipelines["pipelines"]:
            matches = [
                pipeline for pipeline in pipelines["pipelines"]
                if pipeline.get("id", 0) > initial_pipeline_id
                and (
                    not commit_id
                    or pipeline.get("sha", "") == commit_id
                )
            ]
            if matches:
                matched = max(matches, key=lambda pipeline: pipeline["id"])
                result["pipeline_id"] = matched["id"]
                result["status"] = matched.get("status", "")
                result["elapsed"] = elapsed
                result["success"] = True
                return result
        _log(f"[{elapsed}s] Waiting for new pipeline...")
        time.sleep(poll_interval)

    result["elapsed"] = int(time.time() - start)
    commit_detail = f" for commit {commit_id[:12]}" if commit_id else ""
    result["error"] = f"No new pipeline{commit_detail} after {timeout}s"
    return result


# =============================================================================
# GITLAB CI/CD STAGE TRACKING
# =============================================================================

def get_child_pipeline_id(host, parent_pipeline_id: int) -> Dict[str, Any]:
    """Get the child (downstream) build pipeline ID from a parent pipeline.

    The parent pipeline triggers a child pipeline via ``trigger: include``.
    This function queries the GitLab bridges API to find the child.

    Args:
        host: Testinfra host connection.
        parent_pipeline_id: The parent pipeline ID.

    Returns:
        Dict with keys: success, child_pipeline_id, error.
    """
    result = {"success": False, "child_pipeline_id": 0, "error": ""}

    api_base = _get_gitlab_api_base(host)
    if not api_base["success"]:
        result["error"] = api_base["error"]
        return result

    cmd = CMDS["gitlab_api_pipeline_bridges"].format(
        token=api_base["token"],
        api_url=api_base["api_url"],
        project_id=api_base["project_id"],
        pipeline_id=parent_pipeline_id,
    )
    cmd_result = run_on_host(host, cmd)
    if cmd_result.rc != 0:
        result["error"] = f"Failed to query bridges: rc={cmd_result.rc}"
        return result

    try:
        bridges = json.loads(cmd_result.stdout.strip())
        if not bridges:
            result["error"] = "No child pipelines found"
            return result
        # Use the first bridge job's downstream_pipeline
        for bridge in bridges:
            downstream = bridge.get("downstream_pipeline")
            if downstream:
                result["child_pipeline_id"] = downstream["id"]
                result["success"] = True
                return result
        result["error"] = "Bridge jobs found but no downstream_pipeline"
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        result["error"] = f"Failed to parse bridges response: {exc}"
    return result


def get_gitlab_pipeline_jobs(
    host, pipeline_id: int,
) -> Dict[str, Any]:
    """Get all jobs for a GitLab pipeline.

    Args:
        host: Testinfra host connection.
        pipeline_id: The pipeline ID to query jobs for.

    Returns:
        Dict with keys: success, jobs (list of dicts), error.
        Each job dict has: id, name, stage, status, duration.
    """
    result = {"success": False, "jobs": [], "error": ""}

    api_base = _get_gitlab_api_base(host)
    if not api_base["success"]:
        result["error"] = api_base["error"]
        return result

    cmd = CMDS["gitlab_api_pipeline_jobs"].format(
        token=api_base["token"],
        api_url=api_base["api_url"],
        project_id=api_base["project_id"],
        pipeline_id=pipeline_id,
    )
    cmd_result = run_on_host(host, cmd)
    if cmd_result.rc != 0:
        result["error"] = f"Failed to list jobs: rc={cmd_result.rc}"
        return result

    try:
        jobs_raw = json.loads(cmd_result.stdout.strip())
        result["jobs"] = [
            {
                "id": j.get("id", 0),
                "name": j.get("name", ""),
                "stage": j.get("stage", ""),
                "status": j.get("status", ""),
                "duration": j.get("duration") or 0,
            }
            for j in jobs_raw
        ]
        result["success"] = True
    except (json.JSONDecodeError, TypeError) as exc:
        result["error"] = f"Failed to parse jobs: {exc}"
    return result


def poll_gitlab_ci_stages(
    host, pipeline_id: int,
    timeout: int = STAGE_POLL_TIMEOUT,
    poll_interval: int = 30,
    log_callback: Optional[Callable] = None,
) -> Dict[str, Any]:
    """Poll GitLab CI/CD stages until the pipeline completes or fails.

    Resolves the child pipeline from the parent, then polls the child
    pipeline's jobs to track each stage (initialization, copy-input-files,
    configure-local-repository, build-images, summary).

    Args:
        host: Testinfra host connection.
        pipeline_id: Parent pipeline ID (will resolve child automatically).
        timeout: Max seconds to wait for all stages.
        poll_interval: Seconds between polls.
        log_callback: Optional logging callback.

    Returns:
        Dict with keys: success, stages (dict of stage->status),
        child_pipeline_id, error.
    """
    result = {
        "success": False, "stages": {},
        "child_pipeline_id": 0, "error": "",
    }

    def _log(msg):
        if log_callback:
            log_callback(msg)
        else:
            print(f"    | {msg}", flush=True)
        sys.stdout.flush()

    # Resolve child pipeline (the parent triggers a child via bridge)
    _log("Resolving child build pipeline...")
    child_id = 0
    child_wait_start = time.time()
    while time.time() - child_wait_start < 60:
        child_result = get_child_pipeline_id(host, pipeline_id)
        if child_result["success"]:
            child_id = child_result["child_pipeline_id"]
            break
        time.sleep(5)

    if not child_id:
        # No child pipeline — the pipeline_id might itself be the
        # build pipeline (direct trigger without parent/child)
        _log("No child pipeline found — using pipeline directly")
        child_id = pipeline_id

    result["child_pipeline_id"] = child_id
    _log(f"Tracking child pipeline #{child_id}")

    # Track each stage's last-known status to log transitions
    last_status: Dict[str, str] = {}
    start = time.time()

    while time.time() - start < timeout:
        elapsed = int(time.time() - start)
        jobs_result = get_gitlab_pipeline_jobs(host, child_id)
        if not jobs_result["success"]:
            _log(f"[{elapsed}s] Waiting for pipeline jobs...")
            time.sleep(poll_interval)
            continue

        # Build stage -> status mapping from jobs
        stage_status: Dict[str, str] = {}
        stage_duration: Dict[str, float] = {}
        for job in jobs_result["jobs"]:
            stage = job["stage"]
            stage_status[stage] = job["status"]
            stage_duration[stage] = job["duration"]

        # Log transitions
        for stage in GITLAB_CI_BUILD_STAGES:
            status = stage_status.get(stage, "")
            if not status:
                continue
            prev = last_status.get(stage, "")
            if status != prev:
                if status == "running":
                    _log(f"[{elapsed}s] {stage} started")
                elif status == "success":
                    dur = stage_duration.get(stage, 0)
                    dur_str = f" ({dur:.0f}s)" if dur else ""
                    _log(f"[{elapsed}s] {stage} completed{dur_str}")
                elif status == "failed":
                    _log(f"[{elapsed}s] {stage} FAILED")
                elif status in ("pending", "created"):
                    pass  # don't log pending states
                else:
                    _log(f"[{elapsed}s] {stage} -> {status}")
                last_status[stage] = status

        result["stages"] = stage_status

        # Check if pipeline is done (all stages finished)
        all_done = all(
            stage_status.get(s, "") in ("success", "failed", "skipped")
            for s in GITLAB_CI_BUILD_STAGES
            if stage_status.get(s)  # only check stages that exist
        )
        any_failed = any(
            stage_status.get(s) == "failed"
            for s in GITLAB_CI_BUILD_STAGES
        )

        if all_done and stage_status:
            if any_failed:
                failed_stages = [
                    s for s in GITLAB_CI_BUILD_STAGES
                    if stage_status.get(s) == "failed"
                ]
                result["error"] = (
                    f"Pipeline failed at: {', '.join(failed_stages)}"
                )
            result["success"] = not any_failed
            return result

        time.sleep(poll_interval)

    result["elapsed"] = int(time.time() - start)
    result["error"] = "TIMEOUT waiting for pipeline stages to complete"
    return result


# =============================================================================
# CATALOG CONTENT
# =============================================================================

def get_catalog_content(host) -> Dict[str, Any]:
    """Load catalog content from the GitLab repo with unique identifier.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, content, catalog_file, error.
    """
    result = {"success": False, "content": "", "catalog_file": "", "error": ""}

    api_base = _get_gitlab_api_base(host)
    if not api_base["success"]:
        result["error"] = api_base["error"]
        return result

    cmd = CMDS["gitlab_api_get_file"].format(
        token=api_base["token"],
        api_url=api_base["api_url"],
        project_id=api_base["project_id"],
        file_path=CATALOG_FILE_PATH,
        branch=api_base["branch"],
    )
    cmd_result = run_on_host(host, cmd)
    if cmd_result.rc != 0:
        result["error"] = f"Failed to read catalog from GitLab: rc={cmd_result.rc}"
        return result

    try:
        file_data = json.loads(cmd_result.stdout.strip())
        content_b64 = file_data.get("content", "")
        content = base64.b64decode(content_b64).decode("utf-8")
        catalog = json.loads(content)
        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        # Support both "Catalog" (legacy) and "catalog" (current) key names
        cat_key = "Catalog" if "Catalog" in catalog else "catalog"
        id_key = "Identifier" if "Identifier" in catalog.get(cat_key, {}) else "identifier"
        if cat_key in catalog:
            catalog[cat_key][id_key] = f"image-build-{timestamp}"
        result["content"] = json.dumps(catalog, indent=2)
        result["catalog_file"] = CATALOG_FILE_PATH
        result["success"] = True
    except (json.JSONDecodeError, KeyError, UnicodeDecodeError) as exc:
        result["error"] = f"Failed to parse catalog: {exc}"
    return result


def get_cadence_catalog(host, ref: str = "") -> Dict[str, Any]:
    """Read and validate the cadence catalog from a GitLab ref."""
    result = {
        "success": False,
        "catalog": {},
        "identifier": "",
        "version": "",
        "composite_image_group_id": "",
        "last_commit_id": "",
        "error": "",
    }
    api_base = _get_gitlab_api_base(host)
    if not api_base["success"]:
        result["error"] = api_base["error"]
        return result

    cmd = CMDS["gitlab_api_get_file"].format(
        token=api_base["token"],
        api_url=api_base["api_url"],
        project_id=api_base["project_id"],
        file_path=CADENCE_CATALOG_FILE_PATH,
        branch=ref or api_base["branch"],
    )
    response = run_on_host(host, cmd)
    if response.rc != 0:
        result["error"] = (
            "Failed to read cadence catalog from GitLab: "
            f"rc={response.rc}"
        )
        return result

    try:
        file_data = json.loads(response.stdout.strip())
        content = base64.b64decode(file_data.get("content", "")).decode(
            "utf-8"
        )
        catalog_data = json.loads(content)
        section = catalog_data.get("catalog") or catalog_data.get("Catalog")
        if not isinstance(section, dict):
            raise ValueError("catalog section is missing")
        identifier = str(
            section.get("identifier") or section.get("Identifier") or ""
        ).strip()
        version = str(
            section.get("version") or section.get("Version") or ""
        ).strip()
        if not identifier or not version:
            raise ValueError("catalog identifier or version is missing")
    except (
        ValueError,
        TypeError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        result["error"] = f"Invalid cadence catalog: {exc}"
        return result

    result.update({
        "success": True,
        "catalog": catalog_data,
        "identifier": identifier,
        "version": version,
        "composite_image_group_id": f"{identifier}-v{version}",
        "last_commit_id": str(file_data.get("last_commit_id", "")),
    })
    return result


def check_cadence_runtime(host) -> Dict[str, Any]:
    """Validate the deployed prerequisites for a deterministic cadence FVT.

    Cadence product settings remain in ``build_stream_config.yml``.  The FVT
    reads that deployed configuration instead of duplicating it in
    ``test_config.yml``. Every successful repository reconciliation triggers
    the cadence pipeline, regardless of package add/remove counts.
    """
    result = {
        "success": False,
        "config_path": "",
        "error": "",
    }
    config_path = (
        f"{resolve_build_stream_input_path(host)}/{BUILD_STREAM_CONFIG_FILE}"
    )
    result["config_path"] = config_path
    try:
        config = read_remote_yaml(host, config_path)
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        result["error"] = f"Unable to read {config_path}: {exc}"
        return result
    if not isinstance(config, dict):
        result["error"] = f"{config_path} must contain a YAML mapping"
        return result

    cadence = config.get("cadence")
    if not isinstance(cadence, dict):
        result["error"] = f"cadence mapping is missing from {config_path}"
        return result

    errors = []
    if cadence.get("enabled") is not True:
        errors.append("cadence.enabled must be true")
    if cadence.get("catalog_filename") != CADENCE_CATALOG_FILE_PATH:
        errors.append(
            "cadence.catalog_filename must be "
            f"{CADENCE_CATALOG_FILE_PATH}"
        )
    if cadence.get("playbook_name") != "repo_sync.yml":
        errors.append("cadence.playbook_name must be repo_sync.yml")

    if errors:
        result["error"] = "; ".join(errors)
        return result

    prerequisites = (
        (
            "playbook-watcher service",
            "systemctl is-active --quiet playbook-watcher.service",
        ),
        (
            "BuildStream API service",
            "systemctl is-active --quiet omnia_build_stream.service",
        ),
        ("Pulp service", "systemctl is-active --quiet pulp.service"),
    )
    failed = []
    for name, command in prerequisites:
        command_result = run_on_host(host, command)
        if command_result.rc != 0:
            failed.append(name)

    omnia_data_path = resolve_omnia_data_path(host)
    playbook_paths = f"{omnia_data_path}/build_stream/playbook_paths.conf"
    try:
        registry = read_remote_yaml(host, playbook_paths)
        registered = (
            registry.get("playbook_paths", {})
            if isinstance(registry, dict)
            else {}
        )
    except (OSError, RuntimeError, TypeError, ValueError):
        registered = {}
    if "repo_sync.yml" not in registered:
        failed.append(f"repo_sync.yml registration in {playbook_paths}")

    if failed:
        result["error"] = "Missing cadence prerequisites: " + ", ".join(failed)
        return result

    result["success"] = True
    return result


def trigger_cadence_cycle(host) -> Dict[str, Any]:
    """Signal the watcher to execute one cadence cycle immediately."""
    result = {"success": False, "error": ""}
    command = (
        "systemctl kill --kill-who=main --signal=SIGUSR1 "
        "playbook-watcher.service"
    )
    triggered = run_on_host(host, command)
    if triggered.rc != 0:
        result["error"] = (
            "Unable to trigger a cadence cycle through playbook-watcher: "
            f"rc={triggered.rc}"
        )
        return result
    result["success"] = True
    return result


def wait_for_cadence_catalog_update(
    host,
    previous_commit: str,
    previous_version: str,
    timeout: int = STAGE_POLL_TIMEOUT,
    log_callback: Optional[Callable] = None,
) -> Dict[str, Any]:
    """Wait until the watcher pushes a new cadence catalog version."""
    deadline = time.time() + timeout
    attempts = 0
    last_error = ""
    while time.time() < deadline:
        attempts += 1
        catalog = get_cadence_catalog(host)
        if catalog["success"]:
            if (
                catalog["last_commit_id"] != previous_commit
                and catalog["version"] != previous_version
            ):
                catalog["attempts"] = attempts
                return catalog
            last_error = (
                "catalog is unchanged at version "
                f"{catalog['version']}"
            )
        else:
            last_error = catalog["error"]
        if log_callback and (attempts == 1 or attempts % 5 == 0):
            log_callback(
                f"Waiting for cadence watcher catalog update "
                f"({attempts} polls): {last_error}"
            )
        time.sleep(STAGE_POLL_INTERVAL)

    return {
        "success": False,
        "error": (
            "Timed out waiting for cadence watcher to update "
            f"{CADENCE_CATALOG_FILE_PATH}: {last_error}"
        ),
    }


# =============================================================================
# PIPELINE TRIGGER FUNCTIONS
# =============================================================================

def trigger_build_pipeline_auto(  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    host, log_callback: Optional[Callable] = None,
    initial_pipeline_id: int = 0,
    initial_job_id: Optional[str] = None,
    job_wait_timeout: int = JOB_WAIT_TIMEOUT,
) -> Dict[str, Any]:
    """Wait for the build pipeline triggered by the prior catalog push.

    The catalog is already uploaded by ``push_catalog_from_examples()``
    in test_playbook.py step 2, which triggers the GitLab pipeline.
    This function detects that pipeline (running, pending, or already
    finished) and waits for the corresponding BSM job.

    If ``initial_pipeline_id`` is provided (the latest pipeline ID
    *before* the catalog push), the function waits for a pipeline with
    a higher ID.  If not provided, the function adopts the most recent
    pipeline.

    Set ``allow_pipeline_cancel: true`` in ``test_config.yml`` to cancel
    existing pipelines and re-trigger via a fresh catalog upload.

    Args:
        host: Testinfra host connection.
        log_callback: Optional logging callback.
        initial_pipeline_id: Pipeline ID recorded before the catalog
            push (0 = adopt the latest pipeline).
        initial_job_id: Latest BSM job ID recorded before the catalog
        job_wait_timeout: Maximum seconds to wait for the corresponding
            BSM job. Defaults to the standard build-pipeline timeout.
            push. The first different job is the job created by this run.

    Returns:
        Dict with keys: success, pipeline_id, job_id, details, error.
    """
    result = {
        "success": False, "pipeline_id": 0, "job_id": "",
        "details": "", "error": "",
    }

    def _log(msg):
        if log_callback:
            log_callback(msg)
        else:
            print(f"    | {msg}", flush=True)
        sys.stdout.flush()

    _log("Checking for pipelines...")
    pipelines = list_pipelines(host, per_page=10)
    if not pipelines["success"]:
        result["error"] = f"Failed to list pipelines: {pipelines['error']}"
        return result

    all_pipelines = pipelines.get("pipelines", [])
    if not all_pipelines:
        _log("Waiting for the catalog upload to create a pipeline...")
        wait = wait_for_pipeline_triggered(
            host, initial_pipeline_id, log_callback=_log,
        )
        if not wait["success"]:
            result["error"] = wait["error"]
            return result
        all_pipelines = [{
            "id": wait["pipeline_id"],
            "status": wait["status"],
        }]

    # Consider only pipelines created after this execution's catalog upload.
    # Without this filter, an unrelated pipeline that was already running can
    # be adopted and its job_id can be mistaken for the new build job.
    candidate_pipelines = [
        pipeline for pipeline in all_pipelines
        if (
            not initial_pipeline_id
            or pipeline.get("id", 0) > initial_pipeline_id
        )
    ]

    # Separate running from completed pipelines
    running = [
        p for p in candidate_pipelines
        if p.get("status") in (
            "running", "pending", "created", "waiting_for_resource",
        )
    ]

    config = load_test_config()

    # If allow_pipeline_cancel is true and pipelines are running,
    # cancel them and re-trigger with a fresh catalog upload
    if running and config.get("allow_pipeline_cancel", False):
        for p in running:
            _log(f"  Canceling pipeline #{p['id']}...")
            cancel_pipeline(host, p["id"])
        time.sleep(5)
        # Re-upload catalog to trigger a fresh pipeline
        _log("Re-uploading catalog to trigger fresh pipeline...")
        catalog = get_catalog_content(host)
        if catalog["success"]:
            upload = upload_catalog_file(host, catalog["content"])
            if upload["success"]:
                _log("Catalog re-uploaded")
        # Wait for the new pipeline
        latest_id = all_pipelines[0].get("id", 0)
        _log("Waiting for new pipeline to trigger...")
        wait = wait_for_pipeline_triggered(
            host, latest_id, log_callback=_log,
        )
        if not wait["success"]:
            result["error"] = wait["error"]
            return result
        result["pipeline_id"] = wait["pipeline_id"]
        _log(f"Pipeline #{wait['pipeline_id']} triggered ({wait['status']})")
    elif running:
        # Adopt the most recent running pipeline
        adopted = running[0]
        result["pipeline_id"] = adopted["id"]
        _log(
            f"  Pipeline #{adopted['id']} already "
            f"{adopted.get('status', 'running')} — adopting it"
        )
    elif initial_pipeline_id > 0:
        # Catalog was already pushed — find the pipeline it triggered
        # (may already be finished/failed)
        new_pipelines = [
            p for p in all_pipelines
            if p.get("id", 0) > initial_pipeline_id
        ]
        if new_pipelines:
            # Use the most recent one triggered after our push
            target = new_pipelines[0]
            result["pipeline_id"] = target["id"]
            _log(
                f"  Pipeline #{target['id']} "
                f"({target.get('status', 'unknown')}) triggered by "
                f"catalog push — adopting it"
            )
        else:
            # No new pipeline yet — wait for it
            _log("Waiting for pipeline to trigger...")
            wait = wait_for_pipeline_triggered(
                host, initial_pipeline_id, log_callback=_log,
            )
            if not wait["success"]:
                result["error"] = wait["error"]
                return result
            result["pipeline_id"] = wait["pipeline_id"]
            _log(
                f"Pipeline #{wait['pipeline_id']} triggered "
                f"({wait['status']})"
            )
    else:
        # No initial_pipeline_id — adopt the most recent pipeline
        latest = all_pipelines[0]
        result["pipeline_id"] = latest["id"]
        _log(
            f"  Using latest pipeline #{latest['id']} "
            f"({latest.get('status', 'unknown')})"
        )

    # Wait for BSM job in database
    _log("Waiting for BSM job in database...")
    if initial_job_id is None:
        old_job = get_latest_job(host)
        old_job_id = old_job.get("job_id", "") if old_job["success"] else ""
    else:
        old_job_id = initial_job_id
    job_id = _wait_for_new_job(
        host, old_job_id, timeout=job_wait_timeout, log_callback=_log,
    )
    if not job_id:
        result["error"] = "No new BSM job was created by the triggered pipeline"
        return result
    result["job_id"] = job_id

    result["success"] = True
    result["details"] = f"Pipeline {result['pipeline_id']} adopted"
    return result


def _wait_for_new_job(
    host, old_job_id: str,
    timeout: int = JOB_WAIT_TIMEOUT,
    log_callback: Optional[Callable] = None,
) -> str:
    """Wait for a new job to appear in the database.

    Args:
        host: Testinfra host connection.
        old_job_id: Previous latest job ID.
        timeout: Max seconds to wait.
        log_callback: Optional logging callback.

    Returns:
        New job ID string, or empty string if not found.
    """
    def _log(msg):
        if log_callback:
            log_callback(msg)

    start = time.time()
    while time.time() - start < timeout:
        elapsed = int(time.time() - start)
        job = get_latest_job(host)
        if job["success"] and job["job_id"] and job["job_id"] != old_job_id:
            _log(f"Job created: {job['job_id'][:8]}... ({job['job_state']})")
            return job["job_id"]
        _log(f"[{elapsed}s] Waiting for new job...")
        time.sleep(10)
    _log("Warning: No new job found within timeout")
    return ""


def wait_for_new_job(
    host, old_job_id: str, timeout: int = JOB_WAIT_TIMEOUT,
    log_callback: Optional[Callable] = None,
) -> Dict[str, Any]:
    """Wait for and return the BSM job created by a manual trigger."""
    job_id = _wait_for_new_job(
        host, old_job_id, timeout=timeout, log_callback=log_callback,
    )
    return {
        "success": bool(job_id),
        "job_id": job_id,
        "error": "No new BSM job was created by the triggered pipeline" if not job_id else "",
    }


# =============================================================================
# DATABASE QUERY FUNCTIONS
# =============================================================================

def get_latest_job(host) -> Dict[str, Any]:
    """Get the latest job from the database.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, job_id, job_state, created_at, error.
    """
    result = {
        "success": False, "job_id": "", "job_state": "",
        "created_at": "", "error": "",
    }
    sql = (
        "SELECT job_id, job_state, created_at "
        "FROM jobs ORDER BY created_at DESC LIMIT 1"
    )
    query = _exec_psql(host, sql)
    if not query["success"]:
        result["error"] = query["error"]
        return result

    if not query["rows"]:
        result["error"] = "No jobs found in database"
        return result

    parts = query["rows"][0].split("|")
    if len(parts) >= 3:
        result["job_id"] = parts[0].strip()
        result["job_state"] = parts[1].strip()
        result["created_at"] = parts[2].strip()
        result["success"] = True
    return result


def get_stage_state(host, job_id: str, stage_name: str) -> Dict[str, Any]:
    """Get the state of a specific stage for a job.

    Args:
        host: Testinfra host connection.
        job_id: UUID of the job.
        stage_name: Name of the stage.

    Returns:
        Dict with keys: success, stage_name, stage_state, error_code, error.
    """
    result = {
        "success": False, "stage_name": stage_name,
        "stage_state": "", "error_code": "", "error": "",
    }
    sql = (
        f"SELECT stage_state, error_code FROM job_stages "
        f"WHERE job_id = '{job_id}' AND stage_name = '{stage_name}' "
        f"ORDER BY started_at DESC LIMIT 1"
    )
    query = _exec_psql(host, sql)
    if not query["success"]:
        result["error"] = query["error"]
        return result

    if not query["rows"]:
        result["error"] = f"Stage '{stage_name}' not found for job {job_id}"
        return result

    parts = query["rows"][0].split("|")
    if len(parts) >= 2:
        result["stage_state"] = parts[0].strip()
        result["error_code"] = parts[1].strip()
        result["success"] = True
    return result


def verify_stage_completed(
    host, job_id: str, stage_name: str,
) -> Dict[str, Any]:
    """Verify that a specific stage completed successfully.

    Args:
        host: Testinfra host connection.
        job_id: UUID of the job.
        stage_name: Name of the stage.

    Returns:
        Dict with keys: success, stage_name, stage_state, details, error.
    """
    result = {
        "success": False, "stage_name": stage_name,
        "stage_state": "", "details": "", "error": "",
    }
    stage = get_stage_state(host, job_id, stage_name)
    if not stage["success"]:
        result["error"] = stage["error"]
        return result

    result["stage_state"] = stage["stage_state"]
    if stage["stage_state"] == STAGE_STATE_COMPLETED:
        result["success"] = True
        result["details"] = f"Stage '{stage_name}' completed"
    else:
        result["error"] = (
            f"Stage '{stage_name}' is '{stage['stage_state']}' "
            f"(expected '{STAGE_STATE_COMPLETED}')"
        )
        if stage["error_code"]:
            result["error"] += f" - Error: {stage['error_code']}"
    return result


def get_image_groups_for_job(host, job_id: str) -> Dict[str, Any]:
    """Get all image groups for a job.

    Args:
        host: Testinfra host connection.
        job_id: UUID of the job.

    Returns:
        Dict with keys: success, image_groups (list), error.
    """
    result = {"success": False, "image_groups": [], "error": ""}
    sql = (
        f"SELECT id, status, created_at "
        f"FROM image_groups WHERE job_id = '{job_id}'"
    )
    query = _exec_psql(host, sql)
    if not query["success"]:
        result["error"] = query["error"]
        return result

    groups = []
    for row in query["rows"]:
        parts = row.split("|")
        if len(parts) >= 3:
            groups.append({
                "id": parts[0].strip(),
                "status": parts[1].strip(),
                "created_at": parts[2].strip(),
            })
    result["image_groups"] = groups
    result["success"] = True
    return result


def get_catalog_identity_for_job(host, job_id: str) -> Dict[str, Any]:
    """Return job and image-group catalog identities from PostgreSQL."""
    result = {
        "success": False,
        "job_composite_id": "",
        "job_catalog_identifier": "",
        "job_catalog_version": "",
        "image_group_id": "",
        "group_catalog_identifier": "",
        "group_catalog_version": "",
        "error": "",
    }
    if not re.fullmatch(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
        r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
        str(job_id),
    ):
        result["error"] = "job_id must be a valid UUID"
        return result

    sql = (
        "SELECT COALESCE(j.composite_image_group_id, ''), "
        "COALESCE(j.catalog_identifier, ''), "
        "COALESCE(j.catalog_version, ''), ig.id, "
        "COALESCE(ig.catalog_identifier, ''), "
        "COALESCE(ig.catalog_version, '') "
        "FROM jobs j JOIN image_groups ig ON ig.job_id = j.job_id "
        f"WHERE j.job_id = '{job_id}'"
    )
    query = _exec_psql(host, sql)
    if not query["success"]:
        result["error"] = query["error"]
        return result
    if len(query["rows"]) != 1:
        result["error"] = (
            f"Expected one catalog identity for job {job_id}, "
            f"found {len(query['rows'])}"
        )
        return result

    parts = query["rows"][0].split("|")
    if len(parts) != 6:
        result["error"] = "Catalog identity query returned an invalid row"
        return result
    result.update({
        "success": True,
        "job_composite_id": parts[0].strip(),
        "job_catalog_identifier": parts[1].strip(),
        "job_catalog_version": parts[2].strip(),
        "image_group_id": parts[3].strip(),
        "group_catalog_identifier": parts[4].strip(),
        "group_catalog_version": parts[5].strip(),
    })
    return result


def resolve_deploy_image_group(
    host, job_id: str, require_built: bool = False,
) -> Dict[str, Any]:
    """Resolve one, and only one, image group mapped to ``job_id``."""
    result = {
        "success": False, "job_id": job_id,
        "image_group_id": "", "status": "", "error": "",
    }
    if not re.fullmatch(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
        r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
        str(job_id),
    ):
        result["error"] = "job_id must be a valid UUID"
        return result

    groups_result = get_image_groups_for_job(host, job_id)
    if not groups_result["success"]:
        result["error"] = groups_result["error"]
        return result

    groups = groups_result["image_groups"]
    if not groups:
        result["error"] = f"No image group is mapped to job_id {job_id}"
        return result
    if len(groups) != 1:
        result["error"] = (
            f"Expected one image group for job_id {job_id}, found {len(groups)}"
        )
        return result

    group = groups[0]
    if require_built and group["status"] != IMAGE_GROUP_STATUS_BUILT:
        result["error"] = (
            f"Image group {group['id']} is {group['status']}; "
            f"expected {IMAGE_GROUP_STATUS_BUILT} before deploy"
        )
        return result

    result.update({
        "success": True,
        "image_group_id": group["id"],
        "status": group["status"],
    })
    return result


def wait_for_child_pipeline(
    host, parent_pipeline_id: int, timeout: int = PIPELINE_POLL_TIMEOUT,
) -> Dict[str, Any]:
    """Wait for GitLab to create the dynamic deploy child pipeline."""
    started = time.time()
    last_error = ""
    while time.time() - started < timeout:
        child = get_child_pipeline_id(host, parent_pipeline_id)
        if child["success"]:
            return child
        last_error = child["error"]
        time.sleep(PIPELINE_POLL_INTERVAL)
    return {
        "success": False, "child_pipeline_id": 0,
        "error": last_error or "Timed out waiting for deploy child pipeline",
    }


def play_gitlab_job(host, job_id: int) -> Dict[str, Any]:
    """Play one manual GitLab CI job by numeric job ID."""
    result = {"success": False, "job": {}, "error": ""}
    api_base = _get_gitlab_api_base(host)
    if not api_base["success"]:
        result["error"] = api_base["error"]
        return result
    cmd = CMDS["gitlab_api_play_job"].format(
        token=api_base["token"], api_url=api_base["api_url"],
        project_id=api_base["project_id"], job_id=int(job_id),
    )
    response = run_on_host(host, cmd)
    if response.rc != 0:
        result["error"] = f"Unable to play GitLab job {job_id} (rc={response.rc})"
        return result
    try:
        job = json.loads(response.stdout.strip())
    except json.JSONDecodeError as exc:
        result["error"] = f"Invalid play-job response: {exc}"
        return result
    if not job.get("id") or job.get("status") == "failed":
        result["error"] = str(job.get("message", job))
        return result
    result.update({"success": True, "job": job})
    return result


def wait_for_pipeline_job(
    host, pipeline_id: int, job_name: str,
    wanted_statuses: Optional[List[str]] = None,
    timeout: int = STAGE_POLL_TIMEOUT,
) -> Dict[str, Any]:
    """Wait for a named child-pipeline job to appear and reach a status."""
    wanted = set(wanted_statuses or ["manual"])
    started = time.time()
    while time.time() - started < timeout:
        jobs_result = get_gitlab_pipeline_jobs(host, pipeline_id)
        if jobs_result["success"]:
            matches = [
                job for job in jobs_result["jobs"]
                if job["name"] == job_name
            ]
            if len(matches) > 1:
                return {
                    "success": False, "job": {},
                    "error": f"Multiple GitLab jobs named {job_name!r}",
                }
            if matches:
                job = matches[0]
                if job["status"] in wanted:
                    return {"success": True, "job": job, "error": ""}
                if job["status"] in {"failed", "canceled"}:
                    return {
                        "success": False, "job": job,
                        "error": f"GitLab job {job_name} is {job['status']}",
                    }
        time.sleep(PIPELINE_POLL_INTERVAL)
    return {
        "success": False, "job": {},
        "error": f"Timed out waiting for GitLab job {job_name}",
    }


def run_deploy_child_pipeline(  # pylint: disable=too-many-return-statements
    host, child_pipeline_id: int, image_group_id: str,
    log_callback: Optional[Callable] = None,
) -> Dict[str, Any]:
    """Select the mapped image, play deploy, and await all deploy jobs."""
    result = {
        "success": False, "jobs": {}, "summary_job_id": 0, "error": "",
    }

    def _log(message: str) -> None:
        if log_callback:
            log_callback(message)

    selection = wait_for_pipeline_job(
        host, child_pipeline_id, image_group_id, ["manual"],
        timeout=PIPELINE_POLL_TIMEOUT,
    )
    if not selection["success"]:
        result["error"] = selection["error"]
        return result
    _log(f"Selecting image group {image_group_id}")
    played = play_gitlab_job(host, selection["job"]["id"])
    if not played["success"]:
        result["error"] = played["error"]
        return result
    selected = wait_for_pipeline_job(
        host, child_pipeline_id, image_group_id, ["success"],
    )
    if not selected["success"]:
        result["error"] = selected["error"]
        return result
    result["jobs"]["select_image"] = selected["job"]

    deploy = wait_for_pipeline_job(
        host, child_pipeline_id, "deploy", ["manual"],
        timeout=PIPELINE_POLL_TIMEOUT,
    )
    if not deploy["success"]:
        result["error"] = deploy["error"]
        return result
    _log("Starting manual deploy job")
    played = play_gitlab_job(host, deploy["job"]["id"])
    if not played["success"]:
        result["error"] = played["error"]
        return result

    for job_name in ("deploy", "restart", "validate", "summary"):
        _log(f"Waiting for {job_name} job")
        completed = wait_for_pipeline_job(
            host, child_pipeline_id, job_name, ["success"],
        )
        if not completed["success"]:
            result["error"] = completed["error"]
            return result
        result["jobs"][job_name] = completed["job"]

    result["summary_job_id"] = result["jobs"]["summary"]["id"]
    result["success"] = True
    return result


def discover_cleanup_pipeline(  # pylint: disable=too-many-locals
    host, job_id: str, image_group_id: str,
) -> Dict[str, Any]:
    """Find a completed cleanup child pipeline for a job/image group pair."""
    result = {
        "success": False, "parent_pipeline_id": 0,
        "child_pipeline_id": 0, "summary_job_id": 0, "error": "",
    }
    pipelines = list_pipelines(host, per_page=100)
    if not pipelines["success"]:
        result["error"] = pipelines["error"]
        return result

    for root in pipelines["pipelines"]:
        root_id = int(root.get("id", 0) or 0)
        if not root_id:
            continue
        candidates = []
        first = get_child_pipeline_id(host, root_id)
        if first["success"]:
            first_id = first["child_pipeline_id"]
            candidates.append(first_id)
            second = get_child_pipeline_id(host, first_id)
            if second["success"]:
                candidates.append(second["child_pipeline_id"])

        for candidate_id in reversed(candidates):
            jobs_result = get_gitlab_pipeline_jobs(host, candidate_id)
            if not jobs_result["success"]:
                continue
            jobs = jobs_result["jobs"]
            selected = [
                job for job in jobs
                if job["name"] == image_group_id
                and job["status"] == "success"
            ]
            summaries = [job for job in jobs if job["name"] == "summary"]
            if len(selected) != 1 or len(summaries) != 1:
                continue
            trace = get_gitlab_job_trace(host, selected[0]["id"])
            if not trace["success"] or job_id not in trace["trace"]:
                continue
            result.update({
                "success": True,
                "parent_pipeline_id": root_id,
                "child_pipeline_id": candidate_id,
                "summary_job_id": summaries[0]["id"],
            })
            return result

    result["error"] = (
        "No recent GitLab cleanup pipeline selected image group "
        f"{image_group_id} for job_id {job_id}"
    )
    return result


def get_gitlab_job_trace(host, job_id: int) -> Dict[str, Any]:
    """Return the text trace for a GitLab CI job."""
    result = {"success": False, "trace": "", "error": ""}
    api_base = _get_gitlab_api_base(host)
    if not api_base["success"]:
        result["error"] = api_base["error"]
        return result
    cmd = CMDS["gitlab_api_job_trace"].format(
        token=api_base["token"], api_url=api_base["api_url"],
        project_id=api_base["project_id"], job_id=int(job_id),
    )
    response = run_on_host(host, cmd)
    if response.rc != 0:
        result["error"] = f"Unable to read GitLab job trace (rc={response.rc})"
        return result
    result.update({"success": True, "trace": response.stdout or ""})
    return result


def discover_cadence_pipeline(
    host, job_id: str, image_group_id: str,
) -> Dict[str, Any]:
    """Find the cadence child pipeline that created ``job_id``."""
    result = {
        "success": False,
        "parent_pipeline_id": 0,
        "child_pipeline_id": 0,
        "summary_job_id": 0,
        "pipeline_sha": "",
        "jobs": {},
        "error": "",
    }
    pipelines = list_pipelines(host, per_page=100)
    if not pipelines["success"]:
        result["error"] = pipelines["error"]
        return result

    expected = set(GITLAB_CI_CADENCE_JOBS)
    for root in pipelines["pipelines"]:
        root_id = int(root.get("id", 0) or 0)
        if not root_id:
            continue
        child = get_child_pipeline_id(host, root_id)
        if not child["success"]:
            continue
        child_id = child["child_pipeline_id"]
        jobs_result = get_gitlab_pipeline_jobs(host, child_id)
        if not jobs_result["success"]:
            continue
        jobs = {job["name"]: job for job in jobs_result["jobs"]}
        if not expected.issubset(jobs):
            continue

        initialization_trace = get_gitlab_job_trace(
            host, jobs["initialization"]["id"]
        )
        parse_trace = get_gitlab_job_trace(
            host, jobs["parse-catalog"]["id"]
        )
        if (
            not initialization_trace["success"]
            or job_id not in initialization_trace["trace"]
            or not parse_trace["success"]
            or image_group_id not in parse_trace["trace"]
        ):
            continue

        result.update({
            "success": True,
            "parent_pipeline_id": root_id,
            "child_pipeline_id": child_id,
            "summary_job_id": jobs["summary"]["id"],
            "pipeline_sha": str(root.get("sha", "")),
            "jobs": jobs,
        })
        return result

    result["error"] = (
        "No recent cadence pipeline contains job_id "
        f"{job_id} and image group {image_group_id}"
    )
    return result


def discover_deploy_pipeline(  # pylint: disable=too-many-locals
    host, job_id: str, image_group_id: str,
) -> Dict[str, Any]:
    """Discover the latest dynamic deploy child selected for ``job_id``.

    Root pipelines are followed through at most two downstream bridge levels:
    the deploy controller and its generated dynamic child.  A child is a match
    only when its successful image-selection job is named ``image_group_id``
    and its trace contains the configured ``job_id``.
    """
    result = {
        "success": False,
        "parent_pipeline_id": 0,
        "child_pipeline_id": 0,
        "summary_job_id": 0,
        "error": "",
    }
    pipelines = list_pipelines(host, per_page=100)
    if not pipelines["success"]:
        result["error"] = pipelines["error"]
        return result

    for root in pipelines["pipelines"]:
        root_id = int(root.get("id", 0) or 0)
        if not root_id:
            continue
        candidates = []
        first_child = get_child_pipeline_id(host, root_id)
        if first_child["success"]:
            first_id = first_child["child_pipeline_id"]
            candidates.append(first_id)
            second_child = get_child_pipeline_id(host, first_id)
            if second_child["success"]:
                candidates.append(second_child["child_pipeline_id"])

        for candidate_id in reversed(candidates):
            jobs_result = get_gitlab_pipeline_jobs(host, candidate_id)
            if not jobs_result["success"]:
                continue
            selected = [
                job for job in jobs_result["jobs"]
                if job["name"] == image_group_id
                and job["status"] == "success"
            ]
            summary = [
                job for job in jobs_result["jobs"]
                if job["name"] == "summary"
            ]
            if len(selected) != 1 or len(summary) != 1:
                continue
            trace = get_gitlab_job_trace(host, selected[0]["id"])
            if not trace["success"] or job_id not in trace["trace"]:
                continue
            result.update({
                "success": True,
                "parent_pipeline_id": root_id,
                "child_pipeline_id": candidate_id,
                "summary_job_id": summary[0]["id"],
            })
            return result

    result["error"] = (
        "No recent GitLab deploy pipeline selected image group "
        f"{image_group_id} for job_id {job_id}"
    )
    return result


def get_bsm_job_details(host, job_id: str) -> Dict[str, Any]:
    """Fetch a job from the authenticated BuildStream API."""
    result = {"success": False, "job": {}, "error": ""}
    token = _get_bsm_access_token(host)
    config = _get_gitlab_config(host)
    host_ip = config.get(BSM_HOST_IP_KEY, "")
    port = config.get(BSM_PORT_KEY, "")
    if not token or not host_ip or not port:
        result["error"] = "BuildStream API credentials or endpoint unavailable"
        return result
    cmd = CMDS["bsm_api_get_job"].format(
        token=token, host=host_ip, port=port, job_id=job_id,
    )
    response = run_on_host(host, cmd)
    if response.rc != 0:
        result["error"] = f"Unable to fetch job (rc={response.rc})"
        return result
    try:
        job = json.loads(response.stdout.strip())
    except json.JSONDecodeError as exc:
        result["error"] = f"Invalid BuildStream job response: {exc}"
        return result
    if not isinstance(job, dict) or job.get("detail"):
        result["error"] = str(job.get("detail", "Job response is not an object"))
        return result
    result.update({"success": True, "job": job})
    return result


def get_bsm_artifact_json(  # pylint: disable=too-many-locals,too-many-return-statements
    host, job_id: str, label: str,
) -> Dict[str, Any]:
    """Download a JSON artifact; a 404 is returned as an optional absence."""
    result = {
        "success": False, "exists": False, "data": None,
        "http_code": 0, "error": "",
    }
    if label not in {"node-results", "failed-nodes"}:
        result["error"] = f"Unsupported artifact label: {label}"
        return result
    token = _get_bsm_access_token(host)
    config = _get_gitlab_config(host)
    host_ip = config.get(BSM_HOST_IP_KEY, "")
    port = config.get(BSM_PORT_KEY, "")
    if not token or not host_ip or not port:
        result["error"] = "BuildStream API credentials or endpoint unavailable"
        return result
    cmd = CMDS["bsm_api_get_artifact"].format(
        token=token, host=host_ip, port=port,
        job_id=job_id, label=label,
    )
    response = run_on_host(host, cmd)
    if response.rc != 0:
        result["error"] = f"Artifact request failed (rc={response.rc})"
        return result
    body, separator, code_text = (response.stdout or "").rpartition("\n")
    if not separator or not code_text.isdigit():
        result["error"] = "Artifact response did not include an HTTP status"
        return result
    code = int(code_text)
    result["http_code"] = code
    if code == 200:
        try:
            data = json.loads(body)
        except json.JSONDecodeError as exc:
            result["error"] = f"Artifact is not valid JSON: {exc}"
            return result
        result.update({
            "success": True, "exists": True, "data": data,
            "source": "api",
        })
        return result

    filenames = {
        "node-results": "node_results.json",
        "failed-nodes": "failed_nodes.json",
    }
    artifact_path = (
        f"{resolve_omnia_data_path(host)}/build_stream_root/artifacts/"
        f"{job_id}/{filenames[label]}"
    )
    file_response = run_on_host(
        host, CMDS["cat_file"].format(path=artifact_path),
    )
    if file_response.rc == 0 and file_response.stdout.strip():
        try:
            data = json.loads(file_response.stdout)
        except json.JSONDecodeError as exc:
            result["error"] = f"Stored artifact is not valid JSON: {exc}"
            return result
        result.update({
            "success": True,
            "exists": True,
            "data": data,
            "source": "filesystem-fallback",
            "api_error": f"Artifact API returned HTTP {code}",
        })
        return result

    if code == 404:
        result.update({"success": True, "source": "absent"})
        return result
    result["error"] = (
        f"Artifact API returned HTTP {code} and {artifact_path} was unavailable"
    )
    return result


def get_images_for_job(host, job_id: str) -> Dict[str, Any]:
    """Get all images created for a job.

    Args:
        host: Testinfra host connection.
        job_id: UUID of the job.

    Returns:
        Dict with keys: success, images (list), error.
    """
    result = {"success": False, "images": [], "error": ""}
    sql = (
        f"SELECT i.id, i.role, i.image_name, ig.id as group_id "
        f"FROM images i JOIN image_groups ig ON i.image_group_id = ig.id "
        f"WHERE ig.job_id = '{job_id}'"
    )
    query = _exec_psql(host, sql)
    if not query["success"]:
        result["error"] = query["error"]
        return result

    images = []
    for row in query["rows"]:
        parts = row.split("|")
        if len(parts) >= 4:
            images.append({
                "id": parts[0].strip(),
                "role": parts[1].strip(),
                "image_name": parts[2].strip(),
                "group_id": parts[3].strip(),
            })
    result["images"] = images
    result["success"] = True
    return result


# =============================================================================
# STAGE MONITORING
# =============================================================================

def poll_stage_until_complete(
    host, job_id: str, stage_name: str,
    poll_interval: int = STAGE_POLL_INTERVAL,
    poll_timeout: int = STAGE_POLL_TIMEOUT,
    log_callback: Optional[Callable] = None,
) -> Dict[str, Any]:
    """Poll a stage until it completes or fails.

    Args:
        host: Testinfra host connection.
        job_id: UUID of the job.
        stage_name: Name of the stage to monitor.
        poll_interval: Seconds between polls.
        poll_timeout: Max seconds to wait.
        log_callback: Optional logging callback.

    Returns:
        Dict with keys: success, stage_state, elapsed, error.
    """
    result = {
        "success": False, "stage_state": "",
        "elapsed": 0, "error": "",
    }

    def _log(msg):
        if log_callback:
            log_callback(msg)

    _log(
        f"Polling stage '{stage_name}' "
        f"(interval: {poll_interval}s, timeout: {poll_timeout // 60} min)"
    )
    start = time.time()
    last_state = ""

    while time.time() - start < poll_timeout:
        elapsed = int(time.time() - start)
        stage = get_stage_state(host, job_id, stage_name)

        if not stage["success"]:
            _log(f"[{elapsed}s] Stage '{stage_name}' not yet created...")
            time.sleep(poll_interval)
            continue

        current_state = stage["stage_state"]
        if current_state != last_state:
            _log(f"[{elapsed}s] Stage '{stage_name}' -> {current_state}")
            last_state = current_state

        if current_state == STAGE_STATE_COMPLETED:
            result["success"] = True
            result["stage_state"] = current_state
            result["elapsed"] = elapsed
            _log(f"[{elapsed}s] Stage '{stage_name}' COMPLETED")
            return result

        if current_state == STAGE_STATE_FAILED:
            result["stage_state"] = current_state
            result["elapsed"] = elapsed
            result["error"] = (
                f"Stage '{stage_name}' FAILED"
                + (f" - {stage['error_code']}" if stage["error_code"] else "")
            )
            _log(f"[{elapsed}s] Stage '{stage_name}' FAILED")
            return result

        time.sleep(poll_interval)

    result["elapsed"] = int(time.time() - start)
    result["error"] = f"TIMEOUT - Stage '{stage_name}' did not complete"
    return result


# =============================================================================
# BSM API VERIFICATION
# =============================================================================

def verify_registry_images(
    host, job_id: str, roles: List[str],
) -> Dict[str, Any]:
    """Verify container images exist in registry for each role.

    Args:
        host: Testinfra host connection.
        job_id: UUID of the job.
        roles: List of role names.

    Returns:
        Dict with keys: success, found, missing, details, error.
    """
    result = {
        "success": False, "found": [], "missing": [],
        "details": "", "error": "",
    }

    hostname_cmd = run_on_host(host, CMDS["hostname_cmd"])
    if hostname_cmd.rc != 0:
        result["error"] = "Failed to get hostname"
        return result

    hostname = hostname_cmd.stdout.strip()
    registry_url = f"{hostname}:{REGISTRY_PORT}"

    regctl_cmd = run_on_host(
        host, CMDS["regctl_repo_ls"].format(registry_url=registry_url),
    )
    if regctl_cmd.rc != 0:
        result["error"] = f"regctl failed: rc={regctl_cmd.rc}"
        return result

    repos = [
        line.strip() for line in regctl_cmd.stdout.strip().split("\n")
        if line.strip()
    ]

    artifact_images = _get_build_status_images(host, job_id)
    if not artifact_images["success"]:
        result["error"] = artifact_images["error"]
        return result

    for role in roles:
        image = artifact_images["images"].get(role, {})
        rootfs_path = image.get("image", "")
        image_name = (
            PurePosixPath(rootfs_path).parts[-3]
            if len(PurePosixPath(rootfs_path).parts) >= 3
            else ""
        )
        matched = [
            repo for repo in repos
            if image_name
            and (repo == image_name or repo.endswith(f"/{image_name}"))
        ]
        if matched:
            result["found"].append(role)
        else:
            result["missing"].append(role)

    result["success"] = len(result["missing"]) == 0
    result["details"] = (
        f"Registry: {len(result['found'])}/{len(roles)} roles found"
    )
    return result


def verify_registry_images_absent(
    host, job_id: str, roles: List[str],
) -> Dict[str, Any]:
    """Verify that cleanup removed registry images owned by the job's group.

    A BuildStream job can reuse artifacts recorded in ``build_status.yml``.
    Those artifacts belong to an older image group and must not be deleted by
    cleanup of the current group, so absence is matched using the current
    image-group ID rather than the shared build-status paths.
    """
    result = {
        "success": False, "found": [], "missing": [],
        "details": "", "error": "",
    }
    hostname_cmd = run_on_host(host, CMDS["hostname_cmd"])
    if hostname_cmd.rc != 0:
        result["error"] = "Failed to get hostname"
        return result
    registry_url = f"{hostname_cmd.stdout.strip()}:{REGISTRY_PORT}"
    repos_cmd = run_on_host(
        host, CMDS["regctl_repo_ls"].format(registry_url=registry_url),
    )
    if repos_cmd.rc != 0:
        result["error"] = f"regctl failed: rc={repos_cmd.rc}"
        return result
    repos = [line.strip() for line in repos_cmd.stdout.splitlines() if line.strip()]
    groups = get_image_groups_for_job(host, job_id)
    if not groups["success"]:
        result["error"] = groups["error"]
        return result
    if len(groups["image_groups"]) != 1:
        result["error"] = (
            f"Expected one image group for job_id {job_id}, "
            f"found {len(groups['image_groups'])}"
        )
        return result
    image_group_id = groups["image_groups"][0]["id"]
    for role in roles:
        if any(
            image_group_id in repo and role in repo
            for repo in repos
        ):
            result["found"].append(role)
    result["missing"] = [role for role in roles if role not in result["found"]]
    result["success"] = not result["found"]
    result["details"] = (
        f"Registry: {len(result['missing'])}/{len(roles)} roles removed"
    )
    return result


def verify_s3_boot_images(
    host, job_id: str, roles: List[str],
) -> Dict[str, Any]:
    """Verify S3 boot images exist for each role.

    Args:
        host: Testinfra host connection.
        job_id: UUID of the job.
        roles: List of role names.

    Returns:
        Dict with keys: success, found_roles, missing_roles, details, error.
    """
    result = {
        "success": False, "found_roles": [], "missing_roles": [],
        "details": "", "error": "",
    }

    cmd = run_on_host(
        host, CMDS["s3cmd_ls_recursive"].format(bucket=S3_BOOT_IMAGES_BUCKET),
    )
    if cmd.rc != 0:
        result["error"] = f"s3cmd failed: rc={cmd.rc}"
        return result

    s3_paths = []
    for line in cmd.stdout.strip().split("\n"):
        parts = line.strip().split()
        if parts:
            path = parts[-1]
            if path.startswith("s3://"):
                s3_paths.append(path)

    artifact_images = _get_build_status_images(host, job_id)
    if not artifact_images["success"]:
        result["error"] = artifact_images["error"]
        return result

    for role in roles:
        image = artifact_images["images"].get(role, {})
        expected_paths = {
            f"s3://{image.get(key, '').lstrip('/')}"
            for key in ("image", "kernel", "initrd")
            if image.get(key)
        }
        if (
            len(expected_paths) == BOOT_IMAGE_ARTIFACTS_PER_ROLE
            and expected_paths.issubset(set(s3_paths))
        ):
            result["found_roles"].append(role)
        else:
            result["missing_roles"].append(role)

    result["success"] = len(result["missing_roles"]) == 0
    result["details"] = (
        f"S3: {len(result['found_roles'])}/{len(roles)} roles complete"
    )
    return result


def verify_s3_boot_images_absent(
    host, job_id: str, roles: List[str],
) -> Dict[str, Any]:
    """Verify that cleanup removed S3 objects owned by the job's group.

    Reused image paths can belong to an older image group and remain valid for
    that owner.  Match the cleanup target's image-group ID so shared artifacts
    are not reported as stale cleanup output.
    """
    result = {
        "success": False, "found_roles": [], "missing_roles": [],
        "details": "", "error": "",
    }
    cmd = run_on_host(
        host, CMDS["s3cmd_ls_recursive"].format(bucket=S3_BOOT_IMAGES_BUCKET),
    )
    if cmd.rc != 0:
        result["error"] = f"s3cmd failed: rc={cmd.rc}"
        return result
    paths = {
        line.strip().split()[-1]
        for line in cmd.stdout.splitlines()
        if line.strip()
    }
    groups = get_image_groups_for_job(host, job_id)
    if not groups["success"]:
        result["error"] = groups["error"]
        return result
    if len(groups["image_groups"]) != 1:
        result["error"] = (
            f"Expected one image group for job_id {job_id}, "
            f"found {len(groups['image_groups'])}"
        )
        return result
    image_group_id = groups["image_groups"][0]["id"]
    for role in roles:
        present = any(
            image_group_id in path and role in path
            for path in paths
        )
        if present:
            result["found_roles"].append(role)
        else:
            result["missing_roles"].append(role)
    result["success"] = not result["found_roles"]
    result["details"] = (
        f"S3: {len(result['missing_roles'])}/{len(roles)} roles removed"
    )
    return result


def _get_build_status_images(host, job_id: str) -> Dict[str, Any]:
    """Return exact artifact paths keyed by functional group.

    Image Build Manager can reuse an existing up-to-date image when
    ``force_rebuild`` is false.  In that case the artifact name contains the
    original build job ID, not the current BuildStream job ID.  The generated
    build_status.yml is the authoritative contract for both newly built and
    reused images.
    """
    result = {
        "success": False,
        "images": {},
        "image_group_id": "",
        "path": "",
        "latest_path": "",
        "data": {},
        "error": "",
    }
    image_group = resolve_deploy_image_group(host, job_id)
    if not image_group["success"]:
        result["error"] = image_group["error"]
        return result

    image_group_id = image_group["image_group_id"]
    result["image_group_id"] = image_group_id
    if (
        not image_group_id
        or "/" in image_group_id
        or image_group_id in {".", ".."}
    ):
        result["error"] = f"Unsafe image group ID: {image_group_id!r}"
        return result

    project_name = PurePosixPath(resolve_build_stream_input_path(host)).name
    status_path = (
        f"{resolve_omnia_data_path(host)}/image_build_manager/output/"
        f"{project_name}/{image_group_id}/build_status.yml"
    )
    result["path"] = status_path
    result["latest_path"] = (
        f"{resolve_omnia_data_path(host)}/image_build_manager/output/"
        f"{project_name}/build_status.yml"
    )
    try:
        status = read_remote_yaml(host, status_path)
    except (OSError, ValueError, TypeError) as exc:
        result["error"] = f"Unable to read {status_path}: {exc}"
        return result
    if not isinstance(status, dict):
        result["error"] = f"{status_path} must contain a YAML mapping"
        return result
    result["data"] = status

    for architecture in status.get("functional_group_images", []):
        if not isinstance(architecture, dict):
            continue
        for images in architecture.values():
            if not isinstance(images, list):
                continue
            for image in images:
                if isinstance(image, dict) and image.get("functional_group"):
                    result["images"][image["functional_group"]] = image

    if not result["images"]:
        result["error"] = (
            f"No functional-group artifacts found in {status_path}"
        )
        return result
    result["success"] = True
    return result


# =============================================================================
# INITIALIZATION STAGE VERIFICATION
# =============================================================================

def verify_initialization_health(host, job_id: str) -> Dict[str, Any]:
    """Verify initialization stage passed the BSM health check.

    Args:
        host: Testinfra host connection.
        job_id: UUID of the job.

    Returns:
        Dict with keys: success, details, error.
    """
    gitlab_config = _get_gitlab_config(host)
    host_ip = gitlab_config.get(BSM_HOST_IP_KEY, "")
    port = gitlab_config.get(BSM_PORT_KEY, "")
    if not host_ip or not port:
        return {
            "success": False, "details": "",
            "error": "BSM host_ip or port not configured",
        }

    cmd = CMDS["curl_health"].format(
        host=host_ip, port=port, path=BSM_HEALTH_PATH,
    )
    cmd_result = run_on_host(host, cmd)
    http_code = cmd_result.stdout.strip()
    if cmd_result.rc == 0 and http_code == "200":
        return {
            "success": True,
            "details": f"BSM API healthy (HTTP 200)",
            "error": "",
        }
    return {
        "success": False, "details": "",
        "error": f"BSM API unhealthy (HTTP {http_code})",
    }


def verify_initialization_auth(host) -> Dict[str, Any]:
    """Verify OAuth credentials are registered in GitLab CI/CD variables.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, details, error.
    """
    api_base = _get_gitlab_api_base(host)
    if not api_base["success"]:
        return {"success": False, "details": "", "error": api_base["error"]}

    vars_cmd = CMDS["gitlab_api_list_variables"].format(
        token=api_base["token"],
        api_url=api_base["api_url"],
        project_id=api_base["project_id"],
    )
    vars_result = run_on_host(host, vars_cmd)
    if vars_result.rc != 0:
        return {
            "success": False, "details": "",
            "error": "Failed to list CI/CD variables",
        }

    try:
        variables = json.loads(vars_result.stdout.strip())
        keys = [v["key"] for v in variables]
        has_id = "BSM_CLIENT_ID" in keys
        has_secret = "BSM_CLIENT_SECRET" in keys
        if has_id and has_secret:
            return {
                "success": True,
                "details": "BSM_CLIENT_ID and BSM_CLIENT_SECRET found",
                "error": "",
            }
        missing = []
        if not has_id:
            missing.append("BSM_CLIENT_ID")
        if not has_secret:
            missing.append("BSM_CLIENT_SECRET")
        return {
            "success": False, "details": "",
            "error": f"Missing CI/CD variables: {', '.join(missing)}",
        }
    except json.JSONDecodeError:
        return {
            "success": False, "details": "",
            "error": "Invalid JSON from CI/CD variables API",
        }


def verify_initialization_job(host, job_id: str) -> Dict[str, Any]:
    """Verify a BSM job was created with the given job_id.

    Args:
        host: Testinfra host connection.
        job_id: UUID of the job.

    Returns:
        Dict with keys: success, job_id, job_state, details, error.
    """
    result = {
        "success": False, "job_id": job_id,
        "job_state": "", "details": "", "error": "",
    }
    if not job_id:
        result["error"] = "No job_id provided (trigger may have failed)"
        return result

    sql = (
        f"SELECT job_state, created_at FROM jobs "
        f"WHERE job_id = '{job_id}'"
    )
    query = _exec_psql(host, sql)
    if not query["success"]:
        result["error"] = query["error"]
        return result

    if not query["rows"]:
        result["error"] = f"Job {job_id} not found in database"
        return result

    parts = query["rows"][0].split("|")
    if len(parts) >= 2:
        result["job_state"] = parts[0].strip()
        result["success"] = True
        result["details"] = (
            f"Job {job_id[:8]}... state: {parts[0].strip()}"
        )
    return result


def verify_initialization_upload(host, job_id: str) -> Dict[str, Any]:
    """Verify initialization stage uploaded config files.

    Args:
        host: Testinfra host connection.
        job_id: UUID of the job.

    Returns:
        Dict with keys: success, details, error.
    """
    gitlab_config = _get_gitlab_config(host)
    host_ip = gitlab_config.get(BSM_HOST_IP_KEY, "")
    port = gitlab_config.get(BSM_PORT_KEY, "")
    if not host_ip or not port:
        return {"success": False, "details": "", "error": "BSM not configured"}

    token = _get_bsm_access_token(host)
    if not token:
        return {"success": False, "details": "", "error": "No BSM token"}

    cmd = CMDS["bsm_api_get_job"].format(
        token=token, host=host_ip, port=port, job_id=job_id,
    )
    cmd_result = run_on_host(host, cmd)
    if cmd_result.rc != 0:
        return {
            "success": False, "details": "",
            "error": f"API call failed: rc={cmd_result.rc}",
        }

    try:
        data = json.loads(cmd_result.stdout.strip())
        if "job_id" in data:
            return {
                "success": True,
                "details": f"Job {job_id[:8]}... accessible via API",
                "error": "",
            }
        return {
            "success": False, "details": "",
            "error": f"Job not found in API: {data.get('detail', '')}",
        }
    except json.JSONDecodeError:
        return {
            "success": False, "details": "",
            "error": "Invalid JSON from BSM API",
        }


def verify_create_local_repository(host, job_id: str) -> Dict[str, Any]:
    """Verify create-local-repository stage completed in the database.

    Args:
        host: Testinfra host connection.
        job_id: UUID of the job.

    Returns:
        Dict with keys: success, stage_name, stage_state, details, error.
    """
    return verify_stage_completed(host, job_id, "create-local-repository")


def verify_build_image(host, job_id: str) -> Dict[str, Any]:
    """Verify build-image stage completed in the database.

    Args:
        host: Testinfra host connection.
        job_id: UUID of the job.

    Returns:
        Dict with keys: success, stage_name, stage_state, details, error.
    """
    return verify_stage_completed(host, job_id, "build-image")


def verify_build_image_meta(host, job_id: str) -> Dict[str, Any]:
    """Verify build_image_meta.json is written to NFS artifacts.

    Args:
        host: Testinfra host connection.
        job_id: UUID of the job.

    Returns:
        Dict with keys: success, path, details, error.
    """
    artifact_base = resolve_omnia_path(host, "build_stream_root")
    meta_path = f"{artifact_base}/artifacts/{job_id}/build_image_meta.json"

    cmd = CMDS["file_exists"].format(path=meta_path)
    cmd_result = run_on_host(host, cmd)
    if cmd_result.stdout.strip() == "exists":
        return {
            "success": True, "path": meta_path,
            "details": f"Found: {meta_path}", "error": "",
        }
    return {
        "success": False, "path": meta_path, "details": "",
        "error": f"Not found: {meta_path}",
    }


def get_pipeline_summary(
    host, job_id: str, build_only: bool = True,
) -> Dict[str, Any]:
    """Get a summary of stages for the job.

    Args:
        host: Testinfra host connection.
        job_id: UUID of the job.
        build_only: If True, only check build-pipeline stages
            (upload, create-local-repository, build-image).
            Deploy-pipeline stages (deploy, restart, validate) are excluded.

    Returns:
        Dict with keys: success, stages (list), all_completed, details, error.
    """
    result = {
        "success": False, "stages": [], "all_completed": False,
        "details": "", "error": "",
    }
    sql = (
        f"SELECT stage_name, stage_state, error_code "
        f"FROM job_stages WHERE job_id = '{job_id}' "
        f"ORDER BY started_at"
    )
    query = _exec_psql(host, sql)
    if not query["success"]:
        result["error"] = query["error"]
        return result

    stages = []
    for row in query["rows"]:
        parts = row.split("|")
        if len(parts) >= 3:
            stages.append({
                "stage_name": parts[0].strip(),
                "stage_state": parts[1].strip(),
                "error_code": parts[2].strip(),
            })

    # Filter to build-pipeline stages only
    if build_only:
        stages = [
            s for s in stages
            if s["stage_name"] in BUILD_PIPELINE_ONLY_STAGES
        ]

    result["stages"] = stages
    result["all_completed"] = (
        len(stages) > 0
        and all(s["stage_state"] == STAGE_STATE_COMPLETED for s in stages)
    )
    result["success"] = True

    status_lines = [
        f"  {s['stage_name']}: {s['stage_state']}" for s in stages
    ]
    result["details"] = "\n".join(status_lines)
    return result


# =============================================================================
# REPO MANAGER OUTPUT VERIFICATION
# =============================================================================

def check_repo_status(host) -> Dict[str, Any]:
    """Verify repo_status.yml overall_status is success.

    Reads the Repo Manager status file below the ``OMNIA_DATA_PATH`` and
    ``OMNIA_PROJECT_NAME`` configured on the execution OIM and checks that
    the ``overall_status`` key equals ``success``.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, overall_status, path, details, error.
    """
    input_path = resolve_build_stream_input_path(host)
    project = input_path.rstrip("/").rsplit("/", 1)[-1]
    omnia_data_path = resolve_omnia_data_path(host)
    repo_status_path = (
        f"{omnia_data_path}/repo_manager/output/{project}/repo_status.yml"
    )

    result = {
        "success": False, "overall_status": "",
        "path": repo_status_path, "details": "", "error": "",
    }

    cmd = CMDS["cat_file"].format(path=repo_status_path)
    cmd_result = run_on_host(host, cmd)
    if cmd_result.rc != 0:
        result["error"] = f"Cannot read {repo_status_path} (rc={cmd_result.rc})"
        return result

    content = cmd_result.stdout.strip()
    if not content:
        result["error"] = f"File is empty: {repo_status_path}"
        return result

    # Parse YAML to find overall_status
    for line in content.split("\n"):
        if "overall_status" in line and ":" in line:
            _, _, val = line.partition(":")
            result["overall_status"] = val.strip().strip('"').strip("'")
            break

    if not result["overall_status"]:
        result["error"] = f"overall_status not found in {repo_status_path}"
        return result

    if result["overall_status"].lower() == "success":
        result["success"] = True
        result["details"] = f"repo_status.yml overall_status: success"
    else:
        result["error"] = (
            f"overall_status is '{result['overall_status']}' "
            f"(expected 'success')"
        )
    return result


def _catalog_rpm_requirements(catalog_data: Dict[str, Any]) -> set:
    """Return ``(version, architecture, repository)`` catalog requirements."""
    catalog = catalog_data.get("catalog", catalog_data)
    groups = catalog.get("groups", {})
    packages = catalog.get("packages", {})
    referenced_packages = set()
    for functional_layer in catalog.get("functionallayer", []):
        for group_name in functional_layer.get("components", []):
            group = groups.get(group_name, {})
            referenced_packages.update(group.get("components", []))

    requirements = set()
    for package_name in referenced_packages:
        package = packages.get(package_name, {})
        package_type = package.get(
            "type", package.get("packagetype", "rpm")
        )
        if package_type not in {"rpm", "rpm_list", "rpm_repo"}:
            continue
        for source in package.get("sources", []):
            repository = str(source.get("reponame", "")).strip()
            architecture = str(source.get("architecture", "")).strip()
            versions = source.get("version", [])
            if isinstance(versions, str):
                versions = [versions]
            if not repository or architecture not in {"x86_64", "aarch64"}:
                continue
            requirements.update(
                (str(version), architecture, repository)
                for version in versions
            )
    return requirements


def _catalog_repository_identities(catalog_data: Dict[str, Any]) -> set:
    """Return RPM repository identities referenced by a cadence catalog."""
    return {
        f"{architecture}_rhel_{version}_{repository}"
        for version, architecture, repository
        in _catalog_rpm_requirements(catalog_data)
    }


def check_cadence_local_repo_status(
    host, catalog_ref: str = "",
) -> Dict[str, Any]:
    """Validate the local-repository contract for the cadence catalog.

    ``repo_resync_status.yml`` proves the watcher reconciled upstream content.
    This separate check proves the unified pipeline's
    ``configure-local-repository`` stage published every RPM repository needed
    by the exact cadence catalog revision.
    """
    input_path = resolve_build_stream_input_path(host)
    project = input_path.rstrip("/").rsplit("/", 1)[-1]
    status_path = (
        f"{resolve_omnia_data_path(host)}/repo_manager/output/"
        f"{project}/repo_status.yml"
    )
    result = {
        "success": False,
        "path": status_path,
        "overall_status": "",
        "requirements": [],
        "details": "",
        "error": "",
    }
    try:
        status = read_remote_yaml(host, status_path)
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        result["error"] = f"Unable to read {status_path}: {exc}"
        return result
    if not isinstance(status, dict):
        result["error"] = f"{status_path} must contain a YAML mapping"
        return result

    result["overall_status"] = status.get("overall_status", "")
    if result["overall_status"] != "success":
        result["error"] = "repo_status.yml overall_status is not success"
        return result

    catalog_result = get_cadence_catalog(host, ref=catalog_ref)
    if not catalog_result["success"]:
        result["error"] = catalog_result["error"]
        return result
    requirements = _catalog_rpm_requirements(catalog_result["catalog"])
    if not requirements:
        result["error"] = "Cadence catalog references no RPM repositories"
        return result
    result["requirements"] = sorted(requirements)

    execution_contexts = status.get("execution_contexts")
    status_by_version = status.get("overall_status_by_version")
    repositories = status.get("repositories")
    if not isinstance(execution_contexts, list):
        result["error"] = "repo_status.yml execution_contexts is not a list"
        return result
    if not isinstance(status_by_version, dict):
        result["error"] = (
            "repo_status.yml overall_status_by_version is not a mapping"
        )
        return result
    if not isinstance(repositories, dict):
        result["error"] = "repo_status.yml repositories is not a mapping"
        return result

    configured_contexts = {
        (str(context.get("os_version", "")), architecture)
        for context in execution_contexts
        if isinstance(context, dict)
        for architecture in context.get("architectures", [])
    }
    missing = []
    for version, architecture, repository in requirements:
        repository_data = (
            repositories.get(version, {})
            .get(architecture, {})
            .get(repository)
        )
        if (version, architecture) not in configured_contexts:
            missing.append(
                f"execution_context:{version}/{architecture}"
            )
        if status_by_version.get(version) != "success":
            missing.append(f"version_status:{version}")
        if not isinstance(repository_data, dict) or not str(
            repository_data.get("url", "")
        ).strip():
            missing.append(
                f"repository:{version}/{architecture}/{repository}"
            )
    if missing:
        result["error"] = (
            "repo_status.yml is incomplete for cadence catalog: "
            f"{sorted(set(missing))}"
        )
        return result

    result["success"] = True
    result["details"] = (
        "Local repository status succeeded for "
        f"{len(requirements)} catalog RPM repositories"
    )
    return result


def check_build_status(
    host, job_id: str, roles: List[str],
) -> Dict[str, Any]:
    """Validate the versioned and latest Image Build Manager contracts."""
    result = {
        "success": False,
        "path": "",
        "latest_path": "",
        "image_group_id": "",
        "roles": [],
        "missing": [],
        "unexpected": [],
        "details": "",
        "error": "",
    }
    build_status = _get_build_status_images(host, job_id)
    result.update({
        "path": build_status.get("path", ""),
        "latest_path": build_status.get("latest_path", ""),
        "image_group_id": build_status.get("image_group_id", ""),
    })
    if not build_status["success"]:
        result["error"] = build_status["error"]
        return result

    status = build_status["data"]
    if status.get("overall_status") != "success":
        result["error"] = "build_status.yml overall_status is not success"
        return result
    if status.get("image_build_type") not in {
        "image-builder", "image-thrillhouse",
    }:
        result["error"] = "build_status.yml has an invalid image_build_type"
        return result
    s3_config = status.get("s3_configurations")
    if not isinstance(s3_config, dict) or not all(
        str(s3_config.get(key, "")).strip()
        for key in ("endpoint_url", "bucket")
    ):
        result["error"] = "build_status.yml has incomplete S3 configuration"
        return result

    images = build_status["images"]
    expected_roles = set(roles)
    actual_roles = set(images)
    result["roles"] = sorted(actual_roles)
    result["missing"] = sorted(expected_roles - actual_roles)
    result["unexpected"] = sorted(actual_roles - expected_roles)
    incomplete = sorted(
        role for role, image in images.items()
        if not all(str(image.get(key, "")).strip()
                   for key in ("kernel", "initrd", "image"))
    )
    if result["missing"] or result["unexpected"] or incomplete:
        result["error"] = (
            "build_status.yml role contract mismatch: "
            f"missing={result['missing']}, "
            f"unexpected={result['unexpected']}, "
            f"incomplete={incomplete}"
        )
        return result

    try:
        latest_status = read_remote_yaml(host, result["latest_path"])
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        result["error"] = (
            f"Unable to read {result['latest_path']}: {exc}"
        )
        return result
    if latest_status != status:
        result["error"] = (
            "Latest build_status.yml does not match the cadence "
            "image-group contract"
        )
        return result

    result["success"] = True
    result["details"] = (
        f"Build status succeeded for {len(actual_roles)} roles using "
        f"{status['image_build_type']}"
    )
    return result


# =============================================================================
# CADENCE PIPELINE INTEGRITY VERIFICATION
# =============================================================================

def _catalog_functional_groups(catalog: Dict[str, Any]) -> set[str]:
    """Return the functional-layer names declared by a catalog."""
    section = catalog.get("catalog") or catalog.get("Catalog") or {}
    layers = section.get("functionallayer") or section.get(
        "FunctionalLayer", []
    )
    return {
        str(layer.get("name") or layer.get("Name") or "").strip()
        for layer in layers
        if isinstance(layer, dict)
        and str(layer.get("name") or layer.get("Name") or "").strip()
    }


def _read_remote_text(host, path: str) -> Dict[str, Any]:
    """Read a required remote text file."""
    response = run_on_host(host, CMDS["cat_file"].format(path=path))
    if response.rc != 0:
        return {
            "success": False,
            "content": "",
            "error": f"Unable to read required file: {path}",
        }
    return {
        "success": True,
        "content": response.stdout,
        "error": "",
    }


def _parse_iso_timestamp(value: str) -> Optional[datetime.datetime]:
    """Parse an API ISO-8601 timestamp into an aware datetime."""
    if not value:
        return None
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1]
        if not re.search(r"[+-]\d{2}:\d{2}$", normalized):
            normalized += "+00:00"
    try:
        return datetime.datetime.fromisoformat(normalized)
    except ValueError:
        return None


def check_cadence_catalog_commit_integrity(
    host, pipeline_sha: str,
) -> Dict[str, Any]:
    """Verify that one cadence commit preserved identity and bumped version."""
    result = {"success": False, "details": "", "error": ""}
    if not re.fullmatch(r"[0-9a-fA-F]{7,64}", pipeline_sha or ""):
        result["error"] = f"Invalid cadence pipeline SHA: {pipeline_sha!r}"
        return result

    api_base = _get_gitlab_api_base(host)
    if not api_base["success"]:
        result["error"] = api_base["error"]
        return result
    command = CMDS["gitlab_api_get_commit"].format(
        token=api_base["token"],
        api_url=api_base["api_url"],
        project_id=api_base["project_id"],
        commit_id=pipeline_sha,
    )
    response = run_on_host(host, command)
    if response.rc != 0:
        result["error"] = "Unable to read cadence commit from GitLab"
        return result
    try:
        commit = json.loads(response.stdout)
    except json.JSONDecodeError as exc:
        result["error"] = f"Cadence commit response is invalid JSON: {exc}"
        return result
    parents = commit.get("parent_ids") or []
    if len(parents) != 1:
        result["error"] = (
            "Cadence catalog update must have exactly one parent commit"
        )
        return result

    current = get_cadence_catalog(host, ref=pipeline_sha)
    previous = get_cadence_catalog(host, ref=str(parents[0]))
    if not current["success"]:
        result["error"] = current["error"]
        return result
    if not previous["success"]:
        result["error"] = previous["error"]
        return result
    if current["last_commit_id"] != pipeline_sha:
        result["error"] = (
            "Pipeline SHA does not match the cadence catalog commit"
        )
        return result
    if current["identifier"] != previous["identifier"]:
        result["error"] = "Cadence changed the catalog identifier"
        return result

    current_match = re.fullmatch(r"(\d+)\.(\d+)", current["version"])
    previous_match = re.fullmatch(r"(\d+)\.(\d+)", previous["version"])
    if not current_match or not previous_match:
        result["error"] = "Cadence catalog version is not in major.minor form"
        return result
    expected_version = (
        f"{int(previous_match.group(1))}."
        f"{int(previous_match.group(2)) + 1}"
    )
    if current["version"] != expected_version:
        result["error"] = (
            f"Expected one cadence version increment to {expected_version}; "
            f"found {current['version']}"
        )
        return result

    result.update({
        "success": True,
        "details": (
            f"Catalog {current['identifier']} advanced exactly once: "
            f"{previous['version']} -> {current['version']}"
        ),
    })
    return result


def check_cadence_functional_group_coverage(
    host, job_id: str, catalog_ref: str,
) -> Dict[str, Any]:
    """Compare catalog roles with both database and build-status roles."""
    result = {"success": False, "details": "", "error": ""}
    catalog = get_cadence_catalog(host, ref=catalog_ref)
    if not catalog["success"]:
        result["error"] = catalog["error"]
        return result
    expected = _catalog_functional_groups(catalog["catalog"])
    if not expected:
        result["error"] = "Cadence catalog contains no functional groups"
        return result

    database = get_images_for_job(host, job_id)
    if not database["success"]:
        result["error"] = database["error"]
        return result
    database_roles = {
        str(image.get("role", "")).strip()
        for image in database["images"]
        if str(image.get("role", "")).strip()
    }
    build_status = _get_build_status_images(host, job_id)
    if not build_status["success"]:
        result["error"] = build_status["error"]
        return result
    status_roles = set(build_status["images"])

    problems = []
    for source, actual in (
        ("database", database_roles),
        ("build_status.yml", status_roles),
    ):
        missing = sorted(expected - actual)
        unexpected = sorted(actual - expected)
        if missing or unexpected:
            problems.append(
                f"{source}: missing={missing}, unexpected={unexpected}"
            )
    if problems:
        result["error"] = "Functional-group mismatch: " + "; ".join(
            problems
        )
        return result

    result.update({
        "success": True,
        "details": (
            f"Catalog, database, and build status contain the same "
            f"{len(expected)} functional groups"
        ),
    })
    return result


def check_cadence_artifact_identity(
    host, job_id: str, catalog_ref: str,
) -> Dict[str, Any]:
    """Validate the current versioned status and engine-specific paths."""
    result = {"success": False, "details": "", "error": ""}
    catalog = get_cadence_catalog(host, ref=catalog_ref)
    if not catalog["success"]:
        result["error"] = catalog["error"]
        return result
    build_status = _get_build_status_images(host, job_id)
    if not build_status["success"]:
        result["error"] = build_status["error"]
        return result

    expected_group = catalog["composite_image_group_id"]
    if build_status["image_group_id"] != expected_group:
        result["error"] = (
            f"Versioned build status belongs to "
            f"{build_status['image_group_id']}, expected {expected_group}"
        )
        return result
    if f"/{expected_group}/build_status.yml" not in build_status["path"]:
        result["error"] = "Build status is not stored under catalog identity"
        return result

    engine = build_status["data"].get("image_build_type")
    engine_token = {
        "image-builder": "-imgbld",
        "image-thrillhouse": "-imgth",
    }.get(engine)
    if not engine_token:
        result["error"] = f"Unsupported image build engine: {engine!r}"
        return result

    invalid = []
    all_paths = []
    expected_files = {
        "image": "rootfs.squashfs",
        "kernel": "vmlinuz",
        "initrd": "initramfs.img",
    }
    for role, image in build_status["images"].items():
        for key, filename in expected_files.items():
            path = str(image.get(key, ""))
            all_paths.append(path)
            parts = PurePosixPath(path).parts
            if (
                not path
                or len(parts) < 4
                or role not in parts
                or engine_token not in path
                or parts[-1] != filename
            ):
                invalid.append(f"{role}:{key}:{path}")
    if invalid:
        result["error"] = (
            "Artifact paths do not match role/engine contract: "
            f"{invalid}"
        )
        return result
    if len(all_paths) != len(set(all_paths)):
        result["error"] = "Artifact contract contains duplicate object paths"
        return result

    result.update({
        "success": True,
        "details": (
            f"{len(build_status['images'])} role contracts select unique "
            f"{engine} artifacts for {expected_group}"
        ),
    })
    return result


def get_cadence_validation_report(host, job_id: str) -> Dict[str, Any]:
    """Load the newest attempt-isolated validation report for a job."""
    result = {
        "success": False,
        "path": "",
        "total": 0,
        "passed": 0,
        "failed": 0,
        "errors": 0,
        "skipped": 0,
        "tests": [],
        "error": "",
    }
    if not re.fullmatch(
        r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}",
        job_id or "",
    ):
        result["error"] = f"Invalid cadence job_id: {job_id!r}"
        return result
    validate_dir = (
        f"{resolve_omnia_data_path(host)}/build_stream_root/artifacts/"
        f"{job_id}/validate"
    )
    found = run_on_host(
        host,
        CMDS["find_latest_validate_report"].format(path=validate_dir),
    )
    report_path = ""
    if found.rc == 0 and found.stdout.strip():
        _, separator, report_path = found.stdout.strip().partition(" ")
        if not separator:
            report_path = ""
    if not report_path:
        report_path = f"{validate_dir}/test_report.json"

    report_file = _read_remote_text(host, report_path)
    if not report_file["success"]:
        result["error"] = report_file["error"]
        return result
    try:
        report = json.loads(report_file["content"])
    except json.JSONDecodeError as exc:
        result["error"] = f"Validation report is invalid JSON: {exc}"
        return result

    tests = []
    for server in (report.get("servers") or {}).values():
        runs = server.get("runs") if isinstance(server, dict) else []
        for run in runs or []:
            for module in run.get("modules", []):
                tests.extend(module.get("results", []))
    statuses = [
        str(test.get("status", "")).upper()
        for test in tests if isinstance(test, dict)
    ]
    result.update({
        "path": report_path,
        "total": len(statuses),
        "passed": statuses.count("PASSED"),
        "failed": statuses.count("FAILED"),
        "errors": statuses.count("ERROR"),
        "skipped": statuses.count("SKIPPED"),
        "tests": tests,
    })
    if not statuses:
        result["error"] = "Validation report contains zero test results"
    elif result["failed"] or result["errors"]:
        result["error"] = (
            f"Validation report contains {result['failed']} failures and "
            f"{result['errors']} errors"
        )
    else:
        result["success"] = True
    return result


def _read_cadence_pxe_rows(host, job_id: str) -> Dict[str, Any]:
    """Read the PXE snapshot uploaded to a cadence job."""
    path = (
        f"{resolve_omnia_data_path(host)}/build_stream_root/artifacts/"
        f"{job_id}/pxe_mapping_file.csv"
    )
    source = _read_remote_text(host, path)
    if not source["success"]:
        return {"success": False, "rows": [], "error": source["error"]}
    rows = list(csv.DictReader(io.StringIO(source["content"])))
    if not rows:
        return {
            "success": False,
            "rows": [],
            "error": "PXE mapping snapshot contains no nodes",
        }
    return {"success": True, "rows": rows, "error": ""}


def check_cadence_validation_feature_selection(
    host, job_id: str,
) -> Dict[str, Any]:
    """Ensure validation selected Slurm and Kubernetes from PXE groups."""
    result = {"success": False, "details": "", "error": ""}
    mapping = _read_cadence_pxe_rows(host, job_id)
    if not mapping["success"]:
        result["error"] = mapping["error"]
        return result
    report = get_cadence_validation_report(host, job_id)
    if not report["success"]:
        result["error"] = report["error"]
        return result

    groups = {
        str(row.get("FUNCTIONAL_GROUP_NAME", "")).strip().lower()
        for row in mapping["rows"]
    }
    expected = {
        "kubernetes": any(group.startswith("service_kube") for group in groups),
        "slurm": any(
            group.startswith(("slurm_", "login_")) for group in groups
        ),
    }

    def _feature_for(test_name: str) -> str:
        if test_name.startswith((
            "test_k8s_", "test_kubernetes_", "test_kubelet_",
            "test_containerd_",
        )):
            return "kubernetes"
        if test_name.startswith((
            "test_slurm", "test_srun", "test_sbatch", "test_munge",
            "test_login_nodes",
        )):
            return "slurm"
        return ""

    passed = {"kubernetes": [], "slurm": []}
    for test in report["tests"]:
        if not isinstance(test, dict):
            continue
        feature = _feature_for(str(test.get("test_name", "")))
        if feature and str(test.get("status", "")).upper() == "PASSED":
            passed[feature].append(test.get("test_name"))

    problems = []
    for feature, is_expected in expected.items():
        if is_expected and not passed[feature]:
            problems.append(f"{feature} configured but no test passed")
        if not is_expected and passed[feature]:
            problems.append(
                f"{feature} absent but tests passed: {passed[feature]}"
            )
    if problems:
        result["error"] = "Feature-selection mismatch: " + "; ".join(
            problems
        )
        return result

    selected = [name for name, enabled in expected.items() if enabled]
    result.update({
        "success": True,
        "details": (
            f"Validation selected {', '.join(selected)} according to "
            f"{len(mapping['rows'])} PXE-mapped nodes"
        ),
    })
    return result


def check_cadence_restart_node_coverage(
    host, job_id: str,
) -> Dict[str, Any]:
    """Compare successful restart results with the exact PXE snapshot."""
    result = {"success": False, "details": "", "error": ""}
    mapping = _read_cadence_pxe_rows(host, job_id)
    if not mapping["success"]:
        result["error"] = mapping["error"]
        return result
    artifact = get_bsm_artifact_json(host, job_id, "node-results")
    if not artifact["success"] or not artifact["exists"]:
        result["error"] = artifact["error"] or "node_results.json is missing"
        return result

    expected_tags = [
        str(row.get("SERVICE_TAG", "")).strip()
        for row in mapping["rows"]
    ]
    nodes = artifact["data"].get("nodes", [])
    actual_tags = [
        str(node.get("service_tag", "")).strip()
        for node in nodes if isinstance(node, dict)
    ]
    if (
        not all(expected_tags)
        or len(expected_tags) != len(set(expected_tags))
    ):
        result["error"] = "PXE mapping contains empty or duplicate service tags"
        return result
    if not all(actual_tags) or len(actual_tags) != len(set(actual_tags)):
        result["error"] = "Restart results contain empty or duplicate nodes"
        return result
    if set(expected_tags) != set(actual_tags):
        result["error"] = (
            "Restart node coverage mismatch: "
            f"missing={sorted(set(expected_tags) - set(actual_tags))}, "
            f"unexpected={sorted(set(actual_tags) - set(expected_tags))}"
        )
        return result
    failed = [
        node.get("service_tag") if isinstance(node, dict) else "invalid-entry"
        for node in nodes
        if not isinstance(node, dict) or node.get("status") != "success"
    ]
    node_data = artifact["data"]
    if failed or node_data.get("failure_count") != 0:
        result["error"] = f"Restart contains failed nodes: {failed}"
        return result
    if (
        node_data.get("total_nodes") != len(expected_tags)
        or node_data.get("success_count") != len(expected_tags)
    ):
        result["error"] = "Restart summary counts do not match PXE mapping"
        return result

    result.update({
        "success": True,
        "details": (
            f"All {len(expected_tags)} PXE-mapped nodes have one successful "
            f"restart result"
        ),
    })
    return result


def check_cadence_input_snapshot(
    host, job_id: str, catalog_ref: str,
) -> Dict[str, Any]:
    """Verify the canonical catalog and mandatory domain input snapshot."""
    result = {"success": False, "details": "", "error": ""}
    artifact_root = (
        f"{resolve_omnia_data_path(host)}/build_stream_root/artifacts/{job_id}"
    )
    required = {
        "catalog_rhel.json",
        "repo_manager_config.yml",
        "repo_manager_endpoint_config.yml",
        "image_build_config.yml",
        "omnia_config.yml",
        "orchestrator_config.yml",
        "network_spec.yml",
        "pxe_mapping_file.csv",
    }
    missing = []
    for filename in sorted(required):
        exists = run_on_host(
            host,
            CMDS["file_exists"].format(
                path=f"{artifact_root}/{filename}"
            ),
        )
        if exists.stdout.strip() != "exists":
            missing.append(filename)
    if missing:
        result["error"] = f"Cadence input snapshot is missing: {missing}"
        return result

    uploaded = _read_remote_text(host, f"{artifact_root}/catalog_rhel.json")
    if not uploaded["success"]:
        result["error"] = uploaded["error"]
        return result
    expected = get_cadence_catalog(host, ref=catalog_ref)
    if not expected["success"]:
        result["error"] = expected["error"]
        return result
    try:
        uploaded_catalog = json.loads(uploaded["content"])
    except json.JSONDecodeError as exc:
        result["error"] = f"Uploaded catalog is invalid JSON: {exc}"
        return result
    if uploaded_catalog != expected["catalog"]:
        result["error"] = (
            "Uploaded catalog_rhel.json does not match the cadence commit"
        )
        return result

    result.update({
        "success": True,
        "details": (
            f"Canonical cadence catalog and {len(required) - 1} mandatory "
            f"domain inputs are present"
        ),
    })
    return result


def check_cadence_stage_freshness(host, job_id: str) -> Dict[str, Any]:
    """Verify completed stages and their logs are scoped to this job."""
    result = {"success": False, "details": "", "error": ""}
    response = get_bsm_job_details(host, job_id)
    if not response["success"]:
        result["error"] = response["error"]
        return result
    job = response["job"]
    created_at = _parse_iso_timestamp(str(job.get("created_at", "")))
    if not created_at:
        result["error"] = "Cadence job has no valid creation timestamp"
        return result

    required = {
        "parse-catalog",
        "create-local-repository",
        "build-image",
        "deploy",
        "restart",
        "validate",
    }
    stages = {
        stage.get("stage_name"): stage
        for stage in job.get("stages", [])
        if isinstance(stage, dict) and stage.get("stage_name") in required
    }
    if set(stages) != required:
        result["error"] = (
            f"Current job is missing stages: {sorted(required - set(stages))}"
        )
        return result

    problems = []
    for name, stage in stages.items():
        started = _parse_iso_timestamp(str(stage.get("started_at", "")))
        ended = _parse_iso_timestamp(str(stage.get("ended_at", "")))
        if stage.get("stage_state") != STAGE_STATE_COMPLETED:
            problems.append(f"{name}: not completed")
        if not started or not ended or started < created_at or ended < started:
            problems.append(f"{name}: invalid or stale timestamps")
        log_path = str(stage.get("log_file_path") or "")
        if log_path:
            if job_id not in log_path:
                problems.append(f"{name}: log path is not job-scoped")
            else:
                exists = run_on_host(
                    host, CMDS["file_exists"].format(path=log_path)
                )
                if exists.stdout.strip() != "exists":
                    problems.append(f"{name}: stage log does not exist")
    if problems:
        result["error"] = "Stage freshness failures: " + "; ".join(problems)
        return result

    result.update({
        "success": True,
        "details": (
            f"All {len(required)} mandatory DB stages and available logs "
            f"belong to job {job_id}"
        ),
    })
    return result


def check_repo_resync_status(
    host, catalog_ref: str = "",
) -> Dict[str, Any]:
    """Validate the exact-mirror result produced before a cadence pipeline."""
    input_path = resolve_build_stream_input_path(host)
    project = input_path.rstrip("/").rsplit("/", 1)[-1]
    status_path = (
        f"{resolve_omnia_data_path(host)}/repo_manager/output/"
        f"{project}/repo_resync_status.yml"
    )
    result = {
        "success": False,
        "path": status_path,
        "overall_status": "",
        "orphan_cleanup": "",
        "repositories": {},
        "details": "",
        "error": "",
    }
    try:
        status = read_remote_yaml(host, status_path)
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        result["error"] = f"Unable to read {status_path}: {exc}"
        return result
    if not isinstance(status, dict):
        result["error"] = f"{status_path} must contain a YAML mapping"
        return result

    result["overall_status"] = status.get("overall_status", "")
    result["orphan_cleanup"] = status.get("orphan_cleanup", "")
    repositories = status.get("repositories")
    if not isinstance(repositories, dict) or not repositories:
        result["error"] = "repo_resync_status.yml contains no repositories"
        return result
    result["repositories"] = repositories

    catalog_result = get_cadence_catalog(host, ref=catalog_ref)
    if not catalog_result["success"]:
        result["error"] = catalog_result["error"]
        return result
    expected_repositories = _catalog_repository_identities(
        catalog_result["catalog"]
    )
    if not expected_repositories:
        result["error"] = "Cadence catalog references no RPM repositories"
        return result
    if set(repositories) != expected_repositories:
        result["error"] = (
            "repo_resync_status.yml scope does not match cadence catalog: "
            f"missing={sorted(expected_repositories - set(repositories))}, "
            f"unexpected={sorted(set(repositories) - expected_repositories)}"
        )
        return result

    failures = {}
    for name, repository in repositories.items():
        if not isinstance(repository, dict):
            failures[name] = "result is not a mapping"
            continue
        invalid_metrics = [
            key for key in ("packages_added", "packages_removed")
            if not isinstance(repository.get(key), int)
            or isinstance(repository.get(key), bool)
            or repository.get(key, -1) < 0
        ]
        old_version = repository.get("old_version")
        new_version = repository.get("new_version")
        problems = []
        if repository.get("sync_status") != "success":
            problems.append("sync_status is not success")
        if repository.get("cleanup_status") != "success":
            problems.append("cleanup_status is not success")
        if repository.get("stale_packages_remaining") != 0:
            problems.append("stale_packages_remaining is not zero")
        if not isinstance(repository.get("publication_updated"), bool):
            problems.append("publication_updated is not boolean")
        if invalid_metrics:
            problems.append(
                "invalid package metrics: " + ", ".join(invalid_metrics)
            )
        if (
            not isinstance(old_version, int)
            or isinstance(old_version, bool)
            or not isinstance(new_version, int)
            or isinstance(new_version, bool)
            or new_version < old_version
        ):
            problems.append("invalid repository version metrics")
        if problems:
            failures[name] = "; ".join(problems)

    if status.get("overall_status") != "success":
        result["error"] = "overall_status is not success"
    elif status.get("orphan_cleanup") != "success":
        result["error"] = "orphan_cleanup is not success"
    elif failures:
        result["error"] = f"Repository reconciliation failures: {failures}"
    else:
        result["success"] = True
        result["details"] = (
            f"Exact-mirror reconciliation succeeded for "
            f"{len(repositories)} repositories"
        )
    return result


# =============================================================================
# REGISTRY & S3 IMAGE VERIFICATION (simple, direct checks)
# =============================================================================

def check_registry_images_exist(host) -> Dict[str, Any]:
    """Check if container images exist in the local registry.

    Queries the registry catalog via curl (HTTP/HTTPS). Does not require
    job_id or roles — simply checks that the registry has repositories.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, registry_url, found_images, details, error.
    """
    result = {
        "success": False, "registry_url": "",
        "found_images": [], "details": "", "error": "",
    }

    hostname_cmd = run_on_host(host, CMDS["hostname_cmd"])
    hostname = hostname_cmd.stdout.strip() if hostname_cmd.rc == 0 else "localhost"
    registry_url = f"{hostname}:{REGISTRY_PORT}"
    result["registry_url"] = registry_url

    # Query registry catalog
    catalog_repos = []
    catalog_cmd = run_on_host(
        host, CMDS["curl_registry_catalog"].format(port=REGISTRY_PORT),
    )
    if catalog_cmd.rc == 0 and catalog_cmd.stdout.strip():
        try:
            data = json.loads(catalog_cmd.stdout.strip())
            catalog_repos = data.get("repositories", [])
        except json.JSONDecodeError:
            pass

    if not catalog_repos:
        # Fallback to regctl
        regctl_cmd = run_on_host(
            host, CMDS["regctl_repo_ls"].format(registry_url=registry_url),
        )
        if regctl_cmd.rc == 0 and regctl_cmd.stdout.strip():
            catalog_repos = [
                r.strip()
                for r in regctl_cmd.stdout.strip().split("\n")
                if r.strip()
            ]

    if not catalog_repos:
        result["error"] = (
            f"No images found in registry at {registry_url}. "
            "Check: curl -sk https://localhost:5000/v2/_catalog"
        )
        return result

    # Filter for rhel- images (built images follow this pattern)
    built_images = [
        r for r in catalog_repos
        if REGISTRY_IMAGE_PREFIX in r
    ]

    result["found_images"] = built_images if built_images else catalog_repos
    result["success"] = len(result["found_images"]) > 0
    result["details"] = (
        f"Found {len(result['found_images'])} image(s) in registry"
    )
    return result


def check_s3_boot_images_exist(host) -> Dict[str, Any]:
    """Check if boot images exist in S3 boot-images bucket.

    Queries the S3 bucket listing. Does not require job_id or roles —
    simply checks that the bucket has boot image files.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, found_images, details, error.
    """
    result = {
        "success": False, "found_images": [],
        "details": "", "error": "",
    }

    # Check bucket exists first
    bucket_cmd = run_on_host(
        host, CMDS["s3cmd_ls_bucket"].format(bucket=S3_BOOT_IMAGES_BUCKET),
    )
    if bucket_cmd.rc != 0:
        result["error"] = (
            f"S3 bucket {S3_BOOT_IMAGES_BUCKET} not accessible. "
            "Check: s3cmd ls s3://boot-images/"
        )
        return result

    # List contents
    ls_cmd = run_on_host(
        host, CMDS["s3cmd_ls_recursive"].format(bucket=S3_BOOT_IMAGES_BUCKET),
    )
    if ls_cmd.rc != 0 or not ls_cmd.stdout.strip():
        result["error"] = (
            f"S3 bucket {S3_BOOT_IMAGES_BUCKET} is empty or inaccessible. "
            "Check: s3cmd ls -r s3://boot-images/"
        )
        return result

    # Parse S3 listing
    s3_files = []
    for line in ls_cmd.stdout.strip().split("\n"):
        parts = line.strip().split()
        if parts:
            path = parts[-1]
            if path.startswith("s3://"):
                s3_files.append(path)

    if not s3_files:
        result["error"] = (
            f"No files found in {S3_BOOT_IMAGES_BUCKET}. "
            "Verify build-image stage completed."
        )
        return result

    result["found_images"] = s3_files
    result["success"] = True
    result["details"] = (
        f"Found {len(s3_files)} file(s) in S3 boot-images bucket"
    )
    return result


# =============================================================================
# CATALOG PUSH FROM EXAMPLES
# =============================================================================

def push_catalog_from_examples(  # pylint: disable=too-many-locals
    host, catalog_path: str,
    log_callback: Optional[Callable] = None,
    skip_ci: bool = False,
) -> Dict[str, Any]:
    """Load a selected catalog below ``samples/catalogs`` and push it.

    Args:
        host: Testinfra host connection.
        catalog_path: POSIX path relative to ``src/main/samples/catalogs``.
        log_callback: Optional logging callback.
        skip_ci: Stage the catalog without starting a commit-triggered
            pipeline. The caller can then trigger with ``PIPELINE_TYPE``.

    Returns:
        Dict with keys: success, catalog_path, commit_id, error.
    """
    result = {
        "success": False, "catalog_path": catalog_path,
        "commit_id": "", "error": "",
    }

    def _log(msg):
        if log_callback:
            log_callback(msg)
        else:
            print(f"    | {msg}", flush=True)

    selected_path = PurePosixPath(catalog_path)
    if (
        selected_path.is_absolute()
        or ".." in selected_path.parts
        or selected_path.suffix.lower() != ".json"
        or len(selected_path.parts) < 2
    ):
        result["error"] = (
            "catalog_path must be a relative JSON path below "
            "src/main/samples/catalogs (for example, "
            "rhel/10.0/slurm_x86_64_no_vast.json)"
        )
        return result

    # From test/build_stream -> ../../src/main/samples/catalogs/
    test_dir = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)
    )))
    catalogs_dir = Path(
        test_dir, "..", "..", "src", "main", "samples", "catalogs",
    ).resolve()
    selected_catalog = (catalogs_dir / Path(*selected_path.parts)).resolve()
    try:
        selected_catalog.relative_to(catalogs_dir)
    except ValueError:
        result["error"] = "catalog_path resolves outside src/main/samples/catalogs"
        return result

    if not selected_catalog.is_file():
        available = []
        if catalogs_dir.is_dir():
            available = sorted(
                path.relative_to(catalogs_dir).as_posix()
                for path in catalogs_dir.rglob("*.json")
                if path.is_file()
            )
        result["error"] = (
            f"Catalog '{catalog_path}' not found below {catalogs_dir}. "
            f"Available: {', '.join(available) if available else 'N/A'}"
        )
        return result

    _log(f"Loading catalog from: {selected_catalog}")
    try:
        with selected_catalog.open("r", encoding="utf-8") as f:
            content = f.read()
    except (IOError, OSError) as exc:
        result["error"] = f"Failed to read catalog: {exc}"
        return result

    # Add unique identifier to avoid cache hits
    try:
        catalog = json.loads(content)
        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        # Support both "Catalog" (legacy) and "catalog" (current) key names
        cat_key = "Catalog" if "Catalog" in catalog else "catalog"
        if cat_key in catalog:
            id_key = "Identifier" if "Identifier" in catalog[cat_key] else "identifier"
            catalog[cat_key][id_key] = f"image-build-{timestamp}"
        content = json.dumps(catalog, indent=2)
    except json.JSONDecodeError:
        pass  # push raw content if not valid JSON

    _log("Uploading catalog to GitLab (replacing the existing catalog)...")
    upload = upload_catalog_file(host, content, skip_ci=skip_ci)
    if not upload["success"]:
        result["error"] = f"Upload failed: {upload['error']}"
        return result

    result["success"] = True
    result["commit_id"] = upload.get("commit_id", "")
    _log(f"Catalog '{catalog_path}' uploaded to GitLab")
    return result


def update_job_id_in_config(job_id: str) -> bool:
    """Write the job_id back to test_config.yml.

    Args:
        job_id: UUID string to persist.

    Returns:
        True if successfully written, False otherwise.
    """
    test_dir = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)
    )))
    config_path = os.path.join(test_dir, "test_config.yml")

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Replace exactly one job_id line (handles empty and populated values).
        content, replacements = re.subn(
            r'^(job_id:\s*).*$',
            f'job_id: "{job_id}"',
            content,
            flags=re.MULTILINE,
        )
        if replacements != 1:
            return False

        with open(config_path, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    except (IOError, OSError):
        return False
