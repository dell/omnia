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

"""SVT stage driver (run through ./run_svt.sh).

Usage::

    ./run_svt.sh all --theme build_stream --inputs <user_inputs.yml> \\
                     --test-config <test_config.yml>
    ./run_svt.sh <stage> [--run-id <id>] [--quiet]

Each stage writes, under ``reports/<run_id>/``:

- ``<stage>.log``       the complete output (also printed unless --quiet)
- ``<stage>.progress``  one line: the current step, refreshed as it changes
- ``<stage>.status``    ``passed``, ``skipped`` or ``failed <rc>`` when it ends

The GitLab pipeline starts a stage with --quiet and follows these files.
Exit codes: 0 passed or skipped, 1 failed, 2 invalid arguments.
"""

import argparse
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TextIO

from library.functions import stage_func
from library.functions.process_func import format_duration
from library.messages.svt_msgs import STAGE_MSGS
from library.vars.common_vars import (
    MODULE_ROOT,
    RUN_ID_RE,
    STAGE_LOG,
    STAGE_PROGRESS,
    STAGE_STATUS,
    STAGES,
)
from library.vars.theme_vars import THEMES

# Stages that change the OIM; they need an initialized run (or --resume).
GUARDED_STAGES = ("cleanup", "environment_setup", "system_verification")


class _Tee:
    """Write to the stage log and, unless quiet, to the console."""

    def __init__(self, log: TextIO, console: Optional[TextIO]):
        self._log, self._console = log, console

    def write(self, text: str) -> int:
        self._log.write(text)
        if self._console:
            self._console.write(text)
        return len(text)

    def flush(self) -> None:
        self._log.flush()
        if self._console:
            self._console.flush()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_svt.sh", description="Run the SVT integration stages on this OIM.")
    parser.add_argument("stage", choices=[*STAGES, "all"])
    parser.add_argument("--theme", choices=list(THEMES),
                        help="theme (required for initialization and all)")
    parser.add_argument("--inputs", help="cluster user_inputs.yml placed before the generator")
    parser.add_argument("--test-config", help="FVT test_config.yml of the theme's suite")
    parser.add_argument("--run-id", help="run identifier (default: new for initialization/all, "
                                         "else the latest run)")
    parser.add_argument("--start-stage", choices=STAGES[:-1], default=STAGES[0],
                        help="with 'all': first stage to run (re-run from a failed stage)")
    parser.add_argument("--case", help="system_verification: run one SVT case only")
    parser.add_argument("--resume", action="store_true",
                        help="cleanup/environment_setup/system_verification of a new run id: "
                             "continue the last initialized run of this checkout")
    parser.add_argument("--quiet", action="store_true",
                        help="write the output to the stage log only (CI)")
    return parser


def _resolve(args: argparse.Namespace) -> Dict[str, Any]:
    """Validate the arguments; return run_id and theme or raise ValueError."""
    starts_run = args.stage in ("initialization", "all") and args.start_stage == STAGES[0]
    run_id = args.run_id or ("" if starts_run else stage_func.latest_run_id())
    if not run_id:
        run_id = datetime.now(timezone.utc).strftime("svt-%Y%m%dT%H%M%SZ")
    if not RUN_ID_RE.fullmatch(run_id):
        raise ValueError(f"invalid run id {run_id!r}")
    theme = args.theme or stage_func.load_manifest(run_id).get("theme", "")
    if args.stage != "summary" and theme not in THEMES:
        raise ValueError(STAGE_MSGS["unknown_run"] if not args.theme
                         else f"unknown theme {theme!r}")
    if args.case and args.case not in THEMES[theme]["cases"]:
        raise ValueError(f"unknown case {args.case!r} for theme {theme}")
    acting = [stage for stage in (STAGES[STAGES.index(args.start_stage):-1]
                                  if args.stage == "all" else [args.stage])
              if stage in GUARDED_STAGES]
    if acting and not (args.stage == "all" and args.start_stage == STAGES[0]):
        stage_func.require_run(run_id, theme, args.resume)
    return {"run_id": run_id, "theme": theme}


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
        return stage_func.initialization(run_id, theme, args.inputs, args.test_config, emit)
    if stage == "cleanup":
        return stage_func.cleanup(theme, emit)
    if stage == "environment_setup":
        return stage_func.environment_setup(theme, emit)
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
        sys.stdout = _Tee(log, console)
        try:
            emit = _progress(os.path.join(directory, STAGE_PROGRESS.format(stage=label)))
            emit(STAGE_MSGS["start"].format(stage=label, run_id=ctx["run_id"],
                                            theme=ctx["theme"] or "-"))
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


def main(argv: List[str]) -> int:
    """Parse the arguments and run one stage or all of them."""
    args = _parser().parse_args(argv)
    try:
        ctx = _resolve(args)
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


if __name__ == "__main__":
    os.chdir(MODULE_ROOT)
    sys.exit(main(sys.argv[1:]))
