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
Telemetry Deploy — VictoriaLogs Sink Verification Tests.

Test cases:
    TC_SK_006: Verify VictoriaLogs cluster pods running
    TC_SK_007: Verify VLAgent pods running
"""

import pytest

from library.functions import TestLogger
from library.vars.test_case_vars import TEST_CASES as TC
from library.vars.common_vars import (
    VL_POD_PREFIXES,
    VLAGENT_POD_PREFIX,
)
from library.messages.telemetry_msgs import (
    TEST_LOG_MSGS as LOG_MSGS,
    TEST_ASSERT_MSGS as ASSERT_MSGS,
)
from library.functions.k8s_func import verify_pods_by_prefix


@pytest.mark.sink
@pytest.mark.sanity
@pytest.mark.order(25)
def test_vl_cluster_pods(host):
    """TC_SK_006: Verify VictoriaLogs cluster pods running."""
    tc = TC["vl_cluster_pods"]
    tl = TestLogger(tc["title"], tc["id"])

    all_ok = True
    for role, prefix in VL_POD_PREFIXES.items():
        tl.check(f"Checking VL {role} pods (prefix: {prefix})")
        result = verify_pods_by_prefix(host, prefix, min_count=1)

        if result["success"]:
            tl.passed(
                LOG_MSGS["pods_running"].format(
                    component=f"VL {role}",
                    count=result["running_count"],
                    expected=1,
                ),
                f"Running: {result['running_count']}",
            )
        else:
            tl.failed(
                LOG_MSGS["pods_not_running"].format(
                    component=f"VL {role}",
                    running=result["running_count"],
                    expected=1,
                ),
                "",
            )
            all_ok = False

    assert all_ok, ASSERT_MSGS["pods_not_running"].format(
        component="VictoriaLogs cluster",
        expected=1,
        running=0,
    )


@pytest.mark.sink
@pytest.mark.sanity
@pytest.mark.order(26)
def test_vlagent_pods(host):
    """TC_SK_007: Verify VLAgent pods running."""
    tc = TC["vlagent_pods"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check(f"Checking VLAgent pods (prefix: {VLAGENT_POD_PREFIX})")
    result = verify_pods_by_prefix(host, VLAGENT_POD_PREFIX, min_count=1)

    if result["success"]:
        tl.passed(
            LOG_MSGS["pods_running"].format(
                component="VLAgent",
                count=result["running_count"],
                expected=1,
            ),
            f"Running: {result['running_count']}",
        )
    else:
        tl.failed(
            LOG_MSGS["pods_not_running"].format(
                component="VLAgent",
                running=result["running_count"],
                expected=1,
            ),
            "",
        )

    assert result["success"], ASSERT_MSGS["pods_not_running"].format(
        component="VLAgent",
        expected=1,
        running=result["running_count"],
    )
