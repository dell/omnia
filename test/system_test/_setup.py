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

Usage::

    _setup.py all       [--force] [--yes]   configure, [cleanup], install, creds
    _setup.py configure
    _setup.py cleanup   [--yes]
    _setup.py install   [--force] [--yes]   --force: cleanup first, full reinstall
    _setup.py creds     --flag --set-domain-creds|--update-domain-creds|--domain-creds-stdin
                        [--domain <domain>]
    _setup.py status

Each step prints its output and appends it to reports/setup/<step>.log; its
outcome goes to reports/setup/setup.json, which the initialization stage of
./run_validation.sh checks and copies into the run report. Credential
prompts run on the terminal and are never written to a log. ``--yes``
answers every confirmation (unattended runs, pipelines).
Exit codes: 0 passed or skipped, 1 failed, 2 invalid arguments or test_config.yml.
"""

import argparse
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List

from library.functions import setup_func
from library.functions.config_func import ConfigError, load_svt_config
from library.functions.process_func import Tee, format_duration
from library.functions.status_func import render_status
from library.messages.svt_msgs import SETUP_MSGS
from library.vars.common_vars import CREDS_FLAGS, MODULE_ROOT, SETUP_ACTIONS, SETUP_LOG

Step = Callable[[], Dict[str, Any]]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="_setup.py",
                                     description=__doc__.split("\n\n", maxsplit=1)[0])
    parser.add_argument("action", choices=SETUP_ACTIONS)
    parser.add_argument("--flag", choices=CREDS_FLAGS, default=CREDS_FLAGS[0],
                        help="creds: the test/build_stream/setup_env.sh action")
    parser.add_argument("--domain", help="creds: one domain store only")
    parser.add_argument("--force", action="store_true",
                        help="all/install: clean up first, then install everything again")
    parser.add_argument("--yes", action="store_true", help="answer every confirmation")
    return parser


def _emit(text: str) -> None:
    print(f"{datetime.now(timezone.utc):%H:%M:%SZ} {text}", flush=True)


def run_step(name: str, step: Step, theme: str) -> bool:
    """Run one setup step with its log; record the outcome; return success."""
    log_path = os.path.join(setup_func.setup_dir(), SETUP_LOG.format(action=name))
    started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    started = time.monotonic()
    with open(log_path, "a", encoding="utf-8") as log:
        sys.stdout = Tee(log, sys.__stdout__)
        try:
            _emit(SETUP_MSGS["start"].format(action=name, theme=theme, log=log_path))
            try:
                outcome = step()
            except (OSError, ValueError, KeyError) as exc:
                outcome = {"status": "failed", "error": f"{type(exc).__name__}: {exc}"}
            duration = format_duration(time.monotonic() - started)
            _emit(SETUP_MSGS[outcome["status"]].format(
                action=name, duration=duration, reason=outcome["error"], error=outcome["error"]))
        finally:
            sys.stdout.flush()
            sys.stdout = sys.__stdout__
    outcome.update(started_at=started_at, duration=duration, log=log_path)
    setup_func.record_action(name, outcome)
    return outcome["status"] != "failed"


def _steps(args: argparse.Namespace, config: Dict[str, Any]) -> List[tuple]:
    """Return the (name, step) list of the requested action."""
    configure = ("configure", lambda: setup_func.configure(config, _emit))
    cleanup = ("cleanup", lambda: setup_func.cleanup(config, _emit, args.yes))
    install = ("install", lambda: setup_func.install(config, _emit, args.force, args.yes))
    if args.action == "all":
        return [configure, *([cleanup] if args.force else []), install,
                ("creds", lambda: setup_func.auto_creds(config, _emit, args.yes))]
    if args.action == "install":
        return [*([cleanup] if args.force else []), install]
    if args.action == "creds":
        return [("creds", lambda: setup_func.creds(config, args.flag, args.domain, _emit))]
    return [{"configure": configure, "cleanup": cleanup}[args.action]]


def _print_status(theme: str) -> None:
    print("\n".join(render_status(theme)), flush=True)


def main(argv: List[str]) -> int:
    """Parse the arguments, load test_config.yml and run the steps in order."""
    try:
        args = _parser().parse_args(argv)
    except SystemExit as exc:  # argparse: --help (0) or invalid arguments (2)
        return int(exc.code or 0)
    try:
        config = load_svt_config()
    except ConfigError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if args.action == "status":
        _print_status(config["theme"])
        return 0
    for name, step in _steps(args, config):
        if not run_step(name, step, config["theme"]):
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
