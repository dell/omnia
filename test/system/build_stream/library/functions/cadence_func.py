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

"""Cadence trigger and playbook-watcher monitoring.

trigger_cadence.sh sends SIGUSR1 to playbook-watcher. cadence_manager then
fetches the cadence catalog, runs repo_sync.yml, bumps the catalog version,
commits cadence_catalog_rhel.json to GitLab (which auto-triggers the cadence
pipeline) and logs each step to the playbook-watcher journal.
"""

import time
from typing import Any, Callable, Dict, List, Optional

import yaml

from omnia_auto import read_remote_yaml

from . import catalog_func, gitlab_func
from .api_func import load_bsm_context
from .log_func import LogFollower, find_stage_log, mark, print_wrapped, sleep_streaming
from .probe_func import data_path, domain_input_path, render_cmd, run_cmd
from ..messages.system_msgs import PROGRESS_MSGS as PROGRESS
from ..vars.common_vars import (
    BSM_CONFIG_FILE,
    BSM_CONFIG_KEYS,
    BSM_DOMAIN,
    BSM_PLAYBOOK_WATCHER_SERVICE,
    CADENCE_DISABLED_TIMEOUT,
    CADENCE_ERROR_MARKERS,
    CADENCE_HEARTBEAT_POLLS,
    CADENCE_JOURNAL_EVENTS,
    CADENCE_LOG_ROOT,
    CADENCE_LOGGER_NAME,
    CADENCE_SYNC_STAGE,
    CADENCE_TRIGGER_SCRIPT,
    CADENCE_UPLOAD_PIPELINE_CHECK,
    CADENCE_VERSION_RE,
    COMMIT_MESSAGE_CADENCE_UPLOAD,
    GITLAB_CADENCE_CATALOG_FILE,
    JOURNAL_PREFIX_RE,
    JOURNAL_RECORD_RE,
)

Emit = Callable[[str], None]


def host_epoch(host: Any) -> int:
    """Return the OIM clock as a UNIX epoch (journal timestamps use it)."""
    result = run_cmd(host, "epoch_now")
    return int(result.stdout.strip())


def cadence_prechecks(host: Any, context: Dict[str, Any]) -> Dict[str, Any]:
    """Check playbook-watcher, cadence enablement and the trigger script.

    Returns:
        Dict with keys: success, fields, failures, script.
    """
    script = f"{data_path(host)}/{CADENCE_TRIGGER_SCRIPT}"
    cadence = context["config"].get(BSM_CONFIG_KEYS["cadence"]) or {}
    watcher = run_cmd(host, "systemctl_is_active", unit=BSM_PLAYBOOK_WATCHER_SERVICE)
    checks = [
        (f"Unit {BSM_PLAYBOOK_WATCHER_SERVICE}", watcher.stdout.strip() or "unknown",
         watcher.stdout.strip() == "active"),
        ("cadence.enabled", str(cadence.get("enabled", False)).lower(),
         cadence.get("enabled") is True),
        ("Trigger script", script, run_cmd(host, "file_exists", path=script).rc == 0),
    ]
    return {"success": all(ok for _, _, ok in checks),
            "fields": [(mark(ok, label), value) for label, value, ok in checks],
            "failures": [f"{label}: {value}" for label, value, ok in checks if not ok],
            "script": script}


def upload_cadence_catalog(host: Any, context: Dict[str, Any], selection: str,
                           emit: Emit) -> Dict[str, Any]:
    """Silently stage the user-selected catalog as GitLab cadence_catalog_rhel.json.

    The cadence cycle fetches cadence_catalog_rhel.json from GitLab, syncs
    its repositories, bumps the version and commits it, which is what starts
    the cadence pipeline. The upload is committed with ``[skip ci]`` at the
    version just below the next unused one, so no pipeline runs for the
    upload and the cycle's bump lands on an unused version.

    Returns:
        Dict with keys: success, fields, failures, expected (version the
        cycle must commit).
    """
    outcome = {"success": False, "fields": [], "failures": [], "expected": ""}
    selected = catalog_func.selected_catalog(host, selection)
    if not selected["success"]:
        outcome["failures"].append(selected["error"])
        return outcome
    plan = catalog_func.plan_catalog_version(host, context, selected)
    expected = plan["version"]
    version = catalog_func.previous_minor(expected)
    content = catalog_func.render_catalog(selected["catalog"], version)
    outcome["expected"] = expected
    outcome["fields"].extend([("Catalog selection", selection),
                              ("Catalog source", selected["path"]),
                              ("Catalog identifier", selected["identifier"]),
                              ("Versions in use", plan["seen"]),
                              ("Cadence catalog upload version", version),
                              ("Expected cadence bump", expected)])
    current = gitlab_func.get_file(context, GITLAB_CADENCE_CATALOG_FILE)
    if current["success"] and current["content"] == content:
        emit(PROGRESS["cadence_catalog_current"].format(
            file=GITLAB_CADENCE_CATALOG_FILE, source=selected["path"], version=version))
        outcome["fields"].append((mark(True, "Cadence catalog upload"), "already current"))
        outcome["success"] = True
        return outcome
    emit(PROGRESS["cadence_catalog_uploading"].format(
        source=selected["path"], file=GITLAB_CADENCE_CATALOG_FILE, version=version,
        expected=expected))
    commit = gitlab_func.commit_file(
        context, GITLAB_CADENCE_CATALOG_FILE, content,
        COMMIT_MESSAGE_CADENCE_UPLOAD.format(file=GITLAB_CADENCE_CATALOG_FILE,
                                             version=version))
    outcome["fields"].append((mark(commit["success"], "Cadence catalog upload commit"),
                              commit["commit_id"] or commit["error"]))
    if not commit["success"]:
        outcome["failures"].append(f"{GITLAB_CADENCE_CATALOG_FILE} upload: {commit['error']}")
        return outcome
    time.sleep(CADENCE_UPLOAD_PIPELINE_CHECK)
    # GitLab may record a [skip ci] push as a pipeline in status "skipped".
    pipelines = [p for p in gitlab_func.list_pipelines(context, sha=commit["commit_id"])
                 if p.get("status") != "skipped"]
    outcome["fields"].append((mark(not pipelines, "No pipeline for the upload commit"),
                              "none" if not pipelines else
                              ", ".join(f"#{p['id']} {p.get('status')}" for p in pipelines)))
    if pipelines:
        outcome["failures"].append(
            f"the [skip ci] upload commit {commit['commit_id'][:8]} started pipeline(s) "
            f"{', '.join(str(p['id']) for p in pipelines)}")
        return outcome
    emit(PROGRESS["cadence_upload_no_pipeline"].format(commit=commit["commit_id"][:8]))
    outcome["success"] = True
    return outcome


def run_trigger_script(host: Any, script: str, emit: Optional[Emit] = None) -> Dict[str, Any]:
    """Run trigger_cadence.sh (the command is shown first). Returns success, rc, output."""
    if emit:
        emit(PROGRESS["cadence_trigger_command"].format(
            command=render_cmd("run_script", path=script)))
    result = run_cmd(host, "run_script", path=script)
    return {"success": result.rc == 0, "rc": result.rc,
            "output": (result.stdout + result.stderr).strip()}


def _classify(line: str) -> Dict[str, Any]:
    """Map a journal line to a cadence event and its terminal outcome."""
    for key, marker, outcome in CADENCE_JOURNAL_EVENTS:
        if marker in line:
            return {"event": key, "outcome": outcome}
    if CADENCE_LOGGER_NAME in line and any(m in line for m in CADENCE_ERROR_MARKERS):
        return {"event": "error", "outcome": "failed"}
    return {}


def _journal_entry(line: str) -> str:
    """Return a playbook-watcher log record about cadence, without the journal prefix.

    Only application log records (``<time> - <logger> - <LEVEL> - ...``)
    that mention cadence are shown; Ansible task output of the repo sync is
    left to the sync log stream.
    """
    record = JOURNAL_PREFIX_RE.sub("", line.strip())
    if not JOURNAL_RECORD_RE.search(record) or "cadence" not in record.lower():
        return ""
    return record


def _repo_sync_progress(host: Any, log_root: str, since_epoch: int) -> str:
    """Return the latest ansible TASK of the newest cadence sync log."""
    directory = run_cmd(host, "newest_cadence_log_dir", root=log_root).stdout.strip()
    # Cadence job IDs are cadence-<UTC %Y%m%d%H%M%S>; ignore older runs.
    oldest = f"cadence-{time.strftime('%Y%m%d%H%M%S', time.gmtime(since_epoch))}"
    if not directory or directory.rsplit("/", 1)[-1] < oldest:
        return ""
    task = run_cmd(host, "last_ansible_task", directory=directory).stdout.strip()
    return f"{task.strip('* ')} ({directory})" if task else directory


def monitor_cadence_cycle(host: Any, since_epoch: int, poll: int, emit: Emit,
                          debug_mode: bool = False,
                          timeout: Optional[int] = None) -> Dict[str, Any]:
    """Follow the playbook-watcher journal until the cadence cycle ends.

    The cycle ends on its completion message, a failure message (disabled,
    suppressed, repo sync failed/timed out) or a cadence_manager ERROR line.
    There is no timeout unless ``timeout`` (seconds) is given.

    The repo sync playbook log (``cadence-repo-sync_*_attempt<N>.log``) is
    located once the sync starts: streamed live with ``debug_mode``,
    otherwise shown as ``tail -f <log>`` on the progress lines.

    Returns:
        Dict with keys: success, events (ordered event keys), new_version,
        sync_log, error_lines, error.
    """
    outcome = {"success": False, "events": [], "new_version": "", "sync_log": "",
               "error_lines": [], "error": ""}
    log_root = f"{data_path(host)}/{CADENCE_LOG_ROOT}"
    follower = LogFollower(host) if debug_mode else None
    processed, polls, start = 0, 0, time.time()

    def _finish(result: Dict[str, Any]) -> Dict[str, Any]:
        if follower is not None and follower.path:
            follower.drain(final=True)
        return result

    emit(PROGRESS["cadence_journal_header"])
    while True:
        lines = run_cmd(host, "journal_since", unit=BSM_PLAYBOOK_WATCHER_SERVICE,
                        epoch=since_epoch).stdout.splitlines()
        for line in lines[processed:]:
            entry = _journal_entry(line)
            if entry:
                print_wrapped(PROGRESS["cadence_journal_line"].format(line=entry))
            match = _classify(line)
            if not match:
                continue
            message = line.split(" - ", 3)[-1].strip() if " - " in line else line.strip()
            outcome["events"].append(match["event"])
            version = CADENCE_VERSION_RE.search(line)
            if version:
                outcome["new_version"] = version.group(1).rstrip(".")
            if match["outcome"] == "failed":
                outcome["error_lines"].append(message)
            if match["outcome"] == "success":
                outcome["success"] = True
                return _finish(outcome)
            if match["outcome"] == "failed" and match["event"] != "error":
                outcome["error"] = message
                return _finish(outcome)
        processed = len(lines)
        if outcome["error_lines"]:
            outcome["error"] = outcome["error_lines"][0]
            return _finish(outcome)
        if timeout is not None and time.time() - start >= timeout:
            outcome["error"] = f"no terminal cadence message within {timeout}s"
            return _finish(outcome)

        if "sync_submitted" in outcome["events"]:
            found = find_stage_log(host, CADENCE_SYNC_STAGE, since_epoch)
            if found and found != outcome["sync_log"]:
                outcome["sync_log"] = found
                if follower is not None:
                    follower.follow(found)
                    emit(PROGRESS["cadence_log_streaming"].format(path=found))
                else:
                    emit(PROGRESS["cadence_log_follow"].format(path=found))
        polls += 1
        if polls % CADENCE_HEARTBEAT_POLLS == 0:
            progress = _repo_sync_progress(host, log_root, since_epoch)
            beat = PROGRESS["cadence_heartbeat"].format(
                elapsed=int(time.time() - start),
                progress=PROGRESS["cadence_sync_progress"].format(progress=progress)
                if progress else "")
            if outcome["sync_log"] and follower is None:
                beat += f" | tail -f {outcome['sync_log']}"
            emit(beat)
        sleep_streaming(poll, follower)


def cadence_event_fields(events: List[str]) -> List[tuple]:
    """Summarize which cadence milestones were observed."""
    milestones = ("triggered", "cycle_started", "catalog_fetched", "sync_submitted",
                  "sync_succeeded", "committed", "completed")
    return [(mark(name in events, f"Cadence {name}"), "yes" if name in events else "no")
            for name in milestones]


# =============================================================================
# Cadence enable/disable (applied live: cadence_manager reloads
# build_stream_config.yml at the start of every cycle)
# =============================================================================

def is_cadence_enabled(host: Any, context: Dict[str, Any]) -> bool:
    """Return whether cadence is enabled in build_stream_config.yml."""
    del host
    cadence = context["config"].get(BSM_CONFIG_KEYS["cadence"]) or {}
    return cadence.get("enabled") is True


def _config_path(host: Any) -> str:
    """Return the project build_stream_config.yml path on the OIM."""
    return f"{domain_input_path(host, BSM_DOMAIN)}/{BSM_CONFIG_FILE}"


def read_cadence_enabled(host: Any) -> Optional[bool]:
    """Return cadence.enabled from build_stream_config.yml (None if unreadable)."""
    try:
        config = read_remote_yaml(host, _config_path(host)) or {}
    except (ValueError, yaml.YAMLError):
        return None
    value = (config.get(BSM_CONFIG_KEYS["cadence"]) or {}).get("enabled")
    return value if isinstance(value, bool) else None


def set_cadence_enabled(host: Any, enabled: bool, emit: Optional[Emit] = None) -> Dict[str, Any]:
    """Set cadence.enabled in build_stream_config.yml without restarting anything.

    Only the ``enabled:`` line of the ``cadence:`` block is rewritten, so
    comments and the other settings are preserved.

    Returns:
        Dict with keys: success, error.
    """
    try:
        path = _config_path(host)
    except ValueError as exc:
        return {"success": False, "error": str(exc)}
    if emit:
        emit(PROGRESS["cadence_set"].format(enabled=str(enabled).lower(), path=path))
    result = run_cmd(host, "cadence_enable" if enabled else "cadence_disable", path=path)
    actual = read_cadence_enabled(host)
    if result.rc != 0 or actual is not enabled:
        return {"success": False,
                "error": f"cadence.enabled is {actual} in {path} after the edit "
                         f"(expected {enabled}, rc={result.rc})"}
    return {"success": True, "error": ""}


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


def _trigger_and_watch(host: Any, script: str, poll: int, emit: Emit, debug_mode: bool,
                       timeout: Optional[int]) -> Dict[str, Any]:
    """Send SIGUSR1 via trigger_cadence.sh and follow the resulting cycle."""
    epoch = host_epoch(host)
    trigger = run_trigger_script(host, script, emit)
    emit(trigger["output"] or PROGRESS["trigger_script_rc"].format(rc=trigger["rc"]))
    if not trigger["success"]:
        return {"success": False, "events": [], "error":
                f"trigger_cadence.sh failed (rc={trigger['rc']}): {trigger['output']}"}
    return monitor_cadence_cycle(host, epoch, poll, emit, debug_mode, timeout)


def _disabled_cycle(host: Any, script: str, poll: int, emit: Emit,
                    debug_mode: bool) -> Dict[str, Any]:
    """Trigger a cycle that must be skipped as disabled.

    Returns:
        Dict with keys: success, fields, failures, events.
    """
    emit(PROGRESS["cadence_wait_disabled"].format(timeout=CADENCE_DISABLED_TIMEOUT))
    cycle = _trigger_and_watch(host, script, poll, emit, debug_mode, CADENCE_DISABLED_TIMEOUT)
    events = cycle["events"]
    work = [name for name in ("catalog_fetched", "sync_submitted", "committed", "completed")
            if name in events]
    checks = [
        ("Cycle started after trigger", "cycle_started" in events),
        ("'Cadence polling is disabled' logged", "disabled" in events),
        ("No catalog fetch / repo sync / commit", not work),
    ]
    fields = [(mark(ok, label), "yes" if ok else "NO") for label, ok in checks]
    failures = [label for label, ok in checks if not ok]
    if work:
        failures.append(f"disabled cadence still ran: {', '.join(work)}")
    if "disabled" not in events and cycle.get("error"):
        failures.append(cycle["error"])
    return {"success": not failures, "fields": fields, "failures": failures,
            "events": events}


def _toggle_result(host: Any) -> Dict[str, Any]:
    """Start a toggle result with the runtime prechecks."""
    runtime = _runtime_checks(host)
    return {"success": False, "fields": list(runtime["fields"]),
            "failures": list(runtime["failures"]), "script": runtime["script"],
            "original": read_cadence_enabled(host)}


def _restore(host: Any, original: Optional[bool], result: Dict[str, Any], emit: Emit) -> None:
    """Put cadence.enabled back to its value before the test."""
    if original is None or read_cadence_enabled(host) is original:
        return
    restored = set_cadence_enabled(host, original, emit)
    result["fields"].append((mark(restored["success"], "cadence.enabled restored"),
                             str(original).lower()))
    if not restored["success"]:
        result["failures"].append(f"restore cadence.enabled: {restored['error']}")


def verify_cadence_disable_live(host: Any, settings: Dict[str, Any],
                                emit: Emit) -> Dict[str, Any]:
    """Disable cadence in the config (no restart) and verify the next cycle is skipped.

    cadence.enabled is restored to its original value afterwards.

    Returns:
        Dict with keys: success, fields, failures.
    """
    result = _toggle_result(host)
    result["fields"].insert(0, ("cadence.enabled before", str(result["original"]).lower()))
    if result["failures"]:
        return result
    try:
        disabled = set_cadence_enabled(host, False, emit)
        result["fields"].append((mark(disabled["success"], "cadence.enabled set"), "false"))
        if not disabled["success"]:
            result["failures"].append(disabled["error"])
            return result
        cycle = _disabled_cycle(host, result["script"], settings["poll_interval"], emit,
                                settings.get("debug_mode", False))
        result["fields"].extend(cycle["fields"])
        result["failures"].extend(cycle["failures"])
    finally:
        _restore(host, result["original"], result, emit)
    result["success"] = not result["failures"]
    return result


def verify_cadence_reenable_live(host: Any, settings: Dict[str, Any],
                                 emit: Emit) -> Dict[str, Any]:
    """Re-enable cadence (no restart) and verify a triggered cycle runs to completion.

    The watcher is first brought to a disabled state (config false and one
    skipped cycle), so the enable is proven by the live reload
    (``enabled False -> True``) followed by a full cycle.
    cadence.enabled is restored to its original value afterwards.

    Returns:
        Dict with keys: success, fields, failures.
    """
    result = _toggle_result(host)
    result["fields"].insert(0, ("cadence.enabled before", str(result["original"]).lower()))
    if result["failures"]:
        return result
    poll, debug = settings["poll_interval"], settings.get("debug_mode", False)
    try:
        disabled = set_cadence_enabled(host, False, emit)
        if not disabled["success"]:
            result["failures"].append(disabled["error"])
            return result
        precondition = _disabled_cycle(host, result["script"], poll, emit, debug)
        result["fields"].append((mark(precondition["success"], "Precondition: cycle skipped "
                                      "while disabled"),
                                 "yes" if precondition["success"] else "NO"))
        if not precondition["success"]:
            result["failures"].extend(f"precondition: {item}"
                                      for item in precondition["failures"])
            return result

        context = load_bsm_context(host)
        if not context["success"]:
            result["failures"].append(f"BuildStream context: {context['error']}")
            return result
        upload = upload_cadence_catalog(host, context, settings["catalog"], emit)
        result["fields"].extend(upload["fields"])
        if not upload["success"]:
            result["failures"].extend(upload["failures"])
            return result
        enabled = set_cadence_enabled(host, True, emit)
        result["fields"].append((mark(enabled["success"], "cadence.enabled set"), "true"))
        if not enabled["success"]:
            result["failures"].append(enabled["error"])
            return result
        cycle = _trigger_and_watch(host, result["script"], poll, emit, debug, None)
        events = cycle["events"]
        checks = [
            ("Reload logged 'enabled False -> True'", "config_reloaded" in events),
            ("Cycle not skipped as disabled", "disabled" not in events),
            ("Repo sync submitted", "sync_submitted" in events),
            ("Cycle completed", cycle["success"]),
            (f"Cycle bumped the selected catalog to v{upload['expected']}",
             cycle.get("new_version") == upload["expected"]),
        ]
        result["fields"].extend((mark(ok, label), "yes" if ok else "NO") for label, ok in checks)
        result["fields"].extend(cadence_event_fields(events))
        result["fields"].append(("Repo sync log", cycle.get("sync_log") or "-"))
        result["failures"].extend(label for label, ok in checks if not ok)
        if not cycle["success"] and cycle.get("error"):
            result["failures"].append(f"cadence cycle: {cycle['error']}")
    finally:
        _restore(host, result["original"], result, emit)
    result["success"] = not result["failures"]
    return result
