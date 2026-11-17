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
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

import yaml

from omnia_auto import read_remote_yaml

from . import catalog_func, gitlab_api_func
from .log_func import LogFollower, find_stage_log, mark, print_wrapped, sleep_streaming
from .execute_probe_func import data_path, domain_input_path, render_cmd, run_cmd
from ..messages.execute_msgs import PROGRESS_MSGS as PROGRESS
from ..vars.execute_vars import (
    BSM_CONFIG_FILE,
    BSM_CONFIG_KEYS,
    BSM_DOMAIN,
    BSM_PLAYBOOK_WATCHER_SERVICE,
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
    """Silently stage installation.cadence_catalog as GitLab cadence_catalog_rhel.json.

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
    outcome["fields"].extend([("installation.cadence_catalog", selection),
                              ("Catalog source", selected["path"]),
                              ("Catalog identifier", selected["identifier"]),
                              ("Versions in use", plan["seen"]),
                              ("Cadence catalog upload version", version),
                              ("Expected cadence bump", expected)])
    current = gitlab_api_func.get_file(context, GITLAB_CADENCE_CATALOG_FILE)
    if current["success"] and current["content"] == content:
        emit(PROGRESS["cadence_catalog_current"].format(
            file=GITLAB_CADENCE_CATALOG_FILE, source=selected["path"], version=version))
        outcome["fields"].append((mark(True, "Cadence catalog upload"), "already current"))
        outcome["success"] = True
        return outcome
    emit(PROGRESS["cadence_catalog_uploading"].format(
        source=selected["path"], file=GITLAB_CADENCE_CATALOG_FILE, version=version,
        expected=expected))
    commit = gitlab_api_func.commit_file(
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
    pipelines = [p for p in gitlab_api_func.list_pipelines(context, sha=commit["commit_id"])
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


@dataclass
class _CycleWatch:
    """State of one ``monitor_cadence_cycle`` run."""

    host: Any
    since_epoch: int
    emit: Emit
    follower: Optional[LogFollower]
    log_root: str
    start: float
    outcome: Dict[str, Any]


def _apply_journal_line(outcome: Dict[str, Any], line: str) -> bool:
    """Record one journal line in ``outcome``; return True when it ends the cycle."""
    entry = _journal_entry(line)
    if entry:
        print_wrapped(PROGRESS["cadence_journal_line"].format(line=entry))
    match = _classify(line)
    if not match:
        return False
    message = line.split(" - ", 3)[-1].strip() if " - " in line else line.strip()
    outcome["events"].append(match["event"])
    version = CADENCE_VERSION_RE.search(line)
    if version:
        outcome["new_version"] = version.group(1).rstrip(".")
    if match["outcome"] == "failed":
        outcome["error_lines"].append(message)
    if match["outcome"] == "success":
        outcome["success"] = True
        return True
    if match["outcome"] == "failed" and match["event"] != "error":
        outcome["error"] = message
        return True
    return False


def _cycle_ended(watch: _CycleWatch, timeout: Optional[int]) -> bool:
    """End the wait on a logged error line or when ``timeout`` passed."""
    outcome = watch.outcome
    if outcome["error_lines"]:
        outcome["error"] = outcome["error_lines"][0]
        return True
    if timeout is not None and time.time() - watch.start >= timeout:
        outcome["error"] = f"no terminal cadence message within {timeout}s"
        return True
    return False


def _follow_sync_log(watch: _CycleWatch) -> None:
    """Locate the repo sync log and stream it or print ``tail -f``."""
    found = find_stage_log(watch.host, CADENCE_SYNC_STAGE, watch.since_epoch)
    if not found or found == watch.outcome["sync_log"]:
        return
    watch.outcome["sync_log"] = found
    if watch.follower is not None:
        watch.follower.follow(found)
        watch.emit(PROGRESS["cadence_log_streaming"].format(path=found))
    else:
        watch.emit(PROGRESS["cadence_log_follow"].format(path=found))


def _heartbeat(watch: _CycleWatch) -> None:
    """Emit the elapsed time and the repo sync progress."""
    progress = _repo_sync_progress(watch.host, watch.log_root, watch.since_epoch)
    beat = PROGRESS["cadence_heartbeat"].format(
        elapsed=int(time.time() - watch.start),
        progress=PROGRESS["cadence_sync_progress"].format(progress=progress)
        if progress else "")
    if watch.outcome["sync_log"] and watch.follower is None:
        beat += f" | tail -f {watch.outcome['sync_log']}"
    watch.emit(beat)


def _end_cycle(watch: _CycleWatch) -> Dict[str, Any]:
    """Drain the sync log stream and return the outcome."""
    if watch.follower is not None and watch.follower.path:
        watch.follower.drain(final=True)
    return watch.outcome


def monitor_cadence_cycle(host: Any, since_epoch: int, settings: Dict[str, Any], emit: Emit,
                          timeout: Optional[int] = None) -> Dict[str, Any]:
    """Follow the playbook-watcher journal until the cadence cycle ends.

    ``settings`` supplies poll_interval and debug_mode. The cycle ends on
    its completion message, a failure message (disabled, suppressed, repo
    sync failed/timed out) or a cadence_manager ERROR line. There is no
    timeout unless ``timeout`` (seconds) is given.

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
    follower = LogFollower(host) if settings["debug_mode"] else None
    watch = _CycleWatch(host, since_epoch, emit, follower, log_root, time.time(), outcome)
    processed, polls = 0, 0
    emit(PROGRESS["cadence_journal_header"])
    while True:
        lines = run_cmd(host, "journal_since", unit=BSM_PLAYBOOK_WATCHER_SERVICE,
                        epoch=since_epoch).stdout.splitlines()
        if any(_apply_journal_line(outcome, line) for line in lines[processed:]):
            return _end_cycle(watch)
        processed = len(lines)
        if _cycle_ended(watch, timeout):
            return _end_cycle(watch)
        if "sync_submitted" in outcome["events"]:
            _follow_sync_log(watch)
        polls += 1
        if polls % CADENCE_HEARTBEAT_POLLS == 0:
            _heartbeat(watch)
        sleep_streaming(settings["poll_interval"], follower)


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
