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

"""SVT runner: the stages of one theme on this OIM, in the current SVT run.

Prepare the OIM first with ./setup_env.sh (configure starts the run, then
cleanup/install and the credentials). Then::

    ./run_validation.sh --help
    ./run_validation.sh svt_<theme> list
    ./run_validation.sh svt_<theme> <stage> [--retry] [--quiet]
    ./run_validation.sh svt_<theme> all [--start-stage <stage> | --retry] [--quiet]

Stages, in order: initialization (checks the setup), the theme's stages, then
summary. build_stream:

- prepare_build_stream: prepare_base, precheck, prepare and execute; for each
  the playbook (exec), then its verification tests (verify). GitLab is up
  at the end.
- build_deploy: the automatic build pipeline, then the deploy of its image.
- cadence: a new build, one cadence cycle and the cadence pipeline.
- automatic_cleanup: the automatic cleanup of the cadence image.

Each stage is a set of SVT tests (svt/<theme>/); each test runs one FVT step
of test/<domain> and its screen output and FVT results go into the SVT
report. Every stage belongs to the run started by ./setup_env.sh
--configure. A stage is refused (exit 2) when no run was started, the run is
of another theme, or a step of the run failed; summary still runs on a failed
run. A failed stage marks the run failed: the next stage needs a new run
(./setup_env.sh --configure; the installation and credentials are kept) or --retry:
the stage runs again in the same run and its new attempt replaces it in the report,
which keeps the earlier attempts; ``all --retry`` resumes at the first stage that
did not pass.

Every stage but summary needs the Omnia venv; run_validation.sh activates it
when it is not active. Each stage writes, in the run folder
(``reports/<run_id>/``):

- ``<stage>.log``       the complete output (also printed unless --quiet)
- ``<stage>.progress``  one line: the current step, refreshed as it changes
- ``<stage>.status``    ``passed``, ``skipped`` or ``failed <rc>`` when it ends

Exit codes: 0 passed or skipped, 1 failed, 2 invalid arguments, no usable run
or the Omnia venv cannot be activated.
"""

import argparse
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List

from library.functions import run_func, stage_func
from library.functions.config_func import ConfigError, load_svt_config, reapply_run_settings
from library.functions.lock_func import LockError, StepLock
from library.functions.omnia_func import venv_problem
from library.functions.process_func import Tee, format_duration
from library.messages.svt_msgs import LOCK_MSGS, RUN_MSGS, STAGE_MSGS
from library.vars.common_vars import (
    FIRST_STAGE,
    LAST_STAGE,
    MODULE_ROOT,
    RUN_ID_RE,
    STAGE_LOG,
    STAGE_PROGRESS,
    STAGE_STATUS,
)
from library.vars.domain_vars import RUNNER_PREFIX, THEME_NAMES, THEME_STAGES
from library.vars.test_case_vars import TEST_CASES
from library.vars.theme_vars import THEMES, theme_title

# The summary only reads and reports: it runs on a failed run, without the Omnia venv.
REPORT_STAGES = (LAST_STAGE,)


def stages_of(theme: str) -> List[str]:
    """Return every stage of ``theme`` in order: initialization, its stages, summary."""
    return [FIRST_STAGE, *THEME_STAGES[theme], LAST_STAGE]


def _usage() -> str:
    lines = ["Usage: ./run_validation.sh svt_<theme> list",
             "       ./run_validation.sh svt_<theme> <stage>|all [options]", "", "Themes:"]
    for theme in THEME_NAMES:
        lines.append(f"  svt_{theme:<14} {theme_title(theme)}: {THEMES[theme]['description']}")
        lines.append(f"  {'':18} stages: {' -> '.join(stages_of(theme))}")
    lines.append("\nOptions: ./run_validation.sh svt_<theme> <stage> --help")
    return "\n".join(lines)


def _list(theme: str) -> int:
    print(f"svt_{theme}: {theme_title(theme)} - {THEMES[theme]['description']}")
    tests = sorted(((key, tc) for key, tc in TEST_CASES.items() if key.startswith(f"{theme}_")),
                   key=lambda item: item[1]["order"])
    for stage in stages_of(theme):
        print(f"  {stage}")
        for _, tc in tests:
            if tc["stage"] == stage:
                print(f"    {tc['id']:<22} {tc['title']}")
    return 0


def _parser(theme: str) -> argparse.ArgumentParser:
    stages = stages_of(theme)
    parser = argparse.ArgumentParser(
        prog=f"run_validation.sh svt_{theme}",
        description="Run the SVT stages of the theme on this OIM, in the current run "
                    "(started by ./setup_env.sh --configure).")
    parser.add_argument("stage", choices=[*stages, "all"])
    parser.add_argument("--run-id", help="the current run id (set by ./setup_env.sh "
                                         "--configure); another id is refused")
    parser.add_argument("--start-stage", choices=stages[:-1], default=stages[0],
                        help="with 'all': first stage to run (the rest follow in order)")
    parser.add_argument("--retry", action="store_true",
                        help="run again the stage the run failed at (or was interrupted at), "
                             "in the same run: its new attempt replaces it in the report. "
                             "With 'all': resume at the first stage that did not pass")
    parser.add_argument("--quiet", action="store_true",
                        help="write the output to the stage log only (CI)")
    return parser


def _selected(args: argparse.Namespace, theme: str) -> List[str]:
    """Return the stages this call runs (with 'all': from --start-stage, summary last)."""
    stages = stages_of(theme)
    return stages[stages.index(args.start_stage):] if args.stage == "all" else [args.stage]


def _resume_stage(theme: str) -> str:
    """Return the first stage of the current run that did not pass (summary when all did)."""
    stages = stages_of(theme)
    run_id = run_func.load_run().get("run_id", "")
    done = stage_func.load_manifest(run_id).get("stages", {}) if RUN_ID_RE.fullmatch(run_id) \
        else {}
    for stage in stages[:-1]:
        if (done.get(stage) or {}).get("status") not in ("passed", "skipped"):
            return stage
    return LAST_STAGE


def _resolve(args: argparse.Namespace, theme: str) -> str:
    """Return the id of the run the stages belong to, or raise ValueError why none may run."""
    try:
        config = load_svt_config(theme)
    except ConfigError as exc:
        raise ValueError(str(exc)) from exc
    selected = _selected(args, theme)
    steps = [f"stage {stage}" for stage in selected if stage not in REPORT_STAGES]
    if args.retry and steps:
        try:
            message = run_func.retry(config, steps)
        except run_func.RunError as exc:
            raise ValueError(str(exc)) from exc
        if message:
            print(message, flush=True)
    try:
        run_id = run_func.active_run(config, allow_failed=all(
            stage in REPORT_STAGES for stage in selected))["run_id"]
    except run_func.RunError as exc:
        raise ValueError(str(exc)) from exc
    if args.run_id and args.run_id != run_id:
        raise ValueError(RUN_MSGS["run_id_mismatch"].format(given=args.run_id, run_id=run_id))
    if not RUN_ID_RE.fullmatch(run_id):
        raise ValueError(f"invalid run id {run_id!r}")
    if any(stage not in REPORT_STAGES for stage in selected):
        problem = venv_problem()
        if problem:
            raise ValueError(problem)
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


def _call(stage: str, ctx: Dict[str, Any], emit) -> Dict[str, Any]:
    run_id, theme = ctx["run_id"], ctx["theme"]
    if stage == FIRST_STAGE:
        return stage_func.initialization(run_id, theme, emit)
    if stage == LAST_STAGE:
        return stage_func.summary(run_id, emit)
    return stage_func.run_tests(run_id, theme, stage, emit)


def run_stage(stage: str, args: argparse.Namespace, ctx: Dict[str, Any]) -> bool:
    """Run one stage with its log, progress and status files; return success."""
    directory = stage_func.run_dir(ctx["run_id"])
    label = stage
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
                if stage != LAST_STAGE:
                    config = load_svt_config(ctx["theme"])
                    reapply_run_settings(config, run_func.active_run(config, allow_failed=True),
                                         emit)
                outcome = _call(stage, ctx, emit)
            except (OSError, ValueError, KeyError) as exc:
                outcome = {"status": "failed", "error": f"{type(exc).__name__}: {exc}"}
            except KeyboardInterrupt:
                outcome = {"status": "failed", "error": LOCK_MSGS["ctrl_c"]}
            duration = format_duration(time.monotonic() - started)
            key = outcome["status"]
            emit(STAGE_MSGS[key].format(stage=label, duration=duration,
                                        reason=outcome["error"], error=outcome["error"]))
        finally:
            sys.stdout.flush()
            sys.stdout = sys.__stdout__
    outcome["duration"] = duration
    if stage != LAST_STAGE:
        stage_func.record_stage(ctx["run_id"], label, outcome)
        if key == "failed":
            print(run_func.mark_failed(f"stage {label}", outcome["error"]), flush=True)
    with open(status_path, "w", encoding="utf-8") as stream:
        stream.write("failed 1\n" if key == "failed" else f"{key}\n")
    return key != "failed"


def _record_rejection(args: argparse.Namespace, error: str) -> None:
    """Write a rejected stage's reason to its log and status file (seen by the pipeline)."""
    run_id = run_func.load_run().get("run_id", "")
    if args.stage == "all" or not RUN_ID_RE.fullmatch(run_id):
        return
    directory = stage_func.run_dir(run_id)
    label = args.stage
    with open(os.path.join(directory, STAGE_LOG.format(stage=label)), "a",
              encoding="utf-8") as log:
        log.write(f"{datetime.now(timezone.utc):%H:%M:%SZ} [{label}] REJECTED: {error}\n")
    with open(os.path.join(directory, STAGE_STATUS.format(stage=label)), "w",
              encoding="utf-8") as stream:
        stream.write("failed 2\n")


def _stages(theme: str, argv: List[str]) -> int:
    """Run one stage or all of them."""
    parser = _parser(theme)
    args = parser.parse_args(argv)
    if args.retry and args.stage == "all" and args.start_stage != stages_of(theme)[0]:
        parser.error("--retry resumes by itself: do not combine it with --start-stage")
    try:
        with StepLock(f"stage {args.stage}"):
            return _locked_stages(args, theme)
    except LockError as exc:
        # Not recorded in the stage files: they may belong to the step that holds the lock.
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


def _locked_stages(args: argparse.Namespace, theme: str) -> int:
    """Run the selected stages while this process holds the SVT lock."""
    if args.retry and args.stage == "all":
        args.start_stage = _resume_stage(theme)
        print(RUN_MSGS["retry_resume"].format(stage=args.start_stage) if args.start_stage
              != LAST_STAGE else RUN_MSGS["retry_done"].format(
                  run_id=run_func.load_run().get("run_id", "")), flush=True)
    try:
        ctx = {"run_id": _resolve(args, theme), "theme": theme}
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        _record_rejection(args, str(exc))
        return 2
    if args.stage != "all":
        return 0 if run_stage(args.stage, args, ctx) else 1
    ok = True
    for stage in _selected(args, theme)[:-1]:
        ok = run_stage(stage, args, ctx)
        if not ok:
            break
    summary_ok = run_stage(LAST_STAGE, args, ctx)
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
