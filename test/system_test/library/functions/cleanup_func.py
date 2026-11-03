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

"""./setup_env.sh cleanup: remove the previous installation with each suite's own cleanup FVT.

Order: BuildStream (when installed), orchestrator, image_build_manager,
repo_manager, then the Omnia setup (test/main). With cleanup.main.cleanup_all
the main step is the complete reset: first every src/<domain>/domain-init.sh
--cleanup (each domain's input and log artifacts, which omnia.sh requires to
hold no files), then omnia.sh --cleanup --all --skip-approval (test/main),
which deletes the whole OMNIA_DATA_PATH; the next install then asks nothing.
"""

import glob
import os
import sys
from typing import Any, Callable, Dict, List

from .config_func import apply_cleanup_flags, apply_report_settings, cleanup_all, cleanup_enabled
from .fvt_func import describe_step, domain_dir, run_fvt_step
from .omnia_func import omnia_env
from .process_func import stream_command, tee_command
from .setup_func import (
    current_run,
    install_requirements,
    omnia_venv_path,
    result_row,
    row,
    venv_env,
)
from ..messages.svt_msgs import SETUP_MSGS, STAGE_MSGS
from ..vars.common_vars import (
    BUILD_STREAM_QUADLET,
    DOMAIN_INIT_CLEANUP_ARG,
    DOMAIN_INIT_GLOB,
    FVT_BOOTSTRAP_PYTHON,
    FVT_SETUP,
    OMNIA_DATA_KEY,
    OMNIA_ENV_FILE,
    VIRTUAL_ENV_KEY,
)
from ..vars.theme_vars import CLEANUP_FLAGS, OWN_VENV_DOMAINS, STEP_REQUIRES_BUILD_STREAM, THEMES

Emit = Callable[[str], None]
Rows = List[Dict[str, Any]]


def _failed(error: str, rows: Rows) -> Dict[str, Any]:
    return {"status": "failed", "error": error, "rows": rows}


def _venv_ready() -> str:
    """Return the Omnia venv when its interpreter exists ("" otherwise)."""
    venv = omnia_venv_path()
    return venv if venv and os.access(os.path.join(venv, "bin", "python"), os.X_OK) else ""


def _own_venv_env(domain: str) -> Dict[str, str]:
    """Return the environment of a suite that runs from its own .venv (test/main).

    test/main skips omnia.sh --cleanup when VIRTUAL_ENV is the Omnia venv, so
    an Omnia venv the user activated must not leak into this step.
    """
    venv = os.path.dirname(os.path.dirname(os.path.join(domain_dir(domain),
                                                        FVT_BOOTSTRAP_PYTHON)))
    return {VIRTUAL_ENV_KEY: venv, "PATH": f"{venv}/bin:{os.environ.get('PATH', '')}"}


def _select_steps(config: Dict[str, Any], venv: str, emit: Emit, rows: Rows) -> List[tuple]:
    """Return the cleanup steps that apply on this OIM; record why the others are skipped."""
    steps = []
    for step in THEMES[config["theme"]]["cleanup_steps"]:
        domain, label = step[0], describe_step(step)
        if not cleanup_enabled(config, domain):
            reason = SETUP_MSGS["cleanup_disabled"].format(label=label, domain=domain)
        elif step in STEP_REQUIRES_BUILD_STREAM and not os.path.exists(BUILD_STREAM_QUADLET):
            reason = STAGE_MSGS["no_build_stream"].format(path=BUILD_STREAM_QUADLET, label=label)
        elif domain not in OWN_VENV_DOMAINS and not venv:
            reason = STAGE_MSGS["no_omnia_venv"].format(label=label)
        else:
            steps.append(step)
            continue
        emit(reason)
        rows.append(row(label, "SKIPPED", details=reason))
    return steps


def _confirm(steps: List[tuple], full: bool, emit: Emit, assume_yes: bool) -> str:
    """Show the steps and ask for 'yes'; return an error, or "" when confirmed."""
    emit(SETUP_MSGS["cleanup_plan"])
    for step in steps:
        if full and step[0] in OWN_VENV_DOMAINS:
            emit(f"    {SETUP_MSGS['initializer_cleanup_plan']}")
        emit(f"    {describe_step(step)}")
    if full:
        emit(SETUP_MSGS["cleanup_all_warning"].format(data=omnia_env().get(OMNIA_DATA_KEY, "")))
    if assume_yes:
        emit(SETUP_MSGS["cleanup_confirmed_yes"])
        return ""
    if not sys.stdin.isatty():
        return SETUP_MSGS["cleanup_needs_yes"]
    try:
        answer = input(SETUP_MSGS["cleanup_prompt"])
    except EOFError:
        answer = ""
    return "" if answer.strip() == "yes" else SETUP_MSGS["cleanup_declined"]


def _report_inside_data(report_path: str) -> bool:
    """Return whether the report directory would be deleted with OMNIA_DATA_PATH."""
    data = omnia_env().get(OMNIA_DATA_KEY, "")
    if not data:
        return False
    data, report = os.path.realpath(data), os.path.realpath(report_path)
    return report == data or report.startswith(data.rstrip("/") + "/")


def _prepare(theme: str, steps: List[tuple], venv: str, emit: Emit, rows: Rows) -> str:
    """Bootstrap test/main's own .venv and the test requirements in the Omnia venv."""
    for domain in dict.fromkeys(step[0] for step in steps):
        if domain in OWN_VENV_DOMAINS:
            emit(SETUP_MSGS["requirements"].format(domain=domain, venv=f"test/{domain}/.venv"))
            result = stream_command(["bash", FVT_SETUP, "--venv"], cwd=domain_dir(domain))
            rows.append(result_row(f"test requirements: {domain} (own .venv)", result))
            if not result["success"]:
                return STAGE_MSGS["step_failed"].format(label=f"{domain} {FVT_SETUP} --venv",
                                                        rc=result["rc"])
    if not venv:
        return ""
    installed = install_requirements(theme, venv, emit, force=False)
    rows.extend(installed.pop("rows", []))
    return installed["error"] if installed["status"] == "failed" else ""


def _initializer_cleanup(emit: Emit, rows: Rows) -> str:
    """Run every src/<domain>/domain-init.sh --cleanup; return an error or ""."""
    env = omnia_env()
    for script in sorted(glob.glob(DOMAIN_INIT_GLOB)):
        domain = os.path.basename(os.path.dirname(script))
        emit(STAGE_MSGS["step"].format(stage="cleanup",
                                       label=f"{domain}/domain-init.sh {DOMAIN_INIT_CLEANUP_ARG}"))
        result = tee_command(["bash", script, DOMAIN_INIT_CLEANUP_ARG],
                             cwd=os.path.dirname(script), env=env, no_input=True)
        rows.append(result_row(f"domain-init.sh --cleanup: {domain}", result,
                               details="input and log artifacts of the domain"))
        if not result["success"]:
            return STAGE_MSGS["step_failed"].format(label=f"{domain}/domain-init.sh --cleanup",
                                                    rc=result["rc"])
    return ""


def _kept_credentials(config: Dict[str, Any]) -> List[str]:
    """Return the suites set to keep their credentials (a full reset deletes them anyway)."""
    return [suite for suite, flags in config["cleanup"].items()
            if "cleanup_credentials" in CLEANUP_FLAGS[suite][1]
            and flags.get("cleanup_credentials") is False]


def _run_steps(steps: List[tuple], full: bool, venv: str, emit: Emit, rows: Rows) -> str:
    """Run the cleanup FVT steps in order; return the first error or ""."""
    for step in steps:
        own = step[0] in OWN_VENV_DOMAINS
        if own and full:
            error = _initializer_cleanup(emit, rows)
            if error:
                return error
        label = describe_step(step)
        emit(STAGE_MSGS["step"].format(stage="cleanup", label=label))
        result = run_fvt_step(step, env=_own_venv_env(step[0]) if own else venv_env(venv))
        rows.append(result_row(label, result, details="--cleanup --all" if own and full else ""))
        if not result["success"]:
            return STAGE_MSGS["step_failed"].format(label=label, rc=result["rc"])
    return ""


def cleanup(config: Dict[str, Any], emit: Emit, assume_yes: bool = False) -> Dict[str, Any]:
    """Remove the previous installation; see the module docstring for the order."""
    rows: Rows = []
    if not os.path.isfile(OMNIA_ENV_FILE):
        return {"status": "skipped", "rows": rows,
                "error": STAGE_MSGS["no_previous_setup"].format(path=OMNIA_ENV_FILE)}
    settings = current_run(config)
    full = cleanup_all(config)
    if full and _report_inside_data(settings["report_path"]):
        return _failed(SETUP_MSGS["report_inside_data"].format(path=settings["report_path"]), rows)
    apply_cleanup_flags(config, emit)
    apply_report_settings(settings, emit)
    venv = _venv_ready()
    steps = _select_steps(config, venv, emit, rows)
    if not steps:
        return {"status": "skipped", "error": SETUP_MSGS["cleanup_nothing"], "rows": rows}
    if full and _kept_credentials(config):
        emit(SETUP_MSGS["cleanup_all_credentials"].format(
            suites=", ".join(_kept_credentials(config))))
    refused = _confirm(steps, full, emit, assume_yes)
    if refused:
        return _failed(refused, rows)
    error = (_prepare(config["theme"], steps, venv, emit, rows)
             or _run_steps(steps, full, venv, emit, rows))
    if error:
        return _failed(error, rows)
    return {"status": "passed", "error": "", "full": full, "rows": rows,
            "steps": [describe_step(step) for step in steps]}
