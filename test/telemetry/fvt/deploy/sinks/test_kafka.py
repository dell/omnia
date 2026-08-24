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
Telemetry Deploy — Kafka Sink Verification Tests.

Test cases:
    TC_SK_001: Verify Kafka broker/controller pods running
    TC_SK_002: Verify Kafka cluster Ready condition
    TC_SK_003: Verify Kafka bridge pod running
"""

import pytest

from library.functions import TestLogger
from library.vars.test_case_vars import TEST_CASES as TC
from library.vars.common_vars import (
    KAFKA_POD_PREFIXES,
    KAFKA_BRIDGE_PREFIX,
)
from library.messages.telemetry_msgs import (
    TEST_LOG_MSGS as LOG_MSGS,
    TEST_ASSERT_MSGS as ASSERT_MSGS,
)
from library.functions.k8s_func import (
    verify_pods_by_prefix,
    verify_kafka_ready,
)


@pytest.mark.sink
@pytest.mark.sanity
@pytest.mark.order(10)
def test_kafka_pods(host):
    """TC_SK_001: Verify Kafka broker/controller pods running."""
    tc = TC["kafka_pods"]
    tl = TestLogger(tc["title"], tc["id"])

    all_ok = True
    for role, prefix in KAFKA_POD_PREFIXES.items():
        tl.check(f"Checking Kafka {role} pods (prefix: {prefix})")
        result = verify_pods_by_prefix(host, prefix, min_count=1)

        if result["success"]:
            tl.passed(
                LOG_MSGS["pods_running"].format(
                    component=f"Kafka {role}",
                    count=result["running_count"],
                    expected=1,
                ),
                f"Running: {result['running_count']}",
            )
        else:
            tl.failed(
                LOG_MSGS["pods_not_running"].format(
                    component=f"Kafka {role}",
                    running=result["running_count"],
                    expected=1,
                ),
                "",
            )
            all_ok = False

    assert all_ok, ASSERT_MSGS["pods_not_running"].format(
        component="Kafka broker/controller",
        expected=1,
        running=0,
    )


@pytest.mark.sink
@pytest.mark.sanity
@pytest.mark.order(11)
def test_kafka_ready(host):
    """TC_SK_002: Verify Kafka cluster Ready condition."""
    tc = TC["kafka_ready"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking Kafka cluster Ready condition")
    result = verify_kafka_ready(host)

    if result["success"]:
        tl.passed(
            LOG_MSGS["kafka_ready"],
            f"Status: {result['status']}",
        )
    else:
        tl.failed(
            LOG_MSGS["kafka_not_ready"].format(status=result["status"]),
            "",
        )

    assert result["success"], ASSERT_MSGS["pods_not_running"].format(
        component="Kafka cluster",
        expected="Ready",
        running=result["status"],
    )


@pytest.mark.sink
@pytest.mark.sanity
@pytest.mark.order(12)
def test_kafka_bridge(host):
    """TC_SK_003: Verify Kafka bridge pod running."""
    tc = TC["kafka_bridge"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check(f"Checking Kafka bridge pods (prefix: {KAFKA_BRIDGE_PREFIX})")
    result = verify_pods_by_prefix(host, KAFKA_BRIDGE_PREFIX, min_count=1)

    if result["success"]:
        tl.passed(
            LOG_MSGS["pods_running"].format(
                component="Kafka bridge",
                count=result["running_count"],
                expected=1,
            ),
            f"Running: {result['running_count']}",
        )
    else:
        tl.failed(
            LOG_MSGS["pods_not_running"].format(
                component="Kafka bridge",
                running=result["running_count"],
                expected=1,
            ),
            "",
        )

    assert result["success"], ASSERT_MSGS["pods_not_running"].format(
        component="Kafka bridge",
        expected=1,
        running=result["running_count"],
    )
