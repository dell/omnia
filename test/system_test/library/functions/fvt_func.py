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

"""Run FVT steps of the domain test suites (test/<domain>) from the SVT.

An FVT step is ``test/<domain>/_run.py fvt_<domain> <arguments>`` started with
the Python of that domain's environment; its live output streams into the SVT
log and its result is returned in the standard shape. The FVT code itself is
never imported (each suite owns its own ``library`` package); the results an
FVT step adds to its suite's report are read back for the SVT report.
"""

import os
import sys
from typing import Any, Callable, Dict, List, Optional

import yaml

from .process_func import stream_command
from .svt_report_func import fvt_report_file, load_json
from ..vars.common_vars import (
    FVT_BOOTSTRAP_PYTHON,
    FVT_PYTHON_ENV,
    FVT_RUNNER,
    FVT_TEST_CONFIG,
    OMNIA_ENV_FILE,
    OMNIA_VENV_KEY,
    TEST_ROOT,
)
from ..vars.theme_vars import OWN_VENV_DOMAINS, FvtStep

Emit = Callable[[str], None]


def read_env_file(path: str = OMNIA_ENV_FILE) -> Dict[str, str]:
    """Parse ``KEY=value`` lines of an env file (no shell; quotes stripped)."""
    values: Dict[str, str] = {}
    try:
        with open(path, "r", encoding="utf-8") as stream:
            for line in stream:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                values[key.strip().removeprefix("export ").strip()] = value.strip().strip("\"'")
    except OSError:
        return {}
    return values


def omnia_venv_path() -> str:
    """Return OMNIA_VENV_PATH from the installed omnia.env ("" before the setup)."""
    return read_env_file().get(OMNIA_VENV_KEY, "")


def domain_dir(domain: str) -> str:
    """Return the test suite directory of ``domain`` (raises on an unknown name)."""
    path = os.path.join(TEST_ROOT, domain)
    if not domain.replace("_", "").isalnum() or not os.path.isfile(os.path.join(path, FVT_RUNNER)):
        raise ValueError(f"unknown FVT domain {domain!r}: {path}/{FVT_RUNNER} not found")
    return path


def fvt_python(domain: str, override: Optional[str] = None) -> str:
    """Return the interpreter for an FVT domain.

    Order: ``override``, ``SVT_FVT_PYTHON``, the Omnia venv (after the setup),
    the domain's bootstrap ``.venv``, then the current interpreter. Domains in
    OWN_VENV_DOMAINS use their bootstrap ``.venv`` before the Omnia venv.
    """
    bootstrap = os.path.join(domain_dir(domain), FVT_BOOTSTRAP_PYTHON)
    venv = omnia_venv_path()
    omnia = os.path.join(venv, "bin", "python") if venv else ""
    ordered = [bootstrap, omnia] if domain in OWN_VENV_DOMAINS else [omnia, bootstrap]
    candidates = [override or "", os.environ.get(FVT_PYTHON_ENV, ""), *ordered, sys.executable]
    return next(path for path in candidates if path and os.access(path, os.X_OK))


def describe_step(step: FvtStep) -> str:
    """Return the runner command of a step as text, e.g. ``fvt_build_stream execute exec``."""
    domain, arguments = step
    return " ".join([f"fvt_{domain}", *arguments])


def fvt_report_json(domain: str) -> str:
    """Return the omnia_auto JSON report the domain's FVT writes ("" when not configured)."""
    try:
        with open(os.path.join(domain_dir(domain), FVT_TEST_CONFIG), "r",
                  encoding="utf-8") as stream:
            config = yaml.safe_load(stream) or {}
    except (OSError, ValueError, yaml.YAMLError):
        return ""
    if not isinstance(config, dict) or not config.get("report_path"):
        return ""
    return fvt_report_file(os.path.expandvars(str(config["report_path"])),
                           str(config.get("report_name") or domain))


def _result_counts(path: str) -> Dict[tuple, int]:
    """Return the number of results per (server, run, module) in an FVT report."""
    data = load_json(path) if path else {}
    return {(server, run.get("run_id"), module.get("module")): len(module.get("results") or [])
            for server, block in data.get("servers", {}).items()
            for run in block.get("runs", []) for module in run.get("modules", [])}


def _new_results(path: str, before: Dict[tuple, int]) -> List[Dict[str, Any]]:
    """Return the results added to the FVT report since ``before`` (in report order)."""
    data = load_json(path) if path else {}
    added: List[Dict[str, Any]] = []
    for server, block in data.get("servers", {}).items():
        for run in block.get("runs", []):
            for module in run.get("modules", []):
                key = (server, run.get("run_id"), module.get("module"))
                added.extend((module.get("results") or [])[before.get(key, 0):])
    return added


def run_fvt_step(step: FvtStep, python: Optional[str] = None,
                 env: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Run one FVT step and stream its output (``env`` is added to this environment).

    Returns:
        Dict with keys: success, rc, duration, command, output (what it printed),
        step (label), results (the FVT results it added to its report).
    """
    domain, arguments = step
    report = fvt_report_json(domain)
    before = _result_counts(report)
    command = [fvt_python(domain, python), FVT_RUNNER, f"fvt_{domain}", *arguments]
    result: Dict[str, Any] = dict(stream_command(command, cwd=domain_dir(domain), env=env))
    result["step"] = describe_step(step)
    result["results"] = _new_results(report, before)
    return result
