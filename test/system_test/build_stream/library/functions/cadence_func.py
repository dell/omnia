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
from typing import Any, Callable, Dict, List

from .probe_func import data_path, run_cmd
from ..messages.system_test_msgs import PROGRESS_MSGS as PROGRESS
from ..vars.common_vars import (
    BSM_CONFIG_KEYS,
    BSM_PLAYBOOK_WATCHER_SERVICE,
    CADENCE_ERROR_MARKERS,
    CADENCE_HEARTBEAT_POLLS,
    CADENCE_JOURNAL_EVENTS,
    CADENCE_LOG_ROOT,
    CADENCE_LOGGER_NAME,
    CADENCE_TRIGGER_SCRIPT,
    CADENCE_VERSION_RE,
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
            "fields": [(label, value) for label, value, _ in checks],
            "failures": [f"{label}: {value}" for label, value, ok in checks if not ok],
            "script": script}


def run_trigger_script(host: Any, script: str) -> Dict[str, Any]:
    """Run trigger_cadence.sh. Returns dict with success, rc, output."""
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


def _repo_sync_progress(host: Any, log_root: str, since_epoch: int) -> str:
    """Return the latest ansible TASK of the newest cadence sync log."""
    directory = run_cmd(host, "newest_cadence_log_dir", root=log_root).stdout.strip()
    # Cadence job IDs are cadence-<UTC %Y%m%d%H%M%S>; ignore older runs.
    oldest = f"cadence-{time.strftime('%Y%m%d%H%M%S', time.gmtime(since_epoch))}"
    if not directory or directory.rsplit("/", 1)[-1] < oldest:
        return ""
    task = run_cmd(host, "last_ansible_task", directory=directory).stdout.strip()
    return f"{task.strip('* ')} ({directory})" if task else directory


def monitor_cadence_cycle(host: Any, since_epoch: int, poll: int, emit: Emit) -> Dict[str, Any]:
    """Follow the playbook-watcher journal until the cadence cycle ends (no timeout).

    The cycle ends on its completion message, a failure message (disabled,
    suppressed, repo sync failed/timed out) or a cadence_manager ERROR line.

    Returns:
        Dict with keys: success, events (ordered event keys), new_version,
        sync_log, error_lines, error.
    """
    outcome = {"success": False, "events": [], "new_version": "", "sync_log": "",
               "error_lines": [], "error": ""}
    log_root = f"{data_path(host)}/{CADENCE_LOG_ROOT}"
    processed = 0
    start = time.time()
    polls = 0
    while True:
        lines = run_cmd(host, "journal_since", unit=BSM_PLAYBOOK_WATCHER_SERVICE,
                        epoch=since_epoch).stdout.splitlines()
        for line in lines[processed:]:
            match = _classify(line)
            if not match:
                continue
            message = line.split(" - ", 3)[-1].strip() if " - " in line else line.strip()
            emit(PROGRESS["cadence_event"].format(event=match["event"], message=message))
            outcome["events"].append(match["event"])
            if "log_file=" in line and not outcome["sync_log"]:
                outcome["sync_log"] = line.split("log_file=", 1)[1].split(",")[0].strip()
            version = CADENCE_VERSION_RE.search(line)
            if version:
                outcome["new_version"] = version.group(1).rstrip(".")
            if match["outcome"] == "failed":
                outcome["error_lines"].append(message)
            if match["outcome"] == "success":
                outcome["success"] = True
                return outcome
            if match["outcome"] == "failed" and match["event"] != "error":
                outcome["error"] = message
                return outcome
        processed = len(lines)
        if outcome["error_lines"]:
            outcome["error"] = outcome["error_lines"][0]
            return outcome
        polls += 1
        if polls % CADENCE_HEARTBEAT_POLLS == 0:
            progress = _repo_sync_progress(host, log_root, since_epoch)
            emit(PROGRESS["cadence_heartbeat"].format(
                elapsed=int(time.time() - start),
                progress=PROGRESS["cadence_sync_progress"].format(progress=progress)
                if progress else ""))
        time.sleep(poll)


def cadence_event_fields(events: List[str]) -> List[tuple]:
    """Summarize which cadence milestones were observed."""
    milestones = ("triggered", "cycle_started", "catalog_fetched", "sync_submitted",
                  "sync_succeeded", "committed", "completed")
    return [(f"Cadence {name}", "yes" if name in events else "no") for name in milestones]
