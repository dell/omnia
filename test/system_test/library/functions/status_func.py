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

"""./setup_env.sh --status: the setup steps and the readiness checks, drawn in a box."""

import textwrap
from typing import List

from .lock_func import describe_lock
from .run_func import describe, load_run
from .readiness_func import load_setup_record, readiness_checks
from ..vars.common_vars import SETUP_STEPS, STATUS_WIDTH

MARKS = {True: "[ OK ]", False: "[FAIL]"}
STEP_MARKS = {"passed": "[ OK ]", "skipped": "[SKIP]", "failed": "[FAIL]"}


def _row(text: str, width: int) -> str:
    return f"│ {text:<{width - 4}} │"


def _wrapped(text: str, width: int, indent: str) -> List[str]:
    return [_row(line, width) for line in textwrap.wrap(
        text, width - 4, initial_indent=indent, subsequent_indent=indent + "  ")]


def _rule(left: str, title: str, right: str, width: int) -> str:
    head = f"─ {title} " if title else ""
    return f"{left}{head}{'─' * (width - 2 - len(head))}{right}"


def render_status(theme: str, width: int = STATUS_WIDTH) -> List[str]:
    """Return the status box lines of ``theme`` on this OIM (read-only)."""
    record = load_setup_record()
    lines = [_rule("┌", f"SVT setup status - theme {theme}", "┐", width)]
    run = load_run()
    if run.get("run_id"):
        lines.extend(_wrapped(f"run    {run['run_id']} (theme {run.get('theme')}, "
                              f"{describe(run)}, started {run.get('started_at', '')})", width, ""))
        lines.extend(_wrapped(f"report {run.get('report_path', '')}", width, ""))
    else:
        lines.extend(_wrapped("run    none: ./setup_env.sh --configure starts one", width, ""))
    lines.extend(_wrapped(describe_lock(), width, ""))
    lines.append(_row(f"{'':6} {'step':<10} {'status':<8} {'started (UTC)':<26} duration", width))
    for step in SETUP_STEPS:
        outcome = record.get(step) or {}
        state = outcome.get("status", "not run")
        mark = STEP_MARKS.get(state, "[ -- ]")
        earlier = bool(outcome) and outcome.get("run_id") != run.get("run_id")
        if earlier:
            mark = "[PREV]"
        lines.append(_row(f"{mark} {step:<10} {state:<8} "
                          f"{outcome.get('started_at') or '':<26} {outcome.get('duration') or ''}",
                          width))
        if earlier:
            lines.extend(_wrapped(f"earlier run {outcome.get('run_id') or '(not recorded)'}",
                                  width, " " * 7))
        if state == "failed" and outcome.get("error"):
            lines.extend(_wrapped(outcome["error"].splitlines()[0], width, " " * 7))
    lines.append(_rule("├", f"ready for ./run_validation.sh svt_{theme}?", "┤", width))
    checks = readiness_checks(theme)
    for label, ok, detail in checks:
        lines.extend(_wrapped(f"{MARKS[ok]} {label}", width, ""))
        if not ok and detail:
            lines.extend(_wrapped(detail, width, " " * 7))
    ready = all(ok for _, ok, _ in checks)
    lines.append(_rule("├", "", "┤", width))
    lines.append(_row(f"READY: ./run_validation.sh svt_{theme} all" if ready
                      else "NOT READY: fix the [FAIL] items above (./setup_env.sh runs every step)",
                      width))
    lines.append(_rule("└", "", "┘", width))
    return lines
