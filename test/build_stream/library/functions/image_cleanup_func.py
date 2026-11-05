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

"""Image cleanup as one test case per step: cleanup pipeline and automated cleanup.

Cleanup pipeline (``PIPELINE_TYPE=cleanup``, .gitlab-ci-cleanup.yml):
    build      build a dedicated image group (no build when
               pipeline.cleanup_image_group_id is set); a failed build fails
               the step and the start step is skipped with that reason
    start      take that image group, record its S3 objects, registry tags and
               NFS artifacts, trigger the pipeline through the API and play
               the image group's select_image job
    cleanup    play the manual cleanup job (DELETE /api/v1/jobs/<job>), follow
               the image group CLEANING -> CLEANED with the cleanup playbook
               log (streamed with debug_mode), then the cleanup and summary jobs
    db         image group CLEANED, job tombstoned, cleanup audit events
    s3         no boot-images object of the group is left
    registry   no registry tag of the group is left
    nfs        the job's NFS artifact directory is removed

Automated cleanup (``cleanup_cron.main()``, run by AutoCleanupScheduler):
    precheck   retention settings valid, BuildStream container, playbook-watcher
    build      build a dedicated image group (no build when
               pipeline.auto_cleanup_image_group_id is set); a failed build
               fails the step and blocks the pass
    run        mark that image group FAILED in build_stream_db, then one pass:
               every FAILED group (and retention candidates) is submitted; wait
               until none is CLEANING (log streamed)
    db         exactly the expected groups CLEANED, tombstoned, audited
    artifacts  their S3 objects, registry tags and NFS artifacts removed,
               others untouched

Every function returns a result dict with keys: success, fields, failures,
blocked (True when a previous step failed or there is nothing to do).
"""

import time
from typing import Any, Callable, Dict, List, NamedTuple

from . import db_func, gitlab_api_func, pipeline_monitor_func
from .auto_cleanup_func import (
    follow_cleanup_log,
    matching,
    precheck_auto_cleanup,
    run_auto_cleanup,
    s3_keys,
    tombstone_value,
    verify_auto_cleanup_artifacts,
    verify_auto_cleanup_db,
)
from .pipeline_trigger_func import PipelineTrigger, _context, _result, trigger_pipeline
from .state_func import clear_run_state
from .log_func import LogFollower, mark
from .execute_probe_func import data_path, path_exists, run_cmd, summarize
from .pipeline_steps_func import (
    AUTO_CLEANUP_BUILD, PIPELINE_CLEANUP_BUILD, _blocked, _finish, _gate, dedicated_build,
    dedicated_build_outcome, play_and_wait, wait_jobs,
)
from ..messages.execute_msgs import PROGRESS_MSGS as PROGRESS
from ..messages.execute_msgs import STEP_MSGS
from ..vars.execute_vars import (
    AUDIT_CLEANED,
    AUDIT_CLEANUP_FAILED,
    AUDIT_CLEANUP_SUBMITTED,
    CLEANUP_JOB_TIMEOUT,
    GITLAB_BRIDGE_CLEANUP,
    GITLAB_BRIDGE_CLEANUP_CHILD,
    GITLAB_CLEANUP_JOB,
    GITLAB_CLEANUP_SUMMARY_SUCCESS,
    GITLAB_FAILED_STATUSES,
    GITLAB_MANUAL,
    GITLAB_SELECT_IMAGE_STAGE,
    GITLAB_SUCCESS,
    GITLAB_SUMMARY_JOB,
    IMAGE_GROUP_CLEANABLE,
    IMAGE_GROUP_CLEANED,
    IMAGE_GROUP_CLEANUP_FAILED,
    NFS_ARTIFACTS_DIR,
    SELECT_JOBS_TIMEOUT,
)
from ..vars.common_vars import REGISTRY_PORT

Emit = Callable[[str], None]
STATE = pipeline_monitor_func.PIPELINE_STATE
_CLEANUP = "cleanup"
_AUTO = "auto_cleanup"


# =============================================================================
# Storage snapshots
# =============================================================================

def registry_tags(host: Any, group_id: str) -> Dict[str, Any]:
    """Return the registry tags of every repository of ``group_id``.

    Image cleanup deletes the tags (manifests) and keeps the repository
    directories, so a repository with no tag left counts as cleaned.

    Returns:
        Dict with keys: success, tags ({repo: [tags]}), error.
    """
    registry = f"{run_cmd(host, 'hostname').stdout.strip()}:{REGISTRY_PORT}"
    repos = run_cmd(host, "regctl_repo_ls", registry=registry)
    if repos.rc != 0:
        return {"success": False, "tags": {},
                "error": f"regctl repo ls {registry} failed (rc={repos.rc})"}
    tags = {}
    for repo in matching([line.strip() for line in repos.stdout.splitlines()], group_id):
        listed = run_cmd(host, "regctl_tag_ls", registry=registry, repo=repo)
        tags[repo] = [line.strip() for line in listed.stdout.splitlines()
                      if listed.rc == 0 and line.strip()]
    return {"success": True, "tags": tags, "error": ""}


def _nfs_dir(host: Any, job_id: str) -> str:
    """Return the job's NFS artifact directory."""
    return f"{data_path(host)}/{NFS_ARTIFACTS_DIR}/{job_id}"


def _skip(key: str, step: str, message: str) -> Dict[str, Any]:
    """Record why the rest of suite ``key`` has nothing to do and block ``step``."""
    STATE[key] = {"skip_reason": message}
    return _blocked(step, message)


def _suite_gate(key: str, step: str) -> Dict[str, Any]:
    """Like ``_gate``, but repeats the reason when the suite had nothing to do."""
    reason = (STATE.get(key) or {}).get("skip_reason")
    return _blocked(step, reason) if reason else _gate(key, step)


# =============================================================================
# Cleanup pipeline
# =============================================================================

def _cleanup_target(host: Any, settings: Dict[str, Any],
                    key: str = "cleanup_image_group_id") -> Dict[str, Any]:
    """Resolve the image group to clean from ``pipeline.<key>`` (else the first image).

    The first image is the newest BUILT/PASSED/FAILED group, the one the cleanup
    pipeline lists first.

    Returns:
        Dict with keys: group (or None), source, error, nothing (no group to clean).
    """
    wanted = settings.get(key, "")
    if not wanted:
        group = db_func.newest_cleanable_image_group(host)
        return {"group": group, "source": "first BUILT/PASSED/FAILED image group",
                "error": "", "nothing": group is None}
    group = db_func.image_group(host, wanted)
    source = f"pipeline.{key} in test_config.yml"
    if group is None:
        return {"group": None, "source": source, "nothing": False,
                "error": f"image group {wanted} (pipeline.{key}) is not in "
                         "build_stream_db"}
    if group["status"] == IMAGE_GROUP_CLEANED:
        return {"group": None, "source": source, "nothing": True, "error": ""}
    if group["status"] not in IMAGE_GROUP_CLEANABLE:
        return {"group": None, "source": source, "nothing": False,
                "error": f"image group {wanted} is {group['status']}; the cleanup API accepts "
                         f"only {', '.join(IMAGE_GROUP_CLEANABLE)}"}
    return {"group": group, "source": source, "error": "", "nothing": False}


def _pipeline_cleanup_target(host: Any, settings: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve the image group the cleanup pipeline deletes.

    It is ``pipeline.cleanup_image_group_id`` when set, else the group the
    suite's image build test built (this session or a previous process).

    Returns:
        Dict with keys: target (see ``_cleanup_target``), skip (reason the suite has
        nothing to do, else ""), error ("" when the group is usable).
    """
    key = "cleanup_image_group_id"
    built = {} if settings.get(key) else dedicated_build_outcome(PIPELINE_CLEANUP_BUILD)
    if not settings.get(key) and built.get("attempted") and not built.get("success"):
        return {"target": None, "error": "", "skip": STEP_MSGS["pipeline_cleanup_build_skip"]}
    if not settings.get(key) and not built.get("success"):
        return {"target": None, "skip": "",
                "error": STEP_MSGS["pipeline_cleanup_no_build"].format(key=key)}
    wanted = settings.get(key) or built["group_id"]
    target = _cleanup_target(host, {**settings, key: wanted})
    if built:
        target["source"] = "image built for the cleanup pipeline"
    skip = (STEP_MSGS["cleanup_already_cleaned"].format(group_id=wanted, key=key)
            if target["nothing"] else "")
    return {"target": target, "skip": skip, "error": target["error"]}


def start_pipeline_cleanup(host: Any, settings: Dict[str, Any], emit: Emit) -> Dict[str, Any]:
    """Pick the image group, trigger PIPELINE_TYPE=cleanup and select the group.

    Returns:
        Dict with keys: success, fields, failures, blocked, mode.
    """
    result = _result("manual trigger (PIPELINE_TYPE=cleanup)")
    STATE[_CLEANUP] = {}
    context = _context(host, result)
    if context is None:
        result["blocked"] = False
        return result
    pick = _pipeline_cleanup_target(host, settings)
    if pick["skip"]:
        return _skip(_CLEANUP, "cleanup target", pick["skip"])
    if pick["error"]:
        result["failures"].append(pick["error"])
        result["blocked"] = False
        return result
    target = pick["target"]
    group = target["group"]
    emit(PROGRESS["cleanup_target"].format(group_id=group["id"], job_id=group["job_id"],
                                           status=group["status"], source=target["source"]))
    try:
        keys = matching(s3_keys(host), group["id"])
    except RuntimeError as exc:
        result["failures"].append(str(exc))
        result["blocked"] = False
        return result
    tags = registry_tags(host, group["id"])
    nfs = _nfs_dir(host, group["job_id"])
    state = {"context": context, "mode": result["mode"], "failed_step": "", "watched": [],
             "group_id": group["id"], "job_id": group["job_id"], "status": group["status"],
             "roles": db_func.image_roles(host, group["id"]), "s3_before": keys,
             "registry_before": tags["tags"], "nfs_dir": nfs,
             "nfs_before": path_exists(host, nfs), "epoch": db_func.db_now_epoch(host)}
    STATE[_CLEANUP] = state
    result["fields"].extend([
        ("Image group", group["id"]), ("Image group source", target["source"]),
        ("Image group status", group["status"]), ("Job ID", group["job_id"]),
        ("Roles", ", ".join(state["roles"]) or "none"),
        ("S3 objects before", len(keys)),
        ("Registry tags before", sum(len(items) for items in tags["tags"].values())),
        ("NFS artifacts before", f"{nfs} ({'present' if state['nfs_before'] else 'absent'})"),
    ])
    error = _trigger_and_select(context, settings, state, result, emit)
    if error:
        result["failures"].append(error)
    return _finish(result, state, "trigger")


def _trigger_and_select(context: Dict[str, Any], settings: Dict[str, Any],
                        state: Dict[str, Any], result: Dict[str, Any], emit: Emit) -> str:
    """Trigger the cleanup pipeline and play the target's select_image job."""
    busy = pipeline_monitor_func.ensure_no_busy_pipelines(
        context, settings["allow_pipeline_cancel"], emit, "triggering PIPELINE_TYPE=cleanup")
    result["fields"].extend(busy["fields"])
    if not busy["success"]:
        return busy["error"]
    started = trigger_pipeline(context, PipelineTrigger("", "cleanup", ""), result, emit)
    if not started["success"]:
        return started["error"]
    parent_id = started["pipeline_id"]
    child = gitlab_api_func.wait_for_downstream(context, parent_id, GITLAB_BRIDGE_CLEANUP, emit)
    if not child["success"]:
        return child["error"]
    select = gitlab_api_func.wait_for_downstream(context, child["pipeline"]["id"],
                                             GITLAB_BRIDGE_CLEANUP_CHILD, emit,
                                             SELECT_JOBS_TIMEOUT)
    if not select["success"]:
        return select["error"]
    select_id = select["pipeline"]["id"]
    jobs = wait_jobs(context, select_id, GITLAB_SELECT_IMAGE_STAGE)
    result["fields"].extend([("Cleanup child pipeline", f"#{child['pipeline']['id']}"),
                             ("Selection pipeline", f"#{select_id}"),
                             ("Offered image groups",
                              ", ".join(job.get("name", "") for job in jobs) or "-")])
    selected = play_and_wait(context, select_id, jobs, state["group_id"], emit)
    result["fields"].extend(selected["fields"])
    if selected["error"]:
        return selected["error"]
    trace = gitlab_api_func.job_trace(context, selected["job_id"])
    missing = [value for value in (state["group_id"], state["job_id"]) if value not in trace]
    result["fields"].append((mark(not missing, "select job log names the group and job"),
                             "yes" if not missing else f"missing {', '.join(missing)}"))
    state.update(pipeline_id=parent_id, select_pipeline=select_id, watched=[parent_id])
    return f"select job log does not mention {', '.join(missing)}" if missing else ""


def _cleanup_job_status(context: Dict[str, Any], pipeline_id: int, job_id: int) -> str:
    """Return the status of the GitLab cleanup job."""
    for job in gitlab_api_func.pipeline_jobs(context, pipeline_id):
        if job.get("id") == job_id:
            return job.get("status", "")
    return ""


def _follow_group(host: Any, state: Dict[str, Any], job_id: int, settings: Dict[str, Any],
                  emit: Emit) -> List[str]:
    """Follow the image group until CLEANED/CLEANUP_FAILED or the GitLab job fails.

    Returns the image group statuses seen, in order.
    """
    context = state["context"]
    follower = LogFollower(host) if settings.get("debug_mode", True) else None
    shown: Dict[str, str] = {}
    seen: List[str] = []
    started = time.time()
    try:
        while True:
            follow_cleanup_log(host, state["epoch"], follower, shown, emit)
            status = (db_func.image_group(host, state["group_id"]) or {}).get("status",
                                                                             "NOT FOUND")
            gitlab = _cleanup_job_status(context, state["select_pipeline"], job_id)
            line = f"{state['group_id']}={status} (GitLab cleanup job: {gitlab or 'pending'})"
            if not seen or seen[-1] != status:
                seen.append(status)
                emit(PROGRESS["cleanup_statuses"].format(statuses=line))
            elif follower is None:
                emit(PROGRESS["cleanup_still_running"].format(
                    elapsed=int(time.time() - started), statuses=line))
            if status in (IMAGE_GROUP_CLEANED, IMAGE_GROUP_CLEANUP_FAILED, "NOT FOUND") \
                    or gitlab in GITLAB_FAILED_STATUSES:
                return seen
            time.sleep(settings["poll_interval"])
    finally:
        if follower is not None:
            follower.drain(final=True)


def run_pipeline_cleanup(host: Any, settings: Dict[str, Any], emit: Emit) -> Dict[str, Any]:
    """Play the cleanup job and follow the image group to CLEANED.

    Returns:
        Dict with keys: success, fields, failures, blocked, mode.
    """
    gate = _suite_gate(_CLEANUP, "cleanup job")
    if gate:
        return gate
    state = STATE[_CLEANUP]
    context = state["context"]
    result = _result(state["mode"])
    result["fields"].extend([("Image group", state["group_id"]), ("Job ID", state["job_id"])])
    jobs = gitlab_api_func.find_job(
        gitlab_api_func.pipeline_jobs(context, state["select_pipeline"]),
                                name=GITLAB_CLEANUP_JOB)
    if not jobs:
        result["failures"].append(
            f"no '{GITLAB_CLEANUP_JOB}' job in pipeline #{state['select_pipeline']}")
        return _finish(result, state, "cleanup job")
    job = jobs[0]
    if job.get("status") == GITLAB_MANUAL:
        played = gitlab_api_func.play_job(context, job["id"])
        if not played["success"]:
            result["failures"].append(f"cannot play cleanup job: {played['error']}")
            return _finish(result, state, "cleanup job")
    emit(PROGRESS["cleanup_job_started"].format(job_id=job["id"], bsm_job=state["job_id"]))
    seen = _follow_group(host, state, job["id"], settings, emit)
    result["fields"].append((mark(seen[-1] == IMAGE_GROUP_CLEANED, "Image group status"),
                             " -> ".join([state["status"], *seen])))
    if seen[-1] != IMAGE_GROUP_CLEANED:
        result["failures"].append(f"image group {state['group_id']} ended {seen[-1]}")
    status = pipeline_monitor_func.wait_job_status(
        context, (state["select_pipeline"], job["id"]), (GITLAB_SUCCESS,), CLEANUP_JOB_TIMEOUT,
        emit)
    result["fields"].append((mark(status == GITLAB_SUCCESS, f"GitLab cleanup job #{job['id']}"),
                             status))
    if status != GITLAB_SUCCESS:
        result["failures"].append(f"GitLab cleanup job #{job['id']} finished as {status}")
    summary = gitlab_api_func.find_job(
        gitlab_api_func.pipeline_jobs(context, state["select_pipeline"]),
                                   name=GITLAB_SUMMARY_JOB)
    if summary:
        pipeline_monitor_func.wait_job_status(
            context, (state["select_pipeline"], summary[0]["id"]), (GITLAB_SUCCESS,),
            SELECT_JOBS_TIMEOUT, emit)
    trace = gitlab_api_func.job_trace(context, summary[0]["id"]) if summary else ""
    reported = bool(GITLAB_CLEANUP_SUMMARY_SUCCESS.search(trace))
    result["fields"].append((mark(reported, f"GitLab {GITLAB_SUMMARY_JOB} job"),
                             "Status: SUCCESS" if reported
                             else ("job not found" if not summary else "SUCCESS not reported")))
    if not reported:
        result["failures"].append(f"cleanup {GITLAB_SUMMARY_JOB} job does not report SUCCESS")
    return _finish(result, state, "cleanup job")


def verify_pipeline_cleanup_db(host: Any, settings: Dict[str, Any],
                               emit: Emit) -> Dict[str, Any]:
    """Verify build_stream_db: image group CLEANED and audit trail; report the job tombstone.

    Returns:
        Dict with keys: success, fields, failures, blocked, mode.
    """
    del settings, emit
    gate = _suite_gate(_CLEANUP, "database")
    if gate:
        return gate
    state = STATE[_CLEANUP]
    result = _result(state["mode"])
    group = db_func.image_group(host, state["group_id"]) or {}
    tombstoned = db_func.job_tombstoned(host, state["job_id"])
    events = db_func.cleanup_audit_events(host, state["job_id"], state["epoch"])
    audit_ok = ({AUDIT_CLEANUP_SUBMITTED, AUDIT_CLEANED} <= set(events)
                and AUDIT_CLEANUP_FAILED not in events)
    checks = [
        (f"image_groups {state['group_id']} status",
         f"{state['status']} -> {group.get('status', 'NOT FOUND')}",
         group.get("status") == IMAGE_GROUP_CLEANED),
        (f"jobs {state['job_id']} tombstoned", tombstone_value(tombstoned), True),
        ("audit_events since the trigger", ", ".join(events) or "none", audit_ok),
    ]
    result["fields"].extend((mark(ok, label), value) for label, value, ok in checks)
    result["failures"].extend(f"{label}: {value}" for label, value, ok in checks if not ok)
    return _finish(result, state, "database")


def verify_pipeline_cleanup_s3(host: Any, settings: Dict[str, Any],
                               emit: Emit) -> Dict[str, Any]:
    """Verify no boot-images object of the cleaned image group is left in S3.

    Returns:
        Dict with keys: success, fields, failures, blocked, mode.
    """
    del settings, emit
    gate = _suite_gate(_CLEANUP, "S3")
    if gate:
        return gate
    state = STATE[_CLEANUP]
    result = _result(state["mode"])
    try:
        left = matching(s3_keys(host), state["group_id"])
    except RuntimeError as exc:
        result["failures"].append(str(exc))
        return _finish(result, state, "S3")
    result["fields"].append((mark(not left, f"s3://boot-images objects of {state['group_id']}"),
                             f"{len(state['s3_before'])} -> {len(left)}"))
    for role in state["roles"]:
        remaining = [key for key in left if f"/{role}/" in key]
        result["fields"].append((mark(not remaining, f"S3 boot files {role}"),
                                 "deleted" if not remaining else f"{len(remaining)} LEFT"))
    result["failures"].extend(f"S3 object not deleted: {key}" for key in left)
    return _finish(result, state, "S3")


def verify_pipeline_cleanup_registry(host: Any, settings: Dict[str, Any],
                                     emit: Emit) -> Dict[str, Any]:
    """Verify no registry tag of the cleaned image group is left.

    Returns:
        Dict with keys: success, fields, failures, blocked, mode.
    """
    del settings, emit
    gate = _suite_gate(_CLEANUP, "registry")
    if gate:
        return gate
    state = STATE[_CLEANUP]
    result = _result(state["mode"])
    after = registry_tags(host, state["group_id"])
    if not after["success"]:
        result["failures"].append(after["error"])
        return _finish(result, state, "registry")
    for repo in sorted(set(state["registry_before"]) | set(after["tags"])):
        before, left = state["registry_before"].get(repo, []), after["tags"].get(repo, [])
        result["fields"].append((mark(not left, f"Registry {repo}"),
                                 f"tags {len(before)} -> {len(left)}"))
        if left:
            result["failures"].append(f"registry tags not deleted: {repo}:{','.join(left)}")
    if not state["registry_before"] and not after["tags"]:
        result["fields"].append((mark(True, "Registry repositories of the group"), "none"))
    return _finish(result, state, "registry")


def verify_pipeline_cleanup_nfs(host: Any, settings: Dict[str, Any],
                                emit: Emit) -> Dict[str, Any]:
    """Verify the job's NFS artifact directory was removed.

    Returns:
        Dict with keys: success, fields, failures, blocked, mode.
    """
    del settings, emit
    gate = _suite_gate(_CLEANUP, "NFS artifacts")
    if gate:
        return gate
    state = STATE[_CLEANUP]
    result = _result(state["mode"])
    exists = path_exists(host, state["nfs_dir"])
    result["fields"].append((mark(not exists, state["nfs_dir"]),
                             f"{'present' if state['nfs_before'] else 'absent'} -> "
                             f"{'STILL EXISTS' if exists else 'removed'}"))
    if exists:
        result["failures"].append(f"NFS artifacts not removed: {state['nfs_dir']}")
    return _finish(result, state, "NFS artifacts")


# =============================================================================
# Automated cleanup
# =============================================================================

def _probe_result(summary: Dict[str, Any], mode: str) -> Dict[str, Any]:
    """Turn a ``summarize`` result into a step result."""
    return {"success": summary["success"], "fields": [("Mode", mode), *summary["fields"]],
            "failures": summary["failures"], "blocked": False, "mode": mode}


def precheck_auto_cleanup_step(host: Any, settings: Dict[str, Any],
                               emit: Emit) -> Dict[str, Any]:
    """Check the retention settings, the BuildStream container and playbook-watcher.

    Skipped (blocked) when retention.auto_cleanup_enabled is false.

    Returns:
        Dict with keys: success, fields, failures, blocked, mode.
    """
    del settings, emit
    check = precheck_auto_cleanup(host)
    if check["success"] and not check["enabled"]:
        return _skip(_AUTO, "precheck", STEP_MSGS["auto_cleanup_disabled"].format(
            path=check["path"]))
    STATE[_AUTO] = {"context": {"enabled": True}, "failed_step": "", "config": check["config"]}
    return _finish(_probe_result(check, "cleanup_cron.main()"), STATE[_AUTO], "precheck")


def _mark_auto_target(host: Any, settings: Dict[str, Any], result: Dict[str, Any],
                      emit: Emit) -> str:
    """Pick the image group the pass must delete and mark it FAILED; return an error or "".

    cleanup_cron deletes FAILED groups unconditionally, so the target
    (pipeline.auto_cleanup_image_group_id, else the image built for this test) is set
    to FAILED in build_stream_db before the pass. No known image group is an error.
    """
    key = "auto_cleanup_image_group_id"
    built = {} if settings.get(key) else dedicated_build_outcome(AUTO_CLEANUP_BUILD)
    if not settings.get(key) and not built.get("success"):
        return STEP_MSGS["auto_cleanup_no_build"].format(key=key)
    wanted = settings.get(key) or built["group_id"]
    target = _cleanup_target(host, {**settings, key: wanted}, key)
    if built:
        target["source"] = "image built for the automated cleanup"
    group = target["group"]
    if target["nothing"]:
        return STEP_MSGS["cleanup_already_cleaned"].format(group_id=wanted, key=key)
    if target["error"]:
        return target["error"]
    previous = group["status"]
    if previous == "FAILED":
        emit(PROGRESS["auto_cleanup_already_failed"].format(group_id=group["id"],
                                                            source=target["source"]))
    else:
        marked = db_func.mark_image_group_failed(host, group["id"])
        if not marked["success"]:
            return marked["error"]
        emit(PROGRESS["auto_cleanup_marked"].format(
            group_id=group["id"], previous=previous, source=target["source"]))
    tags = registry_tags(host, group["id"])
    before = sum(len(items) for items in tags["tags"].values()) if tags["success"] else None
    STATE[_AUTO]["registry_before"] = {group["id"]: before}
    result["fields"].extend([("Image group (marked FAILED)", group["id"]),
                             ("Status before", previous), ("Source", target["source"]),
                             ("Registry tags before", "unavailable" if before is None else before)])
    return ""


class _CleanupBuild(NamedTuple):
    """A cleanup suite's dedicated image: its config key, build record and messages."""

    config_key: str
    build_key: str
    not_needed: str
    failed: str


AUTO_BUILD = _CleanupBuild("auto_cleanup_image_group_id", AUTO_CLEANUP_BUILD,
                           "auto_cleanup_build_not_needed", "auto_cleanup_build_failed")
PIPELINE_BUILD = _CleanupBuild("cleanup_image_group_id", PIPELINE_CLEANUP_BUILD,
                               "pipeline_cleanup_build_not_needed",
                               "pipeline_cleanup_build_failed")


def _build_cleanup_image(host: Any, settings: Dict[str, Any], emit: Emit,
                         spec: _CleanupBuild) -> Dict[str, Any]:
    """Build the dedicated image group of a cleanup suite, unless one is configured.

    Nothing is built when ``pipeline.<config_key>`` names an image group: that
    group is used instead. The build outcome is recorded for the suite's next
    test, also when it runs in another process.

    Returns:
        Dict with keys: success, fields, failures, mode (``blocked`` is false).
    """
    configured = settings.get(spec.config_key)
    if configured:
        clear_run_state(spec.build_key)
        STATE.pop(spec.build_key, None)
        result = _result("configured image group")
        result["fields"].extend([("Image group", configured),
                                 ("Build", STEP_MSGS[spec.not_needed].format(
                                     key=spec.config_key))])
    else:
        result = _result("automatic trigger")
        context = _context(host, result)
        if context is not None:
            error = dedicated_build(host, context, settings, result, emit, spec.build_key)
            if error:
                result["failures"].append(STEP_MSGS[spec.failed].format(
                    error=error, key=spec.config_key))
    result["success"] = not result["failures"]
    result["blocked"] = False
    return result


def build_auto_cleanup_image_step(host: Any, settings: Dict[str, Any],
                                  emit: Emit) -> Dict[str, Any]:
    """Build the image group the automated cleanup deletes.

    A failed build fails this step and blocks the pass.

    Returns:
        Dict with keys: success, fields, failures, blocked, mode.
    """
    gate = _suite_gate(_AUTO, "image build")
    if gate:
        return gate
    return _finish(_build_cleanup_image(host, settings, emit, AUTO_BUILD), STATE[_AUTO],
                   "image build")


def build_pipeline_cleanup_image_step(host: Any, settings: Dict[str, Any],
                                      emit: Emit) -> Dict[str, Any]:
    """Build the image group the cleanup pipeline deletes.

    A failed build fails this step; the trigger step that follows is skipped
    with that reason.

    Returns:
        Dict with keys: success, fields, failures, blocked, mode.
    """
    return _build_cleanup_image(host, settings, emit, PIPELINE_BUILD)


def run_auto_cleanup_step(host: Any, settings: Dict[str, Any], emit: Emit) -> Dict[str, Any]:
    """Run one automated cleanup pass and wait until it is finalized.

    Returns:
        Dict with keys: success, fields, failures, blocked, mode.
    """
    gate = _suite_gate(_AUTO, "cleanup pass")
    if gate:
        return gate
    state = STATE[_AUTO]
    config = state["config"]
    result = _result("cleanup_cron.main()")
    error = _mark_auto_target(host, settings, result, emit)
    if error:
        result["failures"].append(error)
        return _finish(result, state, "cleanup pass")
    emit(STEP_MSGS["auto_cleanup_rules"].format(**config))
    run = run_auto_cleanup(host, config, settings["poll_interval"], emit,
                           settings.get("debug_mode", True))
    data = run["state"]
    if data:
        state["data"] = data
        expected = data["expected"]
        if not expected["failed"] and not expected["retention"]:
            emit(STEP_MSGS["auto_cleanup_noop"])
        result["fields"].extend([
            ("Image groups before", len(data["before"]["groups"])),
            ("FAILED image groups (deleted by the pass)", ", ".join(expected["failed"]) or "none"),
            ("Retention candidates", ", ".join(expected["retention"]) or "none"),
            ("cleanup_cron exit code", data["cleanup_pass"]["rc"]),
            ("Submitted for cleanup", ", ".join(data["cleanup_pass"]["submitted"]) or "none"),
            ("Final statuses", ", ".join(f"{gid}={status}" for gid, status
                                         in data["final"].items()) or "-"),
        ])
    if not run["success"]:
        result["failures"].append(run["error"])
    return _finish(result, state, "cleanup pass")


def _auto_verify(host: Any, step: str, verifier: Callable) -> Dict[str, Any]:
    """Run an automated-cleanup verifier on the recorded pass."""
    gate = _suite_gate(_AUTO, step)
    if gate:
        return gate
    state = STATE[_AUTO]
    if not state.get("data"):
        return _blocked(step, STEP_MSGS["not_started"].format(pipeline=_AUTO))
    return _finish(_probe_result(verifier(host, state["data"]), "cleanup_cron.main()"),
                   state, step)


def verify_auto_cleanup_db_step(host: Any, settings: Dict[str, Any],
                                emit: Emit) -> Dict[str, Any]:
    """Verify the pass in build_stream_db (statuses, tombstones, audit).

    Returns:
        Dict with keys: success, fields, failures, blocked, mode.
    """
    del settings, emit
    return _auto_verify(host, "database", verify_auto_cleanup_db)


def _verify_auto_artifacts(host: Any, data: Dict[str, Any]) -> Dict[str, Any]:
    """Verify S3 and NFS artifacts, then that no registry tag of a cleaned group is left."""
    base = verify_auto_cleanup_artifacts(host, data)
    before = (STATE.get(_AUTO) or {}).get("registry_before", {})
    probes = []
    for gid in data["cleanup_pass"]["submitted"]:
        tags = registry_tags(host, gid)
        if not tags["success"]:
            probes.append((f"{gid} registry", tags["error"], False))
            continue
        left = sum(len(items) for items in tags["tags"].values())
        was = before.get(gid)
        probes.append((f"{gid} registry tags",
                       f"{left} left" if was is None else f"{was} -> {left}", left == 0))
    registry = summarize("auto_cleanup_registry", probes)
    return {"name": base["name"], "success": base["success"] and registry["success"],
            "fields": [*base["fields"], *registry["fields"]],
            "failures": [*base["failures"], *registry["failures"]]}


def verify_auto_cleanup_artifacts_step(host: Any, settings: Dict[str, Any],
                                       emit: Emit) -> Dict[str, Any]:
    """Verify the pass in S3, the registry (regctl) and the NFS artifacts.

    Returns:
        Dict with keys: success, fields, failures, blocked, mode.
    """
    del settings, emit
    return _auto_verify(host, "S3, registry and NFS artifacts", _verify_auto_artifacts)
