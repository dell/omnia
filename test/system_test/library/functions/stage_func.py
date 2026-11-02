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

"""SVT stages: initialization, system_verification, summary.

The OIM is prepared first with ./setup_env.sh (load, cleanup, install, creds;
library/functions/setup_func.py). The same stage functions serve a local run on
the OIM (``./run_validation.sh svt_<theme> <stage>``) and a pipeline (one job
per stage). Each stage returns ``{"status": passed|skipped|failed, "error": str}``;
the driver records it in the run manifest ``reports/<run_id>/run.json``.
"""

import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

import pytest
import yaml

from .config_func import ConfigError, load_svt_config
from .fvt_func import domain_dir
from .process_func import capture_command
from .setup_func import load_setup_record, readiness_problems, sha256
from ..messages.svt_msgs import STAGE_MSGS
from ..vars.common_vars import (
    FVT_TEST_CONFIG,
    INPUTS_FILE,
    MODULE_ROOT,
    REPO_ROOT,
    REPORT_ROOT,
    RUN_ID_ENV,
    RUN_MANIFEST,
    SETUP_REPORT_DIR,
    SVT_TEST_CONFIG,
)
from ..vars.theme_vars import THEMES

Emit = Callable[[str], None]
LATEST_RUN_FILE = os.path.join(REPORT_ROOT, "latest")


def run_dir(run_id: str) -> str:
    """Return (and create, mode 0750) the report directory of a run."""
    path = os.path.join(REPORT_ROOT, run_id)
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


def require_run(run_id: str, theme: str, resume: bool) -> None:
    """Make sure ``run_id`` was initialized for ``theme`` before a stage acts on the OIM.

    ``resume`` adopts the last initialized run of this checkout (same theme) for a
    new run id, for example a pipeline re-run from a later stage.

    Raises:
        ValueError: When the run (or, with resume, the checkout) was never initialized.
    """
    manifest = load_manifest(run_id)
    if manifest:
        if manifest.get("theme") != theme:
            raise ValueError(f"run {run_id} was initialized for theme "
                             f"{manifest.get('theme')!r}, not {theme!r}")
        return
    if not resume:
        raise ValueError(STAGE_MSGS["not_initialized"].format(run_id=run_id))
    previous = latest_run_id()
    base = load_manifest(previous) if previous else {}
    if base.get("theme") != theme:
        raise ValueError(STAGE_MSGS["nothing_to_resume"].format(theme=theme))
    adopted = {key: base.get(key) for key in ("theme", "commit", "inputs_sha256",
                                               "svt_test_config_sha256",
                                               "test_config_sha256", "setup", "cleanup")}
    adopted.update(run_id=run_id, resumed_from=previous, stages={},
                   started_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    _write_json(os.path.join(run_dir(run_id), RUN_MANIFEST), adopted)


def latest_run_id() -> str:
    """Return the run started last on this checkout ("" when none)."""
    try:
        with open(LATEST_RUN_FILE, "r", encoding="utf-8") as stream:
            return stream.read().strip()
    except OSError:
        return ""


def _passed() -> Dict[str, Any]:
    return {"status": "passed", "error": ""}


def _failed(error: str) -> Dict[str, Any]:
    return {"status": "failed", "error": error}


def _place(source: Optional[str], target: str) -> str:
    """Copy ``source`` over ``target`` unless they are the same file; return an error or ""."""
    if not source:
        return ""
    if not os.path.isfile(source):
        return f"{source} is not a file"
    if os.path.realpath(source) != os.path.realpath(target):
        shutil.copyfile(source, target)
    return ""


def _yaml_mapping_error(path: str) -> str:
    """Return why ``path`` is not a YAML mapping ("" when it is)."""
    try:
        with open(path, "r", encoding="utf-8") as stream:
            data = yaml.safe_load(stream)
    except (OSError, yaml.YAMLError) as exc:
        return f"{path}: {exc}"
    return "" if isinstance(data, dict) else f"{path} is not a YAML mapping"


def _copy_setup_reports(run_id: str) -> None:
    """Copy reports/setup (the ./setup_env.sh logs and record) into the run report."""
    if os.path.isdir(SETUP_REPORT_DIR):
        shutil.copytree(SETUP_REPORT_DIR, os.path.join(run_dir(run_id), "setup"),
                        dirs_exist_ok=True)


def initialization(run_id: str, theme: str, test_config: Optional[str],
                   emit: Emit) -> Dict[str, Any]:
    """Check that ./setup_env.sh prepared this OIM, place the FVT test_config, start the manifest.

    Ready means: test_config.yml selects ``theme``; user_inputs.yml was loaded
    and installed unchanged since; omnia.sh -s completed; the Omnia venv is
    active; every domain credential store of the theme exists.
    """
    if not os.path.isfile(os.path.join(REPO_ROOT, "src", "main", "omnia.sh")):
        return _failed(STAGE_MSGS["repo_missing"].format(path=REPO_ROOT))
    try:
        config = load_svt_config()
    except ConfigError as exc:
        return _failed(str(exc))
    if config["theme"] != theme:
        return _failed(STAGE_MSGS["theme_mismatch"].format(
            path=SVT_TEST_CONFIG, config_theme=config["theme"], theme=theme))
    problems = readiness_problems(theme)
    if problems:
        return _failed(STAGE_MSGS["not_ready"].format(problems="\n  - " + "\n  - ".join(problems)))
    emit(STAGE_MSGS["ready"])
    setup = load_setup_record()
    for path in (setup.get("install") or {}).get("stale_inputs") or []:
        emit(STAGE_MSGS["stale_input"].format(path=path))
    config_target = os.path.join(domain_dir(THEMES[theme]["test_config_domain"]), FVT_TEST_CONFIG)
    error = _yaml_mapping_error(test_config or config_target) or _place(test_config, config_target)
    if error:
        return _failed(error)
    emit(STAGE_MSGS["test_config_placed"].format(target=config_target))
    manifest = {
        "run_id": run_id, "theme": theme,
        "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "commit": capture_command(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT) or "unknown",
        "inputs_sha256": sha256(INPUTS_FILE),
        "svt_test_config_sha256": sha256(SVT_TEST_CONFIG),
        "test_config_sha256": sha256(config_target),
        "cleanup": config["cleanup"],
        "setup": {action: {key: outcome.get(key) for key in ("status", "started_at", "duration")}
                  for action, outcome in setup.items()},
        "stages": load_manifest(run_id).get("stages", {}),
    }
    _write_json(os.path.join(run_dir(run_id), RUN_MANIFEST), manifest)
    _copy_setup_reports(run_id)
    with open(LATEST_RUN_FILE, "w", encoding="utf-8") as stream:
        stream.write(run_id)
    emit(f"commit {manifest['commit']}")
    return _passed()


def system_verification(run_id: str, theme: str, case: Optional[str],
                        emit: Emit) -> Dict[str, Any]:
    """Run the theme's SVT suite (one or all test cases) with pytest in this process."""
    os.environ[RUN_ID_ENV] = run_id
    marker = f"{theme} and {case}" if case else theme
    junit = os.path.join(run_dir(run_id), f"junit_{theme}.xml")
    emit(STAGE_MSGS["step"].format(stage="system_verification", label=f"svt/{theme} -m '{marker}'"))
    rc = int(pytest.main([os.path.join(MODULE_ROOT, "svt", theme), "-m", marker,
                          f"--junitxml={junit}"]))
    if rc != 0:
        return _failed(f"SVT suite failed (rc={rc}); see {run_dir(run_id)}")
    return _passed()


def summary(run_id: str, emit: Emit) -> Dict[str, Any]:
    """Print the run: commit, inputs, stage outcomes and SVT case results."""
    manifest = load_manifest(run_id)
    if not manifest:
        return _failed(STAGE_MSGS["unknown_run"])
    emit(f"run {run_id}  theme {manifest.get('theme')}  commit {manifest.get('commit')}"
         + (f"  (resumed from {manifest['resumed_from']})" if manifest.get("resumed_from") else ""))
    emit(f"inputs sha256 {manifest.get('inputs_sha256')}  "
         f"test_config sha256 {manifest.get('test_config_sha256')}")
    for action, outcome in (manifest.get("setup") or {}).items():
        emit(f"  setup {action:<14} {outcome.get('status') or '?':<8} "
             f"{outcome.get('duration') or '':<8} {outcome.get('started_at') or ''}")
    stages = manifest.get("stages", {})
    for name, outcome in stages.items():
        detail = f" - {outcome.get('error')}" if outcome.get("error") else ""
        emit(f"  {name:<20} {outcome.get('status', '?'):<8} "
             f"{outcome.get('duration', '')}{detail}")
    results_path = os.path.join(run_dir(run_id), "svt_results.json")
    try:
        with open(results_path, "r", encoding="utf-8") as stream:
            cases = json.load(stream)
    except (OSError, json.JSONDecodeError):
        cases = []
    for case in cases:
        emit(f"  {case.get('id', ''):<22} {case.get('outcome', ''):<8} "
             f"{case.get('duration', '')}  {case.get('title', '')}")
    emit(f"reports: {run_dir(run_id)}")
    failed = [name for name, outcome in stages.items() if outcome.get("status") == "failed"]
    return _failed(f"failed stage(s): {', '.join(failed)}") if failed else _passed()
