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
"""Operational resilience and live API security helpers for BuildStream NFT."""

import base64
import json
import shlex
import time
import uuid
from pathlib import PurePosixPath
from typing import Any, Dict, Optional

from omnia_auto import run_on_host

from library.functions import pipeline_func
from library.functions.build_stream_func import check_build_stream_health
from library.vars.common_vars import CMDS


def _parse_http_response(output: str) -> Dict[str, Any]:
    """Split a curl body followed by its numeric HTTP status."""
    body, separator, status_text = (output or "").rpartition("\n")
    if not separator or not status_text.strip().isdigit():
        return {
            "success": False,
            "status": 0,
            "body": body,
            "json": None,
            "error": "HTTP response did not contain a status code",
        }
    parsed = None
    if body.strip():
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            parsed = None
    return {
        "success": True,
        "status": int(status_text.strip()),
        "body": body,
        "json": parsed,
        "error": "",
    }


def _jwt_client_id(token: str) -> str:
    """Read the non-secret client identifier claim without validating the JWT."""
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload).decode("utf-8"))
        # BSM JWTs store the OAuth client identifier in the standard ``sub``
        # claim. Retain ``client_id`` as a compatibility fallback for tokens
        # issued by older deployments.
        return str(data.get("sub") or data.get("client_id", ""))
    except (IndexError, ValueError, UnicodeError, json.JSONDecodeError):
        return ""


def get_bsm_context(host) -> Dict[str, Any]:
    """Return the installed BSM endpoint, token, and authenticated client ID."""
    config = pipeline_func._get_gitlab_config(host)  # pylint: disable=protected-access
    token = pipeline_func._get_bsm_access_token(host)  # pylint: disable=protected-access
    hostname = config.get("build_stream_host_ip", "")
    port = config.get("build_stream_port", "")
    client_id = _jwt_client_id(token)
    success = bool(hostname and port and token and client_id)
    return {
        "success": success,
        "base_url": f"https://{hostname}:{port}/api/v1" if hostname and port else "",
        "token": token,
        "client_id": client_id,
        "error": "" if success else "BSM endpoint or OAuth credentials unavailable",
    }


def bsm_request(
    host,
    method: str,
    path: str,
    token: Optional[str] = None,
    json_body: Optional[dict] = None,
    form_body: Optional[Dict[str, str]] = None,
    headers: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Execute one bounded BSM request and return body plus HTTP status."""
    # pylint: disable=too-many-arguments,too-many-positional-arguments
    context = get_bsm_context(host)
    if not context["base_url"]:
        return {
            "success": False, "status": 0, "body": "", "json": None,
            "error": context["error"],
        }
    parts = [
        "curl", "-sk", "--max-time", "30", "-X", method.upper(),
        "-w", "\n%{http_code}",
    ]
    if token is not None:
        parts.extend(["-H", f"Authorization: Bearer {token}"])
    if headers:
        for name, value in headers.items():
            parts.extend(["-H", f"{name}: {value}"])
    if json_body is not None:
        parts.extend(["-H", "Content-Type: application/json"])
        parts.extend(["--data", json.dumps(json_body, separators=(",", ":"))])
    if form_body:
        for name, value in form_body.items():
            parts.extend(["--data-urlencode", f"{name}={value}"])
    parts.append(f"{context['base_url']}{path}")
    command = shlex.join(parts)
    response = run_on_host(host, command)
    if response.rc != 0:
        return {
            "success": False, "status": 0, "body": response.stdout or "",
            "json": None, "error": f"curl failed with rc={response.rc}",
        }
    return _parse_http_response(response.stdout)


def get_scoped_token(host, scope: str) -> Dict[str, Any]:
    """Request a token restricted to one allowed OAuth scope."""
    context = get_bsm_context(host)
    api_base = pipeline_func._get_gitlab_api_base(host)  # pylint: disable=protected-access
    if not context["success"] or not api_base["success"]:
        return {"success": False, "token": "", "error": "OAuth context unavailable"}
    command = CMDS["gitlab_api_list_variables"].format(
        token=api_base["token"], api_url=api_base["api_url"],
        project_id=api_base["project_id"],
    )
    variables_response = run_on_host(host, command)
    try:
        variables = json.loads(variables_response.stdout or "[]")
        values = {item["key"]: item["value"] for item in variables}
        client_id = values["BSM_CLIENT_ID"]
        client_secret = values["BSM_CLIENT_SECRET"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return {"success": False, "token": "", "error": "OAuth variables unavailable"}
    response = bsm_request(
        host, "POST", "/auth/token", token=None,
        form_body={
            "grant_type": "client_credentials", "client_id": client_id,
            "client_secret": client_secret, "scope": scope,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token = response.get("json", {}).get("access_token", "") if response.get("json") else ""
    return {
        "success": response.get("status") == 200 and bool(token),
        "token": token,
        "error": response.get("error") or response.get("body", ""),
    }


def create_disposable_job(host, token: Optional[str] = None) -> Dict[str, Any]:
    """Create one uniquely identified job for mutation security checks."""
    context = get_bsm_context(host)
    selected_token = context["token"] if token is None else token
    request_id = str(uuid.uuid4())
    response = bsm_request(
        host, "POST", "/jobs", token=selected_token,
        json_body={
            "client_id": context["client_id"],
            "client_name": "omnia-nft-security",
            "metadata": {"purpose": "security-nft", "request_id": request_id},
        },
        headers={
            "Idempotency-Key": request_id,
            "X-Correlation-ID": request_id,
        },
    )
    job_id = response.get("json", {}).get("job_id", "") if response.get("json") else ""
    response["job_id"] = job_id
    return response


def upload_inline_file(
    host, job_id: str, filename: str, content: str, token: str
) -> Dict[str, Any]:
    """Upload controlled inline content with an explicitly supplied filename."""
    context = get_bsm_context(host)
    request_id = str(uuid.uuid4())
    parts = [
        "curl", "-sk", "--max-time", "30", "-X", "PUT",
        "-H", f"Authorization: Bearer {token}",
        "-H", f"X-Correlation-ID: {request_id}",
        "-F", f"files={content};filename={filename}",
        "-w", "\n%{http_code}",
        f"{context['base_url']}/jobs/{job_id}/upload",
    ]
    result = run_on_host(host, shlex.join(parts))
    if result.rc != 0:
        return {"success": False, "status": 0, "body": "", "error": f"curl rc={result.rc}"}
    return _parse_http_response(result.stdout)


def upload_oversized_file(host, job_id: str, token: str) -> Dict[str, Any]:
    """Upload a 5 MiB + 1 byte file and remove the temporary source afterward."""
    context = get_bsm_context(host)
    temp_result = run_on_host(host, "mktemp -t bsm_nft_oversized_XXXXXXXX.yml")
    temp_path = (temp_result.stdout or "").strip()
    valid_path = (
        temp_result.rc == 0
        and bool(temp_path)
        and "\n" not in temp_path
        and PurePosixPath(temp_path).name.startswith("bsm_nft_oversized_")
    )
    if not valid_path:
        return {
            "success": False,
            "status": 0,
            "body": "",
            "error": "Cannot create temporary test file",
        }
    try:
        create_result = run_on_host(
            host, f"head -c 5242881 /dev/zero > {shlex.quote(temp_path)}"
        )
        if create_result.rc != 0:
            return {
                "success": False,
                "status": 0,
                "body": "",
                "error": "Cannot create test payload",
            }
        parts = [
            "curl", "-sk", "--max-time", "60", "-X", "PUT",
            "-H", f"Authorization: Bearer {token}",
            "-H", f"X-Correlation-ID: {uuid.uuid4()}",
            "-F", f"files=@{temp_path};filename=build_stream_config.yml",
            "-w", "\n%{http_code}",
            f"{context['base_url']}/jobs/{job_id}/upload",
        ]
        response = run_on_host(host, shlex.join(parts))
        if response.rc != 0:
            return {"success": False, "status": 0, "body": "", "error": f"curl rc={response.rc}"}
        return _parse_http_response(response.stdout)
    finally:
        run_on_host(host, f"rm -f -- {shlex.quote(temp_path)}")


def pipeline_status(host, pipeline_id: int) -> Dict[str, Any]:
    """Read one GitLab pipeline status."""
    api_base = pipeline_func._get_gitlab_api_base(host)  # pylint: disable=protected-access
    if not api_base["success"]:
        return {"success": False, "status": "", "error": api_base["error"]}
    command = CMDS["gitlab_api_pipeline_status"].format(
        token=api_base["token"], api_url=api_base["api_url"],
        project_id=api_base["project_id"], pipeline_id=int(pipeline_id),
    )
    response = run_on_host(host, command)
    try:
        data = json.loads(response.stdout or "{}")
    except json.JSONDecodeError:
        return {"success": False, "status": "", "error": "Invalid pipeline response"}
    return {"success": response.rc == 0, "status": data.get("status", ""), "error": ""}


def trigger_catalog_job(
    host, catalog_path: str, job_wait_timeout: int = 300,
) -> Dict[str, Any]:
    """Push one uniquely rendered catalog and return only its new pipeline/job."""
    pipelines = pipeline_func.list_pipelines(host, per_page=5)
    if not pipelines["success"]:
        return {"success": False, "error": pipelines["error"]}
    initial_pipeline_id = (
        int(pipelines["pipelines"][0].get("id", 0))
        if pipelines.get("pipelines") else 0
    )
    latest_job = pipeline_func.get_latest_job(host)
    initial_job_id = latest_job.get("job_id", "") if latest_job.get("success") else ""
    pushed = pipeline_func.push_catalog_from_examples(host, catalog_path)
    if not pushed["success"]:
        return {"success": False, "error": pushed["error"]}
    return pipeline_func.trigger_build_pipeline_auto(
        host, initial_pipeline_id=initial_pipeline_id,
        initial_job_id=initial_job_id,
        job_wait_timeout=job_wait_timeout,
    )


def wait_for_pipeline_status(
    host, pipeline_id: int, expected: set[str], timeout: int
) -> Dict[str, Any]:
    """Poll until one GitLab pipeline reaches an expected status."""
    deadline = time.monotonic() + timeout
    latest = ""
    while time.monotonic() < deadline:
        result = pipeline_status(host, pipeline_id)
        latest = result.get("status", "")
        if result["success"] and latest in expected:
            return result
        time.sleep(2)
    return {"success": False, "status": latest, "error": "Pipeline status timeout"}


def restart_service(
    host, service: str, timeout: int, require_health: bool = False
) -> Dict[str, Any]:
    """Restart an allowlisted service and wait for active/healthy state."""
    allowed = {"omnia_build_stream.service", "playbook-watcher.service"}
    if service not in allowed:
        return {"success": False, "error": f"Service is not allowlisted: {service}"}
    restarted = run_on_host(host, f"systemctl restart {service}")
    if restarted.rc != 0:
        return {"success": False, "error": f"Unable to restart {service}"}
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        active = run_on_host(host, f"systemctl is-active {service}")
        if active.rc == 0 and active.stdout.strip() == "active":
            if not require_health or check_build_stream_health(host)["success"]:
                return {"success": True, "error": ""}
        time.sleep(2)
    return {"success": False, "error": f"{service} did not recover within {timeout}s"}


def stop_service(host, service: str) -> Dict[str, Any]:
    """Stop the watcher service for a controlled queue-recovery test."""
    if service != "playbook-watcher.service":
        return {"success": False, "error": f"Service is not allowlisted: {service}"}
    stopped = run_on_host(host, f"systemctl stop {service}")
    if stopped.rc != 0:
        return {"success": False, "error": f"Unable to stop {service}"}
    active = run_on_host(host, f"systemctl is-active {service}")
    if active.stdout.strip() not in {"inactive", "failed"}:
        return {"success": False, "error": f"{service} did not stop"}
    return {"success": True, "error": ""}


def wait_for_queue_entry(host, job_id: str, timeout: int) -> Dict[str, Any]:
    """Wait for the exact NFT job request and return its queue filename."""
    deadline = time.monotonic() + timeout
    command = (
        "find /opt/omnia/playbook_queue/requests "
        "/opt/omnia/playbook_queue/processing -maxdepth 1 -type f "
        f"-name {shlex.quote(f'{job_id}_*.json')} "
        "-printf '%f\\n' 2>/dev/null | sort -u"
    )
    while time.monotonic() < deadline:
        response = run_on_host(host, command)
        names = [line for line in response.stdout.splitlines() if line.strip()]
        if names:
            return {"success": True, "entry": names[0], "error": ""}
        time.sleep(2)
    return {
        "success": False, "entry": "",
        "error": f"No queued request observed for job {job_id}",
    }


def wait_for_queue_claimed(host, entry: str, timeout: int) -> Dict[str, Any]:
    """Wait until the restarted watcher removes one request from pending."""
    deadline = time.monotonic() + timeout
    pending_path = f"/opt/omnia/playbook_queue/requests/{entry}"
    while time.monotonic() < deadline:
        pending = run_on_host(host, f"test -e {shlex.quote(pending_path)}")
        if pending.rc != 0:
            return {"success": True, "error": ""}
        time.sleep(2)
    return {"success": False, "error": f"Watcher did not claim {entry}"}


def artifact_path_absent(host, job_id: str, filename: str) -> bool:
    """Confirm one rejected upload did not appear in the job artifact directory."""
    safe_filename = shlex.quote(filename)
    command = (
        "test ! -e /opt/omnia/build_stream_root/artifacts/"
        f"{shlex.quote(job_id)}/{safe_filename}"
    )
    return run_on_host(host, command).rc == 0


def forbidden_upload_absent(host, basename: str) -> bool:
    """Confirm a rejected traversal upload created no file under Omnia data."""
    command = (
        "find /opt/omnia -xdev -type f "
        f"-name {shlex.quote(basename)} -print -quit 2>/dev/null"
    )
    result = run_on_host(host, command)
    return result.rc == 0 and not result.stdout.strip()


def secret_absent_from_bsm_logs(host, canary: str) -> bool:
    """Return whether a canary value is absent from recent BSM logs."""
    command = (
        "podman logs --tail 2000 omnia_build_stream 2>&1 | "
        f"grep -F -- {shlex.quote(canary)}"
    )
    return run_on_host(host, command).rc != 0
