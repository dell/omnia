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
Telemetry Deploy — VictoriaMetrics Sink Verification Tests.

Test cases:
    TC_SK_004: Verify VictoriaMetrics cluster pods running
    TC_SK_005: Verify VMAgent pods running
"""

import pytest

from library.functions import TestLogger
from library.vars.test_case_vars import TEST_CASES as TC
from library.vars.common_vars import (
    VM_POD_PREFIXES,
    VMAGENT_POD_PREFIX,
)
from library.messages.telemetry_msgs import (
    TEST_LOG_MSGS as LOG_MSGS,
    TEST_ASSERT_MSGS as ASSERT_MSGS,
)
from library.functions.k8s_func import verify_pods_by_prefix


@pytest.mark.sink
@pytest.mark.sanity
@pytest.mark.order(20)
def test_vm_cluster_pods(host):
    """TC_SK_004: Verify VictoriaMetrics cluster pods running."""
    tc = TC["vm_cluster_pods"]
    tl = TestLogger(tc["title"], tc["id"])

    all_ok = True
    for role, prefix in VM_POD_PREFIXES.items():
        tl.check(f"Checking VM {role} pods (prefix: {prefix})")
        result = verify_pods_by_prefix(host, prefix, min_count=1)

        if result["success"]:
            tl.passed(
                LOG_MSGS["pods_running"].format(
                    component=f"VM {role}",
                    count=result["running_count"],
                    expected=1,
                ),
                f"Running: {result['running_count']}",
            )
        else:
            tl.failed(
                LOG_MSGS["pods_not_running"].format(
                    component=f"VM {role}",
                    running=result["running_count"],
                    expected=1,
                ),
                "",
            )
            all_ok = False

    assert all_ok, ASSERT_MSGS["pods_not_running"].format(
        component="VictoriaMetrics cluster",
        expected=1,
        running=0,
    )


@pytest.mark.sink
@pytest.mark.sanity
@pytest.mark.order(21)
def test_vmagent_pods(host):
    """TC_SK_005: Verify VMAgent pods running."""
    tc = TC["vmagent_pods"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check(f"Checking VMAgent pods (prefix: {VMAGENT_POD_PREFIX})")
    result = verify_pods_by_prefix(host, VMAGENT_POD_PREFIX, min_count=1)

    if result["success"]:
        tl.passed(
            LOG_MSGS["pods_running"].format(
                component="VMAgent",
                count=result["running_count"],
                expected=1,
            ),
            f"Running: {result['running_count']}",
        )
    else:
        tl.failed(
            LOG_MSGS["pods_not_running"].format(
                component="VMAgent",
                running=result["running_count"],
                expected=1,
            ),
            "",
        )

    assert result["success"], ASSERT_MSGS["pods_not_running"].format(
        component="VMAgent",
        expected=1,
        running=result["running_count"],
    )
