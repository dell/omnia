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

import time
from typing import Any, Callable, Dict, List, Optional, Sequence

from . import db_func, gitlab_func
from .api_func import get_api_job
from ..messages.system_msgs import PROGRESS_MSGS as PROGRESS
from ..vars.common_vars import (
    GITLAB_BRIDGE_DEPLOY_CHILD,
    GITLAB_DEPLOY_JOB,
    GITLAB_FAILED_STATUSES,
    GITLAB_MANUAL,
    GITLAB_SELECT_IMAGE_STAGE,
    GITLAB_SUCCESS,
    JOB_DB_TIMEOUT,
    JOB_TERMINAL_FAILED,
    PIPELINE_DETECT_INTERVAL,
    SELECT_JOBS_TIMEOUT,
    STAGE_COMPLETED,
    STAGE_FAILED,
    STAGE_SKIPPED,
    STAGE_TERMINAL,
)

Emit = Callable[[str], None]

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
                             emit: Emit) -> Dict[str, Any]:
    """Make sure no pipeline is running before a new one is triggered.

    Returns:
        Dict with keys: success, cancelled (ids), busy (ids), error.
    """
    busy = gitlab_func.busy_pipelines(context)
    if not busy:
        emit(PROGRESS["no_busy_pipelines"])
        return {"success": True, "cancelled": [], "busy": [], "error": ""}
    ids = [pipeline["id"] for pipeline in busy]
    if not allow_cancel:
        return {"success": False, "cancelled": [], "busy": ids,
                "error": f"pipeline(s) {', '.join(map(str, ids))} are running or pending"}
    for pipeline_id in ids:
        result = gitlab_func.cancel_pipeline(context, pipeline_id)
        emit(PROGRESS["pipeline_cancel"].format(
            pipeline_id=pipeline_id, outcome="ok" if result["success"] else result["error"]))
    time.sleep(PIPELINE_DETECT_INTERVAL)
    return {"success": True, "cancelled": ids, "busy": [], "error": ""}


def wait_for_new_job(host: Any, epoch: int, context: Dict[str, Any], pipeline_id: int,
                     emit: Emit, timeout: int = JOB_DB_TIMEOUT) -> Dict[str, Any]:
    """Wait for the pipeline's initialization stage to create a BuildStream job.

    Returns:
        Dict with keys: success, job_id, error.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = db_func.job_since(host, epoch, newest=False)
        if job:
            emit(PROGRESS["job_created"].format(job_id=job["job_id"], state=job["job_state"]))
            return {"success": True, "job_id": job["job_id"], "error": ""}
        status = gitlab_func.get_pipeline(context, pipeline_id).get("status", "")
        if status in GITLAB_FAILED_STATUSES:
            return {"success": False, "job_id": "",
                    "error": f"pipeline #{pipeline_id} {status} before a job was created"}
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
                   seen: Dict[str, str], emit: Emit) -> str:
    """Emit GitLab job status changes; return the first failed pipeline status."""
    failed = ""
    for pipeline_id in pipeline_ids:
        pipeline = gitlab_func.get_pipeline(context, pipeline_id)
        status = pipeline.get("status", "")
        key = f"pipeline:{pipeline_id}"
        if status and seen.get(key) != status:
            emit(PROGRESS["gitlab_pipeline_status"].format(pipeline_id=pipeline_id, status=status))
            seen[key] = status
        for job in gitlab_func.pipeline_jobs(context, pipeline_id):
            job_key = f"job:{job.get('id')}"
            if seen.get(job_key) != job.get("status"):
                emit(PROGRESS["gitlab_job_status"].format(
                    name=job.get("name"), stage=job.get("stage"), status=job.get("status")))
                seen[job_key] = job.get("status")
        if status in GITLAB_FAILED_STATUSES and not failed:
            failed = f"pipeline #{pipeline_id} {status}"
    return failed


def monitor_stages(host: Any, context: Dict[str, Any], job_id: str, stages: Sequence[str],
                   pipeline_ids: Sequence[int], poll: int, emit: Emit,
                   baseline: Optional[Dict[str, Dict[str, str]]] = None) -> Dict[str, Any]:
    """Wait for each stage in order to reach COMPLETED (no timeout).

    A stage is finished when its job_stages row is COMPLETED, FAILED or
    SKIPPED (and, when ``baseline`` is given, was re-run after it). The wait
    ends when a stage finishes or fails, the BuildStream job fails, or a
    watched GitLab pipeline fails or is cancelled.

    Returns:
        Dict with keys: success, results (one dict per stage with stage,
        state, elapsed, attempt, error_code, error_summary, log_file_path),
        failed_stage, error.
    """
    results: List[Dict[str, Any]] = []
    seen: Dict[str, str] = {}
    failure = ""
    for index, stage in enumerate(stages):
        start = time.time()
        last_state, polls = "", 0
        emit(PROGRESS["stage_monitoring"].format(stage=stage, poll=poll))
        while True:
            row = db_func.get_stages(host, job_id).get(stage)
            state = row["stage_state"] if row else "NOT CREATED"
            if row and state in STAGE_TERMINAL and not _stage_changed(row, baseline):
                state = "WAITING FOR RE-RUN"
            if state != last_state:
                emit(PROGRESS["stage_changed"].format(
                    clock=_clock(time.time() - start), stage=stage, state=state))
                last_state = state
            elif polls % 4 == 3:
                emit(PROGRESS["stage_still"].format(
                    clock=_clock(time.time() - start), stage=stage, state=state))
            if state in STAGE_TERMINAL:
                break
            pipeline_failure = _gitlab_status(context, pipeline_ids, seen, emit)
            # A re-used job (deploy on an earlier build) may carry an old state.
            job = {} if baseline else (db_func.get_job(host, job_id) or {})
            if job.get("job_state") in JOB_TERMINAL_FAILED:
                failure = f"BuildStream job {job_id} {job['job_state']} during '{stage}'"
            elif pipeline_failure:
                failure = f"{pipeline_failure} while waiting for stage '{stage}'"
            if failure:
                break
            polls += 1
            time.sleep(poll)

        row = row or {}
        results.append({
            "stage": stage, "state": state, "elapsed": _clock(time.time() - start),
            "attempt": row.get("attempt", ""), "error_code": row.get("error_code", ""),
            "error_summary": row.get("error_summary", ""),
            "log_file_path": row.get("log_file_path", ""),
        })
        if state == STAGE_FAILED and not failure:
            failure = (f"stage '{stage}' FAILED: {row.get('error_code') or ''} "
                       f"{row.get('error_summary') or ''}").strip()
        if failure:
            results.extend({"stage": name, "state": "NOT RUN", "elapsed": "-",
                            "attempt": "", "error_code": "", "error_summary": "",
                            "log_file_path": ""} for name in stages[index + 1:])
            return {"success": False, "results": results, "failed_stage": stage,
                    "error": failure}
        if state == STAGE_SKIPPED:
            emit(PROGRESS["stage_skipped"].format(stage=stage))
    _gitlab_status(context, pipeline_ids, seen, emit)
    return {"success": True, "results": results, "failed_stage": "", "error": ""}


def wait_pipeline_finished(context: Dict[str, Any], pipeline_id: int, timeout: int,
                           poll: int, emit: Emit) -> Dict[str, Any]:
    """Wait for a GitLab pipeline to reach a final status.

    Returns:
        Dict with keys: success (status == success), status, error.
    """
    deadline = time.time() + timeout
    status = ""
    while time.time() < deadline:
        status = gitlab_func.get_pipeline(context, pipeline_id).get("status", "")
        if status == GITLAB_SUCCESS or status in GITLAB_FAILED_STATUSES:
            break
        emit(PROGRESS["pipeline_finishing"].format(pipeline_id=pipeline_id, status=status))
        time.sleep(poll)
    return {"success": status == GITLAB_SUCCESS, "status": status or "unknown",
            "error": "" if status == GITLAB_SUCCESS
            else f"pipeline #{pipeline_id} finished as {status or 'unknown'}"}


# =============================================================================
# DEPLOY: IMAGE SELECTION AND MANUAL JOBS
# =============================================================================

def _wait_job_status(context: Dict[str, Any], pipeline_id: int, job_id: int,
                     wanted: Sequence[str], timeout: int, emit: Emit) -> str:
    """Wait for a GitLab job to reach ``wanted`` or fail; return its status."""
    deadline = time.time() + timeout
    status = ""
    while time.time() < deadline:
        for job in gitlab_func.pipeline_jobs(context, pipeline_id):
            if job.get("id") == job_id:
                status = job.get("status", "")
        if status in wanted or status in GITLAB_FAILED_STATUSES:
            return status
        emit(PROGRESS["gitlab_job_waiting"].format(job_id=job_id, status=status or "pending"))
        time.sleep(PIPELINE_DETECT_INTERVAL)
    return status or "timeout"


def select_image_and_deploy(context: Dict[str, Any], deploy_child_id: int,
                            image_group_id: str, emit: Emit) -> Dict[str, Any]:
    """Select ``image_group_id`` and play the manual deploy job.

    The deploy child pipeline runs list_images and then triggers a generated
    pipeline holding one manual select_image job per BUILT image group and a
    manual ``deploy`` job (.gitlab-ci-deploy.yml).

    Returns:
        Dict with keys: success, select_pipeline_id, select_job, deploy_job,
        available (image group job names), error.
    """
    outcome = {"success": False, "select_pipeline_id": 0, "select_job": 0,
               "deploy_job": 0, "available": [], "error": ""}
    grandchild = gitlab_func.wait_for_downstream(
        context, deploy_child_id, GITLAB_BRIDGE_DEPLOY_CHILD, emit, SELECT_JOBS_TIMEOUT)
    if not grandchild["success"]:
        outcome["error"] = grandchild["error"]
        return outcome
    pipeline_id = grandchild["pipeline"]["id"]
    outcome["select_pipeline_id"] = pipeline_id
    emit(PROGRESS["image_selection_pipeline"].format(pipeline_id=pipeline_id))

    deadline = time.time() + SELECT_JOBS_TIMEOUT
    jobs: List[Dict[str, Any]] = []
    while time.time() < deadline and not jobs:
        jobs = gitlab_func.find_job(gitlab_func.pipeline_jobs(context, pipeline_id),
                                    stage=GITLAB_SELECT_IMAGE_STAGE)
        if not jobs:
            time.sleep(PIPELINE_DETECT_INTERVAL)
    outcome["available"] = [job.get("name") for job in jobs]
    target = [job for job in jobs if job.get("name") == image_group_id]
    if not target:
        outcome["error"] = (f"image group '{image_group_id}' is not offered for "
                            f"deployment; available: {outcome['available'] or 'none'}")
        return outcome

    select_job = target[0]
    outcome["select_job"] = select_job["id"]
    if select_job.get("status") == GITLAB_MANUAL:
        played = gitlab_func.play_job(context, select_job["id"])
        if not played["success"]:
            outcome["error"] = f"cannot play select job: {played['error']}"
            return outcome
    emit(PROGRESS["image_group_selected"].format(group_id=image_group_id,
                                                job_id=select_job["id"]))
    status = _wait_job_status(context, pipeline_id, select_job["id"], (GITLAB_SUCCESS,),
                              SELECT_JOBS_TIMEOUT, emit)
    if status != GITLAB_SUCCESS:
        outcome["error"] = f"select job #{select_job['id']} finished as {status}"
        return outcome

    deploy_jobs = gitlab_func.find_job(gitlab_func.pipeline_jobs(context, pipeline_id),
                                       name=GITLAB_DEPLOY_JOB)
    if not deploy_jobs:
        outcome["error"] = f"no '{GITLAB_DEPLOY_JOB}' job in pipeline #{pipeline_id}"
        return outcome
    deploy_job = deploy_jobs[0]
    outcome["deploy_job"] = deploy_job["id"]
    if deploy_job.get("status") == GITLAB_MANUAL:
        played = gitlab_func.play_job(context, deploy_job["id"])
        if not played["success"]:
            outcome["error"] = f"cannot play deploy job: {played['error']}"
            return outcome
    emit(PROGRESS["deploy_job_started"].format(job_id=deploy_job["id"]))
    outcome["success"] = True
    return outcome


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

def verify_job_records(host: Any, context: Dict[str, Any], job_id: str, stages: Sequence[str],
                       expected_group_statuses: Sequence[str],
                       expected_group_id: str = "",
                       min_deploy_count: int = 0) -> Dict[str, Any]:
    """Verify jobs, job_stages, image_groups and images rows plus the API view.

    Returns:
        Dict with keys: success, fields (label/value pairs), failures,
        image_group (dict or None).
    """
    fields: List[tuple] = []
    failures: List[str] = []
    job = db_func.get_job(host, job_id)
    fields.append(("DB jobs.job_state", job["job_state"] if job else "MISSING"))
    if not job:
        failures.append(f"job {job_id} not found in jobs")

    for row in db_func.stage_rows(host, job_id, stages):
        state = row["stage_state"]
        fields.append((f"DB stage {row['stage_name']}",
                       f"{state} (attempt {row['attempt'] or '-'})"))
        if state not in (STAGE_COMPLETED, STAGE_SKIPPED):
            failures.append(f"stage {row['stage_name']} is {state}")

    group = db_func.image_group_for_job(host, job_id)
    if group:
        images = db_func.image_count(host, group["id"])
        fields.extend([
            ("DB image_group", group["id"]),
            ("DB image_group.status", group["status"]),
            ("DB image_group.deploy_count", group["deploy_count"]),
            ("DB images", images),
        ])
        if group["status"] not in expected_group_statuses:
            failures.append(f"image group status {group['status']} not in "
                            f"{', '.join(expected_group_statuses)}")
        if expected_group_id and group["id"] != expected_group_id:
            failures.append(f"image group {group['id']} != expected {expected_group_id}")
        if images <= 0:
            failures.append(f"no images recorded for {group['id']}")
        if int(group["deploy_count"] or 0) < min_deploy_count:
            failures.append(f"deploy_count {group['deploy_count']} < {min_deploy_count}")
    else:
        fields.append(("DB image_group", "MISSING"))
        failures.append(f"no image group recorded for job {job_id}")

    api = get_api_job(context, job_id)
    if api["success"]:
        mismatched = [name for name in stages
                      if api["stages"].get(name) != db_func.get_stages(host, job_id)
                      .get(name, {}).get("stage_state")]
        fields.append(("API job_state", api["job_state"]))
        fields.append(("API stages match DB", "yes" if not mismatched
                       else f"NO ({', '.join(mismatched)})"))
        if mismatched:
            failures.append(f"API stage states differ from DB: {', '.join(mismatched)}")
    else:
        fields.append(("API job", f"unavailable: {api['error']}"))
        failures.append(f"BuildStream API job lookup failed: {api['error']}")
    return {"success": not failures, "fields": fields, "failures": failures,
            "image_group": group}


def stage_fields(results: Sequence[Dict[str, Any]]) -> List[tuple]:
    """Render monitor results as report fields (one line per stage)."""
    fields = []
    for item in results:
        text = f"{item['state']} ({item['elapsed']})"
        if item.get("error_code") or item.get("error_summary"):
            text += f" {item.get('error_code', '')} {item.get('error_summary', '')}".rstrip()
        if item.get("log_file_path") and item["state"] != STAGE_COMPLETED:
            text += f" log={item['log_file_path']}"
        fields.append((f"Stage {item['stage']}", text))
    return fields
