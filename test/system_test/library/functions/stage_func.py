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

"""SVT stages: initialization, cleanup, environment_setup, system_verification, summary.

The same functions serve a local run on the OIM
(``./run_validation.sh svt_<theme> <stage>``) and the GitLab pipeline (one job
per stage). Each stage returns
``{"status": passed|skipped|failed, "error": str}``; the driver records it
in the run manifest ``reports/<run_id>/run.json``.
"""

import hashlib
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

import pytest
import yaml

from .fvt_func import describe_step, domain_dir, fvt_python, omnia_venv_path, run_fvt_step
from .process_func import capture_command, stream_command
from ..messages.svt_msgs import STAGE_MSGS
from ..vars.common_vars import (
    BUILD_STREAM_QUADLET,
    FVT_SETUP,
    FVT_TEST_CONFIG,
    GENERATOR,
    INPUTS_FILE,
    MODULE_ROOT,
    OMNIA_ENV_FILE,
    REPO_ROOT,
    REPORT_ROOT,
    RUN_ID_ENV,
    RUN_MANIFEST,
)
from ..vars.theme_vars import OWN_VENV_DOMAINS, STEP_REQUIRES_BUILD_STREAM, THEMES

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
                                               "test_config_sha256")}
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


def _sha256(path: str) -> str:
    """Return the SHA-256 of a file ("" when it is absent)."""
    try:
        with open(path, "rb") as stream:
            return hashlib.sha256(stream.read()).hexdigest()
    except OSError:
        return ""


def _passed() -> Dict[str, Any]:
    return {"status": "passed", "error": ""}


def _failed(error: str) -> Dict[str, Any]:
    return {"status": "failed", "error": error}


def _skipped(reason: str) -> Dict[str, Any]:
    return {"status": "skipped", "error": reason}


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


def initialization(run_id: str, theme: str, inputs: Optional[str],
                   test_config: Optional[str], emit: Emit) -> Dict[str, Any]:
    """Place the cluster files in the checkout, fill the src inputs and start the manifest."""
    if not os.path.isfile(os.path.join(REPO_ROOT, "src", "main", "omnia.sh")):
        return _failed(STAGE_MSGS["repo_missing"].format(path=REPO_ROOT))
    config_target = os.path.join(domain_dir(THEMES[theme]["test_config_domain"]), FVT_TEST_CONFIG)
    error = (_yaml_mapping_error(inputs or INPUTS_FILE)
             or _yaml_mapping_error(test_config or config_target)
             or _place(inputs, INPUTS_FILE) or _place(test_config, config_target))
    if error:
        return _failed(error)
    emit(STAGE_MSGS["inputs_placed"].format(target=INPUTS_FILE))
    emit(STAGE_MSGS["test_config_placed"].format(target=config_target))
    generated = stream_command([sys.executable, GENERATOR], cwd=os.path.dirname(GENERATOR))
    manifest = {
        "run_id": run_id, "theme": theme,
        "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "commit": capture_command(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT) or "unknown",
        "inputs_sha256": _sha256(INPUTS_FILE),
        "test_config_sha256": _sha256(config_target),
        "stages": load_manifest(run_id).get("stages", {}),
    }
    _write_json(os.path.join(run_dir(run_id), RUN_MANIFEST), manifest)
    with open(LATEST_RUN_FILE, "w", encoding="utf-8") as stream:
        stream.write(run_id)
    if not generated["success"]:
        return _failed(f"dataset generator failed (rc={generated['rc']})")
    emit(f"commit {manifest['commit']}")
    return _passed()


def _install_into_omnia_venv(domain: str, venv: str, emit: Emit) -> Dict[str, Any]:
    """Install a domain's test requirements into the Omnia venv (setup_env.sh, active venv)."""
    emit(STAGE_MSGS["step"].format(stage="setup", label=f"{domain} test requirements -> {venv}"))
    env = {"VIRTUAL_ENV": venv, "PATH": f"{venv}/bin:{os.environ.get('PATH', '')}"}
    return stream_command(["bash", FVT_SETUP], cwd=domain_dir(domain), env=env)


def _bootstrap_venv(domain: str, emit: Emit) -> Dict[str, Any]:
    """Create or reuse the suite's own .venv (setup_env.sh --venv)."""
    emit(STAGE_MSGS["step"].format(stage="setup", label=f"{domain} {FVT_SETUP} --venv"))
    return stream_command(["bash", FVT_SETUP, "--venv"], cwd=domain_dir(domain))


def _run_steps(stage: str, steps, emit: Emit) -> Dict[str, Any]:
    """Run FVT steps in order; stop at the first failure."""
    for step in steps:
        label = describe_step(step)
        emit(STAGE_MSGS["step"].format(stage=stage, label=label))
        result = run_fvt_step(step)
        if not result["success"]:
            return _failed(STAGE_MSGS["step_failed"].format(label=label, rc=result["rc"]))
    return _passed()


def _omnia_venv_ready() -> str:
    """Return the Omnia venv path when its interpreter exists ("" otherwise)."""
    venv = omnia_venv_path()
    return venv if venv and os.access(os.path.join(venv, "bin", "python"), os.X_OK) else ""


def cleanup(theme: str, emit: Emit) -> Dict[str, Any]:
    """Remove the previous installation with each suite's own cleanup FVT.

    BuildStream (when installed) and the base domains run from the Omnia venv;
    the Omnia setup cleanup (test/main) runs last from its own .venv.
    """
    if not os.path.isfile(OMNIA_ENV_FILE):
        return _skipped(STAGE_MSGS["no_previous_setup"].format(path=OMNIA_ENV_FILE))
    theme_data = THEMES[theme]
    venv = _omnia_venv_ready()
    steps = []
    for step in theme_data["cleanup_steps"]:
        domain = step[0]
        if step in STEP_REQUIRES_BUILD_STREAM and not os.path.exists(BUILD_STREAM_QUADLET):
            emit(STAGE_MSGS["no_build_stream"].format(path=BUILD_STREAM_QUADLET,
                                                      label=describe_step(step)))
        elif domain not in OWN_VENV_DOMAINS and not venv:
            emit(STAGE_MSGS["no_omnia_venv"].format(label=describe_step(step)))
        else:
            steps.append(step)
    for domain in dict.fromkeys(step[0] for step in steps):
        prepared = (_bootstrap_venv(domain, emit) if domain in OWN_VENV_DOMAINS
                    else _install_into_omnia_venv(domain, venv, emit))
        if not prepared["success"]:
            return _failed(STAGE_MSGS["step_failed"].format(label=f"{domain} {FVT_SETUP}",
                                                            rc=prepared["rc"]))
    return _run_steps("cleanup", steps, emit)


def environment_setup(theme: str, emit: Emit) -> Dict[str, Any]:
    """omnia.sh setup and domain init (test/main), then test deps in the Omnia venv."""
    theme_data = THEMES[theme]
    for domain in dict.fromkeys(step[0] for step in theme_data["setup_steps"]):
        bootstrap = _bootstrap_venv(domain, emit)
        if not bootstrap["success"]:
            return _failed(STAGE_MSGS["step_failed"].format(label=f"{domain} {FVT_SETUP} --venv",
                                                            rc=bootstrap["rc"]))
    outcome = _run_steps("environment_setup", theme_data["setup_steps"], emit)
    if outcome["status"] == "failed":
        return outcome
    venv = _omnia_venv_ready()
    if not venv:
        return _failed(STAGE_MSGS["venv_missing"].format(path=omnia_venv_path() or OMNIA_ENV_FILE))
    for domain in theme_data["fvt_domains"]:
        result = _install_into_omnia_venv(domain, venv, emit)
        if not result["success"]:
            return _failed(STAGE_MSGS["step_failed"].format(
                label=f"{domain} {FVT_SETUP}", rc=result["rc"]))
    emit(f"FVT interpreter: {fvt_python(theme_data['test_config_domain'])}")
    emit(STAGE_MSGS["creds_hint"])
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
