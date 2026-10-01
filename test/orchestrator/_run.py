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
Validation runner entry point for Orchestrator FVT, NFT, and UT.

Thin wrapper that loads domain-specific variables from
``library/vars/domain_vars`` and delegates to ``ValidationRunner``.

Usage (via run_validation.sh or run_validation CLI)::

    python3 _run.py fvt_orchestrator prepare test --marker sanity
    python3 _run.py fvt_orchestrator prepare verify --suite openldap
    python3 _run.py fvt_orchestrator provision test --marker sanity
    python3 _run.py fvt_orchestrator provision verify --suite openchami
    python3 _run.py fvt_orchestrator pxeboot test --marker sanity
    python3 _run.py fvt_orchestrator pxeboot verify --suite kubernetes_cluster
    python3 _run.py fvt_orchestrator pxeboot verify --suite slurm_cluster
    python3 _run.py fvt_orchestrator pxeboot verify --suite slurm_ldap
    python3 _run.py fvt_orchestrator list
    python3 _run.py nft_orchestrator test
    python3 _run.py nft_orchestrator test --marker security
    python3 _run.py --config
"""

import os
import sys


def _runner_all_exec_tags(args, lifecycle_tags):
    """Use broad verification only for Orchestrator's untagged verify."""
    if len(args) >= 2 and args[0] == "fvt_orchestrator" and args[1] == "verify":
        return []
    return lifecycle_tags


def _apply_safe_pxeboot_marker_default(args):
    """Default PXE verification to positive, non-disruptive sanity checks."""
    normalized = list(args)
    if (
        len(normalized) >= 3
        and normalized[0] == "fvt_orchestrator"
        and normalized[1] == "pxeboot"
        and normalized[2] in {"test", "verify"}
        and "--marker" not in normalized
    ):
        normalized.extend(["--marker", "sanity"])
    return normalized


def main():
    """Load domain config and run ValidationRunner."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, script_dir)

    from library.vars.domain_vars import (
        ALL_EXEC_MARKER,
        ALL_EXEC_TAGS,
        ALL_VERIFY_EXCLUDE_MARKERS,
        DOMAIN_NAME,
        EXCLUDE_TAGS,
        FVT_TAGS,
        MARKERS,
        REQUIRED_SUITE_TAGS,
        SUITE_EXEC_OWNERS,
        SUITES,
        VERIFY_ONLY_SUITES,
        VERIFY_ONLY_TAGS,
    )
    from omnia_auto.functions.validation_runner import ValidationRunner

    args = _apply_safe_pxeboot_marker_default(sys.argv[1:])
    runner = ValidationRunner(
        domain=DOMAIN_NAME,
        script_dir=script_dir,
        domain_config={
            "tags": FVT_TAGS,
            "markers": MARKERS,
            "suites": SUITES,
            "exclude_tags": EXCLUDE_TAGS,
            "all_exec_tags": _runner_all_exec_tags(
                args,
                ALL_EXEC_TAGS,
            ),
            "all_exec_marker": ALL_EXEC_MARKER,
            "all_verify_exclude_markers": ALL_VERIFY_EXCLUDE_MARKERS,
            "required_suite_tags": REQUIRED_SUITE_TAGS,
            "verify_only_tags": VERIFY_ONLY_TAGS,
            "verify_only_suites": VERIFY_ONLY_SUITES,
            "suite_exec_owners": SUITE_EXEC_OWNERS,
        },
    )
    return runner.main(args)


if __name__ == "__main__":
    sys.exit(main())
