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

"""Build, deploy and cadence pipelines as one test case per step.

Every stage is its own test case. Steps share
``PIPELINE_STATE`` within one pytest session, keyed by the suite:

    build / build_manual       build pipeline, automatic / manual trigger
    deploy / deploy_manual     deploy pipeline, automatic / manual trigger
    cadence                    cadence cycle and its unified pipeline

Only the trigger differs between the automatic and the manual suite:
automatic commits a change that GitLab reacts to (catalog_rhel.json or
the PXE mapping file); manual triggers ``PIPELINE_TYPE=build|deploy``
through the API. Every later step (stages, artifacts, records) is the
same function. The start step stores the BuildStream context and the
pipeline/job IDs, each stage step monitors exactly one stage (its playbook
log streams live with ``debug_mode: true``), and a step whose
predecessor failed reports itself as blocked instead of waiting.

Every function returns a result dict with keys: success, fields, failures,
blocked (True when a previous step failed or nothing was started).
"""

import time
from typing import Any, Callable, Dict, List

from . import db_func, gitlab_api_func, pipeline_monitor_func
from .bsm_api_func import get_api_artifact
from .build_artifacts_func import check_repo_status, verify_build_artifacts
from .pipeline_trigger_func import (
    PipelineTrigger,
    _context,
    _deploy_target,
    _result,
    _trigger_build,
    _trigger_cadence,
    _verify_only_ids,
    trigger_pipeline,
)
from .log_func import mark
from .node_coverage_func import check_node_coverage
from .state_func import clear_run_state, load_run_state, save_run_state
from ..messages.execute_msgs import PROGRESS_MSGS as PROGRESS
from ..messages.execute_msgs import STEP_MSGS
from ..vars.execute_vars import (
    BSM_CI_CLIENT_ID_VAR,
    BSM_CI_CLIENT_VARIABLES,
    BSM_CLIENT_ID_PREFIX,
    COMMIT_MESSAGE_DEPLOY,
    GITLAB_BRIDGE_DEPLOY,
    GITLAB_BRIDGE_DEPLOY_CHILD,
    GITLAB_DEPLOY_JOB,
    GITLAB_MANUAL,
    GITLAB_PXE_MAPPING_FILE,
    GITLAB_SELECT_IMAGE_STAGE,
    GITLAB_SUCCESS,
    GITLAB_SUMMARY_JOB,
    GITLAB_SUMMARY_PASSED,
    IMAGE_GROUP_AFTER_BUILD,
    IMAGE_GROUP_BUILT,
    IMAGE_GROUP_PASSED,
    PIPELINE_DETECT_INTERVAL,
    SELECT_JOBS_TIMEOUT,
    STAGE_COMPLETED,
    VALIDATE_STAGE,
)

Emit = Callable[[str], None]
_FINISH_TIMEOUT = 900
STATE = pipeline_monitor_func.PIPELINE_STATE
# Deploy suite -> build suite whose image group it deploys.
DEPLOY_BUILD_SOURCE = {"deploy": "build", "deploy_manual": "build_manual"}
MANUAL_SUITES = ("build_manual", "deploy_manual")
# Verify-only job ID key of each suite (manual suites share the automatic one).
JOB_ID_KEY = {"build": "build", "build_manual": "build",
              "deploy": "deploy", "deploy_manual": "deploy", "cadence": "cadence"}
# Records step -> image group statuses it accepts.
RECORD_GROUP_STATUSES = {"build result": IMAGE_GROUP_AFTER_BUILD,
                         "deploy result": (IMAGE_GROUP_PASSED,),
                         "cadence result": (IMAGE_GROUP_PASSED,)}


def _blocked(name: str, message: str) -> Dict[str, Any]:
    """Return a result for a step that cannot run."""
    return {"success": False, "fields": [("Step", name)], "failures": [message],
            "blocked": True, "mode": ""}


def _finish(result: Dict[str, Any], state: Dict[str, Any], step: str) -> Dict[str, Any]:
    """Set success, block later steps on failure, and return ``result``."""
    result["success"] = not result["failures"]
    result.setdefault("blocked", False)
    if not result["success"] and not state.get("failed_step"):
        state["failed_step"] = step
    return result


def _gate(pipeline: str, step: str) -> Dict[str, Any]:
    """Return a blocked result when ``pipeline`` was skipped, not started or a step failed."""
    state = STATE.get(pipeline) or {}
    if state.get("skip_reason"):
        return _blocked(step, state["skip_reason"])
    if not state.get("context"):
        return _blocked(step, STEP_MSGS["not_started"].format(pipeline=pipeline))
    if state.get("failed_step"):
        return _blocked(step, STEP_MSGS["previous_failed"].format(
            pipeline=pipeline, step=state["failed_step"]))
    return {}


def _mode(pipeline: str, verify_only: bool) -> str:
    """Return the report mode of a suite."""
    if verify_only:
        return "verify-only"
    return "manual trigger" if pipeline in MANUAL_SUITES else "automatic trigger"


# =============================================================================
# Shared stage step
# =============================================================================

def run_stage_step(host: Any, pipeline: str, stage: str, settings: Dict[str, Any],
                   emit: Emit) -> Dict[str, Any]:
    """Monitor and verify one stage of a started pipeline.

    Waits (no timeout) until the job_stages row is terminal, streams the
    stage's playbook log live when ``debug_mode`` is true (otherwise prints
    ``tail -f <log>``), then checks the DB row and the API stage. The build
    ``upload`` stage also checks the committed catalog reached the host.

    Returns:
        Dict with keys: success, fields, failures, blocked, mode.
    """
    gate = _gate(pipeline, stage)
    if gate:
        return gate
    state = STATE[pipeline]
    result = _result(state["mode"])
    result["fields"].extend([("Job ID", state["job_id"]), ("Stage", stage)])
    monitor = pipeline_monitor_func.monitor_stages(host, state, [stage], settings, emit)
    result["fields"].extend(monitor["fields"])
    result["failures"].extend(monitor["failures"])
    if not monitor["success"]:
        result["failures"].append(monitor["error"])
    item = (monitor["results"] or [{}])[0]
    if item.get("state") != STAGE_COMPLETED and not result["failures"]:
        result["failures"].append(f"stage '{stage}' finished as {item.get('state')}")
    if stage == VALIDATE_STAGE and item.get("state") == STAGE_COMPLETED:
        _check_test_summary(host, state["job_id"], result)
    return _finish(result, state, stage)


def _check_test_summary(host: Any, job_id: str, result: Dict[str, Any]) -> None:
    """Check the validate stage ran tests: some passed and none failed or errored.

    The watcher already fails the stage on failures, errors or an all-zero
    summary; a run where every test was skipped still completes, so this
    also requires at least one passed test.
    """
    summary = db_func.stage_test_summary(host, job_id, VALIDATE_STAGE)
    if summary is None:
        result["fields"].append((mark(False, "Validate test summary"), "not recorded"))
        result["failures"].append("validate stage has no result_detail.test_summary")
        return
    ok = (summary["total"] > 0 and summary["passed"] > 0
          and summary["failed"] == 0 and summary["errors"] == 0)
    result["fields"].append((mark(ok, "Validate test summary"),
                             ", ".join(f"{key}={value}" for key, value in summary.items())))
    if not ok:
        result["failures"].append(
            f"validate test summary is not a clean run: total={summary['total']}, "
            f"passed={summary['passed']}, failed={summary['failed']}, "
            f"errors={summary['errors']}, skipped={summary['skipped']}")


def _records_step(host: Any, pipeline: str, step: str, settings: Dict[str, Any],
                  emit: Emit) -> Dict[str, Any]:
    """Verify the GitLab pipeline result and the job-level DB/API records.

    The accepted image group statuses come from ``RECORD_GROUP_STATUSES[step]``.
    """
    gate = _gate(pipeline, step)
    if gate:
        return gate
    state = STATE[pipeline]
    result = _result(state["mode"])
    watched = state["watched"]
    if watched:
        final = pipeline_monitor_func.wait_pipeline_finished(
            state["context"], watched[-1], _FINISH_TIMEOUT, settings["poll_interval"], emit)
        result["fields"].append((mark(final["success"], f"GitLab pipeline #{watched[-1]}"),
                                 final["status"]))
        if not final["success"]:
            result["failures"].append(final["error"])
    records = pipeline_monitor_func.verify_job_records(host, state,
                                                       RECORD_GROUP_STATUSES[step])
    result["fields"].extend(records["fields"])
    result["failures"].extend(records["failures"])
    if records.get("image_group"):
        state["group_id"] = records["image_group"].get("id", state.get("group_id", ""))
    return _finish(result, state, step)


# =============================================================================
# Build pipeline (build: automatic, build_manual: PIPELINE_TYPE=build)
# =============================================================================

def start_build_pipeline(host: Any, pipeline: str, settings: Dict[str, Any],
                         emit: Emit) -> Dict[str, Any]:
    """Commit the selected catalog (next unused version) and wait for the job.

    ``build``: the catalog commit auto-triggers build_pipeline.
    ``build_manual``: the catalog is committed with ``[skip ci]`` and
    ``PIPELINE_TYPE=build`` is triggered through the API.
    Verify-only mode (pipeline.<suite>_job_id set) commits nothing and uses
    that job.

    Returns:
        Dict with keys: success, fields, failures, blocked, mode.
    """
    block = settings[JOB_ID_KEY[pipeline]]
    verify_only = bool(block["job_id"])
    result = _result(_mode(pipeline, verify_only))
    STATE[pipeline] = {"success": False, "job_id": "", "image_group_id": ""}
    context = _context(host, result)
    if context is None:
        result["blocked"] = False
        return result
    ids = (_verify_only_ids(host, block, emit) if verify_only
           else _trigger_build(host, context, settings, result, emit))
    result["fields"].extend([("Job ID", ids.get("job_id") or "-"),
                             ("Pipeline ID", ids.get("pipeline_id") or "-"),
                             ("Build child pipeline", ids.get("child_id") or "-")])
    if ids["error"]:
        result["failures"].append(ids["error"])
        result.update(success=False, blocked=False)
        return result
    STATE[pipeline].update(
        context=context, mode=result["mode"], job_id=ids["job_id"],
        group_id=ids.get("group_id", ""),
        watched=[pid for pid in (ids.get("pipeline_id"), ids.get("child_id")) if pid],
        stage_checks=ids.get("stage_checks"), failed_step="")
    return _finish(result, STATE[pipeline], "trigger")


def verify_build_result(host: Any, pipeline: str, settings: Dict[str, Any],
                        emit: Emit) -> Dict[str, Any]:
    """Verify the build GitLab pipeline result, job, image group and images.

    Returns:
        Dict with keys: success, fields, failures, blocked, mode.
    """
    result = _records_step(host, pipeline, "build result", settings, emit)
    state = STATE.get(pipeline) or {}
    state["image_group_id"] = state.get("group_id", "")
    state["success"] = result["success"] and not state.get("failed_step")
    return result


def _masked(client_id: str) -> str:
    """Return a client ID shortened for output (GitLab masks the variable)."""
    if not client_id:
        return "-"
    return f"{client_id[:len(BSM_CLIENT_ID_PREFIX)]}... ({len(client_id)} chars)"


def verify_oauth_client(host: Any, pipeline: str, settings: Dict[str, Any],
                        emit: Emit) -> Dict[str, Any]:
    """Verify the build pipeline's OAuth client is registered and created the job.

    The build initialization job registers a client (POST /api/v1/auth/register)
    and stores BSM_CLIENT_ID / BSM_CLIENT_SECRET as GitLab CI/CD variables.
    Checks: both variables exist (keys only; the secret is never read),
    BSM_CLIENT_ID holds a BuildStream client ID, and jobs.client_id of the
    build job is that client.

    Returns:
        Dict with keys: success, fields, failures, blocked, mode.
    """
    del settings, emit
    gate = _gate(pipeline, "OAuth client")
    if gate:
        return gate
    state = STATE[pipeline]
    result = _result(state["mode"])
    keys = set(gitlab_api_func.ci_variable_keys(state["context"]))
    missing = [key for key in BSM_CI_CLIENT_VARIABLES if key not in keys]
    result["fields"].append((mark(not missing, "GitLab CI/CD variables "
                                  + ", ".join(BSM_CI_CLIENT_VARIABLES)),
                             "set" if not missing else f"MISSING {', '.join(missing)}"))
    if missing:
        result["failures"].append(STEP_MSGS["oauth_variables_missing"].format(
            keys=", ".join(missing)))
        return _finish(result, state, "OAuth client")
    variable = gitlab_api_func.ci_variable_value(state["context"], BSM_CI_CLIENT_ID_VAR)
    ci_client = variable["value"]
    format_ok = variable["success"] and ci_client.startswith(BSM_CLIENT_ID_PREFIX)
    result["fields"].append((mark(format_ok, f"{BSM_CI_CLIENT_ID_VAR} client ID"),
                             _masked(ci_client) if variable["success"] else variable["error"]))
    if not variable["success"]:
        result["failures"].append(STEP_MSGS["oauth_client_id_unreadable"].format(
            key=BSM_CI_CLIENT_ID_VAR, error=variable["error"]))
        return _finish(result, state, "OAuth client")
    if not format_ok:
        result["failures"].append(STEP_MSGS["oauth_client_id_format"].format(
            key=BSM_CI_CLIENT_ID_VAR, prefix=BSM_CLIENT_ID_PREFIX))
    job_client = db_func.job_client_id(host, state["job_id"])
    same = job_client == ci_client
    result["fields"].append((mark(same, f"DB jobs.client_id of job {state['job_id']}"),
                             "matches BSM_CLIENT_ID" if same else _masked(job_client or "")))
    if job_client is None:
        result["failures"].append(STEP_MSGS["oauth_job_client_unreadable"].format(
            job_id=state["job_id"]))
    elif not same:
        result["failures"].append(STEP_MSGS["oauth_job_client_mismatch"].format(
            job_id=state["job_id"], job_client=_masked(job_client), ci_client=_masked(ci_client)))
    return _finish(result, state, "OAuth client")


# =============================================================================
# Deploy pipeline (deploy: PXE mapping commit, deploy_manual: PIPELINE_TYPE=deploy)
# =============================================================================

def start_deploy_pipeline(host: Any, pipeline: str, settings: Dict[str, Any],
                          emit: Emit) -> Dict[str, Any]:
    """Start the deploy pipeline for an image group and wait for its child pipeline.

    When a build suite ran in this session the image group is the one it
    built (``deploy`` <- ``build``, ``deploy_manual`` <- ``build_manual``,
    else the other build suite); when that build failed, this step and every
    later deploy step are skipped. A deploy-only run deploys
    pipeline.deploy_image_group_id of test_config.yml and fails when it is
    not set or not in build_stream_db.
    ``deploy``: swaps two PXE mapping rows in GitLab; the commit
    auto-triggers deploy_pipeline.
    ``deploy_manual``: triggers ``PIPELINE_TYPE=deploy`` through the API.
    Verify-only mode (pipeline.<suite>_job_id set) changes nothing.

    Returns:
        Dict with keys: success, fields, failures, blocked, mode.
    """
    block = settings[JOB_ID_KEY[pipeline]]
    verify_only = bool(block["job_id"])
    result = _result(_mode(pipeline, verify_only))
    STATE[pipeline] = {"success": False}
    build_key = "" if verify_only else _session_build(pipeline)
    if build_key and not STATE[build_key].get("success", False):
        STATE[pipeline]["skip_reason"] = STEP_MSGS["build_failed"].format(build=build_key)
        return _blocked("trigger", STATE[pipeline]["skip_reason"])
    context = _context(host, result)
    if context is None:
        result["blocked"] = False
        return result
    state = {"context": context, "mode": result["mode"], "failed_step": "", "watched": []}
    if verify_only:
        ids = _verify_only_ids(host, block, emit)
        group = db_func.image_group_for_job(host, block["job_id"]) or {}
        state.update(job_id=ids["job_id"], group_id=group.get("id", ""))
        result["fields"].extend([("Job ID", ids["job_id"]),
                                 ("Image group", group.get("id") or "-")])
        if ids["error"]:
            result["failures"].append(ids["error"])
        STATE[pipeline] = state
        return _finish(result, state, "trigger")
    target = _deploy_target(host, settings, build_key, emit)
    if target["error"]:
        result["failures"].append(target["error"])
        result["blocked"] = False
        return result
    group = target["group"]
    state.update(job_id=group["job_id"], group_id=group["id"],
                 baseline=db_func.get_stages(host, group["job_id"]),
                 min_deploy_count=int(group["deploy_count"] or 0) + 1)
    result["fields"].extend([("Image group", group["id"]),
                             ("Image group source", target["source"]),
                             ("Image group status", group["status"]),
                             ("Job ID", group["job_id"])])
    STATE[pipeline] = state
    error = _start_deploy(settings, group, result, state, emit)
    if error:
        result["failures"].append(error)
    return _finish(result, state, "trigger")


def _session_build(pipeline: str) -> str:
    """Return the build suite that ran in this session for ``pipeline`` ("" = none).

    The matching build suite wins; otherwise the other one is used.
    """
    preferred = DEPLOY_BUILD_SOURCE[pipeline]
    for build_key in (preferred, *(key for key in DEPLOY_BUILD_SOURCE.values()
                                   if key != preferred)):
        if build_key in STATE:
            return build_key
    return ""


def _start_deploy(settings: Dict[str, Any], group: Dict[str, str], result: Dict[str, Any],
                  state: Dict[str, Any], emit: Emit) -> str:
    """Trigger the deploy pipeline (PXE swap commit or API) and wait for its child.

    ``state["mode"]`` (from ``_mode``) tells the suites apart: "manual
    trigger" uses the API, the automatic one commits a PXE mapping swap.
    """
    context, manual = state["context"], state["mode"] == "manual trigger"
    if group["status"] != IMAGE_GROUP_BUILT:
        return (f"image group {group['id']} is {group['status']}; the deploy pipeline "
                f"only offers {IMAGE_GROUP_BUILT} groups")
    action = ("triggering PIPELINE_TYPE=deploy" if manual
              else f"changing {GITLAB_PXE_MAPPING_FILE}")
    busy = pipeline_monitor_func.ensure_no_busy_pipelines(
        context, settings["allow_pipeline_cancel"], emit, action)
    result["fields"].extend(busy["fields"])
    if not busy["success"]:
        return busy["error"]
    commit_id = ""
    if not manual:
        commit = _commit_pxe_swap(context, result, emit)
        if commit["error"]:
            return commit["error"]
        commit_id = commit["commit_id"]
    started = trigger_pipeline(context, PipelineTrigger(commit_id, "deploy", "PXE mapping"),
                               result, emit)
    if not started["success"]:
        return started["error"]
    parent_id = started["pipeline_id"]
    child = gitlab_api_func.wait_for_downstream(context, parent_id, GITLAB_BRIDGE_DEPLOY, emit)
    if not child["success"]:
        return child["error"]
    state.update(pipeline_id=parent_id, child_id=child["pipeline"]["id"], watched=[parent_id])
    result["fields"].append((mark(True, "Deploy child pipeline"), f"#{child['pipeline']['id']}"))
    return ""


def _commit_pxe_swap(context: Dict[str, Any], result: Dict[str, Any],
                     emit: Emit) -> Dict[str, str]:
    """Swap two PXE mapping rows in GitLab. Returns commit_id and error."""
    current = gitlab_api_func.get_file(context, GITLAB_PXE_MAPPING_FILE)
    if not current["success"]:
        return {"commit_id": "", "error": f"{GITLAB_PXE_MAPPING_FILE}: {current['error']}"}
    swapped = pipeline_monitor_func.swap_pxe_rows(current["content"])
    if not swapped["success"]:
        return {"commit_id": "", "error": swapped["error"]}
    first, second = swapped["rows"]
    emit(PROGRESS["pxe_rows_swapping"].format(first=first, second=second,
                                             file=GITLAB_PXE_MAPPING_FILE))
    commit = gitlab_api_func.commit_file(context, GITLAB_PXE_MAPPING_FILE, swapped["content"],
                                     COMMIT_MESSAGE_DEPLOY.format(first=first, second=second))
    if not commit["success"]:
        return {"commit_id": "", "error": f"commit failed: {commit['error']}"}
    result["fields"].extend([("PXE rows swapped", f"{first} <-> {second}"),
                             ("Commit", commit["commit_id"])])
    return {"commit_id": commit["commit_id"], "error": ""}


def select_deploy_image(host: Any, pipeline: str, settings: Dict[str, Any],
                        emit: Emit) -> Dict[str, Any]:
    """Play the select_image job of the image group and verify the selection.

    The select job must succeed and its log must name the image group and
    its build job ID (the image that will be deployed).

    Returns:
        Dict with keys: success, fields, failures, blocked, mode.
    """
    del host, settings
    gate = _gate(pipeline, "select image")
    if gate:
        return gate
    state = STATE[pipeline]
    result = _result(state["mode"])
    if state["mode"] == "verify-only":
        result["fields"].append(("Image group", state.get("group_id") or "-"))
        result["blocked"] = True
        result["failures"].append(STEP_MSGS["verify_only_nothing"].format(step="image selection"))
        return result
    context = state["context"]
    grandchild = gitlab_api_func.wait_for_downstream(
        context, state["child_id"], GITLAB_BRIDGE_DEPLOY_CHILD, emit, SELECT_JOBS_TIMEOUT)
    if not grandchild["success"]:
        result["failures"].append(grandchild["error"])
        return _finish(result, state, "select image")
    select_pipeline = grandchild["pipeline"]["id"]
    emit(PROGRESS["image_selection_pipeline"].format(pipeline_id=select_pipeline))
    jobs = wait_jobs(context, select_pipeline, GITLAB_SELECT_IMAGE_STAGE)
    available = [job.get("name") for job in jobs]
    result["fields"].extend([("Selection pipeline", f"#{select_pipeline}"),
                             ("Offered image groups", ", ".join(available) or "-")])
    selected = play_and_wait(context, select_pipeline, jobs, state["group_id"], emit)
    result["fields"].extend(selected["fields"])
    if selected["error"]:
        result["failures"].append(selected["error"])
        return _finish(result, state, "select image")
    _check_select_trace(gitlab_api_func.job_trace(context, selected["job_id"]), state, result)
    state.update(select_pipeline=select_pipeline, watched=[state["pipeline_id"], select_pipeline])
    return _finish(result, state, "select image")


def _check_select_trace(trace: str, state: Dict[str, Any], result: Dict[str, Any]) -> None:
    """Check the select job log names the image group and its build job ID."""
    for label, value in (("image group", state["group_id"]), ("build job ID", state["job_id"])):
        found = value in trace
        result["fields"].append((mark(found, f"select job log names the {label}"), value))
        if not found:
            result["failures"].append(f"select job log does not mention {label} {value}")


def play_and_wait(context: Dict[str, Any], pipeline_id: int, jobs: List[Dict[str, Any]],
                  name: str, emit: Emit) -> Dict[str, Any]:
    """Play the manual job ``name`` among ``jobs`` and wait until it succeeds.

    Returns:
        Dict with keys: job_id, fields, error.
    """
    target = [job for job in jobs if job.get("name") == name]
    if not target:
        return {"job_id": 0, "fields": [], "error": STEP_MSGS["deploy_image_not_offered"].format(
            group_id=name, offered=", ".join(job.get("name", "") for job in jobs) or "none")}
    job = target[0]
    if job.get("status") == GITLAB_MANUAL:
        played = gitlab_api_func.play_job(context, job["id"])
        if not played["success"]:
            return {"job_id": job["id"], "fields": [],
                    "error": f"cannot play job '{name}': {played['error']}"}
    emit(PROGRESS["image_group_selected"].format(group_id=name, job_id=job["id"]))
    status = pipeline_monitor_func.wait_job_status(
        context, (pipeline_id, job["id"]), (GITLAB_SUCCESS,), SELECT_JOBS_TIMEOUT, emit)
    fields = [(mark(status == GITLAB_SUCCESS, f"GitLab job '{name}' #{job['id']}"), status)]
    error = "" if status == GITLAB_SUCCESS else f"job '{name}' #{job['id']} finished as {status}"
    return {"job_id": job["id"], "fields": fields, "error": error}


def wait_jobs(context: Dict[str, Any], pipeline_id: int, stage: str) -> List[Dict[str, Any]]:
    """Wait until the pipeline lists jobs of ``stage`` (or the timeout passes)."""
    deadline = time.time() + SELECT_JOBS_TIMEOUT
    jobs: List[Dict[str, Any]] = []
    while time.time() < deadline and not jobs:
        jobs = gitlab_api_func.find_job(gitlab_api_func.pipeline_jobs(context, pipeline_id),
                                        stage=stage)
        if not jobs:
            time.sleep(PIPELINE_DETECT_INTERVAL)
    return jobs


def run_deploy_stage(host: Any, pipeline: str, settings: Dict[str, Any],
                     emit: Emit) -> Dict[str, Any]:
    """Play the manual deploy job, then monitor and verify the deploy stage.

    Returns:
        Dict with keys: success, fields, failures, blocked, mode.
    """
    gate = _gate(pipeline, "deploy")
    if gate:
        return gate
    state = STATE[pipeline]
    played_fields = []
    if state["mode"] != "verify-only":
        context = state["context"]
        jobs = gitlab_api_func.find_job(
            gitlab_api_func.pipeline_jobs(context, state["select_pipeline"]),
            name=GITLAB_DEPLOY_JOB)
        if not jobs:
            result = _result(state["mode"])
            result["failures"].append(
                f"no '{GITLAB_DEPLOY_JOB}' job in pipeline #{state['select_pipeline']}")
            return _finish(result, state, "deploy")
        job = jobs[0]
        if job.get("status") == GITLAB_MANUAL:
            played = gitlab_api_func.play_job(context, job["id"])
            if not played["success"]:
                result = _result(state["mode"])
                result["failures"].append(f"cannot play deploy job: {played['error']}")
                return _finish(result, state, "deploy")
        emit(PROGRESS["deploy_job_started"].format(job_id=job["id"]))
        played_fields.append((mark(True, "GitLab deploy job played"), f"#{job['id']}"))
    result = run_stage_step(host, pipeline, "deploy", settings, emit)
    result["fields"][1:1] = played_fields
    return result


def verify_restart_node_results(host: Any, pipeline: str, settings: Dict[str, Any],
                                emit: Emit) -> Dict[str, Any]:
    """Verify the restart node-result artifacts the API serves for the job.

    ``node-results`` must list the nodes for this job; a ``failed-nodes``
    artifact is optional, and when present every node in it must be failed
    in ``node-results``.

    Returns:
        Dict with keys: success, fields, failures, blocked, mode.
    """
    del host, settings, emit
    gate = _gate(pipeline, "restart node results")
    if gate:
        return gate
    state = STATE[pipeline]
    result = _result(state["mode"])
    nodes = get_api_artifact(state["context"], state["job_id"], "node-results")
    data = nodes.get("data") if isinstance(nodes.get("data"), dict) else {}
    node_list = data.get("nodes") if isinstance(data.get("nodes"), list) else []
    ok = nodes["exists"] and data.get("job_id") == state["job_id"]
    result["fields"].append((mark(ok, "node-results artifact"),
                             f"{len(node_list)} node(s)" if ok
                             else nodes.get("error") or "missing or for another job"))
    if not ok:
        result["failures"].append(nodes.get("error") or "node-results artifact invalid")
    status = {item.get("bmc_ip"): item.get("status") for item in node_list
              if isinstance(item, dict)}
    for bmc_ip, node_status in status.items():
        result["fields"].append((mark(True, f"Node {bmc_ip}"), node_status))
    _check_failed_nodes(state, status, result)
    if ok:
        coverage = check_node_coverage(host, state["context"], state["job_id"], data)
        result["fields"].extend(coverage["fields"])
        result["failures"].extend(coverage["failures"])
    return _finish(result, state, "restart node results")


def _check_failed_nodes(state: Dict[str, Any], status: Dict[Any, Any],
                        result: Dict[str, Any]) -> None:
    """Check every node in the optional failed-nodes artifact is failed in node-results."""
    failed = get_api_artifact(state["context"], state["job_id"], "failed-nodes")
    failed_nodes = (failed.get("data") or {}).get("failed_nodes", []) if failed["exists"] else []
    inconsistent = [item.get("bmc_ip") for item in failed_nodes
                    if not isinstance(item, dict) or status.get(item.get("bmc_ip")) != "failed"]
    result["fields"].append((mark(not inconsistent, "failed-nodes artifact"),
                             "absent (no failed nodes)" if not failed["exists"]
                             else f"{len(failed_nodes)} failed node(s)"))
    if inconsistent:
        result["failures"].append(f"failed-nodes inconsistent with node-results: {inconsistent}")


def verify_deploy_result(host: Any, pipeline: str, settings: Dict[str, Any],
                         emit: Emit) -> Dict[str, Any]:
    """Verify the deploy pipeline result, summary job, image group and API job.

    The image group must be PASSED with an incremented deploy_count, and
    the GitLab summary job log must report ``RESULT:  PASSED``.

    Returns:
        Dict with keys: success, fields, failures, blocked, mode.
    """
    result = _records_step(host, pipeline, "deploy result", settings, emit)
    state = STATE.get(pipeline) or {}
    if result.get("blocked") or not state.get("select_pipeline"):
        state["success"] = result["success"]
        return result
    context = state["context"]
    jobs = gitlab_api_func.find_job(
        gitlab_api_func.pipeline_jobs(context, state["select_pipeline"]),
                                name=GITLAB_SUMMARY_JOB)
    trace = gitlab_api_func.job_trace(context, jobs[0]["id"]) if jobs else ""
    passed = GITLAB_SUMMARY_PASSED in trace
    result["fields"].append((mark(passed, f"GitLab {GITLAB_SUMMARY_JOB} job"),
                             "RESULT: PASSED" if passed
                             else ("job not found" if not jobs else "PASSED not reported")))
    if not passed:
        result["failures"].append(f"{GITLAB_SUMMARY_JOB} job does not report PASSED")
    result = _finish(result, state, "deploy result")
    state["success"] = result["success"] and not state.get("failed_step")
    return result


def verify_job_image_group_mapping(host: Any, pipeline: str, settings: Dict[str, Any],
                                   emit: Emit) -> Dict[str, Any]:
    """Verify the deployed job maps to exactly one image group, the deployed one.

    image_groups.job_id is UNIQUE and image_groups.id is the composite
    catalog ID, so a job owns at most one image group; the deploy pipeline
    deploys that group by its (JOB_ID, IMAGE_GROUP_ID) pair.

    Returns:
        Dict with keys: success, fields, failures, blocked, mode.
    """
    del settings, emit
    gate = _gate(pipeline, "job to image group mapping")
    if gate:
        return gate
    state = STATE[pipeline]
    result = _result(state["mode"])
    job_id, expected = state["job_id"], state.get("group_id", "")
    rows = db_func.image_groups_for_job(host, job_id)
    groups = [group["id"] for group in rows["groups"]]
    result["fields"].append(("Job ID", job_id))
    if not rows["success"]:
        result["failures"].append(STEP_MSGS["job_group_unreadable"].format(
            job_id=job_id, error=rows["error"]))
        return _finish(result, state, "job to image group mapping")
    one = len(groups) == 1
    result["fields"].append((mark(one, "DB image_groups rows for the job"),
                             f"{len(groups)}: {', '.join(groups) or '-'}"))
    if not one:
        result["failures"].append(STEP_MSGS["job_group_count"].format(
            job_id=job_id, count=len(groups), groups=", ".join(groups) or "-"))
    elif expected:
        same = groups[0] == expected
        result["fields"].append((mark(same, "Deployed image group"), expected))
        if not same:
            result["failures"].append(STEP_MSGS["job_group_other"].format(
                job_id=job_id, found=groups[0], expected=expected))
    return _finish(result, state, "job to image group mapping")


# =============================================================================
# Cadence pipeline
# =============================================================================

def build_ran_once(host: Any, context: Dict[str, Any]) -> Dict[str, Any]:
    """Check that a build pipeline has run at least once.

    The first build pipeline registers the BuildStream OAuth client and
    stores BSM_CLIENT_ID / BSM_CLIENT_SECRET as GitLab CI/CD variables; the
    cadence pipeline authenticates with them. It also records the first
    image group in build_stream_db.

    Returns:
        Dict with keys: success, fields, failures.
    """
    keys = set(gitlab_api_func.ci_variable_keys(context))
    missing = [key for key in BSM_CI_CLIENT_VARIABLES if key not in keys]
    groups = db_func.image_group_count(host)
    checks = [
        ("GitLab CI/CD variables " + ", ".join(BSM_CI_CLIENT_VARIABLES),
         "set" if not missing else f"MISSING {', '.join(missing)}", not missing),
        ("Image groups in build_stream_db",
         str(groups["count"]) if groups["success"] else groups["error"],
         groups["success"] and groups["count"] > 0),
    ]
    failures = [f"{label}: {value}" for label, value, ok in checks if not ok]
    if failures:
        failures.append(STEP_MSGS["cadence_needs_build"])
    return {"success": not failures,
            "fields": [(mark(ok, label), value) for label, value, ok in checks],
            "failures": failures}


CADENCE_BUILD = "cadence_build"
CADENCE_BUILD_STAGES = ("upload", "parse-catalog", "create-local-repository", "build-image")
CADENCE_BUILD_FACTS = ("attempted", "success", "group_id", "job_id")


def _cadence_build(host: Any, context: Dict[str, Any], settings: Dict[str, Any],
                   result: Dict[str, Any], emit: Emit) -> str:
    """Build the cadence test's image group and record the outcome; return an error or "".

    The outcome (also a failed build) is saved as run state so an automated
    cleanup started in another process targets this image or skips cleanly.
    """
    error = _run_cadence_build(host, context, settings, result, emit)
    _save_cadence_build()
    return error


def _run_cadence_build(host: Any, context: Dict[str, Any], settings: Dict[str, Any],
                       result: Dict[str, Any], emit: Emit) -> str:
    """Build a new image group for the cadence test; return an error or "".

    The build suites' image group is deployed and validated by the deploy
    suites, so the cadence test (and the automated cleanup that follows it)
    works on its own image: the next unused catalog version is committed, the
    build pipeline runs through ``build-image`` and the image group must be
    BUILT. The outcome is recorded in ``STATE["cadence_build"]``.
    """
    STATE[CADENCE_BUILD] = {"attempted": True, "success": False, "group_id": "", "job_id": ""}
    clear_run_state(CADENCE_BUILD)
    build = _result("automatic trigger")
    ids = _trigger_build(host, context, settings, build, emit)
    result["fields"].extend(build["fields"])
    if ids.get("error"):
        return ids["error"]
    STATE[CADENCE_BUILD].update(
        context=context, mode=build["mode"], job_id=ids["job_id"], group_id=ids["group_id"],
        watched=[pid for pid in (ids.get("pipeline_id"), ids.get("child_id")) if pid],
        stage_checks=ids.get("stage_checks"), failed_step="")
    emit(PROGRESS["cadence_build_started"].format(group_id=ids["group_id"], job_id=ids["job_id"]))
    result["fields"].extend([("Cadence build image group", ids["group_id"]),
                             ("Cadence build job", ids["job_id"])])
    for stage in CADENCE_BUILD_STAGES:
        step = run_stage_step(host, CADENCE_BUILD, stage, settings, emit)
        result["fields"].extend(step["fields"][2:])
        if not step["success"]:
            return f"stage '{stage}': {'; '.join(step['failures'])}"
    records = _records_step(host, CADENCE_BUILD, "build result", settings, emit)
    result["fields"].extend(records["fields"][1:])
    if not records["success"]:
        return f"build result: {'; '.join(records['failures'])}"
    STATE[CADENCE_BUILD]["success"] = True
    return ""


def _save_cadence_build() -> None:
    """Record the cadence build outcome for an automated cleanup in another process."""
    build = STATE.get(CADENCE_BUILD) or {}
    save_run_state(CADENCE_BUILD, {key: build.get(key) for key in CADENCE_BUILD_FACTS})


def cadence_build_outcome() -> Dict[str, Any]:
    """Return this session's cadence build, else the one a previous process recorded.

    Returns:
        Dict with keys attempted, success, group_id, job_id ({} when no
        cadence build is known).
    """
    build = STATE.get(CADENCE_BUILD)
    if build:
        return build
    saved = load_run_state(CADENCE_BUILD)
    return saved["data"] if saved["success"] else {}


def start_cadence_pipeline(host: Any, settings: Dict[str, Any], emit: Emit) -> Dict[str, Any]:
    """Build a new image, trigger a cadence cycle and wait for the cadence pipeline and its job.

    First builds a dedicated new image group inside this test case (see
    ``_cadence_build``); a failed build fails the cadence test. The build also
    registers the OAuth client the cadence pipeline needs, so the check that a
    build pipeline ran at least once passes afterwards.
    Then: upload the selected catalog to cadence_catalog_rhel.json with
    ``[skip ci]`` one minor below the next unused version, run
    trigger_cadence.sh, follow the cycle in the playbook-watcher journal
    (repo sync log streamed with debug_mode), verify the bumped catalog was
    committed and the commit started cadence_pipeline and a job.
    Verify-only mode (pipeline.cadence_job_id set) triggers nothing.

    Returns:
        Dict with keys: success, fields, failures, blocked, mode.
    """
    block = settings["cadence"]
    verify_only = bool(block["job_id"])
    result = _result("verify-only" if verify_only else "trigger")
    STATE["cadence"] = {"success": False}
    context = _context(host, result)
    if context is None:
        result["blocked"] = False
        return result
    if verify_only:
        ids = _verify_only_ids(host, block, emit)
    else:
        error = _cadence_build(host, context, settings, result, emit)
        if error:
            result["failures"].append(STEP_MSGS["cadence_build_failed"].format(error=error))
            result["blocked"] = False
            return result
        ran = build_ran_once(host, context)
        result["fields"].extend(ran["fields"])
        if not ran["success"]:
            result["failures"].extend(ran["failures"])
            result["blocked"] = False
            return result
        ids = _trigger_cadence(host, context, settings, result, emit)
    result["fields"].extend([("Job ID", ids.get("job_id") or "-"),
                             ("Pipeline ID", ids.get("pipeline_id") or "-"),
                             ("Cadence child pipeline", ids.get("child_id") or "-")])
    if ids["error"]:
        result["failures"].append(ids["error"])
        result["blocked"] = False
        return result
    STATE["cadence"] = {
        "context": context, "mode": result["mode"], "job_id": ids["job_id"],
        "group_id": "", "failed_step": "", "success": False,
        "watched": [pid for pid in (ids.get("pipeline_id"), ids.get("child_id")) if pid]}
    return _finish(result, STATE["cadence"], "trigger")


def verify_cadence_result(host: Any, settings: Dict[str, Any], emit: Emit) -> Dict[str, Any]:
    """Verify the cadence GitLab pipeline result, image group PASSED and API job.

    Returns:
        Dict with keys: success, fields, failures, blocked, mode.
    """
    result = _records_step(host, "cadence", "cadence result", settings, emit)
    state = STATE.get("cadence") or {}
    state["success"] = result["success"] and not state.get("failed_step")
    return result


# =============================================================================
# Build outputs: Repo Manager and Image Build Manager
# =============================================================================

def verify_repo_manager_status(host: Any, pipeline: str, settings: Dict[str, Any],
                               emit: Emit) -> Dict[str, Any]:
    """Verify repo_status.yml written by create-local-repository reports success.

    Returns:
        Dict with keys: success, fields, failures, blocked, mode.
    """
    del settings, emit
    gate = _gate(pipeline, "repo_manager status")
    if gate:
        return gate
    state = STATE[pipeline]
    result = _result(state["mode"])
    status = check_repo_status(host)
    result["fields"].extend([
        ("File", status["path"] or "-"),
        (mark(status["success"], "overall_status"), status["overall_status"] or status["error"]),
    ])
    if not status["success"]:
        result["failures"].append(status["error"])
    return _finish(result, state, "repo_manager status")


def verify_image_build_artifacts(host: Any, pipeline: str, settings: Dict[str, Any],
                                 emit: Emit) -> Dict[str, Any]:
    """Verify every built role has its image in the registry and its boot files in S3.

    Roles come from the image group's images rows; build_status.yml names
    each role's image, kernel and initrd. The registry is listed with
    ``regctl`` and the boot-images bucket with ``s3cmd``.

    Returns:
        Dict with keys: success, fields, failures, blocked, mode.
    """
    del settings, emit
    gate = _gate(pipeline, "image_build_manager artifacts")
    if gate:
        return gate
    state = STATE[pipeline]
    result = _result(state["mode"])
    group = db_func.image_group_for_job(host, state["job_id"]) or {}
    group_id = group.get("id", "")
    roles = db_func.image_roles(host, group_id) if group_id else []
    result["fields"].extend([("Image group", group_id or "-"),
                             (mark(bool(roles), "Roles built"), ", ".join(roles) or "none")])
    if not roles:
        result["failures"].append(f"no image group or images for job {state['job_id']}")
        return _finish(result, state, "image_build_manager artifacts")
    artifacts = verify_build_artifacts(host, group_id, roles)
    for role in roles:
        in_registry, in_s3 = artifacts["registry"].get(role), artifacts["s3"].get(role)
        result["fields"].extend([
            (mark(bool(in_registry), f"Registry image {role}"),
             "present" if in_registry else "MISSING"),
            (mark(bool(in_s3), f"S3 boot files {role}"),
             "image, kernel, initrd" if in_s3 else "MISSING"),
        ])
        if not in_registry:
            result["failures"].append(f"registry image missing for {role}")
        if not in_s3:
            result["failures"].append(f"S3 boot files incomplete for {role}")
    result["failures"].extend(artifacts["errors"])
    return _finish(result, state, "image_build_manager artifacts")
