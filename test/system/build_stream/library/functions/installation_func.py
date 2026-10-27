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

"""Installation flows: build_stream.yml, its verification and the pipelines.

``run_build_stream_installation`` is the exec entry point;
``verify_build_stream_services`` and ``verify_gitlab_repository`` verify
it. Each ``run_*_pipeline`` function performs one pipeline test case end to
end and returns a result dict with keys: success, fields (ordered
label/value pairs for the report), failures (list of strings) and mode
(``trigger`` or ``verify-only``). Live progress is sent to ``emit``.
"""

import hashlib
from typing import Any, Callable, Dict, List, Optional, Sequence

from . import catalog_func, db_func, gitlab_func, pipeline_func
from .api_func import check_bsm_health, load_bsm_context
from .cadence_func import (
    cadence_event_fields,
    cadence_prechecks,
    host_epoch,
    monitor_cadence_cycle,
    run_trigger_script,
    upload_cadence_catalog,
)
from .command_func import run_ansible_playbook
from .log_func import mark
from .probe_func import (
    Probe,
    container_running,
    domain_input_path,
    run_cmd,
    summarize,
    unit_active,
)
from ..messages.system_msgs import PROGRESS_MSGS as PROGRESS
from ..vars.common_vars import (
    BSM_CONTAINER,
    BSM_EXPECTED_TABLES,
    BSM_PLAYBOOK,
    BSM_PLAYBOOK_WATCHER_SERVICE,
    BSM_PLAYBOOK_WORKDIR,
    BSM_POSTGRES_CONTAINER,
    BUILD_STAGES,
    CADENCE_STAGES,
    COMMIT_MESSAGE_BUILD,
    COMMIT_MESSAGE_DEPLOY,
    DEPLOY_STAGES,
    GITLAB_BRIDGE_BUILD,
    GITLAB_BRIDGE_CADENCE,
    GITLAB_BRIDGE_DEPLOY,
    GITLAB_CADENCE_CATALOG_FILE,
    GITLAB_CATALOG_FILE,
    GITLAB_CI_FILES,
    GITLAB_INPUT_DIR,
    GITLAB_INPUT_FILES,
    GITLAB_OMNIA_ENV,
    GITLAB_PXE_MAPPING_FILE,
    IMAGE_GROUP_AFTER_BUILD,
    IMAGE_GROUP_BUILT,
    IMAGE_GROUP_PASSED,
)

Emit = Callable[[str], None]
_FINISH_TIMEOUT = 900


def _result(mode: str) -> Dict[str, Any]:
    """Return an empty result for ``mode``."""
    return {"success": False, "fields": [("Mode", mode)], "failures": [], "mode": mode}


def _fail(result: Dict[str, Any], message: str) -> Dict[str, Any]:
    """Record a failure in ``result``."""
    result["failures"].append(message)
    result["success"] = False
    return result


def _context(host: Any, result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Load the BuildStream context into ``result`` (None on failure)."""
    context = load_bsm_context(host)
    if not context["success"]:
        _fail(result, f"BuildStream context: {context['error']}")
        return None
    result["fields"].extend([("BuildStream API", context["bsm_url"]),
                             ("GitLab", context["gitlab_url"])])
    return context


def _finish(result: Dict[str, Any]) -> Dict[str, Any]:
    """Set success from the recorded failures."""
    result["success"] = not result["failures"]
    return result


# =============================================================================
# Installation exec — catalog placement + build_stream.yml
# =============================================================================

def run_build_stream_installation(host: Any, settings: Dict[str, Any],
                                  emit: Emit) -> Dict[str, Any]:
    """Place the selected catalog and run build_stream.yml (entry point only).

    Returns:
        Dict with keys: success, fields, failures, mode.
    """
    result = _result("install")
    emit(PROGRESS["catalog_placing"].format(catalog=settings["catalog"]))
    placed = catalog_func.place_catalog(host, settings["catalog"])
    result["fields"].extend([
        ("Catalog selection", settings["catalog"]),
        ("Catalog source", placed["source"] or "-"),
        ("CATALOG_FILE_PATH", placed["target"] or "-"),
        ("Catalog identifier/version", f"{placed['identifier']} v{placed['version']}"),
        ("Catalog replaced", "yes" if placed["changed"] else "no (already active)"),
        ("Catalog backup", placed["backup"] or "-"),
        ("Catalog sha256", placed["sha256"] or "-"),
    ])
    if not placed["success"]:
        return _fail(result, f"catalog placement: {placed['error']}")

    emit(PROGRESS["playbook_running"].format(playbook=BSM_PLAYBOOK))
    run = run_ansible_playbook(BSM_PLAYBOOK, BSM_PLAYBOOK_WORKDIR)
    result["fields"].extend([("Command", run["command"]), ("Return code", run["rc"]),
                             ("Duration seconds", f"{run['duration']:.1f}")])
    if not run["success"]:
        return _fail(result, f"{BSM_PLAYBOOK} failed (rc={run['rc']}): "
                             f"{run.get('error') or 'see output'}")
    return _finish(result)


# =============================================================================
# Installation verify — services and GitLab repository
# =============================================================================

def verify_build_stream_services(host: Any) -> Dict[str, Any]:
    """Verify the BuildStream runtime build_stream.yml deployed.

    Checks the omnia_build_stream and omnia_postgres containers, the
    playbook-watcher service, every build_stream_db table and the API
    ``/health`` endpoint.

    Returns:
        Dict with keys: name, success, fields, failures.
    """
    probes: List[Probe] = [container_running(host, BSM_CONTAINER),
                           container_running(host, BSM_POSTGRES_CONTAINER),
                           unit_active(host, BSM_PLAYBOOK_WATCHER_SERVICE)]
    tables = db_func.list_tables(host)
    missing = [name for name in BSM_EXPECTED_TABLES if name not in tables["tables"]]
    probes.append(("build_stream_db tables",
                   "all present" if tables["success"] and not missing
                   else f"MISSING {', '.join(missing) or tables['error']}",
                   tables["success"] and not missing))
    context = load_bsm_context(host)
    if not context["success"]:
        probes.append(("BuildStream context", context["error"], False))
        return summarize("build_stream_services", probes)
    health = check_bsm_health(context)
    probes.append((f"API {health['url']}", str(health["status"]) if health["success"]
                   else health["error"], health["success"]))
    return summarize("build_stream_services", probes)


def _input_file_probe(host: Any, context: Dict[str, Any], domain: str,
                      name: str) -> Probe:
    """An input file present on the OIM must be in GitLab with the same content."""
    repo_path = f"{GITLAB_INPUT_DIR}/{domain}/{name}"
    try:
        source = f"{domain_input_path(host, domain)}/{name}"
    except ValueError as exc:
        return f"GitLab {repo_path}", str(exc), False
    digest = run_cmd(host, "sha256_file", path=source)
    if digest.rc != 0:
        return f"GitLab {repo_path}", "not on the OIM (not synced)", True
    remote = gitlab_func.get_file(context, repo_path)
    if not remote["success"]:
        return f"GitLab {repo_path}", "MISSING", False
    same = hashlib.sha256(remote["content"].encode()).hexdigest() == digest.stdout.split()[0]
    return f"GitLab {repo_path}", "identical to the OIM" if same else "DIFFERS from the OIM", same


def verify_gitlab_repository(host: Any) -> Dict[str, Any]:
    """Verify the GitLab catalog project build_stream.yml populated.

    Checks that the project is reachable with the stored token, that every
    CI file and omnia.env are present, and that every domain input file
    found on the OIM was synced to ``input/<domain>/`` unchanged.

    Returns:
        Dict with keys: name, success, fields, failures.
    """
    context = load_bsm_context(host)
    if not context["success"]:
        return summarize("gitlab_repository",
                         [("BuildStream context", context["error"], False)])
    project = gitlab_func.check_gitlab_project(context)
    probes: List[Probe] = [("GitLab project", project["name"] or project["error"],
                            project["success"])]
    for name in (*GITLAB_CI_FILES, GITLAB_OMNIA_ENV):
        present = gitlab_func.get_file(context, name)["success"]
        probes.append((f"GitLab {name}", "present" if present else "MISSING", present))
    probes.extend(_input_file_probe(host, context, domain, name)
                  for domain, name in GITLAB_INPUT_FILES)
    return summarize("gitlab_repository", probes)


# =============================================================================
# Installation verify — build pipeline
# =============================================================================

def _trigger_build(host: Any, context: Dict[str, Any], settings: Dict[str, Any],
                   result: Dict[str, Any], emit: Emit) -> Dict[str, Any]:
    """Commit the selected catalog as catalog_rhel.json with the next unused version.

    The catalog comes from installation.catalog (bundled number or full
    path), never from whatever is active at CATALOG_FILE_PATH.
    """
    selected = catalog_func.selected_catalog(host, settings["catalog"])
    if not selected["success"]:
        return {"error": selected["error"]}
    bump = catalog_func.plan_catalog_version(host, context, selected)
    version = bump["version"]
    group_id = f"{selected['identifier']}-v{version}"
    result["fields"].extend([("Catalog selection", settings["catalog"]),
                             ("Catalog source", selected["path"]),
                             ("Catalog identifier", selected["identifier"]),
                             ("Catalog version", f"{bump['base']} -> {version}"),
                             ("Versions in use", bump["seen"]),
                             ("Expected image group", group_id)])
    busy = pipeline_func.ensure_no_busy_pipelines(
        context, settings["allow_pipeline_cancel"], emit)
    if not busy["success"]:
        return {"error": busy["error"] + " (cancel them or set allow_pipeline_cancel: true)"}

    epoch = db_func.db_now_epoch(host)
    emit(PROGRESS["catalog_committing"].format(file=GITLAB_CATALOG_FILE, version=version))
    commit = gitlab_func.commit_file(
        context, GITLAB_CATALOG_FILE,
        catalog_func.render_catalog(selected["catalog"], version),
        COMMIT_MESSAGE_BUILD.format(file=GITLAB_CATALOG_FILE, version=version))
    if not commit["success"]:
        return {"error": f"commit failed: {commit['error']}"}
    result["fields"].append(("Commit", commit["commit_id"]))
    pipeline = gitlab_func.wait_for_pipeline(context, commit["commit_id"], emit)
    if not pipeline["success"]:
        return {"error": pipeline["error"]}
    parent_id = pipeline["pipeline"]["id"]
    emit(PROGRESS["pipeline_auto_triggered"].format(pipeline_id=parent_id, source="catalog"))
    child = gitlab_func.wait_for_downstream(context, parent_id, GITLAB_BRIDGE_BUILD, emit)
    if not child["success"]:
        return {"error": child["error"]}
    job = pipeline_func.wait_for_new_job(host, epoch, context, child["pipeline"]["id"], emit)
    if not job["success"]:
        return {"error": job["error"]}
    return {"error": "", "pipeline_id": parent_id, "child_id": child["pipeline"]["id"],
            "job_id": job["job_id"], "group_id": group_id}


def _verify_only_ids(host: Any, block: Dict[str, Any], emit: Emit) -> Dict[str, Any]:
    """Use the job ID from test_config.yml; it must exist in build_stream_db."""
    ids = {"error": "", "pipeline_id": 0, "child_id": 0, "job_id": block["job_id"],
           "group_id": ""}
    if not db_func.get_job(host, ids["job_id"]):
        ids["error"] = f"job {ids['job_id']} not found in build_stream_db (table jobs)"
    emit(PROGRESS["verify_only_job"].format(job_id=ids["job_id"]))
    return ids


def _monitor_and_verify(host: Any, context: Dict[str, Any], settings: Dict[str, Any],
                        ids: Dict[str, Any], stages: Sequence[str], result: Dict[str, Any],
                        emit: Emit, group_statuses: Sequence[str],
                        baseline: Optional[Dict[str, Dict[str, str]]] = None,
                        min_deploy_count: int = 0) -> Dict[str, Any]:
    """Monitor and verify ``stages`` one by one, then the GitLab and job-level records."""
    watched = [pid for pid in (ids.get("pipeline_id"), ids.get("child_id")) if pid]
    monitor = pipeline_func.monitor_stages(
        host, context, ids["job_id"], stages, watched,
        settings["poll_interval"], emit, baseline, settings.get("debug_mode", False))
    result["fields"].extend(monitor["fields"])
    if not monitor["success"]:
        _fail(result, monitor["error"])
    result["failures"].extend(monitor["failures"])
    if watched and monitor["success"]:
        final = pipeline_func.wait_pipeline_finished(
            context, watched[-1], _FINISH_TIMEOUT, settings["poll_interval"], emit)
        result["fields"].append((mark(final["success"], f"GitLab pipeline #{watched[-1]}"),
                                 final["status"]))
        if not final["success"]:
            _fail(result, final["error"])
    records = pipeline_func.verify_job_records(
        host, context, ids["job_id"], group_statuses,
        ids.get("group_id", ""), min_deploy_count)
    result["fields"].extend(records["fields"])
    result["failures"].extend(records["failures"])
    return records


def run_build_pipeline(host: Any, settings: Dict[str, Any], emit: Emit) -> Dict[str, Any]:
    """Trigger (or verify) the build pipeline and check every stage and DB row."""
    block = settings["build"]
    verify_only = bool(block["job_id"])
    result = _result("verify-only" if verify_only else "trigger")
    # Recorded up front so an early failure still gates the dependent deploy test.
    pipeline_func.PIPELINE_STATE["build"] = {"job_id": "", "image_group_id": "",
                                             "success": False}
    context = _context(host, result)
    if context is None:
        return result
    ids = (_verify_only_ids(host, block, emit) if verify_only
           else _trigger_build(host, context, settings, result, emit))
    result["fields"].extend([("Job ID", ids.get("job_id") or "-"),
                             ("Pipeline ID", ids.get("pipeline_id") or "-"),
                             ("Build child pipeline", ids.get("child_id") or "-")])
    if ids["error"]:
        return _fail(result, ids["error"])
    records = _monitor_and_verify(host, context, settings, ids, BUILD_STAGES,
                                  result, emit, IMAGE_GROUP_AFTER_BUILD)
    pipeline_func.PIPELINE_STATE["build"] = {
        "job_id": ids["job_id"],
        "image_group_id": (records["image_group"] or {}).get("id", ""),
        "success": not result["failures"],
    }
    return _finish(result)


# =============================================================================
# Installation verify — deploy pipeline
# =============================================================================

def _deploy_target(host: Any, emit: Emit) -> Dict[str, Any]:
    """Pick the image group built by the build pipeline test, else the newest BUILT group."""
    group_id = pipeline_func.PIPELINE_STATE["build"].get("image_group_id", "")
    group = db_func.image_group(host, group_id) if group_id else None
    source = "build test"
    if group is None:
        group, source = db_func.newest_built_image_group(host), "newest BUILT"
    if group is None:
        return {"error": f"no {IMAGE_GROUP_BUILT} image group found in build_stream_db"}
    emit(PROGRESS["deploy_target"].format(group_id=group["id"], source=source,
                                         status=group["status"]))
    return {"error": "", "group": group, "source": source}


def _trigger_deploy(context: Dict[str, Any], settings: Dict[str, Any], group: Dict[str, str],
                    result: Dict[str, Any], emit: Emit) -> Dict[str, Any]:
    """Swap PXE rows in GitLab, then select the image and play deploy."""
    if group["status"] != IMAGE_GROUP_BUILT:
        return {"error": f"image group {group['id']} is {group['status']}; the deploy "
                         f"pipeline only offers {IMAGE_GROUP_BUILT} groups"}
    busy = pipeline_func.ensure_no_busy_pipelines(
        context, settings["allow_pipeline_cancel"], emit)
    if not busy["success"]:
        return {"error": busy["error"] + " (cancel them or set allow_pipeline_cancel: true)"}
    current = gitlab_func.get_file(context, GITLAB_PXE_MAPPING_FILE)
    if not current["success"]:
        return {"error": f"{GITLAB_PXE_MAPPING_FILE}: {current['error']}"}
    swapped = pipeline_func.swap_pxe_rows(current["content"])
    if not swapped["success"]:
        return {"error": swapped["error"]}
    first, second = swapped["rows"]
    emit(PROGRESS["pxe_rows_swapping"].format(first=first, second=second,
                                             file=GITLAB_PXE_MAPPING_FILE))
    commit = gitlab_func.commit_file(context, GITLAB_PXE_MAPPING_FILE, swapped["content"],
                                     COMMIT_MESSAGE_DEPLOY.format(first=first, second=second))
    if not commit["success"]:
        return {"error": f"commit failed: {commit['error']}"}
    result["fields"].extend([("PXE rows swapped", f"{first} <-> {second}"),
                             ("Commit", commit["commit_id"])])
    pipeline = gitlab_func.wait_for_pipeline(context, commit["commit_id"], emit)
    if not pipeline["success"]:
        return {"error": pipeline["error"]}
    parent_id = pipeline["pipeline"]["id"]
    emit(PROGRESS["pipeline_auto_triggered"].format(pipeline_id=parent_id, source="PXE mapping"))
    child = gitlab_func.wait_for_downstream(context, parent_id, GITLAB_BRIDGE_DEPLOY, emit)
    if not child["success"]:
        return {"error": child["error"]}
    selection = pipeline_func.select_image_and_deploy(
        context, child["pipeline"]["id"], group["id"], emit)
    result["fields"].append(("Offered image groups", ", ".join(selection["available"]) or "-"))
    return {"error": selection["error"], "pipeline_id": parent_id,
            "child_id": selection["select_pipeline_id"], "job_id": group["job_id"],
            "group_id": group["id"]}


def run_deploy_pipeline(host: Any, settings: Dict[str, Any], emit: Emit) -> Dict[str, Any]:
    """Trigger (or verify) the deploy pipeline: deploy, restart and validate."""
    block = settings["deploy"]
    verify_only = bool(block["job_id"])
    result = _result("verify-only" if verify_only else "trigger")
    context = _context(host, result)
    if context is None:
        return result

    baseline, min_count = None, 0
    if verify_only:
        # Deploy runs add stages to the build job of the deployed image group.
        ids = _verify_only_ids(host, block, emit)
    else:
        target = _deploy_target(host, emit)
        if target["error"]:
            return _fail(result, target["error"])
        result["fields"].append(("Image group source", target["source"]))
        baseline = db_func.get_stages(host, target["group"]["job_id"])
        min_count = int(target["group"]["deploy_count"] or 0) + 1
        ids = _trigger_deploy(context, settings, target["group"], result, emit)
    result["fields"].extend([("Image group", ids.get("group_id") or "-"),
                             ("Job ID", ids.get("job_id") or "-"),
                             ("Pipeline ID", ids.get("pipeline_id") or "-"),
                             ("Deploy pipeline", ids.get("child_id") or "-")])
    if ids["error"]:
        return _fail(result, ids["error"])
    _monitor_and_verify(host, context, settings, ids, DEPLOY_STAGES, result, emit,
                        (IMAGE_GROUP_PASSED,), baseline, min_count)
    pipeline_func.PIPELINE_STATE["deploy"] = {"job_id": ids["job_id"],
                                              "success": not result["failures"]}
    return _finish(result)


# =============================================================================
# Installation verify — cadence pipeline
# =============================================================================

def _trigger_cadence(host: Any, context: Dict[str, Any], settings: Dict[str, Any],
                     result: Dict[str, Any], emit: Emit) -> Dict[str, Any]:
    """Stage the selected catalog for cadence, trigger a cycle and follow it.

    The selected catalog is uploaded to cadence_catalog_rhel.json with
    [skip ci] (no pipeline). trigger_cadence.sh then starts a cycle that
    fetches it, syncs repositories, bumps the version and commits; that
    commit starts the cadence pipeline.
    """
    checks = cadence_prechecks(host, context)
    result["fields"].extend(checks["fields"])
    if not checks["success"]:
        return {"error": "; ".join(checks["failures"])}
    busy = pipeline_func.ensure_no_busy_pipelines(
        context, settings["allow_pipeline_cancel"], emit)
    if not busy["success"]:
        return {"error": busy["error"] + " (cancel them or set allow_pipeline_cancel: true)"}
    upload = upload_cadence_catalog(host, context, settings["catalog"], emit)
    result["fields"].extend(upload["fields"])
    if not upload["success"]:
        return {"error": "; ".join(upload["failures"])}
    before = gitlab_func.latest_commit(context, GITLAB_CADENCE_CATALOG_FILE)
    db_epoch, journal_epoch = db_func.db_now_epoch(host), host_epoch(host)

    trigger = run_trigger_script(host, checks["script"], emit)
    emit(trigger["output"] or PROGRESS["trigger_script_rc"].format(rc=trigger["rc"]))
    if not trigger["success"]:
        return {"error": f"trigger_cadence.sh failed (rc={trigger['rc']}): {trigger['output']}"}
    cycle = monitor_cadence_cycle(host, journal_epoch, settings["poll_interval"], emit,
                                  debug_mode=settings.get("debug_mode", False))
    result["fields"].extend(cadence_event_fields(cycle["events"]))
    result["fields"].append(("Repo sync log", cycle.get("sync_log") or "-"))
    if not cycle["success"]:
        return {"error": f"cadence cycle failed: {cycle['error']}"}

    after = gitlab_func.latest_commit(context, GITLAB_CADENCE_CATALOG_FILE)
    committed = gitlab_func.get_file(context, GITLAB_CADENCE_CATALOG_FILE)
    gitlab_version = catalog_func.parse_catalog(committed["content"], "GitLab cadence catalog")
    target = catalog_func.catalog_target(host)
    local_version = catalog_func.read_catalog(host, target["path"])["version"]
    result["fields"].extend([
        ("Cadence commit", after["commit_id"] or "-"),
        ("Cadence version (journal/GitLab/local)",
         f"{cycle['new_version']} / {gitlab_version['version']} / {local_version}"),
    ])
    if not after["commit_id"] or after["commit_id"] == before["commit_id"]:
        return {"error": f"{GITLAB_CADENCE_CATALOG_FILE} was not committed to GitLab"}
    if len({cycle["new_version"], gitlab_version["version"], local_version}) != 1:
        return {"error": "cadence catalog versions disagree between journal, GitLab "
                         "and CATALOG_FILE_PATH"}
    if cycle["new_version"] != upload["expected"]:
        return {"error": f"cadence bumped to v{cycle['new_version']}, expected "
                         f"v{upload['expected']} (the selected catalog's next version)"}

    pipeline = gitlab_func.wait_for_pipeline(context, after["commit_id"], emit)
    if not pipeline["success"]:
        return {"error": pipeline["error"]}
    parent_id = pipeline["pipeline"]["id"]
    emit(PROGRESS["pipeline_auto_triggered"].format(pipeline_id=parent_id, source="cadence"))
    child = gitlab_func.wait_for_downstream(context, parent_id, GITLAB_BRIDGE_CADENCE, emit)
    if not child["success"]:
        return {"error": child["error"]}
    job = pipeline_func.wait_for_new_job(host, db_epoch, context, child["pipeline"]["id"], emit)
    return {"error": job["error"], "pipeline_id": parent_id,
            "child_id": child["pipeline"]["id"], "job_id": job["job_id"], "group_id": ""}


def run_cadence_pipeline(host: Any, settings: Dict[str, Any], emit: Emit) -> Dict[str, Any]:
    """Trigger (or verify) a cadence cycle and its unified pipeline."""
    block = settings["cadence"]
    verify_only = bool(block["job_id"])
    result = _result("verify-only" if verify_only else "trigger")
    context = _context(host, result)
    if context is None:
        return result
    ids = (_verify_only_ids(host, block, emit) if verify_only
           else _trigger_cadence(host, context, settings, result, emit))
    result["fields"].extend([("Job ID", ids.get("job_id") or "-"),
                             ("Pipeline ID", ids.get("pipeline_id") or "-"),
                             ("Cadence child pipeline", ids.get("child_id") or "-")])
    if ids["error"]:
        return _fail(result, ids["error"])
    _monitor_and_verify(host, context, settings, ids, CADENCE_STAGES, result, emit,
                        (IMAGE_GROUP_PASSED,))
    pipeline_func.PIPELINE_STATE["cadence"] = {"job_id": ids["job_id"],
                                               "success": not result["failures"]}
    return _finish(result)


def failure_summary(result: Dict[str, Any]) -> str:
    """Return the first failures joined for an assertion message."""
    failures: List[str] = result["failures"]
    return "; ".join(failures[:5]) + (f" (+{len(failures) - 5} more)" if len(failures) > 5 else "")
