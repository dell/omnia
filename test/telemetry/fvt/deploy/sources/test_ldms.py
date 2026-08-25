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

LDMS Architecture:
    LDMS uses a hierarchical collection: sampler -> aggregator -> store.
    The aggregator (nersc-ldms-aggr) receives data from LDMS samplers
    running on compute nodes. The store (nersc-ldms-store) writes data
    to the Kafka topic. Vector-LDMS bridges Kafka to VictoriaMetrics.

    Data pipeline:
        LDMS Samplers (compute) -> Aggregator -> Store -> Kafka 'ldms'
        Kafka 'ldms' -> Vector-LDMS -> VictoriaMetrics

Test cases:
    TC_SR_020: Verify LDMS aggregator pod running
    TC_SR_021: Verify LDMS store pod running
    TC_SR_022: Verify Vector-LDMS bridge deployment ready
    TC_SR_023: Verify LDMS Kafka topic exists
"""

import pytest

from library.functions import TestLogger
from library.vars.test_case_vars import TEST_CASES as TC
from library.vars.common_vars import (
    LDMS_AGG_STS_NAME,
    LDMS_STORE_NAME,
    VECTOR_LDMS_APP_NAME,
    LDMS_KAFKA_TOPIC,
)
from library.messages.telemetry_msgs import (
    TEST_LOG_MSGS as LOG_MSGS,
    TEST_ASSERT_MSGS as ASSERT_MSGS,
)
from library.functions.k8s_func import (
    verify_sts_ready,
    verify_deploy_ready,
    verify_kafka_topic_ready,
    verify_pods_by_prefix,
)
from library.functions.telemetry_func import is_source_enabled


def _skip_if_ldms_disabled(host):
    """Skip test if LDMS source is not enabled."""
    if not is_source_enabled(host, "ldms"):
        pytest.skip("LDMS source not enabled in config")


# =========================================================================
# TC_SR_020: Verify LDMS aggregator pod running
# =========================================================================

@pytest.mark.source
@pytest.mark.sanity
@pytest.mark.order(50)
def test_ldms_aggr_pod(host):
    """TC_SR_020: Verify LDMS aggregator pod running."""
    _skip_if_ldms_disabled(host)
    tc = TC["ldms_aggr_pod"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check(f"Verifying LDMS aggregator StatefulSet '{LDMS_AGG_STS_NAME}'")
    result = verify_sts_ready(host, LDMS_AGG_STS_NAME)

    if result.get("not_found"):
        # Try pods by prefix instead (name may differ)
        pods_result = verify_pods_by_prefix(host, LDMS_AGG_STS_NAME, min_count=1)
        if pods_result["success"]:
            tl.passed(
                LOG_MSGS["pods_running"].format(
                    component="LDMS aggregator",
                    count=len(pods_result["pods"]),
                    expected=1,
                ),
                "\n".join(
                    f"  \u2713 {p['name']}: {p['status']}"
                    for p in pods_result["pods"]
                ),
            )
            return
        tl.failed(
            LOG_MSGS["pods_not_running"].format(
                component="LDMS aggregator", running=0, expected=1,
            ),
            f"StatefulSet '{LDMS_AGG_STS_NAME}' not found",
        )
        pytest.fail(f"LDMS aggregator '{LDMS_AGG_STS_NAME}' not found")

    if result["success"]:
        tl.passed(
            LOG_MSGS["pods_running"].format(
                component="LDMS aggregator",
                count=result["ready_replicas"],
                expected=result["expected"],
            ),
            f"Ready: {result['ready_replicas']}/{result['expected']}",
        )
    else:
        tl.failed(
            LOG_MSGS["pods_not_running"].format(
                component="LDMS aggregator",
                running=result["ready_replicas"],
                expected=result["expected"],
            ),
            "",
        )

    assert result["success"], ASSERT_MSGS["pods_not_running"].format(
        component="LDMS aggregator",
        expected=result["expected"],
        running=result["ready_replicas"],
    )


# =========================================================================
# TC_SR_021: Verify LDMS store pod running
# =========================================================================

@pytest.mark.source
@pytest.mark.sanity
@pytest.mark.order(51)
def test_ldms_store_pod(host):
    """TC_SR_021: Verify LDMS store pod running."""
    _skip_if_ldms_disabled(host)
    tc = TC["ldms_store_pod"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check(f"Verifying LDMS store pods '{LDMS_STORE_NAME}'")
    result = verify_pods_by_prefix(host, LDMS_STORE_NAME, min_count=1)

    details_lines = []
    for p in result.get("pods", []):
        icon = "\u2713" if p["status"] == "Running" else "\u2717"
        details_lines.append(f"  {icon} {p['name']}: {p['status']}")
    details = "\n".join(details_lines) if details_lines else "  (no pods found)"

    if result["success"]:
        tl.passed(
            LOG_MSGS["pods_running"].format(
                component="LDMS store",
                count=len(result["pods"]),
                expected=1,
            ),
            details,
        )
    else:
        tl.failed(
            LOG_MSGS["pods_not_running"].format(
                component="LDMS store",
                running=len(result.get("pods", [])),
                expected=1,
            ),
            details,
        )

    assert result["success"], ASSERT_MSGS["pods_not_running"].format(
        component="LDMS store",
        expected=1,
        running=len(result.get("pods", [])),
    )


# =========================================================================
# TC_SR_022: Verify Vector-LDMS bridge deployment ready
# =========================================================================

@pytest.mark.source
@pytest.mark.sanity
@pytest.mark.order(52)
def test_ldms_vector_bridge(host):
    """TC_SR_022: Verify Vector-LDMS bridge deployment ready."""
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


# =========================================================================
# TC_SR_023: Verify LDMS Kafka topic exists
# =========================================================================

@pytest.mark.source
@pytest.mark.sanity
@pytest.mark.order(53)
def test_ldms_kafka_topic(host):
    """TC_SR_023: Verify LDMS Kafka topic exists."""
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
