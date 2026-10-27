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
Validation runner entry point for the BuildStream system verification test
(SVT) suite.

Loads ``library/vars/domain_vars`` and runs ``utility/svt_runner.SvtRunner``
(the shared ``ValidationRunner`` adapted to the single ``svt_build_stream``
category and the ``svt/`` scenario root).

Usage (via run_validation.sh)::

    python3 _run.py svt_build_stream list
    python3 _run.py svt_build_stream test                       # full flow
    python3 _run.py svt_build_stream prepare_base exec
    python3 _run.py svt_build_stream installation test
    python3 _run.py svt_build_stream installation verify --marker cadence
    python3 _run.py svt_build_stream installation verify --suite build
    python3 _run.py svt_build_stream auto_cleanup test
    python3 _run.py svt_build_stream cleanup test               # destructive
    python3 _run.py --config
"""

import os
import sys


def main():
    """Load the suite configuration and run the SVT runner on svt/."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, script_dir)

    # pylint: disable=import-outside-toplevel
    from library.vars.domain_vars import (
        ALL_EXEC_MARKER,
        ALL_EXEC_TAGS,
        ALL_VERIFY_EXCLUDE_MARKERS,
        CATEGORY,
        DOMAIN_NAME,
        EXCLUDE_TAGS,
        MARKERS,
        REQUIRED_SUITE_TAGS,
        SUITE_EXEC_OWNERS,
        SUITES,
        SVT_TAGS,
        TAG_ROOT,
        VERIFY_ONLY_SUITES,
        VERIFY_ONLY_TAGS,
    )
    from utility.svt_runner import SvtRunner

    runner = SvtRunner(
        domain=DOMAIN_NAME,
        script_dir=script_dir,
        domain_config={
            "tags": SVT_TAGS,
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
        category=CATEGORY,
        tag_root=TAG_ROOT,
    )
    return runner.main(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
