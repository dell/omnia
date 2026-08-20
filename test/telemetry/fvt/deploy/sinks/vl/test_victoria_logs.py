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
    TC_SK_007: Verify VictoriaLogs cluster pods running
    TC_SK_008: Verify VictoriaLogs vlagent pods running
"""

import pytest

from omnia_auto import TestLogger

from library.vars.test_case_vars import TEST_CASES as TC
from library.messages.telemetry_msgs import (
    TEST_LOG_MSGS as LOG_MSGS,
    TEST_ASSERT_MSGS as ASSERT_MSGS,
)
from library.functions.sink_func import (
    verify_vl_cluster_pods,
    verify_vlagent_pods,
)
from library.functions.telemetry_func import is_sink_enabled


def _skip_if_vl_disabled(host):
    """Skip test if victoria_logs sink is not enabled."""
    if not is_sink_enabled(host, "victoria_logs"):
        pytest.skip("VictoriaLogs sink not enabled in config")


@pytest.mark.sink
@pytest.mark.sanity
@pytest.mark.order(27)
def test_vl_cluster_pods(host):
    """TC_SK_007: Verify VictoriaLogs cluster pods running.

    Checks vlstorage, vlinsert, vlselect pods are all Running.
    """
    _skip_if_vl_disabled(host)
    tc = TC["vl_cluster_pods"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying VictoriaLogs cluster pods")
    result = verify_vl_cluster_pods(host)

    details_lines = []
    for comp, info in result.get("components", {}).items():
        status = "OK" if info["all_running"] else "FAIL"
        details_lines.append(
            f"  {comp}: {info['running_count']}/{info['total_count']} running [{status}]"
        )
    details = "\n".join(details_lines)

    if result["success"]:
        tl.passed(
            LOG_MSGS["pods_running"].format(
                component="VictoriaLogs cluster",
                count=result["total_running"],
                expected=result["total_running"],
            ),
            details,
        )
    else:
        tl.failed(
            LOG_MSGS["pods_not_running"].format(
                component="VictoriaLogs cluster",
                running=result["total_running"],
                expected="all",
            ),
            details,
        )

    assert result["success"], ASSERT_MSGS["pods_not_running"].format(
        component="VictoriaLogs cluster",
        running=result["total_running"],
        expected="all",
    )


@pytest.mark.sink
@pytest.mark.sanity
@pytest.mark.order(28)
def test_vlagent_pods(host):
    """TC_SK_008: Verify VictoriaLogs vlagent pods running.

    Checks that vlagent pods (log collection agent) are Running.
    """
    _skip_if_vl_disabled(host)
    tc = TC["vlagent_pods"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying vlagent pods")
    result = verify_vlagent_pods(host)

    if result["success"]:
        tl.passed(
            LOG_MSGS["pods_running"].format(
                component="vlagent",
                count=result["running_count"],
                expected=result["total_count"],
            ),
            f"Running: {result['running_count']}/{result['total_count']}",
        )
    else:
        tl.failed(
            LOG_MSGS["pods_not_running"].format(
                component="vlagent",
                running=result["running_count"],
                expected=result["total_count"],
            ),
            "",
        )

    assert result["success"], ASSERT_MSGS["pods_not_running"].format(
        component="vlagent",
        running=result["running_count"],
        expected=result["total_count"],
    )
