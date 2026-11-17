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
import re
import shlex
import time
import urllib.parse
import uuid
from pathlib import PurePosixPath
from typing import Any, Dict, Optional, Tuple, TypedDict, Unpack

from omnia_auto import run_on_host

from library.functions import gitlab_api_func
from library.functions.bsm_api_func import bsm_access_token, get_api_job, load_bsm_context
from library.functions.config_func import installation_settings
from library.functions.pipeline_trigger_func import _trigger_build
from library.functions._config_helpers import (
    resolve_omnia_data_path,
    resolve_omnia_path,
)
from library.functions.build_stream_func import check_build_stream_health
from library.functions.http_func import http_exchange, multipart_body
from library.vars.execute_vars import (
    BSM_API_PREFIX,
    BSM_CI_CLIENT_ID_VAR,
    BSM_CI_CLIENT_SECRET_VAR,
    GITLAB_BRIDGE_BUILD,
)


# test_config.yml of this domain (library/functions/ -> domain root).
OVERSIZED_UPLOAD_BYTES = 5 * 1024 * 1024 + 1
TEST_CONFIG_PATH = str(PurePosixPath(__file__).parents[2] / "test_config.yml")


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
    context = load_bsm_context(host)
    if not context["success"]:
        return {"success": False, "base_url": "", "token": "", "client_id": "",
                "context": context, "error": context["error"]}
    token = bsm_access_token(context)
    client_id = _jwt_client_id(token["token"])
    success = token["success"] and bool(client_id)
    return {
        "success": success,
        "base_url": f"{context['bsm_url']}{BSM_API_PREFIX}",
        "token": token["token"],
        "client_id": client_id,
        "context": context,
        "error": "" if success else (token["error"] or "BSM OAuth token has no client ID"),
    }


class BsmRequestOptions(TypedDict, total=False):
    """Optional ``bsm_request`` keywords."""

    token: Optional[str]
    json_body: Optional[dict]
    form_body: Optional[Dict[str, str]]
    headers: Optional[Dict[str, str]]


def _request_body(options: BsmRequestOptions) -> Tuple[Optional[bytes], Dict[str, str]]:
    """Return the body and headers of one BSM request (secrets stay in memory)."""
    headers = dict(options.get("headers") or {})
    token, json_body = options.get("token"), options.get("json_body")
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    if json_body is not None:
        headers["Content-Type"] = "application/json"
        return json.dumps(json_body, separators=(",", ":")).encode(), headers
    form_body = options.get("form_body")
    if form_body:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        return urllib.parse.urlencode(form_body).encode(), headers
    return None, headers


def bsm_request(host, method: str, path: str,
                **options: Unpack[BsmRequestOptions]) -> Dict[str, Any]:
    """Execute one bounded BSM request and return body plus HTTP status.

    ``options`` takes token (bearer, None = no Authorization header),
    json_body, form_body and headers.
    """
    context = get_bsm_context(host)
    if not context["base_url"]:
        return {
            "success": False, "status": 0, "body": "", "json": None,
            "error": context["error"],
        }
    body, headers = _request_body(options)
    return http_exchange(context["context"]["bsm_tls"], method.upper(),
                         f"{context['base_url']}{path}", headers=headers, body=body)


def get_scoped_token(host, scope: str) -> Dict[str, Any]:
    """Request a token restricted to one allowed OAuth scope.

    The pipeline client stored in GitLab CI/CD is used; its secret stays in
    this process and is never logged.
    """
    context = get_bsm_context(host)
    if not context["base_url"]:
        return {"success": False, "token": "", "error": "OAuth context unavailable"}
    client_id = gitlab_api_func.ci_variable_value(context["context"], BSM_CI_CLIENT_ID_VAR)
    client_secret = gitlab_api_func.ci_variable_value(context["context"],
                                                      BSM_CI_CLIENT_SECRET_VAR)
    if not client_id["success"] or not client_secret["success"]:
        return {"success": False, "token": "", "error": "OAuth variables unavailable"}
    client_id, client_secret = client_id["value"], client_secret["value"]
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
    return _upload(host, job_id, token, [("files", filename, content.encode())])


def _upload(host, job_id: str, token: str, files, timeout: int = 30) -> Dict[str, Any]:
    """PUT ``files`` as multipart/form-data to the job upload endpoint."""
    context = get_bsm_context(host)
    if not context["base_url"]:
        return {"success": False, "status": 0, "body": "", "json": None,
                "error": context["error"]}
    body, content_type = multipart_body(files)
    headers = {"Authorization": f"Bearer {token}", "X-Correlation-ID": str(uuid.uuid4()),
               "Content-Type": content_type}
    return http_exchange(context["context"]["bsm_tls"], "PUT",
                         f"{context['base_url']}/jobs/{job_id}/upload",
                         headers=headers, body=body, timeout=timeout)


def upload_oversized_file(host, job_id: str, token: str) -> Dict[str, Any]:
    """Upload a 5 MiB + 1 byte file built in memory (nothing is written to disk)."""
    return _upload(host, job_id, token,
                   [("files", "build_stream_config.yml", bytes(OVERSIZED_UPLOAD_BYTES))],
                   timeout=60)


def _gitlab_context(host) -> Dict[str, Any]:
    """Return the GitLab/BuildStream context, raising on failure."""
    context = load_bsm_context(host)
    if not context["success"]:
        raise RuntimeError(f"BuildStream context unavailable: {context['error']}")
    return context


def pipeline_status(host, pipeline_id: int) -> Dict[str, Any]:
    """Read one GitLab pipeline status."""
    try:
        context = _gitlab_context(host)
    except RuntimeError as exc:
        return {"success": False, "status": "", "error": str(exc)}
    pipeline = gitlab_api_func.get_pipeline(context, pipeline_id)
    if not pipeline:
        return {"success": False, "status": "", "error": f"cannot read pipeline #{pipeline_id}"}
    return {"success": True, "status": pipeline.get("status", ""), "error": ""}


def cancel_nft_pipeline(host, pipeline_id: int) -> Dict[str, Any]:
    """Cancel one test-created GitLab pipeline."""
    try:
        context = _gitlab_context(host)
    except RuntimeError as exc:
        return {"success": False, "error": str(exc)}
    response = gitlab_api_func.cancel_pipeline(context, pipeline_id)
    return {"success": response["success"], "error": response.get("error", "")}


def build_child_pipeline_id(host, pipeline_id: int) -> Dict[str, Any]:
    """Return the build child pipeline that ``pipeline_id`` triggered."""
    try:
        context = _gitlab_context(host)
    except RuntimeError as exc:
        return {"success": False, "child_pipeline_id": 0, "error": str(exc)}
    child = gitlab_api_func.downstream_pipeline(context, pipeline_id, GITLAB_BRIDGE_BUILD)
    return {"success": bool(child), "child_pipeline_id": int(child.get("id", 0) or 0),
            "error": "" if child else f"pipeline #{pipeline_id} has no build child pipeline"}


def trigger_catalog_job(host, config: Dict[str, Any], emit) -> Dict[str, Any]:
    """Commit installation.catalog (next unused version) and return its pipeline and job.

    This is the automatic build trigger of the execute suite, so the NFT
    creates a job exactly as a catalog commit does.
    """
    try:
        context = _gitlab_context(host)
    except RuntimeError as exc:
        return {"success": False, "pipeline_id": 0, "job_id": "", "error": str(exc)}
    result: Dict[str, Any] = {"fields": [], "failures": []}
    ids = _trigger_build(host, context, installation_settings(config), result, emit)
    return {"success": not ids["error"], "pipeline_id": int(ids.get("pipeline_id") or 0),
            "job_id": ids.get("job_id", ""), "error": ids["error"]}


def get_bsm_job_details(host, job_id: str) -> Dict[str, Any]:
    """Read one job through the BuildStream API.

    Returns:
        Dict with keys: success, job (job_id, job_state, stages), error.
    """
    try:
        context = _gitlab_context(host)
    except RuntimeError as exc:
        return {"success": False, "job": {}, "error": str(exc)}
    api = get_api_job(context, job_id)
    job = {"job_id": api.get("job_id", ""), "job_state": api["job_state"],
           "stages": list(api["stages"])}
    return {"success": api["success"], "job": job if api["success"] else {},
            "error": api["error"]}


def update_job_id_in_config(job_id: str, config_path: str = TEST_CONFIG_PATH) -> bool:
    """Write ``job_id`` to the top-level job_id key of test_config.yml."""
    with open(config_path, encoding="utf-8") as stream:
        content = stream.read()
    content, replacements = re.subn(r'^(job_id:\s*).*$', f'job_id: "{job_id}"', content,
                                    flags=re.MULTILINE)
    if replacements != 1:
        return False
    with open(config_path, "w", encoding="utf-8") as stream:
        stream.write(content)
    return True


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
    queue_path = resolve_omnia_path(host, "build_stream", "playbook_queue")
    command = (
        f"find {shlex.quote(f'{queue_path}/requests')} "
        f"{shlex.quote(f'{queue_path}/processing')} -maxdepth 1 -type f "
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
    pending_path = (
        f"{resolve_omnia_path(host, 'build_stream', 'playbook_queue', 'requests')}/{entry}"
    )
    while time.monotonic() < deadline:
        pending = run_on_host(host, f"test -e {shlex.quote(pending_path)}")
        if pending.rc != 0:
            return {"success": True, "error": ""}
        time.sleep(2)
    return {"success": False, "error": f"Watcher did not claim {entry}"}


def artifact_path_absent(host, job_id: str, filename: str) -> bool:
    """Confirm one rejected upload did not appear in the job artifact directory."""
    safe_filename = shlex.quote(filename)
    artifact_path = resolve_omnia_path(
        host, "build_stream", "build_stream_root", "artifacts", job_id
    )
    command = (
        f"test ! -e {shlex.quote(artifact_path)}/{safe_filename}"
    )
    return run_on_host(host, command).rc == 0


def forbidden_upload_absent(host, basename: str) -> bool:
    """Confirm a rejected traversal upload created no file under Omnia data."""
    omnia_data_path = resolve_omnia_data_path(host)
    command = (
        f"find {shlex.quote(omnia_data_path)} -xdev -type f "
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
