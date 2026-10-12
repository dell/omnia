#!/usr/bin/env python3
# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

"""Standalone runner for BuildStream integration suites."""

import os
from pathlib import Path
import subprocess
import sys


_ROOT = Path(__file__).resolve().parent
_SUITES = {
    "cadence": _ROOT / "cadence",
    "automatic_cleanup": _ROOT / "automatic_cleanup",
}
_COMMANDS = {"exec", "verify", "test"}


def _usage() -> None:
    print("Usage:")
    print("  ./run_validation.sh list")
    print("  ./run_validation.sh <cadence|automatic_cleanup> <exec|verify|test>")


def _run_pytest(suite: str, phase: str) -> int:
    expression = "deploy" if phase == "exec" else "not deploy"
    env = os.environ.copy()
    env["OMNIA_COMMAND_TYPE"] = phase
    command = [
        sys.executable,
        "-m",
        "pytest",
        str(_SUITES[suite]),
        "-m",
        expression,
        "--marker",
        "sanity",
    ]
    return subprocess.run(command, cwd=_ROOT, env=env, check=False).returncode


def main(args) -> int:
    """Validate arguments and execute one integration suite."""
    if not args or args[0] in {"help", "--help", "-h"}:
        _usage()
        return 0
    if args[0] == "list":
        print("cadence: buildstream install -> full build -> cadence pipeline")
        print("automatic_cleanup: explicit production automatic cleanup")
        return 0
    if len(args) != 2 or args[0] not in _SUITES or args[1] not in _COMMANDS:
        _usage()
        return 2

    suite, command = args
    if command == "test":
        result = _run_pytest(suite, "exec")
        return result if result else _run_pytest(suite, "verify")
    return _run_pytest(suite, command)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
