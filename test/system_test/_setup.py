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

"""SVT setup driver, started by ./setup_env.sh with the SVT .venv Python.

Usage (every action takes ``--theme <theme>``, default build_stream; its
settings are <theme>_test_config.yml)::

    _setup.py all       [--force] [--yes]   configure, [cleanup], install, creds
    _setup.py configure
    _setup.py cleanup   [--yes | --dry-run]   --dry-run: show the plan, change nothing
    _setup.py install   [--force] [--yes]   --force: cleanup first, full reinstall
    _setup.py creds     --flag --set-domain-creds|--update-domain-creds|--domain-creds-stdin
                        [--domain <domain>]
    _setup.py status

Each step prints its output and appends it to reports/setup/<step>.log; its
outcome goes to reports/setup/setup.json, which the initialization stage of
./run_validation.sh checks. cleanup and install go into the SVT report of the
run (one item per sub-step, with its command, screen output and FVT
results); configure and the credentials do not. Credential prompts run on
the terminal and are never written to a log. ``--yes`` answers every
confirmation (unattended runs, pipelines).

configure starts a run (library/functions/run_func.py): a run id, the theme
and the report folder <report_path>/<run_id>/. cleanup, install and creds add
to that run and refuse to start without one, after a theme change, or after a
step of the run failed (configure starts a new run).
Exit codes: 0 passed or skipped, 1 failed, 2 invalid arguments, an invalid
<theme>_test_config.yml or no usable run.
"""

import argparse
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from library.functions import (
    catalog_func,
    cleanup_func,
    readiness_func,
    run_func,
    setup_func,
    svt_report_func,
)
from library.functions.config_func import ConfigError, load_svt_config, reapply_run_settings
from library.functions.lock_func import LockError, StepLock
from library.functions.process_func import Tee, format_duration
from library.functions.status_func import render_status
from library.messages.svt_msgs import LOCK_MSGS, SETUP_MSGS
from library.vars.common_vars import (
    CREDS_FLAGS,
    DEFAULT_THEME,
    MODULE_ROOT,
    REPORTED_SETUP_STEPS,
    SETUP_ACTIONS,
    SETUP_LOG,
)
from library.vars.theme_vars import THEMES

Step = Callable[[], Dict[str, Any]]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="_setup.py",
                                     description=__doc__.split("\n\n", maxsplit=1)[0])
    parser.add_argument("action", choices=SETUP_ACTIONS)
    parser.add_argument("--theme", choices=list(THEMES), default=DEFAULT_THEME,
                        help="the theme; its settings are <theme>_test_config.yml")
    parser.add_argument("--flag", choices=CREDS_FLAGS, default=CREDS_FLAGS[0],
                        help="creds: the test/build_stream/setup_env.sh action")
    parser.add_argument("--domain", help="creds: one domain store only")
    parser.add_argument("--force", action="store_true",
                        help="all/install: clean up first, then install everything again")
    parser.add_argument("--yes", action="store_true", help="answer every confirmation")
    parser.add_argument("--from-openbao", action="store_true",
                        help="all: read the missing credential stores from OpenBao (the openbao "
                             "block of user_inputs.yml; token in BAO_TOKEN) instead of "
                             "prompting")
    parser.add_argument("--dry-run", action="store_true",
                        help="cleanup: show what would be run and removed; change nothing")
    parser.add_argument("--retry", action="store_true",
                        help="run again the step the run failed at (or was interrupted at), in "
                             "the same run; with no action: resume at the failed step")
    return parser


def _emit(text: str) -> None:
    print(f"{datetime.now(timezone.utc):%H:%M:%SZ} {text}", flush=True)


def _report_rows(name: str, outcome: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return the report rows of a finished step (one summary row when it has none)."""
    rows = outcome.pop("rows", None) or []
    if not rows:
        status = {"passed": "PASSED", "skipped": "SKIPPED"}.get(outcome["status"], "FAILED")
        rows = [setup_func.row(name, status, details=outcome.get("error", ""))]
    return rows


def report_step(config: Dict[str, Any], name: str, rows: List[Dict[str, Any]],
                outcome: Dict[str, Any]) -> None:
    """Add a cleanup or install step to the SVT report (configure and the credentials are
    not reported) and re-render it; a report error never fails the step."""
    if name not in REPORTED_SETUP_STEPS:
        return
    try:
        settings = setup_func.current_run(config)
        svt_report_func.add_section(settings, {
            "kind": "setup", "name": name, "rows": rows, "started_at": outcome["started_at"],
            "duration": outcome["seconds"], "status": outcome["status"]})
        path = svt_report_func.render(settings, svt_report_func.run_meta(
            config["theme"], run_func.load_run()))
        print(SETUP_MSGS["report_written"].format(path=path), flush=True)
    except (OSError, ValueError, KeyError, TypeError, run_func.RunError) as exc:
        print(SETUP_MSGS["report_failed"].format(error=f"{type(exc).__name__}: {exc}"),
              flush=True)


def run_step(name: str, step: Step, config: Dict[str, Any]) -> bool:
    """Run one setup step with its log; record it and add it to the report; return success."""
    theme = config["theme"]
    log_path = os.path.join(setup_func.setup_dir(), SETUP_LOG.format(action=name))
    started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    started = time.monotonic()
    with open(log_path, "a", encoding="utf-8") as log:
        sys.stdout = Tee(log, sys.__stdout__)
        try:
            _emit(SETUP_MSGS["start"].format(action=name, theme=theme, log=log_path))
            try:
                if name != "configure":
                    reapply_run_settings(config, setup_func.current_run(config), _emit)
                outcome = step()
            except (OSError, ValueError, KeyError) as exc:
                outcome = {"status": "failed", "error": f"{type(exc).__name__}: {exc}"}
            except KeyboardInterrupt:
                outcome = {"status": "failed", "error": LOCK_MSGS["ctrl_c"], "interrupted": True}
            duration = format_duration(time.monotonic() - started)
            _emit(SETUP_MSGS[outcome["status"]].format(
                action=name, duration=duration, reason=outcome["error"], error=outcome["error"]))
        finally:
            sys.stdout.flush()
            sys.stdout = sys.__stdout__
    rows = _report_rows(name, outcome)
    outcome.update(started_at=started_at, duration=duration, log=log_path)
    setup_func.record_action(name, outcome)
    _mark_run(name, outcome)
    report_step(config, name, rows, {**outcome, "seconds": time.monotonic() - started})
    return outcome["status"] != "failed"


def _mark_run(name: str, outcome: Dict[str, Any]) -> None:
    """A failed step marks the run failed: the next step needs a new run (configure).

    A failed configure marks nothing: install refuses until configure passes.
    """
    if outcome["status"] == "failed" and name != "configure":
        message = run_func.mark_failed(f"setup {name}", outcome["error"])
        if message:
            _emit(message)


def _configure(config: Dict[str, Any]) -> Dict[str, Any]:
    """Configure; a catalog theme then freezes its catalog plan for the new run.

    The plan (catalog_func.write_plan) is what the theme's stages and tests are
    generated from; when it cannot be built, configure fails and says why.
    """
    outcome = setup_func.configure(config, _emit)
    if outcome["status"] != "passed" or not THEMES[config["theme"]].get("catalog_plan"):
        return outcome
    rows, error = catalog_func.write_plan(config["catalog"], outcome["run_id"], _emit)
    outcome["rows"] = [*(outcome.get("rows") or []), *rows]
    return {**outcome, "status": "failed", "error": error} if error else outcome


def _steps(args: argparse.Namespace, config: Dict[str, Any]) -> List[tuple]:
    """Return the (name, step) list of the requested action."""
    configure = ("configure", lambda: _configure(config))
    cleanup = ("cleanup", lambda: cleanup_func.cleanup(config, _emit, args.yes))
    install = ("install", lambda: setup_func.install(config, _emit, args.force, args.yes))
    if args.action == "all":
        return [configure, *([cleanup] if args.force else []), install,
                ("creds", lambda: setup_func.auto_creds(
                    config, _emit, args.yes, args.from_openbao))]
    if args.action == "install":
        return [*([cleanup] if args.force else []), install]
    if args.action == "creds":
        return [("creds", lambda: setup_func.creds(config, args.flag, args.domain, _emit))]
    return [{"configure": configure, "cleanup": cleanup}[args.action]]


def _print_status(theme: str) -> None:
    print("\n".join(render_status(theme)), flush=True)


def _without_step(args: argparse.Namespace, config: Dict[str, Any]) -> Optional[int]:
    """Return the exit code of what needs no step (--status, --dry-run, a refused option)."""
    if args.action == "status":
        _print_status(config["theme"])
        return 0
    if args.dry_run:
        if args.action != "cleanup":
            print("ERROR: --dry-run applies to --cleanup only", file=sys.stderr)
            return 2
        return cleanup_func.plan(config, _emit)
    if args.retry and args.action == "configure":
        print("ERROR: --retry does not apply to configure (it starts a run)", file=sys.stderr)
        return 2
    return None


def main(argv: List[str]) -> int:
    """Parse the arguments, load <theme>_test_config.yml and run the steps in order."""
    try:
        args = _parser().parse_args(argv)
    except SystemExit as exc:  # argparse: --help (0) or invalid arguments (2)
        return int(exc.code or 0)
    try:
        config = load_svt_config(args.theme)
    except ConfigError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    early = _without_step(args, config)
    if early is not None:
        return early
    try:
        with StepLock(f"setup {args.action}", _emit):
            return _run_steps(args, config)
    except LockError as exc:
        print(f"ERROR: [{args.action}] not started: {exc}", file=sys.stderr, flush=True)
        return 2


def _resume(steps: List[tuple]) -> List[tuple]:
    """--retry with no action: leave out configure and the steps this run already passed."""
    record, run_id = readiness_func.load_setup_record(), run_func.load_run().get("run_id", "")
    return [(name, step) for name, step in steps if name != "configure" and not (
        (record.get(name) or {}).get("run_id") == run_id
        and (record.get(name) or {}).get("status") in ("passed", "skipped"))]


def _run_steps(args: argparse.Namespace, config: Dict[str, Any]) -> int:
    """Run the steps of the action in order (the lock is held); return the exit code."""
    steps = _steps(args, config)
    if args.retry:
        steps = _resume(steps) if args.action == "all" else steps
        try:
            message = run_func.retry(config, [f"setup {name}" for name, _ in steps])
        except run_func.RunError as exc:
            print(f"ERROR: {exc}", file=sys.stderr, flush=True)
            return 2
        if message:
            _emit(message)
    for name, step in steps:
        if name != "configure":
            try:
                run_func.active_run(config)
            except run_func.RunError as exc:
                print(f"ERROR: [{name}] not started: {exc}", file=sys.stderr, flush=True)
                return 2
        if not run_step(name, step, config):
            if args.action == "all":
                _print_status(config["theme"])
                _emit(SETUP_MSGS["all_stopped"].format(action=name))
            return 1
    if args.action in ("all", "install"):
        _print_status(config["theme"])
    return 0


if __name__ == "__main__":
    os.chdir(MODULE_ROOT)
    sys.exit(main(sys.argv[1:]))
