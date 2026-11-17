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

"""The SVT run: one run id, one theme, one report folder.

``./setup_env.sh --configure`` starts a run: its id is ``svt-<UTC time>`` (or
<theme>_test_config.yml ``report.run_id``) and its report folder is
``<report_path>/<run_id>/``. Every later step (cleanup, install, creds and the
``./run_validation.sh`` stages) uses that run; none of them starts another one.

A step does not run when:

* no run was started;
* another theme is asked for, or the theme's test_config changed its
  report settings;
* a step of the run failed (or was interrupted), or a section of the run's
  SVT report failed. Results other processes write into the FVT report (a
  suite run by hand, the BuildStream validate stage) do not count. The
  summary stage still runs.

Then ``./setup_env.sh --configure`` starts a new run. The OIM state (the
installation, the credentials, reports/setup/setup.json) is kept across runs.
"""

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List

from . import svt_report_func
from .config_func import report_settings
from ..messages.svt_msgs import RUN_MSGS
from ..vars.common_vars import RUN_ID_FORMAT, RUN_MARKER, RUN_STATE, SETTING_KEYS
from ..vars.theme_vars import soft_stages



class RunError(ValueError):
    """No step may run in the current run; the message says how to fix it."""


def load_run() -> Dict[str, Any]:
    """Return the current run ({} before the first ./setup_env.sh --configure)."""
    return svt_report_func.load_json(RUN_STATE)


def _save(run: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(RUN_STATE), mode=0o750, exist_ok=True)
    svt_report_func.write_atomic(RUN_STATE, json.dumps(run, indent=2, sort_keys=True))


def settings_of(run: Dict[str, Any]) -> Dict[str, str]:
    """Return the report settings of a run (report_path, report_name, run_id)."""
    return {key: run[key] for key in SETTING_KEYS}


def _new_run_id(previous: str) -> str:
    """Return svt-<UTC time>; svt-<time>-2, -3 ... when started within the same second."""
    stamp = datetime.now(timezone.utc).strftime(RUN_ID_FORMAT)
    if previous != stamp and not previous.startswith(f"{stamp}-"):
        return stamp
    suffix = previous[len(stamp) + 1:]
    return f"{stamp}-{int(suffix) + 1 if suffix.isdigit() else 2}"


def describe(run: Dict[str, Any]) -> str:
    """Return the state of a run: "open" or "failed at <step>"."""
    failed = run.get("failed") or {}
    return f"failed at {failed['step']}" if failed.get("step") else "open"


def start_run(config: Dict[str, Any]) -> Dict[str, Any]:
    """Start the run of ``config["theme"]`` and record it; return the run.

    Raises:
        RunError: The report folder already holds this run id for another theme.
    """
    theme = config["theme"]
    previous = load_run()
    run_id = config["report"]["run_id"] or _new_run_id(previous.get("run_id", ""))
    settings = report_settings(config, run_id)
    marker = os.path.join(settings["report_path"], RUN_MARKER)
    held = (svt_report_func.load_json(marker).get("theme")
            or svt_report_func.report_theme(settings))
    if held and held != theme:
        raise RunError(RUN_MSGS["report_theme"].format(
            report=settings["report_path"], run_id=run_id, report_theme=held, theme=theme))
    run = {**settings, "theme": theme, "failed": {},
           "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    if previous.get("run_id") and previous["run_id"] != run_id:
        run["previous"] = {"run_id": previous["run_id"], "state": describe(previous),
                           "report_path": previous.get("report_path", "")}
    _save(run)
    os.makedirs(settings["report_path"], mode=0o750, exist_ok=True)
    svt_report_func.write_atomic(marker, json.dumps(
        {"run_id": run_id, "theme": theme, "started_at": run["started_at"]}, indent=2))
    return run


def active_run(config: Dict[str, Any], allow_failed: bool = False) -> Dict[str, str]:
    """Return the report settings of the current run, or raise why no step may run.

    ``allow_failed`` accepts a failed run (the summary stage and the report).

    Raises:
        RunError: No run, another theme or report settings, or a failed run.
    """
    run = load_run()
    if not run.get("run_id"):
        raise RunError(RUN_MSGS["none"])
    if run.get("theme") != config["theme"]:
        raise RunError(RUN_MSGS["theme_changed"].format(
            run_id=run["run_id"], run_theme=run.get("theme"), theme=config["theme"]))
    expected = report_settings(config, config["report"]["run_id"] or run["run_id"])
    for field in SETTING_KEYS:
        if expected[field] != run.get(field):
            raise RunError(RUN_MSGS["settings_changed"].format(
                run_id=run["run_id"], field=field, old=run.get(field), new=expected[field]))
    settings = settings_of(run)
    if allow_failed:
        return settings
    failed = run.get("failed") or {}
    if failed.get("step"):
        raise RunError(RUN_MSGS["failed"].format(run_id=run["run_id"], step=failed["step"],
                                                 error=failed.get("error") or "see its log"))
    failed_parts = svt_report_func.failed_parts(settings, soft_stages(config["theme"]))
    if failed_parts:
        raise RunError(RUN_MSGS["fvt_failed"].format(run_id=run["run_id"],
                                                     modules=", ".join(failed_parts)))
    return settings


def retry(config: Dict[str, Any], steps: List[str]) -> str:
    """Let the failed step of the current run run again; return the message to print.

    ``steps`` are the step names this command runs (``stage <name>``, ``setup <name>``). When
    the run failed (or was interrupted) at one of them, the failure is cleared (and kept
    in ``retries``) and the failed sections of the report are marked as replaced: the new
    attempt takes their place in the report (the earlier one is archived in the run folder). A run that did not
    fail changes nothing. The run keeps its id, folder and report.

    Raises:
        RunError: No run, another theme or settings, or the run failed at another step.
    """
    settings = active_run(config, allow_failed=True)
    run = load_run()
    failed = run.get("failed") or {}
    step = failed.get("step") or ""
    if step and step.split(" (")[0] not in steps:
        raise RunError(RUN_MSGS["retry_other"].format(
            run_id=run["run_id"], step=step, allowed=", ".join(steps)))
    message = ""
    if step:
        run["retries"] = [*run.get("retries", []), {
            "step": step, "error": failed.get("error", ""), "at": datetime.now(
                timezone.utc).isoformat(timespec="seconds")}]
        run["failed"] = {}
        _save(run)
        message = RUN_MSGS["retrying"].format(run_id=run["run_id"], step=step,
                                              error=failed.get("error") or "no error recorded")
    svt_report_func.supersede_failed(settings, [name.split(" ", 1)[1] for name in steps])
    return message


def mark_failed(step: str, error: str) -> str:
    """Record that ``step`` of the current run failed; return the message to print ("" if none)."""
    run = load_run()
    if not run.get("run_id"):
        return ""
    if not (run.get("failed") or {}).get("step"):
        run["failed"] = {"step": step, "error": (error or "").splitlines()[0][:300] if error
                         else "", "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        _save(run)
    return RUN_MSGS["marked_failed"].format(run_id=run["run_id"], step=run["failed"]["step"])
