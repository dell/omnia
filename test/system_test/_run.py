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

"""SVT runner: the integration stages of one theme on this OIM.

Prepare the OIM first with ./setup_env.sh (configure, install, credentials).
Then::

    ./run_validation.sh --help
    ./run_validation.sh svt_<theme> list
    ./run_validation.sh svt_<theme> all [--test-config <yml>]
    ./run_validation.sh svt_<theme> <stage> [--run-id <id>] [--resume] [--quiet]

Stages: initialization (checks the setup, starts the run), system_verification
(``--case <case>`` runs one SVT case), summary. initialization and
system_verification need the Omnia venv; run_validation.sh activates it when
it is not active. Each stage writes, under
``reports/<run_id>/``:

- ``<stage>.log``       the complete output (also printed unless --quiet)
- ``<stage>.progress``  one line: the current step, refreshed as it changes
- ``<stage>.status``    ``passed``, ``skipped`` or ``failed <rc>`` when it ends

Exit codes: 0 passed or skipped, 1 failed, 2 invalid arguments or the Omnia
venv cannot be activated.
"""

import argparse
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from library.functions import stage_func
from library.functions.omnia_func import venv_problem
from library.functions.process_func import Tee, format_duration
from library.messages.svt_msgs import STAGE_MSGS
from library.vars.common_vars import (
    MODULE_ROOT,
    RUN_ID_RE,
    STAGE_LOG,
    STAGE_PROGRESS,
    STAGE_STATUS,
    STAGES,
)
from library.vars.domain_vars import CASES, RUNNER_PREFIX, THEME_NAMES
from library.vars.test_case_vars import TEST_CASES
from library.vars.theme_vars import THEMES

# Stages that change the OIM; they need an initialized run (or --resume).
GUARDED_STAGES = ("system_verification",)
# Stages that run FVT code; they need the active Omnia venv.
VENV_STAGES = ("initialization", "system_verification")


def _usage() -> str:
    lines = ["Usage: ./run_validation.sh svt_<theme> list",
             "       ./run_validation.sh svt_<theme> <stage>|all [options]", "",
             f"Stages: {', '.join(STAGES)}, all", "", "Themes:"]
    for theme in THEME_NAMES:
        lines.append(f"  svt_{theme:<14} {THEMES[theme]['description']}")
        lines.append(f"  {'':18} cases: {', '.join(CASES[theme])}")
    lines.append("\nOptions: ./run_validation.sh svt_<theme> <stage> --help")
    return "\n".join(lines)


def _list(theme: str) -> int:
    print(f"svt_{theme}: {THEMES[theme]['description']}")
    print(f"stages: {' -> '.join(STAGES)}")
    for case in CASES[theme]:
        tc = TEST_CASES[f"{theme}_{case}"]
        print(f"  {tc['id']:<22} --case {case:<20} {tc['title']}")
    return 0


def _parser(theme: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=f"run_validation.sh svt_{theme}",
        description="Run the SVT integration stages on this OIM.")
    parser.add_argument("stage", choices=[*STAGES, "all"])
    parser.add_argument("--test-config", help="FVT test_config.yml of the theme's suite, "
                                              "placed by initialization")
    parser.add_argument("--run-id", help="run identifier (default: new for initialization/all, "
                                         "else the latest run)")
    parser.add_argument("--start-stage", choices=STAGES[:-1], default=STAGES[0],
                        help="with 'all': first stage to run (re-run from a failed stage)")
    parser.add_argument("--case", choices=CASES[theme],
                        help="system_verification: run one SVT case only")
    parser.add_argument("--resume", action="store_true",
                        help="system_verification of a new run id: "
                             "continue the last initialized run of this checkout")
    parser.add_argument("--quiet", action="store_true",
                        help="write the output to the stage log only (CI)")
    return parser


def _resolve(args: argparse.Namespace, theme: str) -> str:
    """Validate the run; return its id or raise ValueError."""
    starts_run = args.stage in ("initialization", "all") and args.start_stage == STAGES[0]
    run_id = args.run_id or ("" if starts_run else stage_func.latest_run_id())
    if not run_id:
        run_id = datetime.now(timezone.utc).strftime("svt-%Y%m%dT%H%M%SZ")
    if not RUN_ID_RE.fullmatch(run_id):
        raise ValueError(f"invalid run id {run_id!r}")
    selected = (STAGES[STAGES.index(args.start_stage):-1] if args.stage == "all"
                else [args.stage])
    if any(stage in VENV_STAGES for stage in selected):
        problem = venv_problem()
        if problem:
            raise ValueError(problem)
    acting = [stage for stage in selected if stage in GUARDED_STAGES]
    if acting and not (args.stage == "all" and args.start_stage == STAGES[0]):
        stage_func.require_run(run_id, theme, args.resume)
    return run_id


def _progress(path: str):
    """Return an emit function that prints a step and refreshes the progress file."""
    def emit(text: str) -> None:
        line = f"{datetime.now(timezone.utc):%H:%M:%SZ} {text}"
        print(line, flush=True)
        temp = f"{path}.tmp"
        with open(temp, "w", encoding="utf-8") as stream:
            stream.write(line + "\n")
        os.replace(temp, path)
    return emit


def _call(stage: str, args: argparse.Namespace, ctx: Dict[str, Any], emit) -> Dict[str, Any]:
    run_id, theme = ctx["run_id"], ctx["theme"]
    if stage == "initialization":
        return stage_func.initialization(run_id, theme, args.test_config, emit)
    if stage == "system_verification":
        return stage_func.system_verification(run_id, theme, args.case, emit)
    return stage_func.summary(run_id, emit)


def stage_label(stage: str, case: Optional[str]) -> str:
    """Return the file and manifest name of a stage (one per SVT case when --case is set)."""
    return f"{stage}-{case}" if stage == "system_verification" and case else stage


def run_stage(stage: str, args: argparse.Namespace, ctx: Dict[str, Any]) -> bool:
    """Run one stage with its log, progress and status files; return success."""
    directory = stage_func.run_dir(ctx["run_id"])
    label = stage_label(stage, args.case)
    status_path = os.path.join(directory, STAGE_STATUS.format(stage=label))
    if os.path.exists(status_path):
        os.unlink(status_path)
    started = time.monotonic()
    outcome: Dict[str, Any] = {"status": "failed", "error": "stage did not start"}
    key, duration = "failed", "0s"
    console = None if args.quiet else sys.__stdout__
    with open(os.path.join(directory, STAGE_LOG.format(stage=label)), "a",
              encoding="utf-8") as log:
        sys.stdout = Tee(log, console)
        try:
            emit = _progress(os.path.join(directory, STAGE_PROGRESS.format(stage=label)))
            emit(STAGE_MSGS["start"].format(stage=label, run_id=ctx["run_id"],
                                            theme=ctx["theme"]))
            try:
                outcome = _call(stage, args, ctx, emit)
            except (OSError, ValueError, KeyError) as exc:
                outcome = {"status": "failed", "error": f"{type(exc).__name__}: {exc}"}
            duration = format_duration(time.monotonic() - started)
            key = outcome["status"]
            emit(STAGE_MSGS[key].format(stage=label, duration=duration,
                                        reason=outcome["error"], error=outcome["error"]))
        finally:
            sys.stdout.flush()
            sys.stdout = sys.__stdout__
    outcome["duration"] = duration
    if stage != "summary":
        stage_func.record_stage(ctx["run_id"], label, outcome)
    with open(status_path, "w", encoding="utf-8") as stream:
        stream.write("failed 1\n" if key == "failed" else f"{key}\n")
    return key != "failed"


def _record_rejection(args: argparse.Namespace, error: str) -> None:
    """Write a rejected stage's reason to its log and status file (seen by the pipeline)."""
    if args.stage == "all" or not RUN_ID_RE.fullmatch(args.run_id or ""):
        return
    directory = stage_func.run_dir(args.run_id)
    label = stage_label(args.stage, args.case)
    with open(os.path.join(directory, STAGE_LOG.format(stage=label)), "a",
              encoding="utf-8") as log:
        log.write(f"{datetime.now(timezone.utc):%H:%M:%SZ} [{label}] REJECTED: {error}\n")
    with open(os.path.join(directory, STAGE_STATUS.format(stage=label)), "w",
              encoding="utf-8") as stream:
        stream.write("failed 2\n")


def _stages(theme: str, argv: List[str]) -> int:
    """Run one stage or all of them."""
    args = _parser(theme).parse_args(argv)
    try:
        ctx = {"run_id": _resolve(args, theme), "theme": theme}
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        _record_rejection(args, str(exc))
        return 2
    if args.stage != "all":
        return 0 if run_stage(args.stage, args, ctx) else 1
    ok = True
    for stage in STAGES[STAGES.index(args.start_stage):-1]:
        ok = run_stage(stage, args, ctx)
        if not ok:
            break
    summary_ok = run_stage("summary", args, ctx)
    return 0 if ok and summary_ok else 1


def main(argv: List[str]) -> int:
    """Validate the category and dispatch."""
    if not argv or argv[0] in ("-h", "--help"):
        print(_usage())
        return 0
    category = argv[0]
    theme = category.removeprefix(RUNNER_PREFIX)
    if not category.startswith(RUNNER_PREFIX) or theme not in THEME_NAMES:
        print(f"ERROR: unknown category {category!r}\n\n{_usage()}", file=sys.stderr)
        return 2
    if argv[1:] == ["list"]:
        return _list(theme)
    try:
        return _stages(theme, argv[1:])
    except SystemExit as exc:  # argparse: --help (0) or invalid arguments (2)
        return int(exc.code or 0)


if __name__ == "__main__":
    os.chdir(MODULE_ROOT)
    sys.exit(main(sys.argv[1:]))
