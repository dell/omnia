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
Validation runner entry point for build_stream.

Thin wrapper that loads domain-specific variables from
``library/vars/domain_vars`` and delegates to ``ValidationRunner``.

Usage (via run_validation.sh or run_validation CLI)::

    python3 _run.py fvt_build_stream test
    python3 _run.py fvt_build_stream execute verify --suite build_automatic
    python3 _run.py fvt_build_stream execute verify --marker sanity
    python3 _run.py --config
"""

import os
import sys

from omnia_auto.functions.validation_runner import ValidationRunner

from library.vars.domain_vars import (
    ALL_EXEC_MARKER,
    ALL_EXEC_TAGS,
    DOMAIN_NAME,
    ENABLE_UT,
    EXCLUDE_TAGS,
    FVT_TAGS,
    MARKERS,
    SUITES,
)


def _help_requested(args):
    """Return whether this invocation prints BuildStream FVT help."""
    if not args or args[0] in {"help", "--help", "-h"}:
        return True
    return args[0] == "fvt_build_stream" and (
        len(args) == 1 or args[1] in {"help", "--help", "list"}
    )


def _print_lifecycle_help():
    """Print the BuildStream lifecycle and the explicit-only tags."""
    print("BUILDSTREAM LIFECYCLE")
    print("  Default (no tag): precheck -> prepare -> execute")
    print("     ./run_validation.sh fvt_build_stream test")
    print("  Without --marker every test runs; --marker sanity narrows the run.")
    print("  Manual pipeline suites (build_manual, deploy_manual) are not sanity:")
    print("     ./run_validation.sh fvt_build_stream execute verify --suite build_manual")
    print()
    print("EXPLICIT ONLY (NOT IN THE DEFAULT LIFECYCLE)")
    print("  ./run_validation.sh fvt_build_stream prepare_base test")
    print("  ./run_validation.sh fvt_build_stream cleanup test   (destructive)")
    print()


def main():
    """Load domain config and run ValidationRunner."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    args = sys.argv[1:]
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
            "enable_ut": ENABLE_UT,
        },
    )
    result = runner.main(args)
    if result == 0 and _help_requested(args):
        _print_lifecycle_help()
    sys.exit(result)


if __name__ == "__main__":
    main()
