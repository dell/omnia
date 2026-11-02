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

"""Shared body of an SVT test case: log, run the FVT steps, render, assert."""

from omnia_auto import TestLogger

from .fvt_func import run_svt_case
from ..messages.svt_msgs import TEST_ASSERT_MSGS, TEST_LOG_MSGS
from ..vars.test_case_vars import TEST_CASES


def check_svt_case(theme: str, case: str) -> None:
    """Run SVT case ``case`` of ``theme`` and assert that every FVT step passed."""
    tc = TEST_CASES[f"{theme}_{case}"]
    logger = TestLogger(tc["title"], tc["id"])
    result = run_svt_case(theme, case, logger.info)
    fields = [*result["fields"], ("FVT reports", result["report_path"])]
    if result["success"]:
        logger.passed_fields(TEST_LOG_MSGS["case_ok"].format(
            case=case, count=len(result["fields"]), duration=result["duration"]), fields)
    else:
        logger.failed_fields(TEST_LOG_MSGS["case_failed"].format(
            case=case, step=result["failed_step"], rc=result["rc"],
            duration=result["duration"]), fields)
    assert result["success"], TEST_ASSERT_MSGS["case_failed"].format(
        case=case, step=result["failed_step"], rc=result["rc"],
        report_path=result["report_path"], theme=theme)
