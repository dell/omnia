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

"""Shared body of an SVT test: run its FVT step, add it to the stage report, assert.

Each SVT test (svt/<theme>/) runs one FVT step of test_case_vars.TEST_CASES:
``exec`` runs the playbook, ``verify`` its verification tests. The screen
output and the FVT results of the step go into the stage section of the SVT
report. Once a test of a stage failed, the later tests of that stage are
skipped (they need what it should have set up).
"""

import os
from typing import Any, Dict

import pytest
from omnia_auto import TestLogger

from . import run_func, svt_report_func
from .config_func import load_svt_config
from .fvt_func import describe_step, run_fvt_step, step_info
from ..messages.svt_msgs import SETUP_MSGS, TEST_ASSERT_MSGS, TEST_LOG_MSGS
from ..vars.common_vars import REPORT_SECTION_ENV
from ..vars.test_case_vars import TEST_CASES

# Stage -> ID of its first failed test, in this pytest session.
_FAILED: Dict[str, str] = {}


def _report(theme: str, item: Dict[str, Any]) -> None:
    """Add ``item`` to the running stage section and re-render; never fails the test."""
    section = os.environ.get(REPORT_SECTION_ENV, "")
    if not section:
        return
    try:
        settings = run_func.active_run(load_svt_config(theme), allow_failed=True)
        svt_report_func.add_item(settings, section, item)
        svt_report_func.render(settings, svt_report_func.run_meta(theme, run_func.load_run()))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(SETUP_MSGS["report_failed"].format(error=f"{type(exc).__name__}: {exc}"))


def run_svt_test(theme: str, name: str) -> None:
    """Run SVT test ``<theme>_<name>`` and assert that its FVT step passed."""
    tc = TEST_CASES[f"{theme}_{name}"]
    label = describe_step(tc["step"])
    blocked = _FAILED.get(tc["stage"])
    if blocked:
        reason = TEST_LOG_MSGS["blocked"].format(test=blocked)
        _report(theme, svt_report_func.make_item({
            "id": tc["id"], "name": tc["title"], "status": "Skipped", "details": reason,
            "command": label, "fvt": step_info(tc["step"])}))
        pytest.skip(reason)
    logger = TestLogger(tc["title"], tc["id"])
    result = run_fvt_step(tc["step"])
    _report(theme, svt_report_func.make_item({
        "id": tc["id"], "name": tc["title"], "status": "Passed" if result["success"] else "Failed",
        "duration": result["duration"], "command": label, "output": result["output"],
        "results": result["results"], "fvt": result["fvt"], "details": f"$ {result['command']}",
        "error": "" if result["success"] else f"{label} failed (rc={result['rc']})"}))
    fields = [("FVT step", label), ("rc", result["rc"]),
              ("FVT results", len(result["results"]))]
    if result["success"]:
        logger.passed_fields(TEST_LOG_MSGS["test_ok"].format(step=label), fields)
        return
    _FAILED[tc["stage"]] = tc["id"]
    logger.failed_fields(TEST_LOG_MSGS["test_failed"].format(step=label, rc=result["rc"]), fields)
    assert result["success"], TEST_ASSERT_MSGS["test_failed"].format(
        step=label, rc=result["rc"], theme=theme, stage=tc["stage"])
