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

"""Test-layer rendering and assertion policy for structured FVT results."""

import pytest
from library.functions import TestLogger
from library.messages import CLEANUP_TEST_ASSERT_MSGS as CLEANUP_ASSERT
from library.messages import CLEANUP_TEST_LOG_MSGS as CLEANUP_LOG
from library.messages import PRECHECK_TEST_ASSERT_MSGS as PRECHECK_ASSERT
from library.messages import PRECHECK_TEST_LOG_MSGS as PRECHECK_LOG
from library.messages import PXEBOOT_TEST_ASSERT_MSGS as PXEBOOT_ASSERT
from library.messages import PXEBOOT_TEST_LOG_MSGS as PXEBOOT_LOG
from library.vars import TEST_CASES


def _report(case, result, fields, component, messages):
    """Render one final result and enforce its success contract."""
    log_messages, assert_messages = messages
    test_log = TestLogger(case["title"], case["id"])
    if result["success"]:
        test_log.passed_fields(
            log_messages["check_passed"].format(component=component),
            fields,
        )
    else:
        test_log.failed_fields(
            log_messages["check_failed"].format(component=component),
            [*fields, ("Error", result["error"])],
        )
    assert result["success"], assert_messages["verification_failed"].format(
        component=component,
        error=result["error"],
    )


def verify_precheck(host, key, checker):
    """Execute and enforce one precheck verification result."""
    case = TEST_CASES[key]
    result = checker(host)
    _report(
        case,
        result,
        result["fields"],
        case["component"],
        (PRECHECK_LOG, PRECHECK_ASSERT),
    )


def verify_cleanup(host, key, component, checker):
    """Execute and enforce one cleanup verification result."""
    case = TEST_CASES[key]
    result = checker(host)
    _report(
        case,
        result,
        result["fields"],
        component,
        (CLEANUP_LOG, CLEANUP_ASSERT),
    )


def verify_pxeboot(host, key, checker):
    """Execute and enforce one PXE post-boot verification result."""
    case = TEST_CASES[key]
    result = checker(host)
    fields = result["details"]["fields"]
    if result.get("skipped"):
        TestLogger(case["title"], case["id"]).skipped_fields(
            PXEBOOT_LOG["check_skipped"].format(component=case["component"]),
            fields,
        )
        reason = fields[0][1] if fields else f"{case['component']} is not enabled"
        pytest.skip(str(reason))
    _report(
        case,
        result,
        fields,
        case["component"],
        (PXEBOOT_LOG, PXEBOOT_ASSERT),
    )
