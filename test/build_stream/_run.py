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

    python3 _run.py fvt_build_stream build_pipeline verify --marker sanity
    python3 _run.py fvt_build_stream buildstream_install test
    python3 _run.py --config
"""

import os
import re
import sys

import yaml


def _load_configured_report_id(script_dir):
    """Return a validated report_id from test_config.yml, if configured."""
    config_path = os.path.join(script_dir, "test_config.yml")
    try:
        with open(config_path, encoding="utf-8") as config_stream:
            config = yaml.safe_load(config_stream) or {}
    except (OSError, yaml.YAMLError):
        return ""

    report_id = str(config.get("report_id", "")).strip()
    if report_id and re.fullmatch(r"[A-Za-z0-9_-]+", report_id):
        return report_id
    return ""


def _manual_pipeline_help_requested(args):
    """Return whether this invocation prints BuildStream FVT help."""
    if not args or args[0] in {"help", "--help", "-h"}:
        return True
    return (
        args[0] == "fvt_build_stream"
        and (len(args) == 1 or args[1] in {"help", "--help"})
    )


def _print_manual_pipeline_help():
    """Print the BuildStream-specific manual pipeline workflow."""
    print("BUILDSTREAM MANUAL PIPELINES (RUN IN ORDER)")
    print("  1. Verify the installed BuildStream stack:")
    print(
        "     ./run_validation.sh fvt_build_stream "
        "buildstream_install verify --marker sanity"
    )
    print("  2. Trigger and verify a new manual build:")
    print(
        "     ./run_validation.sh fvt_build_stream build_pipeline test "
        "--suite manual --marker manual"
    )
    print("  3. Deploy the exact job_id created by the manual build:")
    print(
        "     ./run_validation.sh fvt_build_stream deploy_pipeline test "
        "--suite manual --marker manual"
    )
    print()


def main():
    """Load domain config and run ValidationRunner."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, script_dir)

    from library.vars.domain_vars import (
        DOMAIN_NAME,
        ENABLE_UT,
        FVT_TAGS,
        MARKERS,
        SUITES,
        EXCLUDE_TAGS,
        ALL_EXEC_TAGS,
        ALL_EXEC_MARKER,
        SUITE_EXEC_OWNERS,
        REQUIRED_SUITE_TAGS,
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
            "suite_exec_owners": SUITE_EXEC_OWNERS,
            "required_suite_tags": REQUIRED_SUITE_TAGS,
            "enable_ut": ENABLE_UT,
        },
    )
    args = sys.argv[1:]
    result = runner.main(args)
    if result == 0 and _manual_pipeline_help_requested(args):
        _print_manual_pipeline_help()
    sys.exit(result)


if __name__ == "__main__":
    main()
