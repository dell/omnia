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

"""Log query checks on fixture logs of one disposable job (ER-BSM-003).

Enabled only by ``nft_allow_security_mutation: true``. The suite creates one
job (client_name ``omnia-fvt-log-query``) with the pipeline client, writes
synthetic ``fvt_*.log`` files into its log directory (mode 0644; the file
mode and SELinux label are checked against the directory, like the
watcher's published copies) and points ``job_stages.log_file_path`` at
them. Only that job's rows and files are changed; every update is read back
(``RETURNING``) so a missing row is reported instead of being ignored.

Teardown (``release_log_fixture_job``) removes the fixture files and resets
every stage row and the owner. The job row itself stays,
labelled, like the security NFT jobs. No real secret is ever written.
"""

import base64
import math
import posixpath
import threading
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from omnia_auto import load_test_config, log

from . import db_func, gitlab_api_func
from .execute_probe_func import data_path, run_cmd
from .log_redaction_func import mode_and_label
from .log_query_func import (
    SESSION, add_check, blocked_result, detail, expect_error, finish, job_path, log_api,
    log_request, logs_path, new_result, reserve, retry_after)
from ..messages.execute_msgs import STEP_MSGS
from ..vars.execute_vars import (
    BSM_JOB_LOG_ROOT,
    CLIENT_ID_RE,
    LOG_API_ERRORS,
    LOG_API_JOB_LOG,
    LOG_AUDIT_409,
    LOG_BINARY_FIXTURE,
    LOG_CONCURRENCY_ATTEMPTS,
    LOG_CONCURRENCY_FACTOR,
    LOG_CONCURRENCY_FIXTURE_BYTES,
    LOG_FIXTURE_NAME_RE,
    LOG_FIXTURE_WIDTH,
    LOG_FOREIGN_CLIENT_ID,
    LOG_FVT_CLIENT_NAME,
    LOG_HTTP_TIMEOUT,
    LOG_PLAIN_FIXTURE,
    LOG_PLAYBOOK_STAGES,
    LOG_RATE_MARGIN,
    LOG_RATE_WINDOW,
    LOG_REASON_MISSING,
    LOG_REASON_NOT_PUBLISHED,
    LOG_REASON_NOT_RECORDED,
    LOG_REASON_NOT_TEXT,
    LOG_REASON_NOT_YET,
    LOG_REDACTION_EXPECTED,
    LOG_REDACTION_FIXTURE,
    LOG_REDACTION_SECRETS,
    LOG_SECURITY_EVENT,
    LOG_STORED_PATH_RE,
    PLAYBOOK_LOG_BASE_DIR,
    SQL,
    UUID_RE,
)

Emit = Callable[[str], None]
_STAGE_STATES = ("PENDING", "COMPLETED")
_RESET = ("PENDING", None)


# =============================================================================
# Disposable job and fixture files
# =============================================================================

def _mutation_gate() -> Optional[Dict[str, Any]]:
    """Return a blocked result unless nft_allow_security_mutation is true."""
    if load_test_config().get("nft_allow_security_mutation", False) is not True:
        return blocked_result(STEP_MSGS["log_mutation_disabled"])
    return None


def _guard(value: str, pattern: Any, label: str) -> str:
    """Return ``value`` when it fully matches ``pattern`` (SQL/shell guard)."""
    if not pattern.fullmatch(value or ""):
        raise ValueError(f"invalid {label}: {value!r}")
    return value


def _update(host: Any, sql_key: str, expected: str, **values: str) -> Dict[str, Any]:
    """Run one RETURNING update and check the row was changed."""
    result = db_func.query(host, SQL[sql_key].format(**values))
    changed = any(row and row[0].strip() == expected for row in result["rows"])
    error = result["error"] or ("" if changed else f"no row matched ({sql_key})")
    return {"success": result["success"] and changed, "error": error}


def set_stage(host: Any, job_id: str, stage: str, state: str,
              path: Optional[str]) -> Dict[str, Any]:
    """Set one stage row of the disposable job (state and log_file_path)."""
    if state not in _STAGE_STATES or stage not in LOG_PLAYBOOK_STAGES:
        raise ValueError(f"unsupported stage update: {stage}={state}")
    literal = "NULL" if path is None else f"'{_guard(path, LOG_STORED_PATH_RE, 'path')}'"
    return _update(host, "log_stage_set", stage, state=state, path=literal, stage=stage,
                   job_id=_guard(job_id, UUID_RE, "job_id"))


def _set_owner(host: Any, job_id: str, client_id: str) -> Dict[str, Any]:
    """Set jobs.client_id of the disposable job."""
    return _update(host, "log_job_owner_set", job_id,
                   client_id=_guard(client_id, CLIENT_ID_RE, "client_id"),
                   job_id=_guard(job_id, UUID_RE, "job_id"))


def fixture_job(host: Any, emit: Emit) -> Dict[str, Any]:
    """Return the disposable job, creating it once per session.

    Returns:
        Dict with keys: success, error and, on success, job_id, directory,
        client_id.
    """
    if SESSION.get("disposable"):
        return SESSION["disposable"]
    api = log_api(host)
    if not api["success"]:
        return {"success": False, "error": api["error"]}
    request_id = str(uuid.uuid4())
    response = log_request(api, "POST", "/api/v1/jobs", json_body={
        "client_id": api["client_id"], "client_name": LOG_FVT_CLIENT_NAME,
        "metadata": {"purpose": "log-observability-fvt", "request_id": request_id}},
        headers={"Idempotency-Key": request_id})
    job_id = str((response.get("json") or {}).get("job_id", ""))
    if response["status"] != 201 or not UUID_RE.fullmatch(job_id):
        return {"success": False, "error": STEP_MSGS["log_fixture_job_failed"].format(
            error=f"POST /api/v1/jobs returned HTTP {response['status']}")}
    stages = db_func.get_stages(host, job_id)
    missing = [stage for stage in LOG_PLAYBOOK_STAGES if stage not in stages]
    owner = db_func.job_client_id(host, job_id)
    if missing or not owner:
        return {"success": False, "error": STEP_MSGS["log_fixture_job_failed"].format(
            error=f"job {job_id} has no jobs.client_id or no stage row for "
                  f"{', '.join(missing) or '-'}")}
    SESSION["disposable"] = {
        "success": True, "error": "", "job_id": job_id, "client_id": owner,
        "directory": f"{data_path(host)}/{BSM_JOB_LOG_ROOT}/{job_id}"}
    emit(f"disposable log query job {job_id} ({LOG_FVT_CLIENT_NAME})")
    return SESSION["disposable"]


def plant(host: Any, job: Dict[str, Any], stage: str, name: str,
          content: Union[bytes, int]) -> Dict[str, Any]:
    """Write a fixture log and record it as the completed stage's log.

    Bytes are written verbatim; an integer generates that many bytes of
    ``x`` lines (LOG_FIXTURE_WIDTH wide) on the OIM.

    Returns:
        Dict with keys: success, path, error.
    """
    _guard(name, LOG_FIXTURE_NAME_RE, "fixture name")
    path = f"{job['directory']}/{name}"
    if isinstance(content, bytes):
        write = run_cmd(host, "log_write_b64", directory=job["directory"], path=path,
                        data=base64.b64encode(content).decode("ascii"))
    else:
        write = run_cmd(host, "log_fill", directory=job["directory"], path=path,
                        size=int(content), width=LOG_FIXTURE_WIDTH)
    error = f"write failed (rc={write.rc})" if write.rc != 0 else ""
    if not error:
        readable = mode_and_label(host, path)
        error = "" if readable["ok"] else readable["state"]
    if not error:
        error = set_stage(host, job["job_id"], stage, "COMPLETED", path)["error"]
    if error:
        error = STEP_MSGS["log_fixture_failed"].format(name=name, stage=stage, error=error)
    return {"success": not error, "path": path, "error": error}


def _remove(host: Any, path: str) -> None:
    """Delete one fixture file."""
    run_cmd(host, "log_remove", path=path)


def _reset(host: Any, job: Dict[str, Any], stages: List[str]) -> None:
    """Reset stage rows of the disposable job to PENDING without a log."""
    for stage in stages:
        set_stage(host, job["job_id"], stage, *_RESET)


def release_log_fixture_job(host: Any) -> None:
    """Remove every fixture and restore the disposable job (teardown)."""
    job = SESSION.pop("disposable", None)
    if not job:
        return
    errors = []
    if run_cmd(host, "log_remove_fixtures", directory=job["directory"]).rc != 0:
        errors.append("fixture files not removed")
    errors += [item["error"] for item in (
        *(set_stage(host, job["job_id"], stage, *_RESET) for stage in LOG_PLAYBOOK_STAGES),
        _set_owner(host, job["job_id"], job["client_id"])) if not item["success"]]
    if errors:
        log(STEP_MSGS["log_release_failed"].format(job_id=job["job_id"],
                                                    error="; ".join(errors)), "WARN")


def _start(host: Any, emit: Emit) -> Any:
    """Return (api, job, result) for a mutation step, or a blocked/failed result."""
    gate = _mutation_gate()
    if gate:
        return None, None, gate
    result = new_result()
    job = fixture_job(host, emit)
    if not job["success"]:
        result["failures"].append(job["error"])
        return None, None, finish(result)
    result["fields"].append(("Disposable job", job["job_id"]))
    return SESSION["client"], job, result


def _entry(response: Dict[str, Any], stage: str) -> Dict[str, Any]:
    """Return the stage entry of a 200 log query response ({} otherwise)."""
    body = response.get("json") if response["status"] == 200 else None
    stages = body.get("stages") if isinstance(body, dict) else None
    return next((item for item in stages or [] if item.get("stage_name") == stage), {})


def _job_stage(api: Dict[str, Any], job_id: str, stage: str) -> Dict[str, Any]:
    """Return a stage of GET /api/v1/jobs/{id} ({} when unreadable)."""
    response = log_request(api, "GET", job_path(job_id))
    body = response.get("json") if response["status"] == 200 else None
    stages = body.get("stages") if isinstance(body, dict) else None
    return next((item for item in stages or [] if item.get("stage_name") == stage), {})


def _planted(result: Dict[str, Any], planted: Dict[str, Any]) -> bool:
    """Record a fixture plant and return whether it worked."""
    return add_check(result, planted["success"], "Fixture log",
                     posixpath.basename(planted["path"]), planted["error"])


# =============================================================================
# Mutation checks
# =============================================================================

def verify_log_missing_file(host: Any, settings: Dict[str, Any], emit: Emit) -> Dict[str, Any]:
    """TC-FVT-018: a recorded log whose file was deleted reports has_log=false."""
    del settings
    api, job, result = _start(host, emit)
    if job is None:
        return result
    stage = "deploy"
    planted = plant(host, job, stage, "fvt_missing.log", LOG_PLAIN_FIXTURE)
    try:
        if not _planted(result, planted):
            return finish(result)
        before = _job_stage(api, job["job_id"], stage)
        add_check(result, before.get("has_log") is True
                  and before.get("log_lines") == LOG_PLAIN_FIXTURE.count(b"\n"),
                  "Before delete: GET /jobs has_log/log_lines",
                  f"{before.get('has_log')}/{before.get('log_lines')}")
        _remove(host, planted["path"])
        after = _job_stage(api, job["job_id"], stage)
        add_check(result, after.get("has_log") is False and after.get("log_lines") == 0,
                  "After delete: GET /jobs has_log/log_lines",
                  f"{after.get('has_log')}/{after.get('log_lines')}")
        expect_error(result, f"After delete: stage={stage}", log_request(
            api, "GET", logs_path(job["job_id"]), params={"stage": stage}), "not_available")
        entry = _entry(log_request(api, "GET", logs_path(job["job_id"])), stage)
        add_check(result, entry.get("has_log") is False
                  and entry.get("unavailable_reason") == LOG_REASON_MISSING,
                  "After delete: unfiltered entry",
                  f"has_log={entry.get('has_log')}, reason={entry.get('unavailable_reason')}")
    finally:
        _remove(host, planted["path"])
        _reset(host, job, [stage])
    return finish(result)


def verify_log_unavailable_reasons(host: Any, settings: Dict[str, Any],
                                   emit: Emit) -> Dict[str, Any]:
    """Unservable logs: not yet available, not recorded (legacy), not published, binary.

    A COMPLETED stage without log_file_path is the pre-ER-BSM-003 case: the API
    returns 404 and must not discover the fvt_orphan.log file in the job
    directory. A binary log returns 422 and is never served.
    """
    del settings
    api, job, result = _start(host, emit)
    if job is None:
        return result
    try:
        cases = _prepare_unavailable(host, job, result)
        path = logs_path(job["job_id"])
        listing = log_request(api, "GET", path)
        add_check(result, listing["status"] == 200, "GET /logs (unfiltered)",
                  f"HTTP {listing['status']}")
        for stage, key, reason in cases:
            expect_error(result, f"stage={stage}", log_request(
                api, "GET", path, params={"stage": stage}), key)
            entry = _entry(listing, stage)
            add_check(result, entry.get("has_log") is False
                      and entry.get("unavailable_reason") == reason
                      and entry.get("log_content") is None,
                      f"{stage}: unfiltered entry",
                      f"has_log={entry.get('has_log')}, reason={entry.get('unavailable_reason')}")
    finally:
        run_cmd(host, "log_remove_fixtures", directory=job["directory"])
        _reset(host, job, ["restart", "validate", "create-local-repository", "build-image"])
    return finish(result)


def _prepare_unavailable(host: Any, job: Dict[str, Any],
                         result: Dict[str, Any]) -> List[Tuple[str, str, str]]:
    """Set up one stage per unavailable reason; return (stage, error key, reason)."""
    unpublished = f"{PLAYBOOK_LOG_BASE_DIR}/build_stream/fvt_unpublished.log"
    rows = [("restart", "PENDING", None), ("validate", "COMPLETED", None),
            ("create-local-repository", "COMPLETED", unpublished)]
    # The orphan file sits in the job directory but no row points at it.
    _planted(result, plant(host, job, "validate", "fvt_orphan.log", LOG_PLAIN_FIXTURE))
    for stage, state, stored in rows:
        updated = set_stage(host, job["job_id"], stage, state, stored)
        add_check(result, updated["success"], f"{stage}: {state}, path {stored or 'NULL'}",
                  "set" if updated["success"] else updated["error"])
    _planted(result, plant(host, job, "build-image", "fvt_binary.log", LOG_BINARY_FIXTURE))
    return [("restart", "not_yet_available", LOG_REASON_NOT_YET),
            ("validate", "not_available", LOG_REASON_NOT_RECORDED),
            ("create-local-repository", "not_available", LOG_REASON_NOT_PUBLISHED),
            ("build-image", "not_text", LOG_REASON_NOT_TEXT)]


def verify_log_response_redaction(host: Any, settings: Dict[str, Any],
                                  emit: Emit) -> Dict[str, Any]:
    """TC-FVT-020: secrets are redacted in responses; the file on disk is unchanged."""
    del settings
    api, job, result = _start(host, emit)
    if job is None:
        return result
    stage = "build-image"
    fixture = LOG_REDACTION_FIXTURE.encode("utf-8")
    planted = plant(host, job, stage, "fvt_redaction.log", fixture)
    try:
        if not _planted(result, planted):
            return finish(result)
        contents = [
            _check_redacted(result, label, fixture.count(b"\n"), _entry(log_request(
                api, "GET", logs_path(job["job_id"]), params=params), stage))
            for label, params in (("full=true", {"stage": stage, "full": "true"}),
                                  ("default tail", {"stage": stage}))]
        add_check(result, len(set(contents)) == 1, "Redaction is idempotent",
                  "same content for both reads")
        read = run_cmd(host, "log_read_b64", path=planted["path"])
        on_disk = base64.b64decode(read.stdout.strip()) if read.rc == 0 else b""
        add_check(result, on_disk == fixture, "File on disk unchanged",
                  f"{len(on_disk)} of {len(fixture)} bytes identical"
                  if on_disk == fixture else "content differs")
    finally:
        _remove(host, planted["path"])
        _reset(host, job, [stage])
    return finish(result)


def _check_redacted(result: Dict[str, Any], label: str, lines: int,
                    entry: Dict[str, Any]) -> str:
    """Check one read of the redaction fixture; return its content."""
    content = entry.get("log_content") or ""
    leaked = [value[:6] for value in LOG_REDACTION_SECRETS if value in content]
    kept = [text for text in LOG_REDACTION_EXPECTED if text not in content]
    add_check(result, bool(content) and not leaked, f"{label}: secrets redacted",
              "none returned" if not leaked else f"returned: {', '.join(leaked)}...")
    add_check(result, not kept, f"{label}: context and markers kept",
              "all present" if not kept else f"missing: {', '.join(kept)}")
    add_check(result, entry.get("total_lines") == lines == entry.get("returned_lines"),
              f"{label}: line counts",
              f"{entry.get('returned_lines')}/{entry.get('total_lines')}")
    return content


def verify_log_full_truncation(host: Any, settings: Dict[str, Any],
                               emit: Emit) -> Dict[str, Any]:
    """TC-FVT-014: a log above max_log_response_bytes is truncated from the head."""
    del settings
    api, job, result = _start(host, emit)
    if job is None:
        return result
    stage = "build-image"
    limits = api["settings"]
    size = limits["max_bytes"] + 64 * 1024
    planted = plant(host, job, stage, "fvt_oversize.log", size)
    try:
        if not _planted(result, planted):
            return finish(result)
        # fold inserts a newline every LOG_FIXTURE_WIDTH input bytes.
        total = math.ceil(size / LOG_FIXTURE_WIDTH)
        entry = _entry(log_request(api, "GET", logs_path(job["job_id"]),
                                   params={"stage": stage, "full": "true"},
                                   timeout=LOG_HTTP_TIMEOUT), stage)
        returned = len((entry.get("log_content") or "").encode("utf-8"))
        add_check(result, entry.get("truncated") is True and 0 < returned <= limits["max_bytes"]
                  and entry.get("total_lines") == total
                  and entry.get("returned_lines", 0) < total,
                  "full=true above the byte limit",
                  f"truncated={entry.get('truncated')}, {returned}/{limits['max_bytes']} bytes, "
                  f"{entry.get('returned_lines')}/{entry.get('total_lines')} lines")
        tail = _entry(log_request(api, "GET", logs_path(job["job_id"]),
                                  params={"stage": stage, "tail_lines": limits["max_tail"]}),
                      stage)
        expected = min(limits["max_tail"], total)
        add_check(result, tail.get("returned_lines") == expected and tail.get("truncated") is True,
                  f"tail_lines={limits['max_tail']}",
                  f"{tail.get('returned_lines')}/{tail.get('total_lines')} lines")
    finally:
        _remove(host, planted["path"])
        _reset(host, job, [stage])
    return finish(result)


def verify_log_path_violation(host: Any, settings: Dict[str, Any],
                              emit: Emit) -> Dict[str, Any]:
    """TC-FVT-016: a stored path outside the job's log directory returns 409.

    No content or path is returned, GET /jobs stays 200 with has_log=false,
    and the per-job API log records a sanitized security event (correlation
    ID, no path).
    """
    del settings
    api, job, result = _start(host, emit)
    if job is None:
        return result
    stage = "build-image"
    root = posixpath.dirname(job["directory"])
    variants = {"outside the log root": "/etc/passwd",
                "another job's directory": f"{root}/{uuid.uuid4()}/fvt_other.log",
                "parent traversal": f"{job['directory']}/../../../../etc/passwd"}
    correlations: List[str] = []
    try:
        for label, stored in variants.items():
            if add_check(result, set_stage(host, job["job_id"], stage, "COMPLETED",
                                           stored)["success"], f"{label}: stored", stored):
                correlations += _check_violation(api, job, result, (label, stored, stage))
        api_log = run_cmd(host, "cat_file", path=f"{job['directory']}/"
                          f"{LOG_API_JOB_LOG.format(job_id=job['job_id'])}").stdout
        _check_security_events(result, api_log, correlations, variants)
    finally:
        _reset(host, job, [stage])
    return finish(result)


def _check_violation(api: Dict[str, Any], job: Dict[str, Any], result: Dict[str, Any],
                     item: Tuple[str, str, str]) -> List[str]:
    """Query a job whose ``(label, stored path, stage)`` escapes; return correlation IDs."""
    label, stored, stage = item
    correlations = []
    for query, params in (("unfiltered", None), ("stage filter", {"stage": stage})):
        response = log_request(api, "GET", logs_path(job["job_id"]), params=params)
        correlations.append(response["correlation_id"])
        expect_error(result, f"{label}: {query}", response, "path_violation")
        body = response.get("body") or ""
        add_check(result, stored not in body and "root:" not in body,
                  f"{label}: {query} echoes nothing", "no path or content")
    meta = _job_stage(api, job["job_id"], stage)
    add_check(result, meta.get("has_log") is False, f"{label}: GET /jobs",
              f"has_log={meta.get('has_log')}")
    return correlations


def _check_security_events(result: Dict[str, Any], api_log: str, correlations: List[str],
                           variants: Dict[str, str]) -> None:
    """Check the per-job API log audited every violation without echoing a path."""
    events = [line for line in api_log.splitlines() if LOG_SECURITY_EVENT in line]
    recorded = [corr for corr in correlations if any(corr in line for line in events)]
    add_check(result, bool(correlations) and len(recorded) == len(correlations),
              "Security events recorded", f"{len(recorded)} of {len(correlations)} requests")
    add_check(result, LOG_AUDIT_409 in api_log, "Audit line with status=409",
              "present" if LOG_AUDIT_409 in api_log else "missing")
    echoed = [label for label, stored in variants.items() if stored in api_log]
    add_check(result, not echoed, "API log holds no stored path",
              "none" if not echoed else ", ".join(echoed))


def verify_log_job_ownership(host: Any, settings: Dict[str, Any],
                             emit: Emit) -> Dict[str, Any]:
    """TC-FVT-016: another client's job returns 404 "Job not found".

    BuildStream registers one OAuth client, so another owner is simulated by
    setting jobs.client_id of the disposable job; the body must equal the
    unknown-job body (no existence leak). The owner is restored afterwards.
    """
    del settings
    api, job, result = _start(host, emit)
    if job is None:
        return result
    stage = "deploy"
    planted = plant(host, job, stage, "fvt_owned.log", LOG_PLAIN_FIXTURE)
    path = logs_path(job["job_id"])
    try:
        if not _planted(result, planted):
            return finish(result)
        add_check(result, log_request(api, "GET", path)["status"] == 200, "Owned job",
                  "HTTP 200")
        unknown = detail(log_request(api, "GET", logs_path(str(uuid.uuid4()))))
        label = "another client's job"
        changed = _set_owner(host, job["job_id"], LOG_FOREIGN_CLIENT_ID)
        if add_check(result, changed["success"], f"{label}: set", changed["error"] or "updated"):
            try:
                _check_hidden(api, result, (path, stage), label, unknown)
            finally:
                restored = _set_owner(host, job["job_id"], job["client_id"])
                add_check(result, restored["success"], f"{label}: restored",
                          restored["error"] or "updated")
        add_check(result, log_request(api, "GET", path)["status"] == 200, "Owned job again",
                  "HTTP 200")
    finally:
        _remove(host, planted["path"])
        _reset(host, job, [stage])
    return finish(result)


def _check_hidden(api: Dict[str, Any], result: Dict[str, Any], target_path: Tuple[str, str],
                  label: str, unknown: Dict[str, Any]) -> None:
    """Check ``(logs path, stage)`` answers 404 exactly like an unknown job."""
    path, stage = target_path
    for query, params in (("unfiltered", None), ("stage filter", {"stage": stage})):
        response = log_request(api, "GET", path, params=params)
        expect_error(result, f"{label}: {query}", response, "job_not_found")
        found = detail(response)
        same = (found.get("error"), found.get("message")) == (
            unknown.get("error"), unknown.get("message"))
        add_check(result, same, f"{label}: {query} = unknown job body",
                  "identical" if same else "differs")


def _burst(api: Dict[str, Any], path: str, params: Dict[str, Any],
           count: int) -> List[Dict[str, Any]]:
    """Send ``count`` requests at the same moment; return their responses."""
    barrier = threading.Barrier(count)
    responses: List[Dict[str, Any]] = [{} for _ in range(count)]

    def worker(index: int) -> None:
        barrier.wait()
        responses[index] = log_request(api, "GET", path, params=params, retry_on_429=False,
                                       budget=False, timeout=LOG_HTTP_TIMEOUT)

    threads = [threading.Thread(target=worker, args=(index,)) for index in range(count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return responses


def _bursts(api: Dict[str, Any], result: Dict[str, Any], target_path: Tuple[str, str],
            count: int, emit: Emit) -> List[Dict[str, Any]]:
    """Send up to LOG_CONCURRENCY_ATTEMPTS bursts; return the 503 responses of the last."""
    path, stage = target_path
    busy: List[Dict[str, Any]] = []
    for attempt in range(1, LOG_CONCURRENCY_ATTEMPTS + 1):
        with api["lock"]:
            reserve(api, count)
            api["history"].extend([time.monotonic()] * count)
        responses = _burst(api, path, {"stage": stage, "full": "true"}, count)
        statuses = sorted(response.get("status", 0) for response in responses)
        emit(f"concurrency burst {attempt}: HTTP {statuses}")
        busy = [response for response in responses if response.get("status") == 503]
        others = [status for status in statuses if status not in (200, 503)]
        add_check(result, not others, f"Burst {attempt}: {count} parallel requests",
                  f"{len(busy)} x 503, {statuses.count(200)} x 200"
                  + (f", other {others}" if others else ""))
        if busy:
            break
    return busy


def verify_log_concurrency_limit(host: Any, settings: Dict[str, Any],
                                 emit: Emit) -> Dict[str, Any]:
    """HLD 6.2: above log_query_max_concurrent parallel queries return 503 + Retry-After."""
    del settings
    api, job, result = _start(host, emit)
    if job is None:
        return result
    limits = api["settings"]
    count = min(limits["max_concurrent"] * LOG_CONCURRENCY_FACTOR, limits["rate_limit"])
    if count <= limits["max_concurrent"]:
        return blocked_result(STEP_MSGS["log_concurrency_budget"].format(
            rate=limits["rate_limit"], concurrent=limits["max_concurrent"]))
    stage = "build-image"
    planted = plant(host, job, stage, "fvt_concurrency.log",
                    min(LOG_CONCURRENCY_FIXTURE_BYTES, limits["max_bytes"]))
    try:
        if not _planted(result, planted):
            return finish(result)
        busy = _bursts(api, result, (logs_path(job["job_id"]), stage), count, emit)
        if not add_check(result, bool(busy), "HTTP 503 above the concurrency limit",
                         f"{len(busy)} request(s)",
                         STEP_MSGS["log_concurrency_not_reached"].format(
                             attempts=LOG_CONCURRENCY_ATTEMPTS, count=count,
                             concurrent=limits["max_concurrent"])):
            return finish(result)
        _, code, message = LOG_API_ERRORS["busy"]
        found = detail(busy[0])
        add_check(result, found.get("error") == code and found.get("message") == message
                  and retry_after(busy[0]) >= 1, "503 body and Retry-After",
                  f"{found.get('error')}, Retry-After={retry_after(busy[0])}")
    finally:
        _remove(host, planted["path"])
        _reset(host, job, [stage])
    return finish(result)


def verify_log_rate_limit(host: Any, settings: Dict[str, Any], emit: Emit) -> Dict[str, Any]:
    """TC-FVT-017: request log_query_rate_limit + 1 in one window returns 429.

    Runs only when no GitLab pipeline is running (the CI after_script uses the
    same client budget). The first ``limit`` requests must pass, the next one
    returns 429 with "Rate limit exceeded" and Retry-After, and a request after
    Retry-After passes again.
    """
    del settings
    api, job, result = _start(host, emit)
    if job is None:
        return result
    busy = gitlab_api_func.busy_pipelines(api["context"])
    if busy:
        return blocked_result(STEP_MSGS["log_pipelines_busy"].format(
            pipelines=", ".join(f"#{item.get('id')}" for item in busy)))
    limit = api["settings"]["rate_limit"]
    path = logs_path(job["job_id"])
    emit(f"waiting for an empty {LOG_RATE_WINDOW}s rate window, then sending {limit + 1} "
         "requests")
    with api["lock"]:
        reserve(api, limit)
    statuses, last = [], {}
    for _ in range(limit + 1):
        api["history"].append(time.monotonic())
        last = log_request(api, "GET", path, params={"tail_lines": 1}, retry_on_429=False,
                           budget=False)
        statuses.append(last["status"])
    first_429 = statuses.index(429) + 1 if 429 in statuses else 0
    add_check(result, statuses[:limit] == [200] * limit, f"First {limit} requests",
              f"HTTP 200 x {statuses[:limit].count(200)}"
              + (f", first 429 at request {first_429}" if 0 < first_429 <= limit else ""))
    expect_error(result, f"Request {limit + 1}", last, "rate_limited")
    wait = retry_after(last)
    add_check(result, 1 <= wait <= LOG_RATE_WINDOW, "Retry-After", wait or "missing")
    if wait:
        time.sleep(wait + LOG_RATE_MARGIN)
        recovered = log_request(api, "GET", path, params={"tail_lines": 1}, retry_on_429=False)
        add_check(result, recovered["status"] == 200, "After Retry-After",
                  f"HTTP {recovered['status']}")
    return finish(result)
