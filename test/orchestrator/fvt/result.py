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

"""Test-layer rendering and assertion policy for structured FVT results.

Each test resolves its registry entry, creates its own ``TestLogger`` start
record, and passes both here. These helpers only render the final record and
enforce the result contract.
"""

import pytest
from library.functions import TestLogger
from library.messages import CLEANUP_TEST_ASSERT_MSGS as CLEANUP_ASSERT
from library.messages import CLEANUP_TEST_LOG_MSGS as CLEANUP_LOG
from library.messages import PRECHECK_TEST_ASSERT_MSGS as PRECHECK_ASSERT
from library.messages import PRECHECK_TEST_LOG_MSGS as PRECHECK_LOG
from library.messages import PXEBOOT_TEST_ASSERT_MSGS as PXEBOOT_ASSERT
from library.messages import PXEBOOT_TEST_LOG_MSGS as PXEBOOT_LOG
from library.vars import TEST_CASES


def _report(test_log, result, fields, component, messages):
    """Render one final result and enforce its success contract."""
    log_messages, assert_messages = messages
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


def _skip_if_requested(test_log, case, result, fields, log_messages):
    """Record and raise a documented skip for an optional capability."""
    if not result.get("skipped"):
        return
    test_log.skipped_fields(
        log_messages["check_skipped"].format(component=case["component"]),
        fields,
    )
    reason = dict(fields).get("Reason") or (fields[0][1] if fields else "")
    pytest.skip(str(reason or f"{case['component']} is not enabled"))


def verify_precheck(test_log, case, host, checker):
    """Execute and enforce one precheck verification result."""
    result = checker(host)
    _skip_if_requested(test_log, case, result, result["fields"], PRECHECK_LOG)
    _report(
        test_log,
        result,
        result["fields"],
        case["component"],
        (PRECHECK_LOG, PRECHECK_ASSERT),
    )


def verify_precheck_rejection(test_log, case, host, checker):
    """Require one precheck to reject an invalid condition with an error."""
    result = checker(host)
    fields = result["fields"]
    _skip_if_requested(test_log, case, result, fields, PRECHECK_LOG)
    component = case["component"]
    rejected = not result["success"] and bool(result["error"])
    if rejected:
        test_log.passed_fields(
            PRECHECK_LOG["rejection_passed"].format(component=component),
            [*fields, ("Rejection", result["error"])],
        )
    else:
        test_log.failed_fields(
            PRECHECK_LOG["rejection_failed"].format(component=component),
            fields,
        )
    assert rejected, PRECHECK_ASSERT["rejection_missing"].format(
        component=component
    )


def verify_cleanup(test_log, host, component, checker):
    """Execute and enforce one cleanup verification result."""
    result = checker(host)
    _report(
        test_log,
        result,
        result["fields"],
        component,
        (CLEANUP_LOG, CLEANUP_ASSERT),
    )


def verify_pxeboot(host, key, checker):
    """Execute and enforce one PXE post-boot verification result."""
    case = TEST_CASES[key]
    test_log = TestLogger(case["title"], case["id"])
    result = checker(host)
    fields = result["details"]["fields"]
    _skip_if_requested(test_log, case, result, fields, PXEBOOT_LOG)
    _report(
        test_log,
        result,
        fields,
        case["component"],
        (PXEBOOT_LOG, PXEBOOT_ASSERT),
    )
