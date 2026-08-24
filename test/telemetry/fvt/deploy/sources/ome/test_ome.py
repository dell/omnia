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
Telemetry Deploy — OME Source Verification Tests.

OME Architecture:
    OME itself is external (NOT deployed by Omnia).
    Omnia deploys the Vector-OME bridge that reads from OME's Kafka broker
    and writes to VictoriaMetrics/VictoriaLogs via vmagent-vector/vlagent-vector.

Test cases:
    TC_SR_011: Verify Vector-OME bridge deployment ready
    TC_SR_012: Verify OME KafkaUser CR exists
    TC_SR_013: Verify OME bridge sink prerequisites (kafka + VM/VL)
"""

import pytest

from omnia_auto import TestLogger

from library.vars.test_case_vars import TEST_CASES as TC
from library.messages.telemetry_msgs import (
    TEST_LOG_MSGS as LOG_MSGS,
    TEST_ASSERT_MSGS as ASSERT_MSGS,
)
from library.functions.source_func import (
    verify_vector_ome,
    verify_ome_kafka_user,
    verify_ome_sink_prerequisites,
)
from library.functions.telemetry_func import (
    is_source_enabled,
    load_telemetry_config_from_target,
)



def _skip_if_ome_disabled(host):
    """Skip test if OME source/bridge is not enabled.

    OME is gated on both:
    - telemetry_sources.ome.metrics_enabled or logs_enabled
    - telemetry_bridges.vector_ome.metrics_enabled or logs_enabled
    """
    config = load_telemetry_config_from_target(host)
    if not config:
        pytest.skip("Cannot load telemetry config")

    src = config.get("telemetry_sources", {}).get("ome", {})
    bridge = config.get("telemetry_bridges", {}).get("vector_ome", {})
    src_enabled = src.get("metrics_enabled", False) or src.get("logs_enabled", False)
    bridge_enabled = bridge.get("metrics_enabled", False) or bridge.get("logs_enabled", False)

    if not (src_enabled and bridge_enabled):
        pytest.skip("OME source or Vector-OME bridge not enabled")


@pytest.mark.source
@pytest.mark.sanity
@pytest.mark.order(60)
def test_vector_ome(host):
    """TC_SR_011: Verify Vector-OME bridge deployment ready.

    Checks that the vector-ome Deployment has ready replicas.
    """
    _skip_if_ome_disabled(host)
    tc = TC["vector_ome"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying Vector-OME bridge deployment")
    result = verify_vector_ome(host)

    if result["success"]:
        tl.passed(
            LOG_MSGS["pods_running"].format(
                component="Vector-OME",
                count=result["ready_replicas"],
                expected=result["ready_replicas"],
            ),
            f"Ready replicas: {result['ready_replicas']}",
        )
    else:
        tl.failed(
            LOG_MSGS["pods_not_running"].format(
                component="Vector-OME",
                running=result["ready_replicas"],
                expected="1+",
            ),
            "",
        )

    assert result["success"], ASSERT_MSGS["pods_not_running"].format(
        component="Vector-OME",
        running=result["ready_replicas"],
        expected="1+",
    )


@pytest.mark.source
@pytest.mark.order(61)
def test_ome_kafka_user(host):
    """TC_SR_012: Verify OME KafkaUser CR exists.

    OME uses a dedicated KafkaUser (vector-ome-user) for its bridge,
    separate from the shared kafkapump user.
    """
    _skip_if_ome_disabled(host)
    tc = TC["ome_kafka_user"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking OME KafkaUser CR")
    result = verify_ome_kafka_user(host)

    if result["success"]:
        tl.passed(
            f"KafkaUser '{result['user_name']}' exists",
            "",
        )
    else:
        tl.failed(
            f"KafkaUser '{result['user_name']}' not found",
            "Expected KafkaUser for Vector-OME bridge",
        )

    assert result["success"], (
        f"KafkaUser '{result['user_name']}' not found in telemetry namespace"
    )


@pytest.mark.source
@pytest.mark.order(62)
def test_ome_sink_prerequisites(host):
    """TC_SR_013: Verify OME bridge sink prerequisites.

    OME bridge requires Kafka support. Depending on which OME functions
    are enabled, it also requires VictoriaMetrics and/or VictoriaLogs.
    This test verifies Kafka is Ready (the base prerequisite for OME).
    """
    _skip_if_ome_disabled(host)
    tc = TC["ome_sink_prereqs"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying Kafka is Ready (OME prerequisite)")
    result = verify_ome_sink_prerequisites(host)

    if result["success"]:
        tl.passed(
            LOG_MSGS["health_ok"].format(component="Kafka (OME prerequisite)"),
            f"Status: {result['status']}",
        )
    else:
        tl.failed(
            LOG_MSGS["health_failed"].format(component="Kafka (OME prerequisite)"),
            f"Status: {result['status']}",
        )

    assert result["success"], (
        "Kafka is not Ready — OME bridge requires Kafka support"
    )
