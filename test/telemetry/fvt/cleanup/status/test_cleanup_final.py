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
Telemetry Cleanup — Final State Verification Tests.

Verifies that no pods or PVCs remain in the telemetry namespace after
a full cleanup has completed.

Test cases:
    TC_CL_012: Verify no pods remain after full cleanup
    TC_CL_013: Verify no PVCs remain after full cleanup
"""

import pytest

from omnia_auto import TestLogger

from library.vars.test_case_vars import TEST_CASES as TC
from library.messages.telemetry_msgs import (
    TEST_LOG_MSGS as LOG_MSGS,
    TEST_ASSERT_MSGS as ASSERT_MSGS,
)
from library.functions.cleanup_func import (
    verify_no_pods_remaining,
    verify_no_pvcs_remaining,
)


@pytest.mark.sanity
@pytest.mark.order(61)
def test_no_pods_after_full_cleanup(host):
    """TC_CL_012: Verify no pods remain in telemetry namespace.

    After a full cleanup (--tags cleanup), the telemetry namespace
    should contain zero pods.
    """
    tc = TC["no_pods_after_full_cleanup"]
    tl = TestLogger(tc["title"], tc["id"])

    result = verify_no_pods_remaining(host)

    if result["success"]:
        tl.passed(LOG_MSGS["no_pods_remaining"], result["details"])
    else:
        tl.failed(
            LOG_MSGS["pods_remaining"].format(count=result["count"]),
            result["details"],
        )

    assert result["success"], ASSERT_MSGS["pods_remaining"].format(
        count=result["count"],
    )


@pytest.mark.sanity
@pytest.mark.order(62)
def test_no_pvcs_after_full_cleanup(host):
    """TC_CL_013: Verify no PVCs remain in telemetry namespace.

    After a full cleanup (--tags cleanup), the telemetry namespace
    should contain zero PersistentVolumeClaims.
    """
    tc = TC["no_pvcs_after_full_cleanup"]
    tl = TestLogger(tc["title"], tc["id"])

    result = verify_no_pvcs_remaining(host)

    if result["success"]:
        tl.passed(LOG_MSGS["no_pvcs_remaining"], result["details"])
    else:
        tl.failed(
            LOG_MSGS["pvcs_remaining"].format(count=result["count"]),
            result["details"],
        )

    assert result["success"], ASSERT_MSGS["pvcs_remaining"].format(
        count=result["count"],
    )
