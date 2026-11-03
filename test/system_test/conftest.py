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

"""Pytest session for the SVT suites (svt/<theme>/).

- configures omnia_auto for this module (output helpers only; the SVT itself
  holds no credentials and opens no SSH session: FVT steps run locally)
- registers the theme and test case markers from library/vars/domain_vars.py
- writes one result record per test case to <run folder>/svt_results.json
  for the summary stage
"""

import json
import os
from datetime import datetime, timezone

import omnia_auto

from library.functions.stage_func import run_dir
from library.vars.common_vars import MODULE_ROOT, RUN_ID_ENV, RUN_ID_RE
from library.vars.domain_vars import MARKERS
from library.vars.test_case_vars import TEST_CASES

omnia_auto.configure(module_root=MODULE_ROOT)

_RESULTS = []
_IDS = {f"test_{key}": case for key, case in TEST_CASES.items()}


def _run_id() -> str:
    run_id = os.environ.get(RUN_ID_ENV, "")
    if RUN_ID_RE.fullmatch(run_id):
        return run_id
    return datetime.now(timezone.utc).strftime("svt-%Y%m%dT%H%M%SZ")


def pytest_configure(config):
    """Register markers so unknown ones fail (--strict-markers in pytest.ini)."""
    config.addinivalue_line("markers", "order(n): execution order (lower first)")
    for marker in MARKERS:
        config.addinivalue_line("markers", f"{marker}: SVT theme or test case selector")


def pytest_runtest_logreport(report):
    """Record the call phase (or a setup failure/skip) of every SVT case once."""
    if report.when != "call" and not (report.when == "setup" and report.outcome != "passed"):
        return
    name = report.nodeid.rsplit("::", 1)[-1]
    case = _IDS.get(name, {})
    _RESULTS.append({"id": case.get("id", name), "title": case.get("title", ""),
                     "outcome": report.outcome, "duration": f"{report.duration:.0f}s"})


def pytest_sessionfinish(session):
    """Write the case results for the summary stage."""
    del session
    directory = run_dir(_run_id())
    with open(os.path.join(directory, "svt_results.json"), "w", encoding="utf-8") as stream:
        json.dump(_RESULTS, stream, indent=2)
