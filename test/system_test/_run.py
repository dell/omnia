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

"""SVT runner: run the system verification suite of one theme.

Usage::

    ./run_validation.sh --help
    ./run_validation.sh svt_<theme> list
    ./run_validation.sh svt_<theme> test [--case <case>]

Every argument is validated against library/vars/domain_vars.py before pytest
starts; unknown themes or cases fail. JUnit XML goes to
reports/<run_id>/junit_<theme>.xml (run id from SVT_RUN_ID or generated).
"""

import os
import sys
from datetime import datetime, timezone
from typing import List

import pytest

from library.vars.common_vars import MODULE_ROOT, REPORT_ROOT, RUN_ID_ENV, RUN_ID_RE
from library.vars.domain_vars import CASES, RUNNER_PREFIX, THEME_NAMES
from library.vars.test_case_vars import TEST_CASES
from library.vars.theme_vars import THEMES


def _usage() -> str:
    lines = ["Usage: ./run_validation.sh svt_<theme> list|test [--case <case>]", "", "Themes:"]
    for theme in THEME_NAMES:
        lines.append(f"  svt_{theme:<14} {THEMES[theme]['description']}")
        lines.append(f"  {'':18} cases: {', '.join(CASES[theme])}")
    return "\n".join(lines)


def _list(theme: str) -> int:
    print(f"svt_{theme}: {THEMES[theme]['description']}")
    for case in CASES[theme]:
        tc = TEST_CASES[f"{theme}_{case}"]
        print(f"  {tc['id']:<22} --case {case:<20} {tc['title']}")
    return 0


def _test(theme: str, case: str) -> int:
    run_id = os.environ.get(RUN_ID_ENV, "")
    if not RUN_ID_RE.fullmatch(run_id):
        run_id = datetime.now(timezone.utc).strftime("svt-%Y%m%dT%H%M%SZ")
        os.environ[RUN_ID_ENV] = run_id
    report_dir = os.path.join(REPORT_ROOT, run_id)
    os.makedirs(report_dir, mode=0o750, exist_ok=True)
    marker = f"{theme} and {case}" if case else theme
    args = [os.path.join(MODULE_ROOT, "svt", theme), "-m", marker,
            f"--junitxml={os.path.join(report_dir, f'junit_{theme}.xml')}"]
    return int(pytest.main(args))


def main(argv: List[str]) -> int:
    """Validate the arguments and dispatch."""
    if not argv or argv[0] in ("-h", "--help"):
        print(_usage())
        return 0
    category = argv[0]
    theme = category.removeprefix(RUNNER_PREFIX)
    if not category.startswith(RUNNER_PREFIX) or theme not in THEME_NAMES:
        print(f"ERROR: unknown category {category!r}\n\n{_usage()}", file=sys.stderr)
        return 2
    rest = argv[1:]
    if rest == ["list"]:
        return _list(theme)
    case = ""
    if rest[:1] == ["test"] and len(rest) in (1, 3) and (len(rest) == 1 or rest[1] == "--case"):
        case = rest[2] if len(rest) == 3 else ""
        if case and case not in CASES[theme]:
            print(f"ERROR: unknown case {case!r} for svt_{theme}; "
                  f"choose one of: {', '.join(CASES[theme])}", file=sys.stderr)
            return 2
        return _test(theme, case)
    print(f"ERROR: unsupported arguments {' '.join(rest)!r}\n\n{_usage()}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    os.chdir(MODULE_ROOT)
    sys.exit(main(sys.argv[1:]))
