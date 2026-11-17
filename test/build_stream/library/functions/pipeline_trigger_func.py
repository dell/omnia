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

"""Pipeline triggers for the execute suites (build, deploy, cadence).

``trigger_pipeline`` returns the parent pipeline either auto-triggered by a
commit (automatic suites) or started through the GitLab API with
``PIPELINE_TYPE`` (manual suites). ``_trigger_build`` commits the selected
catalog with the next unused version (``[skip ci]`` in manual mode),
``_deploy_target`` picks the image group to deploy and ``_trigger_cadence``
stages the cadence catalog, triggers a cycle and follows it. Results are
dicts with keys: success, fields (ordered label/value pairs for the report),
failures and mode. Live progress is sent to ``emit``.
"""

import time
from typing import Any, Callable, Dict, NamedTuple, Optional

from . import catalog_func, db_func, gitlab_api_func, pipeline_monitor_func
from .bsm_api_func import load_bsm_context
from .cadence_func import (
    cadence_event_fields,
    cadence_prechecks,
    host_epoch,
    monitor_cadence_cycle,
    run_trigger_script,
    upload_cadence_catalog,
)
from .log_func import mark
from ..messages.execute_msgs import PROGRESS_MSGS as PROGRESS
from ..messages.execute_msgs import STEP_MSGS
from ..vars.execute_vars import (
    BSM_CONTAINER,
    BUILD_UPLOAD_STAGE,
    CADENCE_UPLOAD_PIPELINE_CHECK,
    COMMIT_MESSAGE_BUILD,
    GITLAB_BRIDGE_BUILD,
    GITLAB_BRIDGE_CADENCE,
    GITLAB_CADENCE_CATALOG_FILE,
    GITLAB_CATALOG_FILE,
    SKIP_CI,
)

Emit = Callable[[str], None]


def _result(mode: str) -> Dict[str, Any]:
    """Return an empty result for ``mode``."""
    return {"success": False, "fields": [("Mode", mode)], "failures": [], "mode": mode}


def _context(host: Any, result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Load the BuildStream context into ``result`` (None on failure)."""
    context = load_bsm_context(host)
    if not context["success"]:
        result["failures"].append(f"BuildStream context: {context['error']}")
        result["success"] = False
        return None
    result["fields"].extend([("BuildStream API", context["bsm_url"]),
                             ("GitLab", context["gitlab_url"])])
    return context


# =============================================================================
# Installation exec — catalog placement + build_stream.yml
# =============================================================================

# =============================================================================
# Installation verify — services and GitLab repository
# =============================================================================

# =============================================================================
# Installation verify — build pipeline
# =============================================================================

def _no_pipeline_for(context: Dict[str, Any], commit_id: str) -> Dict[str, Any]:
    """Check that a ``[skip ci]`` commit started no pipeline.

    Returns:
        Dict with keys: success, field (report pair), error.
    """
    time.sleep(CADENCE_UPLOAD_PIPELINE_CHECK)
    # GitLab may record a [skip ci] push as a pipeline in status "skipped".
    started = [p for p in gitlab_api_func.list_pipelines(context, sha=commit_id)
               if p.get("status") != "skipped"]
    listed = ", ".join(f"#{p['id']} {p.get('status')}" for p in started)
    return {"success": not started,
            "field": (mark(not started, "No pipeline for the [skip ci] commit"), listed or "none"),
            "error": f"the [skip ci] commit {commit_id[:8]} started pipeline(s) {listed}"
                     if started else ""}


class PipelineTrigger(NamedTuple):
    """How a parent pipeline starts: by ``commit_id`` or, when empty, through the API."""

    commit_id: str
    pipeline_type: str
    source: str


def trigger_pipeline(context: Dict[str, Any], trigger: PipelineTrigger,
                     result: Dict[str, Any], emit: Emit) -> Dict[str, Any]:
    """Return the parent pipeline: auto-triggered by a commit or API-triggered.

    Automatic mode (``trigger.commit_id`` set) waits for the pipeline GitLab
    starts for the commit. Manual mode (empty ``commit_id``) starts one
    through the API with ``PIPELINE_TYPE=<pipeline_type>``, like a user
    clicking Run pipeline with that variable.

    Returns:
        Dict with keys: success, pipeline_id, error.
    """
    commit_id, pipeline_type, source = trigger
    if commit_id:
        pipeline = gitlab_api_func.wait_for_pipeline(context, commit_id, emit)
        if not pipeline["success"]:
            return {"success": False, "pipeline_id": 0, "error": pipeline["error"]}
        parent_id = pipeline["pipeline"]["id"]
        emit(PROGRESS["pipeline_auto_triggered"].format(pipeline_id=parent_id, source=source))
        how = f"auto ({source} commit {commit_id[:8]})"
    else:
        pipeline = gitlab_api_func.create_pipeline(context, {"PIPELINE_TYPE": pipeline_type})
        if not pipeline["success"]:
            return {"success": False, "pipeline_id": 0,
                    "error": f"API trigger PIPELINE_TYPE={pipeline_type}: {pipeline['error']}"}
        parent_id = pipeline["pipeline"]["id"]
        emit(PROGRESS["pipeline_api_triggered"].format(pipeline_id=parent_id,
                                                       pipeline_type=pipeline_type))
        how = f"manual (API, PIPELINE_TYPE={pipeline_type})"
    result["fields"].append((mark(True, "Pipeline trigger"), f"{how} -> #{parent_id}"))
    return {"success": True, "pipeline_id": parent_id, "error": ""}


def _plan_build(host: Any, context: Dict[str, Any], settings: Dict[str, Any],
                result: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve the selected catalog and the next unused version.

    Returns:
        Dict with keys: error, selected, version, group_id.
    """
    selected = catalog_func.selected_catalog(host, settings["catalog"])
    if not selected["success"]:
        return {"error": selected["error"]}
    bump = catalog_func.plan_catalog_version(host, context, selected)
    version = bump["version"]
    group_id = f"{selected['identifier']}-v{version}"
    result["fields"].extend([("installation.catalog", settings["catalog"]),
                             ("Catalog source", selected["path"]),
                             ("Catalog identifier", selected["identifier"]),
                             ("Catalog version", f"{bump['base']} -> {version}"),
                             ("Versions in use", bump["seen"]),
                             ("Expected image group", group_id)])
    return {"error": "", "selected": selected, "version": version, "group_id": group_id}


def _commit_build_catalog(context: Dict[str, Any], plan: Dict[str, Any],
                          result: Dict[str, Any], emit: Emit) -> Dict[str, Any]:
    """Commit the planned catalog (``[skip ci]`` and no pipeline when manual).

    Returns:
        Dict with keys: error, commit_id.
    """
    manual, version = plan["manual"], plan["version"]
    message = COMMIT_MESSAGE_BUILD.format(file=GITLAB_CATALOG_FILE, version=version)
    emit(PROGRESS["catalog_committing_skip_ci" if manual else "catalog_committing"].format(
        file=GITLAB_CATALOG_FILE, version=version))
    commit = gitlab_api_func.commit_file(
        context, GITLAB_CATALOG_FILE,
        catalog_func.render_catalog(plan["selected"]["catalog"], version),
        f"{message} {SKIP_CI}" if manual else message)
    if not commit["success"]:
        return {"error": f"commit failed: {commit['error']}"}
    result["fields"].append(("Commit", commit["commit_id"]))
    if manual:
        quiet = _no_pipeline_for(context, commit["commit_id"])
        result["fields"].append(quiet["field"])
        if not quiet["success"]:
            return {"error": quiet["error"]}
    return {"error": "", "commit_id": commit["commit_id"]}


def _await_build_job(host: Any, context: Dict[str, Any], plan: Dict[str, Any],
                     result: Dict[str, Any], emit: Emit) -> Dict[str, Any]:
    """Start build_pipeline for the commit (or the API) and wait for its job.

    Returns:
        Dict with keys: error, pipeline_id, child_id, job_id, group_id,
        stage_checks.
    """
    trigger = PipelineTrigger("" if plan["manual"] else plan["commit_id"], "build", "catalog")
    started = trigger_pipeline(context, trigger, result, emit)
    if not started["success"]:
        return {"error": started["error"]}
    parent_id = started["pipeline_id"]
    child = gitlab_api_func.wait_for_downstream(context, parent_id, GITLAB_BRIDGE_BUILD, emit)
    if not child["success"]:
        return {"error": child["error"]}
    job = pipeline_monitor_func.wait_for_new_job(host, plan["epoch"], context,
                                                 child["pipeline"]["id"], emit)
    if not job["success"]:
        return {"error": job["error"]}
    identifier, version = plan["selected"]["identifier"], plan["version"]
    return {"error": "", "pipeline_id": parent_id, "child_id": child["pipeline"]["id"],
            "job_id": job["job_id"], "group_id": plan["group_id"],
            "stage_checks": {BUILD_UPLOAD_STAGE: lambda: active_catalog_check(
                host, identifier, version)}}


def _trigger_build(host: Any, context: Dict[str, Any], settings: Dict[str, Any],
                   result: Dict[str, Any], emit: Emit) -> Dict[str, Any]:
    """Commit the selected catalog as catalog_rhel.json with the next unused version.

    The catalog comes from installation.catalog (bundled number or full
    path), never from whatever is active at CATALOG_FILE_PATH. Automatic
    mode lets the commit start build_pipeline. Manual mode (``result["mode"]``
    is "manual trigger") commits with ``[skip ci]`` (no pipeline) and then
    triggers ``PIPELINE_TYPE=build`` through the API; everything after the
    trigger is identical.
    """
    manual = result.get("mode") == "manual trigger"
    plan = _plan_build(host, context, settings, result)
    if plan["error"]:
        return {"error": plan["error"]}
    busy = pipeline_monitor_func.ensure_no_busy_pipelines(
        context, settings["allow_pipeline_cancel"], emit,
        f"committing {GITLAB_CATALOG_FILE}" + (" and triggering PIPELINE_TYPE=build"
                                               if manual else ""))
    result["fields"].extend(busy["fields"])
    if not busy["success"]:
        return {"error": busy["error"]}
    plan.update(manual=manual, epoch=db_func.db_now_epoch(host))
    commit = _commit_build_catalog(context, plan, result, emit)
    if commit["error"]:
        return {"error": commit["error"]}
    plan["commit_id"] = commit["commit_id"]
    return _await_build_job(host, context, plan, result, emit)


def active_catalog_check(host: Any, identifier: str, version: str) -> Dict[str, Any]:
    """Check that CATALOG_FILE_PATH on the host holds ``identifier`` v``version``.

    The upload stage writes the committed catalog there for the host
    playbooks (create-local-repository reads it). If it is not on the host
    (for example the path is not mounted into omnia_build_stream), the
    pipeline would build a different catalog.

    Returns:
        Dict with keys: fields, failures.
    """
    target = catalog_func.catalog_target(host)
    active = catalog_func.read_catalog(host, target["path"]) if target["success"] else {}
    found = f"{active.get('identifier') or '?'} v{active.get('version') or '?'}"
    ok = active.get("identifier") == identifier and active.get("version") == version
    fields = [(mark(ok, f"Host {target['path'] or 'CATALOG_FILE_PATH'}"),
               found if ok else f"{found} (expected {identifier} v{version})")]
    failures = [] if ok else [
        f"{target['path'] or 'CATALOG_FILE_PATH'} on the host holds {found}, not the "
        f"committed {identifier} v{version}; the upload stage did not write it to the "
        f"host (check the {BSM_CONTAINER} volume mounts)"]
    return {"fields": fields, "failures": failures}


def _verify_only_ids(host: Any, block: Dict[str, Any], emit: Emit) -> Dict[str, Any]:
    """Use the job ID from test_config.yml; it must exist in build_stream_db."""
    ids = {"error": "", "pipeline_id": 0, "child_id": 0, "job_id": block["job_id"],
           "group_id": ""}
    if not db_func.get_job(host, ids["job_id"]):
        ids["error"] = f"job {ids['job_id']} not found in build_stream_db (table jobs)"
    emit(PROGRESS["verify_only_job"].format(job_id=ids["job_id"]))
    return ids


# =============================================================================
# Installation verify — deploy pipeline
# =============================================================================

def _deploy_target(host: Any, settings: Dict[str, Any], build_key: str,
                   emit: Emit) -> Dict[str, Any]:
    """Pick the image group a deploy suite deploys.

    ``build_key`` set: the image group that build suite built in this run.
    Empty (deploy-only run): pipeline.deploy_image_group_id of
    test_config.yml, which must be set and exist in build_stream_db.

    Returns:
        Dict with keys: error, group, source.
    """
    if build_key:
        state = pipeline_monitor_func.PIPELINE_STATE.get(build_key) or {}
        group_id = state.get("image_group_id", "")
        source = f"built by {build_key} in this run"
        if not group_id:
            return {"error": STEP_MSGS["deploy_build_no_group"].format(build=build_key)}
    else:
        group_id = settings["deploy_image_group_id"]
        source = "pipeline.deploy_image_group_id in test_config.yml"
        if not group_id:
            return {"error": STEP_MSGS["deploy_image_not_set"]}
    group = db_func.image_group(host, group_id)
    if group is None:
        return {"error": STEP_MSGS["deploy_image_not_found"].format(group_id=group_id,
                                                                   source=source)}
    emit(PROGRESS["deploy_target"].format(group_id=group["id"], source=source,
                                         status=group["status"]))
    return {"error": "", "group": group, "source": source}


# =============================================================================
# Installation verify — cadence pipeline
# =============================================================================

def _stage_cadence(host: Any, context: Dict[str, Any], settings: Dict[str, Any],
                   result: Dict[str, Any], emit: Emit) -> Dict[str, Any]:
    """Run the cadence prechecks, clear busy pipelines and upload the catalog.

    Returns:
        Dict with keys: error, script, upload.
    """
    checks = cadence_prechecks(host, context)
    result["fields"].extend(checks["fields"])
    if not checks["success"]:
        return {"error": "; ".join(checks["failures"])}
    busy = pipeline_monitor_func.ensure_no_busy_pipelines(
        context, settings["allow_pipeline_cancel"], emit,
        f"uploading {GITLAB_CADENCE_CATALOG_FILE} and triggering a cadence cycle")
    result["fields"].extend(busy["fields"])
    if not busy["success"]:
        return {"error": busy["error"]}
    upload = upload_cadence_catalog(host, context, settings["cadence_catalog"], emit)
    result["fields"].extend(upload["fields"])
    if not upload["success"]:
        return {"error": "; ".join(upload["failures"])}
    return {"error": "", "script": checks["script"], "upload": upload}


def _run_cadence_cycle(host: Any, script: str, settings: Dict[str, Any],
                       result: Dict[str, Any], emit: Emit) -> Dict[str, Any]:
    """Run trigger_cadence.sh and follow the cycle in the watcher journal.

    Returns:
        Dict with keys: error, cycle.
    """
    journal_epoch = host_epoch(host)
    trigger = run_trigger_script(host, script, emit)
    emit(trigger["output"] or PROGRESS["trigger_script_rc"].format(rc=trigger["rc"]))
    if not trigger["success"]:
        return {"error": f"trigger_cadence.sh failed (rc={trigger['rc']}): {trigger['output']}"}
    cycle = monitor_cadence_cycle(host, journal_epoch, settings, emit)
    result["fields"].extend(cadence_event_fields(cycle["events"]))
    result["fields"].append(("Repo sync log", cycle.get("sync_log") or "-"))
    if not cycle["success"]:
        return {"error": f"cadence cycle failed: {cycle['error']}"}
    return {"error": "", "cycle": cycle}


def _verify_cadence_commit(host: Any, context: Dict[str, Any], run: Dict[str, Any],
                           result: Dict[str, Any]) -> Dict[str, Any]:
    """Check the cycle committed the bumped catalog everywhere at the expected version.

    ``run`` holds before (the latest commit before the cycle), cycle and
    upload.

    Returns:
        Dict with keys: error, commit_id.
    """
    cycle, expected = run["cycle"], run["upload"]["expected"]
    after = gitlab_api_func.latest_commit(context, GITLAB_CADENCE_CATALOG_FILE)
    committed = gitlab_api_func.get_file(context, GITLAB_CADENCE_CATALOG_FILE)
    gitlab_version = catalog_func.parse_catalog(committed["content"], "GitLab cadence catalog")
    target = catalog_func.catalog_target(host)
    local_version = catalog_func.read_catalog(host, target["path"])["version"]
    result["fields"].extend([
        ("Cadence commit", after["commit_id"] or "-"),
        ("Cadence version (journal/GitLab/local)",
         f"{cycle['new_version']} / {gitlab_version['version']} / {local_version}"),
    ])
    error = ""
    if not after["commit_id"] or after["commit_id"] == run["before"]["commit_id"]:
        error = f"{GITLAB_CADENCE_CATALOG_FILE} was not committed to GitLab"
    elif len({cycle["new_version"], gitlab_version["version"], local_version}) != 1:
        error = ("cadence catalog versions disagree between journal, GitLab "
                 "and CATALOG_FILE_PATH")
    elif cycle["new_version"] != expected:
        error = (f"cadence bumped to v{cycle['new_version']}, expected "
                 f"v{expected} (the selected catalog's next version)")
    return {"error": error, "commit_id": after["commit_id"]}


def _await_cadence_job(host: Any, context: Dict[str, Any], commit_id: str, db_epoch: int,
                       emit: Emit) -> Dict[str, Any]:
    """Wait for the pipeline the cadence commit starts, its child and the job.

    Returns:
        Dict with keys: error, pipeline_id, child_id, job_id, group_id.
    """
    pipeline = gitlab_api_func.wait_for_pipeline(context, commit_id, emit)
    if not pipeline["success"]:
        return {"error": pipeline["error"]}
    parent_id = pipeline["pipeline"]["id"]
    emit(PROGRESS["pipeline_auto_triggered"].format(pipeline_id=parent_id, source="cadence"))
    child = gitlab_api_func.wait_for_downstream(context, parent_id, GITLAB_BRIDGE_CADENCE, emit)
    if not child["success"]:
        return {"error": child["error"]}
    job = pipeline_monitor_func.wait_for_new_job(host, db_epoch, context,
                                                 child["pipeline"]["id"], emit)
    return {"error": job["error"], "pipeline_id": parent_id,
            "child_id": child["pipeline"]["id"], "job_id": job["job_id"], "group_id": ""}


def _trigger_cadence(host: Any, context: Dict[str, Any], settings: Dict[str, Any],
                     result: Dict[str, Any], emit: Emit) -> Dict[str, Any]:
    """Stage the selected catalog for cadence, trigger a cycle and follow it.

    The selected catalog is uploaded to cadence_catalog_rhel.json with
    [skip ci] (no pipeline). trigger_cadence.sh then starts a cycle that
    fetches it, syncs repositories, bumps the version and commits; that
    commit starts the cadence pipeline.
    """
    staged = _stage_cadence(host, context, settings, result, emit)
    if staged["error"]:
        return {"error": staged["error"]}
    before = gitlab_api_func.latest_commit(context, GITLAB_CADENCE_CATALOG_FILE)
    db_epoch = db_func.db_now_epoch(host)
    ran = _run_cadence_cycle(host, staged["script"], settings, result, emit)
    if ran["error"]:
        return {"error": ran["error"]}
    commit = _verify_cadence_commit(
        host, context, {"before": before, "cycle": ran["cycle"], "upload": staged["upload"]},
        result)
    if commit["error"]:
        return {"error": commit["error"]}
    return _await_cadence_job(host, context, commit["commit_id"], db_epoch, emit)
