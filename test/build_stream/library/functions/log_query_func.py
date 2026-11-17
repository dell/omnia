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

"""Pipeline log query API (ER-BSM-003) checks, one test case per check.

The suite loads the BuildStream context once (``load_bsm_context``) and
reuses one pipeline-client token, so a test does not pay an SSH vault read
per request. The pipeline client shares the per-client log query budget
(``log_query_rate_limit`` per minute) with the GitLab CI after_script, so
every authenticated request first reserves a slot in a local sliding window
and a stray HTTP 429 is retried once after ``Retry-After``.

The limits come from the target ``build_stream_config.yml`` (built-in
defaults for absent keys; all defaults when one value is invalid, as the
API does). The API reads them once at start, so the container must have been
restarted after they were edited.

The target job is ``pipeline.build_job_id`` (verify-only), else the job of
the deploy or build suite that ran in this session. Every function returns a
result dict with keys: success, fields, failures, blocked.
"""

import json
import threading
import time
import urllib.parse
import uuid
from collections import deque
from typing import Any, Callable, Dict, List, Optional, Tuple

from . import gitlab_api_func, pipeline_monitor_func
from .bsm_api_func import bsm_access_token, load_bsm_context
from .http_func import http_exchange
from .log_func import mark
from .nft_func import jwt_client_id
from ..messages.execute_msgs import STEP_MSGS
from ..vars.execute_vars import (
    BSM_API_GRANT_TYPE,
    BSM_API_JOB_PATH,
    BSM_API_LOGS_PATH,
    BSM_API_TOKEN_PATH,
    BSM_CI_CLIENT_ID_VAR,
    BSM_CI_CLIENT_SECRET_VAR,
    HTTP_TIMEOUT,
    HTTP_UNPROCESSABLE,
    LOG_API_ERRORS,
    LOG_CI_PREVIEW_KEY,
    LOG_CORRELATION_HEADER,
    LOG_INPUT_DEFAULTS,
    LOG_PLAYBOOK_STAGES,
    LOG_RATE_MARGIN,
    LOG_RATE_WINDOW,
    LOG_SCOPE_ALLOWED,
    LOG_SCOPES_DENIED,
    LOG_STAGE_PARAM_MAX,
)

Emit = Callable[[str], None]
# Session state: "client" (API client), "target" (job under test), "ci" (GitLab
# jobs found for it), "disposable" (fixture job, log_fixture_func).
SESSION: Dict[str, Any] = {}
_DEFAULT = object()
# Session pipeline suites whose job carries stage logs, best first: a deploy
# job is the build job of the deployed group and holds all five playbook logs.
_SESSION_SUITES = (("deploy", "deploy_automatic"), ("deploy_manual", "deploy_manual"),
                   ("build", "build_automatic"), ("build_manual", "build_manual"))
_BOUNDS = {
    "log_tail_lines_max": (1, 10000),
    "max_log_response_bytes": (1024, 50 * 1024 * 1024),
    "log_query_rate_limit": (1, None),
    "log_query_max_concurrent": (1, None),
}


# =============================================================================
# Result helpers
# =============================================================================

def new_result() -> Dict[str, Any]:
    """Return an empty step result."""
    return {"success": False, "fields": [], "failures": [], "blocked": False}


def blocked_result(message: str) -> Dict[str, Any]:
    """Return a result for a step that cannot run (the test is skipped)."""
    return {"success": False, "fields": [], "failures": [message], "blocked": True}


def finish(result: Dict[str, Any]) -> Dict[str, Any]:
    """Set success from the failures and return ``result``."""
    result["success"] = not result["failures"]
    return result


def add_check(result: Dict[str, Any], ok: bool, label: str, state: Any,
              failure: str = "") -> bool:
    """Record one checked item as a field (and a failure when not ``ok``)."""
    result["fields"].append((mark(ok, label), str(state)))
    if not ok:
        result["failures"].append(failure or f"{label}: {state}")
    return ok


# =============================================================================
# Settings and session API client
# =============================================================================

def log_settings(config: Dict[str, Any]) -> Dict[str, Any]:
    """Return the effective log query limits for ``build_stream_config.yml`` values.

    Mirrors common/config.py: absent keys keep the default; a non-integer or
    out-of-range value rejects every operator input (defaults stay in effect).
    The CI preview follows the hosted_gitlab BSM_LOG_TAIL_LINES template.
    """
    values = {key: config.get(key, default) for key, default in LOG_INPUT_DEFAULTS.items()}
    invalid = [key for key, value in values.items()
               if isinstance(value, bool) or not isinstance(value, int)]
    if not invalid:
        for key, (low, high) in _BOUNDS.items():
            if values[key] < low or (high is not None and values[key] > high):
                invalid.append(key)
        if not 1 <= values["log_tail_lines_default"] <= values["log_tail_lines_max"]:
            invalid.append("log_tail_lines_default")
    if invalid:
        values = dict(LOG_INPUT_DEFAULTS)
    return {
        "default_tail": values["log_tail_lines_default"],
        "max_tail": values["log_tail_lines_max"],
        "max_bytes": values["max_log_response_bytes"],
        "rate_limit": values["log_query_rate_limit"],
        "max_concurrent": values["log_query_max_concurrent"],
        "ci_preview": config.get(LOG_CI_PREVIEW_KEY,
                                 config.get("log_tail_lines_default",
                                            LOG_INPUT_DEFAULTS["log_tail_lines_default"])),
        "source": (f"defaults (invalid: {', '.join(sorted(set(invalid)))})" if invalid
                   else "build_stream_config.yml"),
    }


def log_api(host: Any) -> Dict[str, Any]:
    """Return the session API client, loading the context and token once.

    Returns:
        Dict with keys: success, error and, on success, context, token,
        client_id, settings, history (request times), lock, retries.
    """
    api = SESSION.get("client")
    if api and api["success"]:
        return api
    context = load_bsm_context(host)
    if not context["success"]:
        return {"success": False, "error": f"BuildStream context: {context['error']}"}
    token = bsm_access_token(context)
    if not token["success"]:
        return {"success": False, "error": f"BuildStream token: {token['error']}"}
    api = {"success": True, "error": "", "context": context, "token": token["token"],
           "client_id": jwt_client_id(token["token"]),
           "settings": log_settings(context["config"]), "history": deque(),
           "lock": threading.Lock(), "retries": 0}
    SESSION["client"] = api
    return api


def reserve(api: Dict[str, Any], count: int) -> None:
    """Wait until ``count`` requests fit in the local rate window."""
    window = LOG_RATE_WINDOW + LOG_RATE_MARGIN
    limit = api["settings"]["rate_limit"]
    history = api["history"]
    while True:
        now = time.monotonic()
        while history and now - history[0] >= window:
            history.popleft()
        if len(history) + count <= limit or not history:
            return
        time.sleep(max(0.1, window - (now - history[0])))


def _send(api: Dict[str, Any], request: Dict[str, Any]) -> Dict[str, Any]:
    """Send one request (method, url, headers, body, budget, timeout).

    A budgeted request is recorded in the local rate window first.
    """
    if request["budget"]:
        with api["lock"]:
            reserve(api, 1)
            api["history"].append(time.monotonic())
    started = time.monotonic()
    response = http_exchange(api["context"]["bsm_tls"], request["method"], request["url"],
                             headers=request["headers"], body=request["body"],
                             timeout=request["timeout"])
    response["elapsed_ms"] = int((time.monotonic() - started) * 1000)
    return response


def retry_after(response: Dict[str, Any]) -> int:
    """Return the integer Retry-After header of a response (0 when absent)."""
    value = str((response.get("headers") or {}).get("retry-after", "")).strip()
    return int(value) if value.isdigit() else 0


def log_request(api: Dict[str, Any], method: str, path: str, **options: Any) -> Dict[str, Any]:
    """Call the BuildStream API with the session client.

    Options: params (query), json_body, form, token (default: session token;
    None: no Authorization header), headers, retry_on_429 (default True),
    budget (default True: reserve a rate-window slot), timeout.

    Returns:
        http_exchange result plus correlation_id and elapsed_ms.
    """
    params = options.get("params")
    correlation_id = str(uuid.uuid4())
    token = options.get("token", _DEFAULT)
    bearer = api["token"] if token is _DEFAULT else token
    request = {
        "method": method, "body": None, "timeout": options.get("timeout", HTTP_TIMEOUT),
        "url": f"{api['context']['bsm_url']}{path}"
               + (f"?{urllib.parse.urlencode(params)}" if params else ""),
        "headers": {LOG_CORRELATION_HEADER: correlation_id, **(options.get("headers") or {})},
        "budget": options.get("budget", True) and bearer is not None,
    }
    if bearer is not None:
        request["headers"]["Authorization"] = f"Bearer {bearer}"
    if options.get("json_body") is not None:
        request["headers"]["Content-Type"] = "application/json"
        request["body"] = json.dumps(options["json_body"]).encode()
    elif options.get("form") is not None:
        request["headers"]["Content-Type"] = "application/x-www-form-urlencoded"
        request["body"] = urllib.parse.urlencode(options["form"]).encode()
    response = _send(api, request)
    if response["status"] == 401 and token is _DEFAULT and _refresh_token(api):
        request["headers"]["Authorization"] = f"Bearer {api['token']}"
        response = _send(api, request)
    if response["status"] == 429 and options.get("retry_on_429", True):
        api["retries"] += 1
        time.sleep(retry_after(response) + LOG_RATE_MARGIN)
        response = _send(api, request)
    response["correlation_id"] = correlation_id
    return response


def _refresh_token(api: Dict[str, Any]) -> bool:
    """Replace an expired session token; return whether a new one was issued."""
    token = bsm_access_token(api["context"])
    if token["success"]:
        api["token"] = token["token"]
    return token["success"]


def logs_path(job_id: str) -> str:
    """Return the log query path of ``job_id``."""
    return BSM_API_LOGS_PATH.format(job_id=job_id)


def job_path(job_id: str) -> str:
    """Return the job detail path of ``job_id``."""
    return BSM_API_JOB_PATH.format(job_id=job_id)


def scoped_token(api: Dict[str, Any], scope: str) -> Dict[str, Any]:
    """Issue a pipeline-client token limited to ``scope`` (secret stays in memory).

    Returns:
        Dict with keys: success, status, token, error.
    """
    context = api["context"]
    client_id = gitlab_api_func.ci_variable_value(context, BSM_CI_CLIENT_ID_VAR)
    secret = gitlab_api_func.ci_variable_value(context, BSM_CI_CLIENT_SECRET_VAR)
    if not client_id["success"] or not secret["success"]:
        return {"success": False, "status": 0, "token": "",
                "error": client_id["error"] or secret["error"]}
    response = log_request(api, "POST", BSM_API_TOKEN_PATH, token=None, form={
        "grant_type": BSM_API_GRANT_TYPE, "client_id": client_id["value"],
        "client_secret": secret["value"], "scope": scope})
    token = (response.get("json") or {}).get("access_token", "")
    return {"success": response["status"] == 200 and bool(token), "status": response["status"],
            "token": token, "error": response["error"] or f"HTTP {response['status']}"}


def detail(response: Dict[str, Any]) -> Dict[str, Any]:
    """Return the ``detail`` object of an error response ({} when absent)."""
    body = response.get("json")
    value = body.get("detail") if isinstance(body, dict) else None
    return value if isinstance(value, dict) else {}


def expect_error(result: Dict[str, Any], label: str, response: Dict[str, Any],
                 key: str, **fmt: Any) -> bool:
    """Check an error response against ``LOG_API_ERRORS[key]``.

    The status, ``detail.error`` and (when defined) ``detail.message`` must
    match; route errors must echo the request correlation ID; no error body
    may carry log content.
    """
    status, code, message = LOG_API_ERRORS[key]
    found = detail(response)
    problems = []
    if response["status"] != status:
        problems.append(f"HTTP {response['status']} (expected {status})")
    if found.get("error") != code:
        problems.append(f"error {found.get('error')!r} (expected {code!r})")
    if message and found.get("message") != message.format(**fmt):
        problems.append(f"message {found.get('message')!r}")
    if "correlation_id" in found and found["correlation_id"] != response["correlation_id"]:
        problems.append("correlation_id is not the request's X-Correlation-Id")
    if "log_content" in (response.get("body") or ""):
        problems.append("error body contains log_content")
    state = f"HTTP {response['status']} {found.get('error', '-')}"
    return add_check(result, not problems, label, state,
                     f"{label}: {'; '.join(problems)}" if problems else "")


# =============================================================================
# Target job
# =============================================================================

def _target_job(settings: Dict[str, Any]) -> Tuple[str, str]:
    """Return (job_id, source) of the job under test ("" when none)."""
    configured = settings["build"]["job_id"]
    if configured:
        return configured, "pipeline.build_job_id"
    for key, suite in _SESSION_SUITES:
        state = pipeline_monitor_func.PIPELINE_STATE.get(key) or {}
        if state.get("job_id") and not state.get("skip_reason"):
            return state["job_id"], f"{suite} in this run"
    return "", ""


def target() -> Optional[Dict[str, Any]]:
    """Return the resolved target job (None before resolve_log_target passed)."""
    return SESSION.get("target")


def _gate() -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Return (api, target); both are None before resolve_log_target passed."""
    job = target()
    api = SESSION.get("client")
    return (api, job) if job and api else (None, None)


def resolve_log_target(host: Any, settings: Dict[str, Any], emit: Emit) -> Dict[str, Any]:
    """Resolve the job under test and the stages that have a published log."""
    SESSION.pop("target", None)
    SESSION.pop("ci", None)
    job_id, source = _target_job(settings)
    if not job_id:
        return blocked_result(STEP_MSGS["log_no_job"])
    result = new_result()
    api = log_api(host)
    if not api["success"]:
        result["failures"].append(api["error"])
        return finish(result)
    limits = api["settings"]
    result["fields"].extend([
        ("Job ID", job_id), ("Source", source), ("Limits from", limits["source"]),
        ("Tail lines", f"default {limits['default_tail']}, max {limits['max_tail']}"),
        ("Max response bytes", limits["max_bytes"]),
        ("Rate / concurrency", f"{limits['rate_limit']}/min, {limits['max_concurrent']} "
                               "concurrent"),
        ("CI preview lines", limits["ci_preview"])])
    response = log_request(api, "GET", job_path(job_id))
    body = response.get("json") if response["status"] == 200 else None
    if not add_check(result, isinstance(body, dict), "GET /jobs/{id}",
                     f"HTTP {response['status']}",
                     STEP_MSGS["log_job_unreadable"].format(job_id=job_id,
                                                            status=response["status"])):
        return finish(result)
    stages = body.get("stages") or []
    has_fields = bool(stages) and all("has_log" in s and "log_lines" in s for s in stages)
    if not add_check(result, has_fields, "has_log/log_lines per stage",
                     "present" if has_fields else "missing",
                     STEP_MSGS["log_feature_missing"].format(job_id=job_id)):
        return finish(result)
    logged = {s["stage_name"]: int(s.get("log_lines") or 0) for s in stages
              if s.get("has_log") and s.get("stage_name") in LOG_PLAYBOOK_STAGES}
    add_check(result, bool(logged), "Stages with a published log",
              ", ".join(f"{name} ({lines})" for name, lines in sorted(logged.items())) or "none",
              STEP_MSGS["log_no_logged_stage"].format(job_id=job_id))
    if logged:
        SESSION["target"] = {"job_id": job_id, "stages": stages, "logged": logged}
        emit(f"log query target: job {job_id} ({source}), {len(logged)} stage log(s)")
    return finish(result)


# =============================================================================
# Read-only API checks (TC-FVT-013, 014, 015, 016, 018)
# =============================================================================

def _entries(body: Any) -> Dict[str, Dict[str, Any]]:
    """Return the stage entries of a log query response by stage name."""
    stages = body.get("stages") if isinstance(body, dict) else None
    return {item.get("stage_name"): item for item in stages or [] if isinstance(item, dict)}


def _ok_body(result: Dict[str, Any], label: str,
             response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Check an HTTP 200 JSON response and return its body (None otherwise)."""
    body = response.get("json") if response["status"] == 200 else None
    ok = isinstance(body, dict)
    add_check(result, ok, label, f"HTTP {response['status']} ({response['elapsed_ms']} ms)")
    return body if ok else None


def _content_lines(entry: Dict[str, Any]) -> int:
    """Return the number of lines in an entry's log_content."""
    content = entry.get("log_content")
    return len(content.split("\n")) if content and entry.get("returned_lines") else 0


def _check_tail(result: Dict[str, Any], entry: Optional[Dict[str, Any]], stage: str,
                lines: int, label: str) -> None:
    """Check one stage entry of a tail query for ``lines`` lines."""
    if entry is None:
        add_check(result, False, f"{stage}: {label}", "stage missing from the response")
        return
    total, returned = int(entry.get("total_lines") or 0), int(entry.get("returned_lines") or 0)
    expected = min(lines, total)
    ok = (entry.get("has_log") is True and returned == expected
          and entry.get("truncated") is (returned < total)
          and _content_lines(entry) == returned and entry.get("unavailable_reason") is None)
    add_check(result, ok, f"{stage}: {label}",
              f"{returned}/{total} lines, truncated={entry.get('truncated')}",
              f"{stage}: {label} returned {returned} of {total} lines (expected {expected}), "
              f"truncated={entry.get('truncated')}, content lines={_content_lines(entry)}, "
              f"reason={entry.get('unavailable_reason')}")


def verify_log_tail(host: Any, settings: Dict[str, Any], emit: Emit) -> Dict[str, Any]:
    """TC-FVT-013: default tail, custom tail and the 1 / max boundaries per stage.

    The default-tail case does not assume a value: the API reports the default
    it applied in the response ``tail_lines`` (query_logs.py sets it from
    ``log_tail_lines_default``), so the per-stage line checks use that. A
    separate check compares the applied default with the operator value read
    from ``build_stream_config.yml``, so a config or restart mismatch is
    reported on its own instead of making every stage look like a full log.
    """
    del host, settings, emit
    api, job = _gate()
    if not job:
        return blocked_result(STEP_MSGS["log_no_target"])
    result = new_result()
    applied = _check_default_tail(api, job, result)
    limits = api["settings"]
    custom = min(100 if applied != 100 else 99, limits["max_tail"])
    for label, tail in ((f"tail_lines={custom}", custom), ("tail_lines=1", 1),
                        (f"tail_lines={limits['max_tail']} (max)", limits["max_tail"])):
        body = _ok_body(result, f"GET /logs {label}", log_request(
            api, "GET", logs_path(job["job_id"]), params={"tail_lines": tail}))
        if body is None:
            continue
        add_check(result, body.get("tail_lines") == tail and body.get("full") is False
                  and body.get("job_id") == job["job_id"], f"{label}: tail_lines / full",
                  f"tail_lines={body.get('tail_lines')}, full={body.get('full')}")
        for stage in sorted(job["logged"]):
            _check_tail(result, _entries(body).get(stage), stage, tail, label)
    return finish(result)


def _check_default_tail(api: Dict[str, Any], job: Dict[str, Any],
                        result: Dict[str, Any]) -> int:
    """Check the omitted-tail_lines default and return the N the API applied.

    Falls back to the configured default only when the response is unusable,
    so the per-stage checks never silently expect the whole log.
    """
    limits = api["settings"]
    body = _ok_body(result, "GET /logs default tail",
                    log_request(api, "GET", logs_path(job["job_id"])))
    if body is None:
        return limits["default_tail"]
    applied = body.get("tail_lines")
    valid = isinstance(applied, int) and not isinstance(applied, bool) \
        and 1 <= applied <= limits["max_tail"]
    add_check(result, valid and body.get("full") is False
              and body.get("job_id") == job["job_id"], "default tail: applied tail_lines",
              f"tail_lines={applied}, full={body.get('full')}")
    add_check(result, applied == limits["default_tail"],
              "default tail = configured log_tail_lines_default",
              f"API applied {applied}, build_stream_config.yml {limits['default_tail']}",
              f"API default {applied} != configured {limits['default_tail']} "
              "(restart omnia_build_stream after editing the config)")
    effective = applied if valid else limits["default_tail"]
    for stage in sorted(job["logged"]):
        _check_tail(result, _entries(body).get(stage), stage, effective, "default tail")
    return effective


def verify_log_full(host: Any, settings: Dict[str, Any], emit: Emit) -> Dict[str, Any]:
    """TC-FVT-014: full=true returns each complete log, bounded by max_log_response_bytes."""
    del host, settings, emit
    api, job = _gate()
    if not job:
        return blocked_result(STEP_MSGS["log_no_target"])
    result = new_result()
    max_bytes = api["settings"]["max_bytes"]
    for stage in sorted(job["logged"]):
        body = _ok_body(result, f"{stage}: GET /logs full=true", log_request(
            api, "GET", logs_path(job["job_id"]), params={"stage": stage, "full": "true"}))
        if body is None:
            continue
        entry = _entries(body).get(stage) or {}
        size = len((entry.get("log_content") or "").encode("utf-8"))
        total, returned = int(entry.get("total_lines") or 0), int(entry.get("returned_lines") or 0)
        complete = entry.get("truncated") or returned == total
        ok = (body.get("full") is True and body.get("tail_lines") is None and complete
              and size <= max_bytes and len(body.get("stages") or []) == 1)
        add_check(result, ok, f"{stage}: complete log",
                  f"{returned}/{total} lines, {size} bytes, truncated={entry.get('truncated')}",
                  f"{stage}: full=true returned {returned} of {total} lines, {size} bytes "
                  f"(limit {max_bytes}), truncated={entry.get('truncated')}, "
                  f"tail_lines={body.get('tail_lines')}")
    return finish(result)


def verify_log_stage_filter(host: Any, settings: Dict[str, Any], emit: Emit) -> Dict[str, Any]:
    """TC-FVT-015: ?stage= returns exactly that stage, with the default or given tail.

    The default-tail sub-case reads the applied N from the response, like
    :func:`_check_default_tail`, so it never expects the whole log.
    """
    del host, settings, emit
    api, job = _gate()
    if not job:
        return blocked_result(STEP_MSGS["log_no_target"])
    result = new_result()
    max_tail = api["settings"]["max_tail"]
    for stage, recorded in sorted(job["logged"].items()):
        default_body = _ok_body(result, f"GET /logs?stage={stage} default tail",
                                log_request(api, "GET", logs_path(job["job_id"]),
                                            params={"stage": stage}))
        if default_body is not None:
            applied = default_body.get("tail_lines")
            lines = applied if isinstance(applied, int) and 1 <= applied <= max_tail \
                else api["settings"]["default_tail"]
            _check_filtered(result, default_body, stage, (lines, recorded), "default tail")
        one_body = _ok_body(result, f"GET /logs?stage={stage} tail_lines=1", log_request(
            api, "GET", logs_path(job["job_id"]), params={"stage": stage, "tail_lines": 1}))
        if one_body is not None:
            _check_filtered(result, one_body, stage, (1, recorded), "tail_lines=1")
    return finish(result)


def _check_filtered(result: Dict[str, Any], body: Dict[str, Any], stage: str,
                    counts: Tuple[int, int], label: str) -> None:
    """Check a stage-filtered response: only ``stage``, its tail, and the recorded length."""
    lines, recorded = counts
    names = [str(item.get("stage_name")) for item in body.get("stages") or []]
    add_check(result, names == [stage], f"{stage}: only this stage", ", ".join(names))
    entry = _entries(body).get(stage)
    _check_tail(result, entry, stage, lines, label)
    total = (entry or {}).get("total_lines")
    add_check(result, total == recorded, f"{stage}: total_lines = GET /jobs log_lines",
              f"{total} / {recorded}")


def verify_log_errors(host: Any, settings: Dict[str, Any], emit: Emit) -> Dict[str, Any]:
    """TC-FVT-016 (read-only scenarios): the documented error contract."""
    del host, settings, emit
    api, job = _gate()
    if not job:
        return blocked_result(STEP_MSGS["log_no_target"])
    result = new_result()
    path = logs_path(job["job_id"])
    max_tail = api["settings"]["max_tail"]
    cases = [
        ("unknown job", logs_path(str(uuid.uuid4())), None, "job_not_found"),
        ("malformed job_id", logs_path("nonexistent"), None, "invalid_job_id"),
        ("unknown stage", path, {"stage": "nonexistent-stage"}, "stage_not_found"),
        ("tail_lines=0", path, {"tail_lines": 0}, "tail_range"),
        (f"tail_lines={max_tail + 1}", path, {"tail_lines": max_tail + 1}, "tail_range"),
        ("full and tail_lines", path, {"full": "true", "tail_lines": 10}, "full_and_tail"),
    ]
    for label, target_path, params, key in cases:
        expect_error(result, label, log_request(api, "GET", target_path, params=params),
                     key, max=max_tail)
    for label, params in ((f"stage longer than {LOG_STAGE_PARAM_MAX}",
                           {"stage": "x" * (LOG_STAGE_PARAM_MAX + 1)}),
                          ("tail_lines=abc", {"tail_lines": "abc"})):
        response = log_request(api, "GET", path, params=params)
        add_check(result, response["status"] == HTTP_UNPROCESSABLE
                  and "log_content" not in (response.get("body") or ""),
                  label, f"HTTP {response['status']}")
    for label, token, key in (("no Authorization header", None, "missing_token"),
                              ("malformed token", "not-a-jwt", "invalid_token")):
        expect_error(result, label, log_request(api, "GET", path, token=token), key)
    return finish(result)


def verify_log_scopes(host: Any, settings: Dict[str, Any], emit: Emit) -> Dict[str, Any]:
    """Scope rule: job:read or job:write is required (403 insufficient_scope otherwise).

    A token limited to a catalog scope must be refused; a job:write token (the
    CI pipeline client's grant) must be served. Staging aligned the log route
    with the other job endpoints (PR #5820); this is the only automated check
    that a catalog-only token cannot read another's pipeline logs.
    """
    del host, settings, emit
    api, job = _gate()
    if not job:
        return blocked_result(STEP_MSGS["log_no_target"])
    result = new_result()
    path = logs_path(job["job_id"])
    for scope in LOG_SCOPES_DENIED:
        issued = scoped_token(api, scope)
        if add_check(result, issued["success"], f"{scope} token", f"HTTP {issued['status']}",
                     f"{scope} token not issued: {issued['error']}"):
            expect_error(result, f"{scope}: GET /logs",
                         log_request(api, "GET", path, token=issued["token"]),
                         "insufficient_scope")
    issued = scoped_token(api, LOG_SCOPE_ALLOWED)
    if add_check(result, issued["success"], f"{LOG_SCOPE_ALLOWED} token",
                 f"HTTP {issued['status']}", f"token not issued: {issued['error']}"):
        _ok_body(result, f"{LOG_SCOPE_ALLOWED}: GET /logs",
                 log_request(api, "GET", path, token=issued["token"]))
    return finish(result)


def verify_log_job_metadata(host: Any, settings: Dict[str, Any], emit: Emit) -> Dict[str, Any]:
    """TC-FVT-018: GET /jobs has_log/log_lines agree with the log query API."""
    del host, settings, emit
    api, job = _gate()
    if not job:
        return blocked_result(STEP_MSGS["log_no_target"])
    result = new_result()
    job_body = _ok_body(result, "GET /jobs/{id}",
                        log_request(api, "GET", job_path(job["job_id"])))
    logs = _ok_body(result, "GET /logs", log_request(api, "GET", logs_path(job["job_id"])))
    if job_body is None or logs is None:
        return finish(result)
    entries = _entries(logs)
    for stage in job_body.get("stages") or []:
        name = stage.get("stage_name")
        has_log, lines = stage.get("has_log"), stage.get("log_lines")
        entry = entries.get(name) or {}
        if name not in LOG_PLAYBOOK_STAGES:
            ok = has_log is False and lines == 0
        elif has_log:
            ok = entry.get("has_log") is True and lines == entry.get("total_lines")
        else:
            ok = lines == 0 and entry.get("has_log") is not True
        add_check(result, ok, f"{name}", f"has_log={has_log}, log_lines={lines}, "
                  f"logs API total_lines={entry.get('total_lines', '-')}")
    return finish(result)


def session_pipeline_ids(job_id: str) -> List[int]:
    """Return GitLab pipeline IDs the session suites ran for ``job_id``."""
    ids: List[int] = []
    for key, _suite in _SESSION_SUITES:
        state = pipeline_monitor_func.PIPELINE_STATE.get(key) or {}
        if state.get("job_id") != job_id:
            continue
        for value in (*(state.get("watched") or []), state.get("child_id"),
                      state.get("select_pipeline")):
            if value and int(value) not in ids:
                ids.append(int(value))
    return ids
