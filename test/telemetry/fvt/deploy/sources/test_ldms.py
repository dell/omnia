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
Telemetry Deploy — LDMS Source Verification Tests.

Test cases:
    TC_SR_006: Verify Vector-LDMS bridge deployment ready
    TC_SR_007: Verify LDMS Kafka topic exists
"""

import pytest

from library.functions import TestLogger
from library.vars.test_case_vars import TEST_CASES as TC
from library.vars.common_vars import (
    VECTOR_LDMS_APP_NAME,
    LDMS_KAFKA_TOPIC,
)
from library.messages.telemetry_msgs import (
    TEST_LOG_MSGS as LOG_MSGS,
    TEST_ASSERT_MSGS as ASSERT_MSGS,
)
from library.functions.k8s_func import (
    verify_deploy_ready,
    verify_kafka_topic_ready,
)
from library.functions.telemetry_func import is_source_enabled


def _skip_if_ldms_disabled(host):
    """Skip test if LDMS source is not enabled."""
    if not is_source_enabled(host, "ldms"):
        pytest.skip("LDMS source not enabled in config")


@pytest.mark.source
@pytest.mark.sanity
@pytest.mark.order(50)
def test_ldms_vector_bridge(host):
    """TC_SR_006: Verify Vector-LDMS bridge deployment ready."""
    _skip_if_ldms_disabled(host)
    tc = TC["ldms_vector_bridge"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying Vector-LDMS bridge deployment")
    result = verify_deploy_ready(host, VECTOR_LDMS_APP_NAME)

    if result["success"]:
        tl.passed(
            LOG_MSGS["pods_running"].format(
                component="Vector-LDMS bridge",
                count=result["ready_replicas"],
                expected=result["expected"],
            ),
            f"Ready: {result['ready_replicas']}/{result['expected']}",
        )
    else:
        tl.failed(
            LOG_MSGS["pods_not_running"].format(
                component="Vector-LDMS bridge",
                running=result["ready_replicas"],
                expected=result["expected"],
            ),
            "",
        )

    assert result["success"], ASSERT_MSGS["pods_not_running"].format(
        component="Vector-LDMS bridge",
        expected=result["expected"],
        running=result["ready_replicas"],
    )


@pytest.mark.source
@pytest.mark.sanity
@pytest.mark.order(51)
def test_ldms_kafka_topic(host):
    """TC_SR_007: Verify LDMS Kafka topic exists."""
    _skip_if_ldms_disabled(host)
    tc = TC["ldms_kafka_topic"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check(f"Checking Kafka topic '{LDMS_KAFKA_TOPIC}'")
    result = verify_kafka_topic_ready(host, LDMS_KAFKA_TOPIC)

    if result["success"]:
        tl.passed(
            LOG_MSGS["topic_exists"].format(topic=LDMS_KAFKA_TOPIC),
            f"Status: {result['status']}",
        )
    else:
        tl.failed(
            LOG_MSGS["topic_missing"].format(topic=LDMS_KAFKA_TOPIC),
            "",
        )

    assert result["success"], ASSERT_MSGS["topic_missing"].format(
        topic=LDMS_KAFKA_TOPIC,
    )
