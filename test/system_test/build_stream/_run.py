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
Validation runner entry point for the BuildStream system (e2e) suite.

Thin wrapper that loads ``library/vars/domain_vars`` and delegates to the
shared ``ValidationRunner`` with ``e2e/`` as the tag root (the shared runner
defaults to ``fvt/``).

Usage (via run_validation.sh)::

    python3 _run.py e2e_build_stream list
    python3 _run.py e2e_build_stream test                       # prepare_base + installation
    python3 _run.py e2e_build_stream prepare_base exec
    python3 _run.py e2e_build_stream installation test
    python3 _run.py e2e_build_stream installation test --suite cadence
    python3 _run.py e2e_build_stream installation verify --suite build
    python3 _run.py e2e_build_stream auto_cleanup exec
    python3 _run.py e2e_build_stream cleanup exec                # destructive
    python3 _run.py --config
"""

import os
import sys


def main():
    """Load the suite configuration and run ValidationRunner on e2e/."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, script_dir)

    from library.vars.domain_vars import (  # pylint: disable=import-outside-toplevel
        ALL_EXEC_MARKER,
        ALL_EXEC_TAGS,
        ALL_VERIFY_EXCLUDE_MARKERS,
        CATEGORY,
        DOMAIN_NAME,
        E2E_TAGS,
        EXCLUDE_TAGS,
        MARKERS,
        REQUIRED_SUITE_TAGS,
        SUITE_EXEC_OWNERS,
        SUITES,
        TAG_ROOT,
        VERIFY_ONLY_SUITES,
        VERIFY_ONLY_TAGS,
    )
    from omnia_auto.functions.validation_runner import (  # pylint: disable=import-outside-toplevel
        ValidationRunner,
    )

    runner = ValidationRunner(
        domain=DOMAIN_NAME,
        script_dir=script_dir,
        domain_config={
            "tags": E2E_TAGS,
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
            "enable_ut": False,
        },
    )
    # The shared runner reads tags from fvt/ under the fvt_<domain> category;
    # this suite keeps its scenarios in e2e/ under e2e_build_stream.
    runner.fvt_dir = os.path.join(script_dir, TAG_ROOT)
    runner.cat_fvt = CATEGORY
    runner.categories = (CATEGORY,)
    return runner.main(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
