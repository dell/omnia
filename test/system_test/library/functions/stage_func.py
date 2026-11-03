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

"""SVT stages: initialization, the theme's stages (pytest tests), summary.

The OIM is prepared first with ./setup_env.sh (load, cleanup, install, creds;
library/functions/setup_func.py). The same stage functions serve a local run on
the OIM (``./run_validation.sh svt_<theme> <stage>``) and a pipeline (one job
per stage). Each stage returns ``{"status": passed|skipped|failed, "error": str}``;
the driver records it in the run manifest ``<run folder>/run.json``. The run
(id, theme, folder) is the one started by ./setup_env.sh --configure
(run_func.py); the stage logs, the manifest and the report share its folder.
"""

import json
import os
import shutil
import tempfile
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict

import pytest

from . import svt_report_func
from .config_func import ConfigError, load_svt_config, theme_config_path
from .process_func import capture_command
from .run_func import describe, load_run, settings_of
from .setup_func import load_setup_record, readiness_checks, sha256
from ..messages.svt_msgs import STAGE_MSGS
from ..vars.common_vars import (
    FIRST_STAGE,
    INPUTS_FILE,
    MODULE_ROOT,
    REPO_ROOT,
    REPORT_ROOT,
    REPORT_SECTION_ENV,
    RUN_ID_ENV,
    RUN_MANIFEST,
    SETUP_REPORT_DIR,
    SETUP_STEPS,
)

Emit = Callable[[str], None]


def run_dir(run_id: str) -> str:
    """Return (and create, mode 0750) the folder of a run: its report folder when it is
    the current run, else reports/<run_id>."""
    run = load_run()
    path = run["report_path"] if run.get("run_id") == run_id and run.get("report_path") \
        else os.path.join(REPORT_ROOT, run_id)
    os.makedirs(path, mode=0o750, exist_ok=True)
    return path


def _write_json(path: str, data: Dict[str, Any]) -> None:
    """Write JSON atomically."""
    handle, temp = tempfile.mkstemp(prefix=".tmp.", dir=os.path.dirname(path))
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(data, stream, indent=2, sort_keys=True)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def load_manifest(run_id: str) -> Dict[str, Any]:
    """Return the run manifest ({} when the run has none)."""
    try:
        with open(os.path.join(run_dir(run_id), RUN_MANIFEST), "r", encoding="utf-8") as stream:
            data = json.load(stream)
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def record_stage(run_id: str, stage: str, outcome: Dict[str, Any]) -> None:
    """Store a stage outcome in the run manifest."""
    manifest = load_manifest(run_id)
    manifest.setdefault("stages", {})[stage] = outcome
    _write_json(os.path.join(run_dir(run_id), RUN_MANIFEST), manifest)


def _passed() -> Dict[str, Any]:
    return {"status": "passed", "error": ""}


def _failed(error: str) -> Dict[str, Any]:
    return {"status": "failed", "error": error}


def _copy_setup_reports(run_id: str) -> None:
    """Copy reports/setup (the ./setup_env.sh logs and record) into the run folder."""
    if os.path.isdir(SETUP_REPORT_DIR):
        shutil.copytree(SETUP_REPORT_DIR, os.path.join(run_dir(run_id), "setup"),
                        dirs_exist_ok=True)


def _report_section(theme: str, done: Dict[str, Any], emit: Emit) -> None:
    """Add a finished stage section (svt_report_func.add_section ``done``) to the SVT
    report and re-render it; never fails the stage."""
    run = load_run()
    try:
        settings = settings_of(run)
        svt_report_func.add_section(settings, {"kind": "stage", "status": None, **done})
        svt_report_func.render(settings, svt_report_func.run_meta(theme, run))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        emit(f"WARNING: the SVT report was not updated: {type(exc).__name__}: {exc}")


def initialization(run_id: str, theme: str, emit: Emit) -> Dict[str, Any]:
    """Check that ./setup_env.sh prepared this OIM for ``theme``; start the run manifest.

    Ready means: the inputs were configured and installed unchanged since;
    omnia.sh -s completed; the test requirements are in the Omnia venv; every
    domain credential store of the theme exists. Each check is a report item.
    """
    started = time.monotonic()
    started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if not os.path.isfile(os.path.join(REPO_ROOT, "src", "main", "omnia.sh")):
        return _failed(STAGE_MSGS["repo_missing"].format(path=REPO_ROOT))
    try:
        config = load_svt_config(theme)
    except ConfigError as exc:
        return _failed(str(exc))
    checks = readiness_checks(theme)
    rows = [{"name": label, "status": "Passed" if ok else "Failed",
             "details": "" if ok else detail} for label, ok, detail in checks]
    _report_section(theme, {"name": FIRST_STAGE, "rows": rows, "started_at": started_at,
                            "duration": time.monotonic() - started}, emit)
    problems = [f"{label}: {detail}" for label, ok, detail in checks if not ok]
    if problems:
        return _failed(STAGE_MSGS["not_ready"].format(problems="\n  - " + "\n  - ".join(problems)))
    emit(STAGE_MSGS["ready"])
    setup = load_setup_record()
    for path in (setup.get("install") or {}).get("stale_inputs") or []:
        emit(STAGE_MSGS["stale_input"].format(path=path))
    manifest = {
        "run_id": run_id, "theme": theme, "started_at": started_at,
        "commit": capture_command(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT) or "unknown",
        "inputs_sha256": sha256(INPUTS_FILE),
        "theme_config_sha256": sha256(theme_config_path(theme)),
        "cleanup": config["cleanup"], "fvt_settings": config["fvt_settings"],
        "setup": {action: {key: setup[action].get(key)
                           for key in ("status", "started_at", "duration")}
                  for action in SETUP_STEPS if action in setup},
        "stages": load_manifest(run_id).get("stages", {}),
    }
    _write_json(os.path.join(run_dir(run_id), RUN_MANIFEST), manifest)
    _copy_setup_reports(run_id)
    emit(f"commit {manifest['commit']}")
    return _passed()


def run_tests(run_id: str, theme: str, stage: str, emit: Emit) -> Dict[str, Any]:
    """Run the SVT tests of ``stage`` (svt/<theme>, markers ``<theme> and <stage>``).

    The stage is a section of the SVT report; each test adds its item (FVT
    step output and results) while it runs.
    """
    os.environ[RUN_ID_ENV] = run_id
    started = time.monotonic()
    run = load_run()
    settings = settings_of(run)
    section = svt_report_func.open_section(settings, "stage", stage)
    os.environ[REPORT_SECTION_ENV] = section
    marker = f"{theme} and {stage}"
    junit = os.path.join(run_dir(run_id), f"junit_{theme}_{stage}.xml")
    emit(STAGE_MSGS["step"].format(stage=stage, label=f"svt/{theme} -m '{marker}'"))
    rc = 1  # stays 1 when pytest does not finish
    try:
        rc = int(pytest.main([os.path.join(MODULE_ROOT, "svt", theme), "-m", marker,
                              f"--junitxml={junit}"]))
    finally:
        os.environ.pop(REPORT_SECTION_ENV, None)
        svt_report_func.close_section(settings, section, time.monotonic() - started,
                                      "Failed" if rc != 0 else None)
        svt_report_func.render(settings, svt_report_func.run_meta(theme, load_run()))
    if rc != 0:
        return _failed(STAGE_MSGS["tests_failed"].format(stage=stage, rc=rc,
                                                         path=run_dir(run_id)))
    return _passed()


def _render_report(run_id: str, emit: Emit) -> None:
    """Re-render the SVT report of this run with the current run details."""
    run = load_run()
    if run.get("run_id") != run_id:
        return
    try:
        path = svt_report_func.render(settings_of(run),
                                      svt_report_func.run_meta(run["theme"], run))
        emit(f"report: {path}")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        emit(f"WARNING: the SVT report was not updated: {type(exc).__name__}: {exc}")


def summary(run_id: str, emit: Emit) -> Dict[str, Any]:
    """Print the run: commit, setup and stage outcomes, SVT test results; render the report."""
    manifest = load_manifest(run_id)
    stages = manifest.get("stages", {})
    if manifest:
        emit(f"run {run_id}  theme {manifest.get('theme')}  commit {manifest.get('commit')}")
        for action, outcome in (manifest.get("setup") or {}).items():
            emit(f"  setup {action:<14} {outcome.get('status') or '?':<8} "
                 f"{outcome.get('duration') or '':<8} {outcome.get('started_at') or ''}")
        for name, outcome in stages.items():
            detail = f" - {outcome.get('error')}" if outcome.get("error") else ""
            emit(f"  {name:<22} {outcome.get('status', '?'):<8} "
                 f"{outcome.get('duration', '')}{detail}")
    else:
        emit(STAGE_MSGS["no_manifest"].format(run_id=run_id))
    try:
        with open(os.path.join(run_dir(run_id), "svt_results.json"), "r",
                  encoding="utf-8") as stream:
            tests = json.load(stream)
    except (OSError, json.JSONDecodeError):
        tests = []
    for test in tests:
        emit(f"  {test.get('id', ''):<22} {test.get('outcome', ''):<8} "
             f"{test.get('duration', ''):>6}  {test.get('title', '')}")
    emit(f"run folder: {run_dir(run_id)}")
    _render_report(run_id, emit)
    return _verdict(run_id, stages, emit)


def _verdict(run_id: str, stages: Dict[str, Any], emit: Emit) -> Dict[str, Any]:
    """Fail the summary when a stage or step failed or the run holds failed results."""
    problems = [f"stage {name} failed" for name, outcome in stages.items()
                if outcome.get("status") == "failed"]
    run = load_run()
    if run.get("run_id") == run_id:
        state = describe(run)
        if state != "open" and not any(state.endswith(f"stage {name}") for name in stages):
            problems.append(f"run {state}")
        failed = svt_report_func.failed_parts(settings_of(run))
        if failed:
            emit(f"failed: {', '.join(failed)}")
            problems.append(f"failed: {', '.join(failed)}")
    return _failed("; ".join(problems)) if problems else _passed()
