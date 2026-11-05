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

"""BuildStream pipeline triggering, stage monitoring and DB verification.

Stage progress is read from build_stream_db.job_stages (the BuildStream
source of truth) while the GitLab pipeline is watched in parallel so that a
failed or cancelled pipeline ends the wait. Stages have no timeout.
``emit`` callbacks receive one human-readable progress line at a time.
"""

import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from . import db_func, gitlab_api_func
from .bsm_api_func import get_api_job
from .cadence_func import host_epoch
from .log_func import LogFollower, find_stage_log, mark, sleep_streaming
from .execute_probe_func import data_path
from ..messages.execute_msgs import PROGRESS_MSGS as PROGRESS
from ..vars.execute_vars import (
    API_JOB_STATE,
    BSM_JOB_LOG_ROOT,
    GITLAB_FAILED_STATUSES,
    GITLAB_SUCCESS,
    JOB_DB_TIMEOUT,
    JOB_TERMINAL_FAILED,
    PIPELINE_DETECT_INTERVAL,
    STAGE_COMPLETED,
    STAGE_FAILED,
    STAGE_SKIPPED,
    STAGE_TERMINAL,
)

Emit = Callable[[str], None]
# The job row turns FAILED a moment before the stage row; re-read it this often.
_SETTLE_READS = 6
_SETTLE_INTERVAL = 5
# Failed GitLab job logs: report the first real error of the earliest failed job.
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
_TRACE_PREFIX_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T[\d:.]+Z\s+\d{2}[A-Z]\s?")
# Lines every failed job ends with (artifact upload, cleanup, exit status): they
# are consequences of the failure, never its cause.
_TRACE_NOISE_RE = re.compile(
    r"^section_(start|end):|no matching files|No files to upload|Uploading artifacts|"
    r"Cleaning up|Job failed: exit code|Running with gitlab-runner|Preparing |"
    r"Getting source|Fetching changes")
_CAUSE_RE = re.compile(r"\b(ERROR|FATAL)\b|^fatal:|Traceback")
_EXIT_CODE_RE = re.compile(r"Job failed: exit code (\d+)")
_CAUSE_LINES = 3

# Results shared between installation tests (build -> deploy).
PIPELINE_STATE: Dict[str, Dict[str, Any]] = {"build": {}, "deploy": {}, "cadence": {}}


def _clock(seconds: float) -> str:
    """Format seconds as ``<m>m<ss>s``."""
    seconds = int(seconds)
    return f"{seconds // 60}m{seconds % 60:02d}s"


# =============================================================================
# PRE-TRIGGER CHECKS
# =============================================================================

def ensure_no_busy_pipelines(context: Dict[str, Any], allow_cancel: bool,
                             emit: Emit, action: str = "triggering a new pipeline"
                             ) -> Dict[str, Any]:
    """Make sure no pipeline is running before ``action`` starts a new one.

    With ``allow_cancel`` every running/pending pipeline is reported and
    cancelled before ``action``; without it the step fails and lists them.

    Returns:
        Dict with keys: success, cancelled (ids), busy (ids), fields, error.
    """
    busy = gitlab_api_func.busy_pipelines(context)
    if not busy:
        emit(PROGRESS["no_busy_pipelines"].format(action=action))
        return {"success": True, "cancelled": [], "busy": [], "error": "",
                "fields": [(mark(True, "Running pipelines"), "none")]}
    described = ", ".join(f"#{p['id']} ({p.get('status')}, {p.get('source', '?')})"
                          for p in busy)
    ids = [pipeline["id"] for pipeline in busy]
    if not allow_cancel:
        return {"success": False, "cancelled": [], "busy": ids,
                "fields": [(mark(False, "Running pipelines"), described)],
                "error": PROGRESS["busy_pipelines_blocked"].format(
                    pipelines=described, action=action)}
    emit(PROGRESS["busy_pipelines_found"].format(pipelines=described, action=action))
    failed = []
    for pipeline_id in ids:
        result = gitlab_api_func.cancel_pipeline(context, pipeline_id)
        if not result["success"]:
            failed.append(f"#{pipeline_id}: {result['error']}")
        emit(PROGRESS["pipeline_cancel"].format(
            pipeline_id=pipeline_id, outcome="cancelled" if result["success"] else result["error"]))
    time.sleep(PIPELINE_DETECT_INTERVAL)
    fields = [(mark(not failed, "Running pipelines cancelled"), described)]
    if failed:
        return {"success": False, "cancelled": [], "busy": ids, "fields": fields,
                "error": f"cannot cancel running pipeline(s): {'; '.join(failed)}"}
    emit(PROGRESS["busy_pipelines_cancelled"].format(action=action))
    return {"success": True, "cancelled": ids, "busy": [], "fields": fields, "error": ""}


def _trace_cause(trace: str) -> Tuple[List[str], str]:
    """Return (cause lines, exit code) from a failed GitLab job log.

    The cause is the first real ERROR/FATAL line (plus the WARNING right before
    it and the lines after it that explain it); artifact-upload and cleanup
    lines at the end of the log are skipped.
    """
    lines = [_TRACE_PREFIX_RE.sub("", _ANSI_RE.sub("", raw)).strip()
             for raw in trace.splitlines()]
    lines = [line for line in lines if line]
    exit_code = next((m.group(1) for line in reversed(lines)
                      if (m := _EXIT_CODE_RE.search(line))), "")
    first = next((i for i, line in enumerate(lines)
                  if _CAUSE_RE.search(line) and not _TRACE_NOISE_RE.search(line)), None)
    if first is None:
        window = [line for line in lines if not _TRACE_NOISE_RE.search(line)][-_CAUSE_LINES:]
        return window, exit_code
    start = first - 1 if first and lines[first - 1].startswith("WARNING") else first
    window = [line for line in lines[start:first + _CAUSE_LINES]
              if not _TRACE_NOISE_RE.search(line)]
    return window[:_CAUSE_LINES], exit_code


def failed_job_reasons(context: Dict[str, Any], pipeline_id: int) -> List[str]:
    """Return report rows that say why a GitLab pipeline failed ([] when no job failed).

    The earliest failed job is the cause (later ones, such as ``summary``, only
    fail because of it): its name, GitLab failure reason, exit code, the first
    real error lines of its log and a link to the full log.
    """
    failed = sorted((job for job in gitlab_api_func.pipeline_jobs(context, pipeline_id)
                     if job.get("status") == "failed"), key=lambda job: job.get("id", 0))
    if not failed:
        return []
    cause, others = failed[0], failed[1:]
    lines, exit_code = _trace_cause(gitlab_api_func.job_trace(context, cause["id"]))
    head = (f"GitLab job '{cause.get('name')}' (stage {cause.get('stage')}): "
            f"{cause.get('failure_reason') or 'failed'}")
    rows = [f"{head}, exit code {exit_code}" if exit_code else head, *lines]
    if cause.get("web_url"):
        rows.append(f"Job log: {cause['web_url']}")
    if others:
        rows.append("Also failed: " + ", ".join(str(job.get("name")) for job in others))
    return rows


def _with_reasons(context: Dict[str, Any], pipeline_id: int, text: str) -> str:
    """Return ``text`` followed by the failed-job reasons, one per line (when any)."""
    return "\n".join([text, *failed_job_reasons(context, pipeline_id)])


def wait_for_new_job(host: Any, epoch: int, context: Dict[str, Any], pipeline_id: int,
                     emit: Emit) -> Dict[str, Any]:
    """Wait (up to JOB_DB_TIMEOUT) for the pipeline to create a BuildStream job.

    Returns:
        Dict with keys: success, job_id, error.
    """
    timeout = JOB_DB_TIMEOUT
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = db_func.job_since(host, epoch, newest=False)
        if job:
            emit(PROGRESS["job_created"].format(job_id=job["job_id"], state=job["job_state"]))
            return {"success": True, "job_id": job["job_id"], "error": ""}
        status = gitlab_api_func.get_pipeline(context, pipeline_id).get("status", "")
        if status in GITLAB_FAILED_STATUSES:
            return {"success": False, "job_id": "",
                    "error": _with_reasons(context, pipeline_id,
                                           f"pipeline #{pipeline_id} {status} "
                                           "before a job was created")}
        emit(PROGRESS["job_waiting"].format(pipeline_id=pipeline_id, status=status))
        time.sleep(PIPELINE_DETECT_INTERVAL)
    return {"success": False, "job_id": "",
            "error": f"no BuildStream job created within {timeout}s"}


# =============================================================================
# STAGE MONITORING
# =============================================================================

def _stage_changed(row: Dict[str, str], baseline: Optional[Dict[str, Dict[str, str]]]) -> bool:
    """A terminal row counts only if it differs from the pre-trigger baseline."""
    if not baseline or row["stage_name"] not in baseline:
        return True
    before = baseline[row["stage_name"]]
    return (row.get("attempt"), row.get("started_at")) != (
        before.get("attempt"), before.get("started_at"))


def _gitlab_status(context: Dict[str, Any], pipeline_ids: Sequence[int],
                   seen: Dict[str, str], emit: Emit) -> Tuple[str, int]:
    """Emit GitLab job status changes; return (text, id) of the first failed pipeline."""
    failed = ("", 0)
    for pipeline_id in pipeline_ids:
        pipeline = gitlab_api_func.get_pipeline(context, pipeline_id)
        status = pipeline.get("status", "")
        key = f"pipeline:{pipeline_id}"
        if status and seen.get(key) != status:
            emit(PROGRESS["gitlab_pipeline_status"].format(pipeline_id=pipeline_id, status=status))
            seen[key] = status
        for job in gitlab_api_func.pipeline_jobs(context, pipeline_id):
            job_key = f"job:{job.get('id')}"
            if seen.get(job_key) != job.get("status"):
                emit(PROGRESS["gitlab_job_status"].format(
                    name=job.get("name"), stage=job.get("stage"), status=job.get("status")))
                seen[job_key] = job.get("status")
        if status in GITLAB_FAILED_STATUSES and not failed[0]:
            failed = (f"pipeline #{pipeline_id} {status}", pipeline_id)
    return failed


def _row_state(row: Optional[Dict[str, str]],
               baseline: Optional[Dict[str, Dict[str, str]]]) -> str:
    """Stage state from a job_stages row, ignoring a terminal pre-trigger row."""
    state = row["stage_state"] if row else "NOT CREATED"
    if row and state in STAGE_TERMINAL and not _stage_changed(row, baseline):
        return "WAITING FOR RE-RUN"
    return state


def _settle_row(host: Any, job_id: str, stage: str,
                baseline: Optional[Dict[str, Dict[str, str]]], emit: Emit) -> tuple:
    """After a job failure, re-read the stage until its row is terminal."""
    emit(PROGRESS["stage_settle"].format(stage=stage))
    row, state = None, ""
    for _ in range(_SETTLE_READS):
        row = db_func.get_stages(host, job_id).get(stage)
        state = _row_state(row, baseline)
        if state in STAGE_TERMINAL:
            break
        time.sleep(_SETTLE_INTERVAL)
    return row, state


def verify_stage_record(host: Any, context: Dict[str, Any], job_id: str,
                        item: Dict[str, Any]) -> Dict[str, Any]:
    """Check one finished stage in job_stages and the BuildStream API.

    Returns:
        Dict with keys: fields (marked label/value pairs), failures.
    """
    stage, state = item["stage"], item["state"]
    text = f"{state} ({item['elapsed']})"
    if item.get("error_code") or item.get("error_summary"):
        text += f" {item.get('error_code') or ''} {item.get('error_summary') or ''}".rstrip()
    if item.get("log_path"):
        text += f" log={item['log_path']}"
    ok_states = (STAGE_COMPLETED, STAGE_SKIPPED)
    row = db_func.get_stages(host, job_id).get(stage) or {}
    db_state = row.get("stage_state") or "NOT CREATED"
    fields = [(mark(state in ok_states, f"Stage {stage}"), text),
              (mark(db_state in ok_states, f"DB stage {stage}"),
               f"{db_state} (attempt {row.get('attempt') or '-'})")]
    failures = []
    api = get_api_job(context, job_id)
    if api["success"]:
        api_state = api["stages"].get(stage) or "MISSING"
        fields.append((mark(api_state == db_state, f"API stage {stage}"),
                       api_state if api_state == db_state else f"{api_state} (DB {db_state})"))
        if api_state != db_state:
            failures.append(f"API stage {stage} is {api_state}, DB is {db_state}")
    else:
        fields.append((mark(False, f"API stage {stage}"), f"unavailable: {api['error']}"))
        failures.append(f"BuildStream API job lookup failed: {api['error']}")
    return {"fields": fields, "failures": failures}


@dataclass
class _Watch:
    """What every stage of one ``monitor_stages`` run shares."""

    host: Any
    pipeline: Dict[str, Any]
    poll: int
    debug: bool
    emit: Emit
    job_dir: str
    seen: Dict[str, str] = field(default_factory=dict)


@dataclass
class _StageRun:
    """Progress of the stage being monitored."""

    stage: str
    start: float
    since: int
    follower: Optional[LogFollower]
    last_state: str = ""
    log_path: str = ""
    polls: int = 0


def _locate_log(watch: _Watch, run: _StageRun, row: Optional[Dict[str, str]]) -> None:
    """Pick up the current attempt's log and stream it or print ``tail -f``."""
    found = find_stage_log(watch.host, run.stage, run.since, watch.job_dir,
                           (row or {}).get("attempt"))
    if not found or found == run.log_path:
        return
    run.log_path = found
    if run.follower is None:
        watch.emit(PROGRESS["stage_log_follow"].format(stage=run.stage, path=found))
    elif run.follower.follow(found):
        watch.emit(PROGRESS["stage_log_streaming"].format(stage=run.stage, path=found))


def _report_state(watch: _Watch, run: _StageRun, state: str) -> None:
    """Emit a state change, or every fourth poll a still-waiting line."""
    clock = _clock(time.time() - run.start)
    if state != run.last_state:
        watch.emit(PROGRESS["stage_changed"].format(clock=clock, stage=run.stage, state=state))
        run.last_state = state
    elif run.polls % 4 == 3:
        still = PROGRESS["stage_still"].format(clock=clock, stage=run.stage, state=state)
        if run.log_path and run.follower is None:
            still += f" | tail -f {run.log_path}"
        watch.emit(still)


def _run_failure(watch: _Watch, stage: str) -> str:
    """Return why the wait for ``stage`` must end (job or pipeline failed), or ""."""
    pipeline = watch.pipeline
    pipeline_failure, failed_pipeline = _gitlab_status(pipeline["context"],
                                                       pipeline["watched"],
                                                       watch.seen, watch.emit)
    # A re-used job (deploy on an earlier build) may carry an old state.
    job = ({} if pipeline.get("baseline")
           else (db_func.get_job(watch.host, pipeline["job_id"]) or {}))
    if job.get("job_state") in JOB_TERMINAL_FAILED:
        return f"BuildStream job {pipeline['job_id']} {job['job_state']} during '{stage}'"
    if pipeline_failure:
        return _with_reasons(pipeline["context"], failed_pipeline,
                             f"{pipeline_failure} while waiting for stage '{stage}'")
    return ""


def _wait_stage(watch: _Watch, run: _StageRun) -> tuple:
    """Poll the stage until it is terminal or the run fails.

    Returns:
        Tuple (row, state, failure).
    """
    job_id, baseline = watch.pipeline["job_id"], watch.pipeline.get("baseline")
    while True:
        row = db_func.get_stages(watch.host, job_id).get(run.stage)
        state = _row_state(row, baseline)
        if state not in ("NOT CREATED", "WAITING FOR RE-RUN"):
            _locate_log(watch, run, row)
        _report_state(watch, run, state)
        if state in STAGE_TERMINAL:
            return row, state, ""
        failure = _run_failure(watch, run.stage)
        if failure:
            row, state = _settle_row(watch.host, job_id, run.stage, baseline, watch.emit)
            if state != run.last_state:
                watch.emit(PROGRESS["stage_changed"].format(
                    clock=_clock(time.time() - run.start), stage=run.stage, state=state))
            return row, state, failure
        run.polls += 1
        sleep_streaming(watch.poll, run.follower)


def _close_log(watch: _Watch, run: _StageRun, row: Dict[str, str]) -> str:
    """Find the finished attempt's log, drain the live stream; return the log path."""
    final_log = (find_stage_log(watch.host, run.stage, run.since, watch.job_dir,
                                row.get("attempt"))
                 or row.get("log_file_path") or run.log_path)
    if run.follower is not None and final_log:
        if run.follower.follow(final_log):
            watch.emit(PROGRESS["stage_log_streaming"].format(stage=run.stage, path=final_log))
        run.follower.drain(final=True)
        watch.emit(PROGRESS["stage_log_end"].format(stage=run.stage, lines=run.follower.lines))
    return final_log


def _emit_fields(watch: _Watch, report: Dict[str, Any], fields: List[tuple]) -> None:
    """Emit check fields and add them to the report."""
    for label, value in fields:
        watch.emit(PROGRESS["stage_check"].format(label=label, value=value))
    report["fields"].extend(fields)


def _verify_finished(watch: _Watch, report: Dict[str, Any], item: Dict[str, Any],
                     failure: str, extra: Optional[Callable[[], Dict[str, Any]]]) -> str:
    """Verify a finished stage (DB, API, extra check); return the run failure or ""."""
    stage, state = item["stage"], item["state"]
    watch.emit(PROGRESS["stage_verifying"].format(stage=stage, state=state))
    check = verify_stage_record(watch.host, watch.pipeline["context"],
                                watch.pipeline["job_id"], item)
    _emit_fields(watch, report, check["fields"])
    report["failures"].extend(check["failures"])
    if state == STAGE_FAILED:
        stage_error = (f"stage '{stage}' FAILED: {item['error_code'] or ''} "
                       f"{item['error_summary'] or ''}").strip()
        failure = f"{failure}; {stage_error}" if failure else stage_error
    if extra and state == STAGE_COMPLETED and not failure:
        result = extra()
        _emit_fields(watch, report, result["fields"])
        if result["failures"]:
            failure = f"after stage '{stage}': {'; '.join(result['failures'])}"
    return failure


def _monitor_one(watch: _Watch, report: Dict[str, Any], stage: str,
                 extra: Optional[Callable[[], Dict[str, Any]]]) -> str:
    """Wait for and verify one stage; return the run failure or ""."""
    run = _StageRun(stage, time.time(), host_epoch(watch.host),
                    LogFollower(watch.host) if watch.debug else None)
    watch.emit(PROGRESS["stage_monitoring"].format(stage=stage, poll=watch.poll))
    row, state, failure = _wait_stage(watch, run)
    row = row or {}
    final_log = _close_log(watch, run, row)
    item = {
        "stage": stage, "state": state, "elapsed": _clock(time.time() - run.start),
        "attempt": row.get("attempt", ""), "error_code": row.get("error_code", ""),
        "error_summary": row.get("error_summary", ""),
        "log_path": final_log if state != STAGE_COMPLETED else "",
    }
    report["results"].append(item)
    failure = _verify_finished(watch, report, item, failure, extra)
    if not failure and state == STAGE_SKIPPED:
        watch.emit(PROGRESS["stage_skipped"].format(stage=stage))
    return failure


def _mark_not_run(watch: _Watch, report: Dict[str, Any], stages: Sequence[str]) -> None:
    """Report the stages after a failed one as NOT RUN."""
    states = db_func.get_stages(watch.host, watch.pipeline["job_id"])
    for name in stages:
        db_state = (states.get(name) or {}).get("stage_state") or "NOT CREATED"
        report["results"].append({"stage": name, "state": "NOT RUN", "elapsed": "-",
                                  "attempt": "", "error_code": "", "error_summary": "",
                                  "log_path": ""})
        report["fields"].append((mark(False, f"Stage {name}"), f"NOT RUN (DB {db_state})"))


def monitor_stages(host: Any, pipeline: Dict[str, Any], stages: Sequence[str],
                   settings: Dict[str, Any], emit: Emit) -> Dict[str, Any]:
    """Monitor each stage in order and verify it as soon as it finishes (no timeout).

    ``pipeline`` is the started pipeline's state: context, job_id, watched
    (GitLab pipeline IDs), and optionally baseline (pre-trigger job_stages
    rows) and stage_checks. ``settings`` supplies poll_interval and
    debug_mode (default true).

    ``stage_checks`` maps a stage name to an extra check run right after that
    stage COMPLETED; it returns a dict with ``fields`` and ``failures``. A
    failed extra check stops the monitoring, since later stages consume what
    it verified.

    A stage is finished when its job_stages row is COMPLETED, FAILED or
    SKIPPED (and, when ``baseline`` is given, was re-run after it). Its DB
    row and API state are then checked before the next stage is monitored.
    The wait ends when a stage fails, the BuildStream job fails, or a
    watched GitLab pipeline fails or is cancelled.

    The current attempt's playbook log is located while the stage runs.
    With ``debug_mode`` it is streamed live (pipe-prefixed lines);
    otherwise the progress lines carry ``tail -f <log>``.

    Returns:
        Dict with keys: success, results (one dict per stage), fields
        (marked, stage by stage), failures (verification failures),
        failed_stage, error.
    """
    watch = _Watch(host, pipeline, settings["poll_interval"], settings.get("debug_mode", True),
                   emit, f"{data_path(host)}/{BSM_JOB_LOG_ROOT}/{pipeline['job_id']}")
    report: Dict[str, Any] = {"results": [], "fields": [], "failures": []}
    checks = pipeline.get("stage_checks") or {}
    for index, stage in enumerate(stages):
        failure = _monitor_one(watch, report, stage, checks.get(stage))
        if failure:
            _mark_not_run(watch, report, stages[index + 1:])
            return {"success": False, **report, "failed_stage": stage, "error": failure}
    _gitlab_status(pipeline["context"], pipeline["watched"], watch.seen, emit)
    return {"success": True, **report, "failed_stage": "", "error": ""}


def wait_pipeline_finished(context: Dict[str, Any], pipeline_id: int, timeout: int,
                           poll: int, emit: Emit) -> Dict[str, Any]:
    """Wait for a GitLab pipeline to reach a final status.

    Returns:
        Dict with keys: success (status == success), status, error.
    """
    deadline = time.time() + timeout
    status = ""
    while time.time() < deadline:
        status = gitlab_api_func.get_pipeline(context, pipeline_id).get("status", "")
        if status == GITLAB_SUCCESS or status in GITLAB_FAILED_STATUSES:
            break
        emit(PROGRESS["pipeline_finishing"].format(pipeline_id=pipeline_id, status=status))
        time.sleep(poll)
    return {"success": status == GITLAB_SUCCESS, "status": status or "unknown",
            "error": "" if status == GITLAB_SUCCESS
            else _with_reasons(context, pipeline_id,
                               f"pipeline #{pipeline_id} finished as {status or 'unknown'}")}


# =============================================================================
# DEPLOY: IMAGE SELECTION AND MANUAL JOBS
# =============================================================================

def wait_job_status(context: Dict[str, Any], target: Tuple[int, int], wanted: Sequence[str],
                    timeout: int, emit: Emit) -> str:
    """Wait for a GitLab job to reach ``wanted`` or fail; return its status.

    ``target`` is the (pipeline_id, job_id) pair.
    """
    pipeline_id, job_id = target
    deadline = time.time() + timeout
    status = ""
    while time.time() < deadline:
        for job in gitlab_api_func.pipeline_jobs(context, pipeline_id):
            if job.get("id") == job_id:
                status = job.get("status", "")
        if status in wanted or status in GITLAB_FAILED_STATUSES:
            return status
        emit(PROGRESS["gitlab_job_waiting"].format(job_id=job_id, status=status or "pending"))
        time.sleep(PIPELINE_DETECT_INTERVAL)
    return status or "timeout"


def swap_pxe_rows(content: str) -> Dict[str, Any]:
    """Swap the first two data rows of the PXE mapping CSV.

    Returns:
        Dict with keys: success, content, rows (1-based data row numbers),
        error.
    """
    newline = "\r\n" if "\r\n" in content else "\n"
    lines = content.splitlines()
    data = [index for index, line in enumerate(lines[1:], start=1) if line.strip()]
    if len(data) < 2:
        return {"success": False, "content": content, "rows": (),
                "error": "pxe_mapping_file.csv needs at least two node rows to swap"}
    first, second = data[0], data[1]
    lines[first], lines[second] = lines[second], lines[first]
    trailer = newline if content.endswith(("\n", "\r\n")) else ""
    return {"success": True, "content": newline.join(lines) + trailer,
            "rows": (first, second), "error": ""}


# =============================================================================
# DATABASE AND API VERIFICATION
# =============================================================================

def _check_image_group(host: Any, group: Optional[Dict[str, Any]], job_id: str,
                       expected: Dict[str, Any]) -> Dict[str, Any]:
    """Check the job's image_groups row and its images rows.

    ``expected`` holds group_statuses, group_id ("" = any) and
    min_deploy_count. A group that was deployed (min_deploy_count >= 1) must
    also have last_deployed_at set.

    Returns:
        Dict with keys: fields, failures.
    """
    if not group:
        return {"fields": [(mark(False, "DB image_group"), "MISSING")],
                "failures": [f"no image group recorded for job {job_id}"]}
    images = db_func.image_count(host, group["id"])
    statuses, group_id = expected["group_statuses"], expected["group_id"]
    min_count = expected["min_deploy_count"]
    status_ok = group["status"] in statuses
    id_ok = not group_id or group["id"] == group_id
    count_ok = int(group["deploy_count"] or 0) >= min_count
    deployed_at_ok = min_count < 1 or bool((group.get("last_deployed_at") or "").strip())
    fields = [
        (mark(id_ok, "DB image_group"), group["id"]),
        (mark(status_ok, "DB image_group.status"), group["status"]),
        (mark(count_ok, "DB image_group.deploy_count"), group["deploy_count"]),
        (mark(deployed_at_ok, "DB image_group.last_deployed_at"),
         group.get("last_deployed_at") or "not set"),
        (mark(images > 0, "DB images"), images),
    ]
    checks = [
        (status_ok, f"image group status {group['status']} not in {', '.join(statuses)}"),
        (id_ok, f"image group {group['id']} != expected {group_id}"),
        (images > 0, f"no images recorded for {group['id']}"),
        (count_ok, f"deploy_count {group['deploy_count']} < {min_count}"),
        (deployed_at_ok,
         f"last_deployed_at not set although deploy_count is {group['deploy_count']}"),
    ]
    return {"fields": fields, "failures": [message for ok, message in checks if not ok]}


def _check_api_job(context: Dict[str, Any], job_id: str, job_state: str) -> Dict[str, Any]:
    """Check the BuildStream API reports the DB job state (as its display name).

    Returns:
        Dict with keys: fields, failures.
    """
    api = get_api_job(context, job_id)
    if not api["success"]:
        return {"fields": [(mark(False, "API job"), f"unavailable: {api['error']}")],
                "failures": [f"BuildStream API job lookup failed: {api['error']}"]}
    expected = API_JOB_STATE.get(job_state, job_state)
    api_ok = api["job_state"] == expected
    shown = f"{api['job_state']} (DB {job_state})"
    return {"fields": [(mark(api_ok, "API job_state"), shown)],
            "failures": [] if api_ok
            else [f"API job_state {api['job_state']} differs from DB {job_state} "
                  f"(expected {expected})"]}


def verify_job_records(host: Any, pipeline: Dict[str, Any],
                       expected_group_statuses: Sequence[str]) -> Dict[str, Any]:
    """Verify the job-level rows (jobs, image_groups, images) and the API job.

    ``pipeline`` is the started pipeline's state: context, job_id, and
    optionally group_id (expected image group) and min_deploy_count.
    Stage rows are verified stage by stage in ``monitor_stages``.

    Returns:
        Dict with keys: success, fields (marked label/value pairs), failures,
        image_group (dict or None).
    """
    job_id = pipeline["job_id"]
    job = db_func.get_job(host, job_id)
    job_state = job["job_state"] if job else "MISSING"
    fields: List[tuple] = [(mark(bool(job) and job_state not in JOB_TERMINAL_FAILED,
                                 "DB jobs.job_state"), job_state)]
    failures: List[str] = [] if job else [f"job {job_id} not found in jobs"]
    group = db_func.image_group_for_job(host, job_id)
    expected = {"group_statuses": expected_group_statuses,
                "group_id": pipeline.get("group_id", ""),
                "min_deploy_count": pipeline.get("min_deploy_count", 0)}
    for check in (_check_image_group(host, group, job_id, expected),
                  _check_api_job(pipeline["context"], job_id, job_state)):
        fields.extend(check["fields"])
        failures.extend(check["failures"])
    return {"success": not failures, "fields": fields, "failures": failures,
            "image_group": group}
