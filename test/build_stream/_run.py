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
    python3 _run.py fvt_build_stream build_deploy_lifecycle test --marker sanity
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
        and (
            len(args) == 1
            or args[1] in {"help", "--help", "list"}
        )
    )


def _select_named_lifecycle(args, named_lifecycles, default_tags):
    """Translate a named lifecycle into the runner's untagged lifecycle."""
    if (
        len(args) >= 3
        and args[0] == "fvt_build_stream"
        and args[1] in named_lifecycles
        and args[2] in {"exec", "verify", "test"}
    ):
        lifecycle_name = args[1]
        translated = [args[0], args[2], *args[3:]]
        return translated, named_lifecycles[lifecycle_name], lifecycle_name
    return args, default_tags, ""


def _print_manual_pipeline_help():
    """Print BuildStream-specific lifecycle and manual workflows."""
    print("BUILDSTREAM SANITY LIFECYCLES")
    print("  Default — installation plus unified cadence pipeline:")
    print(
        "     ./run_validation.sh fvt_build_stream test --marker sanity"
    )
    print("  Build/deploy — installation plus separate build and deploy:")
    print(
        "     ./run_validation.sh fvt_build_stream "
        "build_deploy_lifecycle test --marker sanity"
    )
    print()
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
    print("  4. Trigger and verify the unified cadence pipeline:")
    print(
        "     ./run_validation.sh fvt_build_stream cadence_pipeline test "
        "--marker sanity"
    )
    print()
    print("CADENCE TEST INPUT CONTRACT")
    print("  Catalog: cadence_catalog_rhel.json (fixed GitLab CI contract)")
    print("  exec/test: signals the watcher to sync, bump, and push catalog")
    print("  product config: cadence.enabled=true and force_build=true")
    print("  prerequisites: watcher, Pulp, Git worktree, repo_sync.yml")
    print("  verify: reads mandatory job_id; never selects the latest job")
    print("  sanity coverage: 1 execution + 23 verification cases")
    print()
    print("BUILDSTREAM EXPLICIT CLEANUP SUITES")
    print(
        "  ./run_validation.sh fvt_build_stream buildstream_cleanup test "
        "--suite gitlab_cleanup --marker sanity"
    )
    print(
        "  ./run_validation.sh fvt_build_stream buildstream_cleanup test "
        "--suite buildstream_cleanup --marker sanity"
    )
    print(
        "  ./run_validation.sh fvt_build_stream buildstream_cleanup test "
        "--suite cleanup_pipeline --marker sanity"
    )
    print()


def main():  # pylint: disable=too-many-locals
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
        NAMED_LIFECYCLES,
        SUITE_EXEC_OWNERS,
        REQUIRED_SUITE_TAGS,
    )
    from omnia_auto.functions.validation_runner import ValidationRunner

    original_args = sys.argv[1:]
    args, lifecycle_tags, lifecycle_name = _select_named_lifecycle(
        original_args, NAMED_LIFECYCLES, ALL_EXEC_TAGS,
    )
    runner = ValidationRunner(
        domain=DOMAIN_NAME,
        script_dir=script_dir,
        domain_config={
            "tags": FVT_TAGS,
            "markers": MARKERS,
            "suites": SUITES,
            "exclude_tags": EXCLUDE_TAGS,
            "all_exec_tags": lifecycle_tags,
            "all_exec_marker": ALL_EXEC_MARKER,
            "suite_exec_owners": SUITE_EXEC_OWNERS,
            "required_suite_tags": REQUIRED_SUITE_TAGS,
            "enable_ut": ENABLE_UT,
        },
    )
    if lifecycle_name:
        print(
            f"Selected lifecycle group: {lifecycle_name} "
            f"({' -> '.join(lifecycle_tags)})"
        )
    result = runner.main(args)
    if result == 0 and _manual_pipeline_help_requested(original_args):
        _print_manual_pipeline_help()
    sys.exit(result)


if __name__ == "__main__":
    main()
