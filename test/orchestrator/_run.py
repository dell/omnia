#!/usr/bin/env python3
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

"""
Validation runner entry point for orchestrator.

Thin wrapper that loads domain-specific variables from
``library/vars/domain_vars`` and delegates to ``ValidationRunner``.

Usage (via run_validation.sh or run_validation CLI)::

    python3 _run.py fvt_orchestrator deploy verify --marker sanity
    python3 _run.py fvt_orchestrator list
    python3 _run.py --config
"""

import os
import sys


_DESTRUCTIVE_TAGS = {"cleanup", "pxeboot", "rollback"}


def _validate_destructive_opt_in(args):
    """Reject state-changing standalone flows without explicit opt-in."""
    if len(args) < 2 or args[0] != "fvt_orchestrator":
        return True
    tag = args[1]
    if tag not in _DESTRUCTIVE_TAGS:
        return True
    command = args[2] if len(args) > 2 else "verify"
    if command not in {"exec", "test"}:
        return True
    try:
        marker_index = args.index("--marker")
        marker_value = args[marker_index + 1]
    except (ValueError, IndexError):
        marker_value = ""
    markers = marker_value.replace("+", ",").split(",")
    if "destructive" in markers:
        return True
    print(
        f"ERROR: '{tag} {command}' is destructive; rerun with "
        "--marker destructive",
        file=sys.stderr,
    )
    return False


def main():
    """Load domain config and run ValidationRunner."""
    if not _validate_destructive_opt_in(sys.argv[1:]):
        return 2
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, script_dir)

    from library.vars.domain_vars import (
        DOMAIN_NAME,
        FVT_TAGS,
        MARKERS,
        SUITES,
        EXCLUDE_TAGS,
        ALL_EXEC_TAGS,
        ALL_EXEC_MARKER,
        ALL_VERIFY_EXCLUDE_MARKERS,
        REQUIRED_SUITE_TAGS,
        VERIFY_ONLY_TAGS,
        VERIFY_ONLY_SUITES,
        SUITE_EXEC_OWNERS,
    )
    from omnia_auto.functions.validation_runner import ValidationRunner

    runner = ValidationRunner(
        domain=DOMAIN_NAME,
        script_dir=script_dir,
        domain_config={
            "tags": FVT_TAGS,
            "markers": MARKERS,
            "suites": SUITES,
            "exclude_tags": EXCLUDE_TAGS,
            "all_exec_tags": ALL_EXEC_TAGS,
            "all_exec_marker": ALL_EXEC_MARKER,
            "all_verify_exclude_markers": ALL_VERIFY_EXCLUDE_MARKERS,
            "required_suite_tags": REQUIRED_SUITE_TAGS,
            "verify_only_tags": VERIFY_ONLY_TAGS,
            "verify_only_suites": VERIFY_ONLY_SUITES,
            "suite_exec_owners": SUITE_EXEC_OWNERS,
        },
    )
    return runner.main(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
