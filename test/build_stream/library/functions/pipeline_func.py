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

import json
import sys
import time
import base64
import datetime
from typing import Any, Callable, Dict, List, Optional

from omnia_auto import load_test_config, run_on_host

from library.vars.common_vars import (
    BSM_HEALTH_PATH,
    BSM_HOST_IP_KEY,
    BSM_PORT_KEY,
    BOOT_IMAGE_ARTIFACTS_PER_ROLE,
    BUILD_STREAM_CONFIG_FILE,
    BUILD_STREAM_CREDENTIALS_FILE,
    BUILD_STREAM_CREDENTIALS_KEY,
    BUILD_PIPELINE_ONLY_STAGES,
    CATALOG_DEFAULT_FILENAME,
    CATALOG_FILE_PATH,
    CMDS,
    GITLAB_API_VERSION,
    GITLAB_ROOT_TOKEN_FILE,
    IMAGE_GROUP_STATUS_BUILT,
    IMAGE_GROUP_STATUS_CLEANED,
    JOB_WAIT_TIMEOUT,
    NFS_ARTIFACT_BASE_DEFAULT,
    PIPELINE_POLL_INTERVAL,
    PIPELINE_POLL_TIMEOUT,
    PIPELINE_TYPE_BUILD,
    PIPELINE_TYPE_KEY,
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
    STAGE_STATE_RUNNING,
    GITLAB_CI_BUILD_STAGES,
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
    config = load_test_config()
    project = config.get("project_name", "project_default")
    data_path = config.get("shared_path", "/opt/omnia/build_stream")
    config_path = f"{data_path}/input/{project}/{BUILD_STREAM_CONFIG_FILE}"

    cmd = CMDS["cat_file"].format(path=config_path)
    result = run_on_host(host, cmd)

    values = {"_config_path": config_path}
    if result.rc == 0 and result.stdout.strip():
        for line in result.stdout.strip().split("\n"):
            if ":" in line and not line.strip().startswith("#"):
                key, _, val = line.partition(":")
                values[key.strip()] = val.strip().strip('"').strip("'")
    return values


_server_creds_cache: Dict[str, str] = {}


def load_server_credentials(host) -> Dict[str, str]:
    """Load credentials from build_stream_credentials.yml on the target host.

    Reads from /opt/omnia/build_stream/input/<project>/build_stream_credentials.yml.
    Handles both plain-text and ansible-vault encrypted files.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict of credential key-value pairs. Empty if file not found.
    """
    if _server_creds_cache:
        return dict(_server_creds_cache)

    config = load_test_config()
    project = config.get("project_name", "project_default")
    data_path = config.get("shared_path", "/opt/omnia/build_stream")
    creds_path = f"{data_path}/input/{project}/{BUILD_STREAM_CREDENTIALS_FILE}"
    key_path = f"{data_path}/input/{project}/{BUILD_STREAM_CREDENTIALS_KEY}"

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


def _get_gitlab_ssh_password(host) -> str:
    """Load gitlab_ssh_password from server credentials file.

    Args:
        host: Testinfra host connection.

    Returns:
        Password string, or empty string if not found.
    """
    creds = load_server_credentials(host)
    return creds.get("gitlab_ssh_password", "")


def _ssh_to_gitlab(host, cmd: str) -> Dict[str, Any]:
    """Run a command on the GitLab server via SSH from OIM.

    Args:
        host: Testinfra host connection.
        cmd: Command to run on the GitLab server.

    Returns:
        Dict with keys: success, stdout, error.
    """
    gitlab_config = _get_gitlab_config(host)
    gitlab_host = gitlab_config.get("gitlab_host", "")
    if not gitlab_host:
        return {"success": False, "stdout": "", "error": "gitlab_host not configured"}

    ssh_cmd = CMDS["ssh_to_gitlab"].format(gitlab_host=gitlab_host, cmd=cmd)
    result = run_on_host(host, ssh_cmd)

    if result.rc == 0:
        return {"success": True, "stdout": result.stdout or "", "error": ""}

    password = _get_gitlab_ssh_password(host)
    if password:
        sshpass_cmd = CMDS["sshpass_to_gitlab"].format(
            password=password, gitlab_host=gitlab_host, cmd=cmd,
        )
        result = run_on_host(host, sshpass_cmd)
        if result.rc == 0:
            return {"success": True, "stdout": result.stdout or "", "error": ""}
        return {
            "success": False, "stdout": result.stdout or "",
            "error": f"SSH to {gitlab_host} failed (rc={result.rc})",
        }
    return {
        "success": False, "stdout": "",
        "error": f"SSH to {gitlab_host} failed (key-based auth rejected)",
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
        variables = json.loads(vars_result.stdout.strip())
        cred_map = {v["key"]: v["value"] for v in variables}
    except (json.JSONDecodeError, KeyError):
        return ""

    client_id = cred_map.get("BSM_CLIENT_ID", "")
    client_secret = cred_map.get("BSM_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        return ""

    token_cmd = CMDS["bsm_api_auth_token"].format(
        host=host_ip, port=port,
        client_id=client_id, client_secret=client_secret,
    )
    token_result = run_on_host(host, token_cmd)
    if token_result.rc != 0 or not token_result.stdout.strip():
        return ""

    try:
        token_data = json.loads(token_result.stdout.strip())
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


def upload_catalog_file(host, catalog_content: str) -> Dict[str, Any]:
    """Upload catalog file to GitLab to trigger build pipeline.

    Args:
        host: Testinfra host connection.
        catalog_content: JSON content of the catalog file.

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
    data = {
        "branch": api_base["branch"],
        "content": encoded_content,
        "commit_message": (
            f"Automation: Update catalog to trigger build ({timestamp})"
        ),
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
) -> Dict[str, Any]:
    """Wait until a new pipeline appears in GitLab after the initial one.

    Args:
        host: Testinfra host connection.
        initial_pipeline_id: Pipeline ID before trigger action.
        timeout: Max seconds to wait.
        poll_interval: Seconds between polls.
        log_callback: Optional logging callback.

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
        pipelines = list_pipelines(host, per_page=5)
        if pipelines["success"] and pipelines["pipelines"]:
            latest = pipelines["pipelines"][0]
            if latest.get("id", 0) > initial_pipeline_id:
                result["pipeline_id"] = latest["id"]
                result["status"] = latest.get("status", "")
                result["elapsed"] = elapsed
                result["success"] = True
                return result
        _log(f"[{elapsed}s] Waiting for new pipeline...")
        time.sleep(poll_interval)

    result["elapsed"] = int(time.time() - start)
    result["error"] = f"No new pipeline after {timeout}s"
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

    config = load_test_config()
    catalog_name = config.get("catalog_name", "") or CATALOG_DEFAULT_FILENAME

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


# =============================================================================
# PIPELINE TRIGGER FUNCTIONS
# =============================================================================

def trigger_build_pipeline_auto(
    host, log_callback: Optional[Callable] = None,
    initial_pipeline_id: int = 0,
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
        result["error"] = "No pipelines found in GitLab"
        return result

    # Separate running from completed pipelines
    running = [
        p for p in all_pipelines
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
    old_job = get_latest_job(host)
    old_job_id = old_job.get("job_id", "") if old_job["success"] else ""
    job_id = _wait_for_new_job(host, old_job_id, log_callback=_log)
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

def get_catalog_roles(host, job_id: str) -> Dict[str, Any]:
    """Get catalog roles and architectures from BSM API.

    Args:
        host: Testinfra host connection.
        job_id: UUID of the job.

    Returns:
        Dict with keys: success, roles, architectures, image_key, error.
    """
    result = {
        "success": False, "roles": [], "architectures": [],
        "image_key": "", "error": "",
    }

    gitlab_config = _get_gitlab_config(host)
    host_ip = gitlab_config.get(BSM_HOST_IP_KEY, "")
    port = gitlab_config.get(BSM_PORT_KEY, "")
    if not host_ip or not port:
        result["error"] = "BSM host_ip or port not configured"
        return result

    token = _get_bsm_access_token(host)
    if not token:
        result["error"] = "Failed to obtain BSM access token"
        return result

    cmd = CMDS["bsm_api_catalog_roles"].format(
        token=token, host=host_ip, port=port, job_id=job_id,
    )
    cmd_result = run_on_host(host, cmd)
    if cmd_result.rc != 0:
        result["error"] = f"API call failed: rc={cmd_result.rc}"
        return result

    try:
        data = json.loads(cmd_result.stdout.strip())
        if "detail" in data:
            result["error"] = f"API error: {data['detail']}"
            return result
        result["roles"] = data.get("roles", [])
        result["architectures"] = data.get("architectures", [])
        result["image_key"] = data.get("image_key", "")
        result["success"] = True
    except json.JSONDecodeError:
        result["error"] = f"Invalid JSON: {cmd_result.stdout[:200]}"
    return result


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

    for role in roles:
        role_pattern = f"{REGISTRY_IMAGE_PREFIX}{role}"
        matched = [r for r in repos if role_pattern in r and job_id in r]
        if matched:
            result["found"].append(role)
        else:
            result["missing"].append(role)

    result["success"] = len(result["missing"]) == 0
    result["details"] = (
        f"Registry: {len(result['found'])}/{len(roles)} roles found"
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

    for role in roles:
        rootfs = [
            p for p in s3_paths
            if p.startswith(f"{S3_BOOT_IMAGES_BUCKET}{role}/") and job_id in p
        ]
        efi = [
            p for p in s3_paths
            if p.startswith(f"{S3_EFI_IMAGES_PREFIX}{role}/") and job_id in p
        ]
        total = len(rootfs) + len(efi)
        if (
            len(rootfs) >= 1
            and len(efi) >= 2
            and total >= BOOT_IMAGE_ARTIFACTS_PER_ROLE
        ):
            result["found_roles"].append(role)
        else:
            result["missing_roles"].append(role)

    result["success"] = len(result["missing_roles"]) == 0
    result["details"] = (
        f"S3: {len(result['found_roles'])}/{len(roles)} roles complete"
    )
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
    artifact_base = NFS_ARTIFACT_BASE_DEFAULT
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

    Reads /opt/omnia/repo_manager/output/project_default/repo_status.yml
    and checks that the overall_status key equals 'success'.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, overall_status, path, details, error.
    """
    config = load_test_config()
    project = config.get("project_name", "project_default")
    repo_status_path = f"/opt/omnia/repo_manager/output/{project}/repo_status.yml"

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

def push_catalog_from_examples(
    host, catalog_name: str,
    log_callback: Optional[Callable] = None,
) -> Dict[str, Any]:
    """Load catalog from src/main/samples/ folder and push to GitLab.

    Args:
        host: Testinfra host connection.
        catalog_name: Filename (e.g. 'catalog_rhel.json').
        log_callback: Optional logging callback.

    Returns:
        Dict with keys: success, catalog_name, commit_id, error.
    """
    import os

    result = {
        "success": False, "catalog_name": catalog_name,
        "commit_id": "", "error": "",
    }

    def _log(msg):
        if log_callback:
            log_callback(msg)
        else:
            print(f"    | {msg}", flush=True)

    # Resolve catalog path
    # From test/build_stream -> ../../src/main/samples/
    test_dir = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)
    )))
    samples_dir = os.path.normpath(os.path.join(
        test_dir, "..", "..", "src", "main", "samples",
    ))
    catalog_path = os.path.join(samples_dir, catalog_name)

    if not os.path.isfile(catalog_path):
        result["error"] = (
            f"Catalog '{catalog_name}' not found in {samples_dir}. "
            f"Available: {', '.join(os.listdir(samples_dir)) if os.path.isdir(samples_dir) else 'N/A'}"
        )
        return result

    _log(f"Loading catalog from: {catalog_path}")
    try:
        with open(catalog_path, "r", encoding="utf-8") as f:
            content = f.read()
    except (IOError, OSError) as exc:
        result["error"] = f"Failed to read catalog: {exc}"
        return result

    # Add unique identifier to avoid cache hits
    try:
        catalog = json.loads(content)
        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        # Support both "Catalog" (legacy) and "catalog" (current) key names
        cat_key = "Catalog" if "Catalog" in catalog else "catalog"
        if cat_key in catalog:
            id_key = "Identifier" if "Identifier" in catalog[cat_key] else "identifier"
            catalog[cat_key][id_key] = f"image-build-{timestamp}"
        content = json.dumps(catalog, indent=2)
    except json.JSONDecodeError:
        pass  # push raw content if not valid JSON

    _log("Uploading catalog to GitLab...")
    upload = upload_catalog_file(host, content)
    if not upload["success"]:
        result["error"] = f"Upload failed: {upload['error']}"
        return result

    result["success"] = True
    result["commit_id"] = upload.get("commit_id", "")
    _log(f"Catalog '{catalog_name}' uploaded to GitLab")
    return result


def update_job_id_in_config(job_id: str) -> bool:
    """Write the job_id back to test_config.yml.

    Args:
        job_id: UUID string to persist.

    Returns:
        True if successfully written, False otherwise.
    """
    import os
    import re

    test_dir = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)
    )))
    config_path = os.path.join(test_dir, "test_config.yml")

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Replace job_id line (handles empty and populated values)
        content = re.sub(
            r'^(job_id:\s*).*$',
            f'job_id: "{job_id}"',
            content,
            flags=re.MULTILINE,
        )

        with open(config_path, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    except (IOError, OSError):
        return False
