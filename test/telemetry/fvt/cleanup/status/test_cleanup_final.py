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
    TEL_FVT_CLEANUP_V012: Verify no pods remain after full cleanup
    TEL_FVT_CLEANUP_V013: Verify no PVCs remain after full cleanup
    TEL_FVT_CLEANUP_V014: Verify sink PVCs are preserved after cleanup
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
    verify_pvcs_preserved,
    verify_source_pvcs_deleted,
    verify_sink_pvcs_deleted,
)


@pytest.mark.sanity
@pytest.mark.order(61)
def test_no_pods_after_full_cleanup(host):
    """TEL_FVT_CLEANUP_V012: Verify no pods remain in telemetry namespace.

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
def test_no_pvcs_after_full_cleanup(host, delete_sinks_volume):
    """TEL_FVT_CLEANUP_V013/TEL_FVT_CLEANUP_V014: Verify cleanup PVC state.

    After a full cleanup (--tags cleanup):
      - With delete_sinks_volume=true: zero PVCs must remain (all deleted).
      - With delete_sinks_volume=false: sink PVCs must be preserved and
        source PVCs must be deleted.
    """
    case_key = (
        "no_pvcs_after_full_cleanup"
        if delete_sinks_volume
        else "pvcs_preserved_after_cleanup"
    )
    tc = TC[case_key]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying source PVCs were deleted during cleanup")
    result_source = verify_source_pvcs_deleted(host)
    if not result_source["success"]:
        tl.failed(
            LOG_MSGS["pvcs_remaining"].format(count=result_source["count"]),
            result_source["details"],
        )
    assert result_source["success"], (
        f"Source PVCs were not deleted: {result_source['error']}"
    )

    if delete_sinks_volume:
        tl.check("Verifying sink PVCs were deleted during cleanup")
        result_sink = verify_sink_pvcs_deleted(host)
        if result_sink["success"]:
            tl.passed(
                LOG_MSGS["no_pvcs_remaining"],
                f"{result_source['details']}\n{result_sink['details']}",
            )
        else:
            tl.failed(
                LOG_MSGS["pvcs_remaining"].format(count=result_sink["count"]),
                result_sink["details"],
            )
        assert result_sink["success"], (
            f"Sink PVCs were not deleted: {result_sink['error']}"
        )
    else:
        tl.check("Verifying sink PVCs were preserved during cleanup")
        result = verify_pvcs_preserved(host)
        if result["success"]:
            tl.passed(LOG_MSGS["pvcs_preserved"], result["details"])
        else:
            tl.failed(
                LOG_MSGS["pvcs_not_preserved"],
                result["details"],
            )
        assert result["success"], ASSERT_MSGS["pvcs_not_preserved"]
