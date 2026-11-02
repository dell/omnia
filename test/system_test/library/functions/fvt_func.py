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
never imported (each suite owns its own ``library`` package).
"""

import os
import sys
from typing import Callable, Dict, List, Optional, Sequence

import yaml

from .process_func import format_duration, stream_command
from ..vars.common_vars import (
    FVT_BOOTSTRAP_PYTHON,
    FVT_PYTHON_ENV,
    FVT_RUNNER,
    FVT_TEST_CONFIG,
    OMNIA_ENV_FILE,
    OMNIA_VENV_KEY,
    TEST_ROOT,
)
from ..vars.theme_vars import THEMES, FvtStep

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
    the domain's bootstrap ``.venv``, then the current interpreter.
    """
    candidates = [override or "", os.environ.get(FVT_PYTHON_ENV, "")]
    venv = omnia_venv_path()
    if venv:
        candidates.append(os.path.join(venv, "bin", "python"))
    candidates.extend([os.path.join(domain_dir(domain), FVT_BOOTSTRAP_PYTHON), sys.executable])
    return next(path for path in candidates if path and os.access(path, os.X_OK))


def describe_step(step: FvtStep) -> str:
    """Return the runner command of a step as text, e.g. ``fvt_build_stream execute exec``."""
    domain, arguments = step
    return " ".join([f"fvt_{domain}", *arguments])


def fvt_report_path(domain: str) -> str:
    """Return ``report_path`` of the domain's test_config.yml (expanded), or ""."""
    try:
        with open(os.path.join(domain_dir(domain), FVT_TEST_CONFIG), "r",
                  encoding="utf-8") as stream:
            config = yaml.safe_load(stream) or {}
    except (OSError, ValueError, yaml.YAMLError):
        return ""
    return os.path.expandvars(str(config.get("report_path") or "")) if isinstance(config, dict) else ""


def run_fvt_step(step: FvtStep, python: Optional[str] = None) -> Dict[str, object]:
    """Run one FVT step and stream its output.

    Returns:
        Dict with keys: success, rc, duration, command, step.
    """
    domain, arguments = step
    command = [fvt_python(domain, python), FVT_RUNNER, f"fvt_{domain}", *arguments]
    result = stream_command(command, cwd=domain_dir(domain))
    result["step"] = describe_step(step)
    return result


def run_fvt_steps(steps: Sequence[FvtStep], emit: Emit,
                  python: Optional[str] = None) -> Dict[str, object]:
    """Run FVT steps in order and stop at the first failure.

    Returns:
        Dict with keys: success, fields (one line per step), failures,
        failed_step, rc, duration (text).
    """
    fields: List[tuple] = []
    total = 0.0
    for index, step in enumerate(steps, 1):
        label = describe_step(step)
        emit(f"step {index}/{len(steps)}: {label}")
        result = run_fvt_step(step, python)
        total += float(result["duration"])
        state = "passed" if result["success"] else f"FAILED (rc={result['rc']})"
        fields.append((label, f"{state} in {format_duration(float(result['duration']))}"))
        if not result["success"]:
            return {"success": False, "fields": fields, "failures": [label],
                    "failed_step": label, "rc": result["rc"], "duration": format_duration(total)}
    return {"success": True, "fields": fields, "failures": [], "failed_step": "",
            "rc": 0, "duration": format_duration(total)}


def run_svt_case(theme: str, case: str, emit: Emit) -> Dict[str, object]:
    """Run the FVT steps of one SVT test case of ``theme``.

    Returns:
        ``run_fvt_steps`` result plus ``report_path`` (FVT HTML/JSON reports).
    """
    steps = THEMES[theme]["cases"][case]
    result = run_fvt_steps(steps, emit)
    result["report_path"] = fvt_report_path(steps[0][0]) or "the FVT report_path"
    return result
