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


"""Cadence enable/disable applied live, without restarting any service.

cadence_manager reloads build_stream_config.yml at the start of every
cycle, so a cadence.enabled change applies to the next triggered cycle:

    disable    the cycle logs "Cadence polling is disabled" and does nothing:
               no catalog fetch, repo sync or commit, and GitLab gets no new
               cadence_catalog_rhel.json commit and no new pipeline
    re-enable  the reload logs "enabled False -> True", the cycle runs to
               completion, and its commit starts the cadence pipeline in
               GitLab and a BuildStream job

cadence.enabled is restored to its value before the test in every case.
"""

from typing import Any, Callable, Dict, Optional

from . import db_func, gitlab_api_func, pipeline_monitor_func
from .bsm_api_func import load_bsm_context
from .cadence_func import (
    cadence_event_fields,
    host_epoch,
    monitor_cadence_cycle,
    read_cadence_enabled,
    run_trigger_script,
    set_cadence_enabled,
    upload_cadence_catalog,
)
from .execute_probe_func import data_path, run_cmd
from .log_func import mark
from ..messages.execute_msgs import PROGRESS_MSGS as PROGRESS
from ..vars.execute_vars import (
    BSM_PLAYBOOK_WATCHER_SERVICE,
    CADENCE_DISABLED_TIMEOUT,
    CADENCE_TRIGGER_SCRIPT,
    GITLAB_BRIDGE_CADENCE,
    GITLAB_CADENCE_CATALOG_FILE,
)

Emit = Callable[[str], None]


def _runtime_checks(host: Any) -> Dict[str, Any]:
    """Watcher active and trigger script present (cadence.enabled not required)."""
    script = f"{data_path(host)}/{CADENCE_TRIGGER_SCRIPT}"
    watcher = run_cmd(host, "systemctl_is_active", unit=BSM_PLAYBOOK_WATCHER_SERVICE)
    state = watcher.stdout.strip() or "unknown"
    checks = [(f"Unit {BSM_PLAYBOOK_WATCHER_SERVICE}", state, state == "active"),
              ("Trigger script", script, run_cmd(host, "file_exists", path=script).rc == 0)]
    return {"success": all(ok for _, _, ok in checks),
            "fields": [(mark(ok, label), value) for label, value, ok in checks],
            "failures": [f"{label}: {value}" for label, value, ok in checks if not ok],
            "script": script}


def _gitlab_baseline(context: Dict[str, Any]) -> Dict[str, Any]:
    """Return the newest cadence catalog commit and the newest pipeline ID."""
    commit = gitlab_api_func.latest_commit(context, GITLAB_CADENCE_CATALOG_FILE)
    pipelines = gitlab_api_func.list_pipelines(context, per_page=1)
    return {"commit_id": commit["commit_id"],
            "pipeline_id": int(pipelines[0].get("id", 0)) if pipelines else 0}


def _trigger_and_watch(host: Any, script: str, settings: Dict[str, Any], emit: Emit,
                       timeout: Optional[int]) -> Dict[str, Any]:
    """Send SIGUSR1 via trigger_cadence.sh and follow the resulting cycle."""
    epoch = host_epoch(host)
    trigger = run_trigger_script(host, script, emit)
    emit(trigger["output"] or PROGRESS["trigger_script_rc"].format(rc=trigger["rc"]))
    if not trigger["success"]:
        return {"success": False, "events": [], "error":
                f"trigger_cadence.sh failed (rc={trigger['rc']}): {trigger['output']}"}
    return monitor_cadence_cycle(host, epoch, settings, emit, timeout)


def _disabled_cycle(host: Any, toggle: Dict[str, Any], settings: Dict[str, Any],
                    emit: Emit) -> Dict[str, Any]:
    """Trigger a cycle that must be skipped as disabled, with nothing sent to GitLab.

    ``toggle`` is the toggle result holding the GitLab context and script.

    Returns:
        Dict with keys: success, fields, failures, events.
    """
    context = toggle["context"]
    baseline = _gitlab_baseline(context)
    emit(PROGRESS["cadence_wait_disabled"].format(timeout=CADENCE_DISABLED_TIMEOUT))
    cycle = _trigger_and_watch(host, toggle["script"], settings, emit, CADENCE_DISABLED_TIMEOUT)
    events = cycle["events"]
    work = [name for name in ("catalog_fetched", "sync_submitted", "committed", "completed")
            if name in events]
    after = _gitlab_baseline(context)
    new_pipelines = [f"#{item.get('id')}" for item in gitlab_api_func.list_pipelines(context)
                     if int(item.get("id", 0)) > baseline["pipeline_id"]]
    checks = [
        ("Cycle started after trigger", "cycle_started" in events, ""),
        ("'Cadence polling is disabled' logged", "disabled" in events, ""),
        ("No catalog fetch / repo sync / commit", not work, ", ".join(work)),
        (f"No new {GITLAB_CADENCE_CATALOG_FILE} commit in GitLab",
         after["commit_id"] == baseline["commit_id"], after["commit_id"]),
        ("No cadence pipeline started in GitLab", not new_pipelines, ", ".join(new_pipelines)),
    ]
    fields = [(mark(ok, label), "yes" if ok else f"NO {detail}".strip())
              for label, ok, detail in checks]
    failures = [f"{label}: {detail}".rstrip(": ") for label, ok, detail in checks if not ok]
    if "disabled" not in events and cycle.get("error"):
        failures.append(cycle["error"])
    return {"success": not failures, "fields": fields, "failures": failures,
            "events": events}


def _cadence_pipeline_started(host: Any, context: Dict[str, Any], baseline: Dict[str, Any],
                              db_epoch: int, emit: Emit) -> Dict[str, Any]:
    """Verify the cycle's commit started the cadence pipeline and a BuildStream job.

    Returns:
        Dict with keys: fields, failures.
    """
    after = _gitlab_baseline(context)
    committed = bool(after["commit_id"]) and after["commit_id"] != baseline["commit_id"]
    fields = [(mark(committed, f"Cadence commit of {GITLAB_CADENCE_CATALOG_FILE}"),
               after["commit_id"] or "-")]
    if not committed:
        return {"fields": fields,
                "failures": [f"{GITLAB_CADENCE_CATALOG_FILE} was not committed to GitLab"]}
    pipeline = gitlab_api_func.wait_for_pipeline(context, after["commit_id"], emit)
    if not pipeline["success"]:
        return {"fields": fields, "failures": [pipeline["error"]]}
    parent_id = pipeline["pipeline"]["id"]
    emit(PROGRESS["pipeline_auto_triggered"].format(pipeline_id=parent_id, source="cadence"))
    fields.append((mark(True, "GitLab pipeline started by the commit"), f"#{parent_id}"))
    child = gitlab_api_func.wait_for_downstream(context, parent_id, GITLAB_BRIDGE_CADENCE, emit)
    if not child["success"]:
        return {"fields": fields, "failures": [child["error"]]}
    child_id = child["pipeline"]["id"]
    fields.append((mark(True, "Cadence child pipeline"), f"#{child_id}"))
    job = pipeline_monitor_func.wait_for_new_job(host, db_epoch, context, child_id, emit)
    fields.append((mark(job["success"], "BuildStream job"), job["job_id"] or "-"))
    return {"fields": fields, "failures": [] if job["success"] else [job["error"]]}


def _toggle_result(host: Any) -> Dict[str, Any]:
    """Start a toggle result with the runtime prechecks and the GitLab context."""
    runtime = _runtime_checks(host)
    result = {"success": False, "fields": list(runtime["fields"]),
              "failures": list(runtime["failures"]), "script": runtime["script"],
              "original": read_cadence_enabled(host), "context": {}}
    result["fields"].insert(0, ("cadence.enabled before", str(result["original"]).lower()))
    context = load_bsm_context(host)
    if context["success"]:
        result["context"] = context
    else:
        result["failures"].append(f"BuildStream context: {context['error']}")
    return result


def _restore(host: Any, original: Optional[bool], result: Dict[str, Any], emit: Emit) -> None:
    """Put cadence.enabled back to its value before the test."""
    if original is None or read_cadence_enabled(host) is original:
        return
    restored = set_cadence_enabled(host, original, emit)
    result["fields"].append((mark(restored["success"], "cadence.enabled restored"),
                             str(original).lower()))
    if not restored["success"]:
        result["failures"].append(f"restore cadence.enabled: {restored['error']}")


def _finish(result: Dict[str, Any]) -> Dict[str, Any]:
    """Drop internal keys and set success."""
    result["success"] = not result["failures"]
    for key in ("context", "script", "original"):
        result.pop(key, None)
    return result


def verify_cadence_disable_live(host: Any, settings: Dict[str, Any],
                                emit: Emit) -> Dict[str, Any]:
    """Disable cadence (no restart); the triggered cycle must not start cadence.

    Returns:
        Dict with keys: success, fields, failures.
    """
    result = _toggle_result(host)
    if result["failures"]:
        return _finish(result)
    try:
        disabled = set_cadence_enabled(host, False, emit)
        result["fields"].append((mark(disabled["success"], "cadence.enabled set"), "false"))
        if not disabled["success"]:
            result["failures"].append(disabled["error"])
            return _finish(result)
        cycle = _disabled_cycle(host, result, settings, emit)
        result["fields"].extend(cycle["fields"])
        result["failures"].extend(cycle["failures"])
    finally:
        _restore(host, result["original"], result, emit)
    return _finish(result)


def verify_cadence_reenable_live(host: Any, settings: Dict[str, Any],
                                 emit: Emit) -> Dict[str, Any]:
    """Re-enable cadence (no restart); the triggered cycle must start cadence.

    The watcher is first brought to a disabled state (config false and one
    skipped cycle), so the enable is proven by the live reload
    (``enabled False -> True``), a full cycle, and the cadence pipeline and
    BuildStream job its commit starts.

    Returns:
        Dict with keys: success, fields, failures.
    """
    result = _toggle_result(host)
    if result["failures"]:
        return _finish(result)
    context = result["context"]
    try:
        if not _reach_disabled_state(host, result, settings, emit):
            return _finish(result)
        upload = upload_cadence_catalog(host, context, settings["cadence_catalog"], emit)
        result["fields"].extend(upload["fields"])
        if not upload["success"]:
            result["failures"].extend(upload["failures"])
            return _finish(result)
        enabled = set_cadence_enabled(host, True, emit)
        result["fields"].append((mark(enabled["success"], "cadence.enabled set"), "true"))
        if not enabled["success"]:
            result["failures"].append(enabled["error"])
            return _finish(result)
        baseline, db_epoch = _gitlab_baseline(context), db_func.db_now_epoch(host)
        cycle = _trigger_and_watch(host, result["script"], settings, emit, None)
        _check_enabled_cycle(result, cycle, upload["expected"])
        if cycle["success"]:
            started = _cadence_pipeline_started(host, context, baseline, db_epoch, emit)
            result["fields"].extend(started["fields"])
            result["failures"].extend(started["failures"])
    finally:
        _restore(host, result["original"], result, emit)
    return _finish(result)


def _reach_disabled_state(host: Any, result: Dict[str, Any], settings: Dict[str, Any],
                          emit: Emit) -> bool:
    """Disable cadence and prove it with one skipped cycle (re-enable precondition)."""
    disabled = set_cadence_enabled(host, False, emit)
    if not disabled["success"]:
        result["failures"].append(disabled["error"])
        return False
    precondition = _disabled_cycle(host, result, settings, emit)
    result["fields"].append((mark(precondition["success"],
                                  "Precondition: cycle skipped while disabled"),
                             "yes" if precondition["success"] else "NO"))
    result["failures"].extend(f"precondition: {item}" for item in precondition["failures"])
    return precondition["success"]


def _check_enabled_cycle(result: Dict[str, Any], cycle: Dict[str, Any], expected: str) -> None:
    """Add the checks of a cycle that ran after cadence was re-enabled."""
    events = cycle["events"]
    checks = [
        ("Reload logged 'enabled False -> True'", "config_reloaded" in events),
        ("Cycle not skipped as disabled", "disabled" not in events),
        ("Repo sync submitted", "sync_submitted" in events),
        ("Cycle completed", cycle["success"]),
        (f"Cycle bumped the selected catalog to v{expected}",
         cycle.get("new_version") == expected),
    ]
    result["fields"].extend((mark(ok, label), "yes" if ok else "NO") for label, ok in checks)
    result["fields"].extend(cadence_event_fields(events))
    result["fields"].append(("Repo sync log", cycle.get("sync_log") or "-"))
    result["failures"].extend(label for label, ok in checks if not ok)
    if not cycle["success"] and cycle.get("error"):
        result["failures"].append(f"cadence cycle: {cycle['error']}")
