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
Telemetry Deploy — iDRAC Source Verification Tests.

Test cases:
    TC_SR_001: Verify iDRAC StatefulSet pods ready
    TC_SR_002: Verify all iDRAC containers running
    TC_SR_003: Verify iDRAC Kafka topic 'idrac' exists
    TC_SR_004: Verify iDRAC VictoriaPump metrics endpoint
    TC_SR_005: Verify iDRAC service exists
"""

import pytest

from omnia_auto import TestLogger

from library.vars.test_case_vars import TEST_CASES as TC
from library.vars.common_vars import (
    IDRAC_SERVICE_NAME,
    TELEMETRY_NAMESPACE,
)
from library.messages.telemetry_msgs import (
    TEST_LOG_MSGS as LOG_MSGS,
    TEST_ASSERT_MSGS as ASSERT_MSGS,
)
from library.functions.source_func import (
    verify_idrac_sts_ready,
    verify_idrac_containers,
    verify_idrac_kafka_topic,
    verify_idrac_victoriapump,
    verify_idrac_service,
)
from library.functions.telemetry_func import is_source_enabled


def _skip_if_idrac_disabled(host):
    """Skip test if iDRAC source is not enabled."""
    if not is_source_enabled(host, "idrac"):
        pytest.skip("iDRAC source not enabled in config")


@pytest.mark.source
@pytest.mark.sanity
@pytest.mark.order(40)
def test_idrac_sts_ready(host):
    """TC_SR_001: Verify iDRAC StatefulSet pods ready.

    Checks that the idrac-telemetry StatefulSet has >= 1 ready replica.
    """
    _skip_if_idrac_disabled(host)
    tc = TC["idrac_sts_ready"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying iDRAC telemetry StatefulSet")
    result = verify_idrac_sts_ready(host)

    if result["success"]:
        tl.passed(
            LOG_MSGS["pods_running"].format(
                component="iDRAC StatefulSet",
                count=result["ready_replicas"],
                expected=result["expected"],
            ),
            f"Ready: {result['ready_replicas']}/{result['expected']}",
        )
    else:
        tl.failed(
            LOG_MSGS["pods_not_running"].format(
                component="iDRAC StatefulSet",
                running=result["ready_replicas"],
                expected=result["expected"],
            ),
            "",
        )

    assert result["success"], ASSERT_MSGS["pods_not_running"].format(
        component="iDRAC StatefulSet",
        running=result["ready_replicas"],
        expected=result["expected"],
    )


@pytest.mark.source
@pytest.mark.sanity
@pytest.mark.order(41)
def test_idrac_containers(host):
    """TC_SR_002: Verify all iDRAC containers running.

    Checks that all 5 containers (receiver, kafkapump, victoriapump,
    mysqldb, activemq) are running inside the iDRAC pod.
    """
    _skip_if_idrac_disabled(host)
    tc = TC["idrac_containers"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying iDRAC container statuses")
    result = verify_idrac_containers(host)

    details_lines = []
    for c in result.get("containers", []):
        status = "ready" if c["ready"] else "NOT READY"
        details_lines.append(f"  {c['name']}: {status}")
    details = "\n".join(details_lines) if details_lines else result.get("error", "")

    if result["success"]:
        tl.passed(
            LOG_MSGS["containers_ready"].format(
                pod=result["pod_name"],
                count=len(result["containers"]),
            ),
            details,
        )
    else:
        tl.failed(
            LOG_MSGS["containers_not_ready"].format(
                pod=result.get("pod_name", "unknown"),
                not_ready=", ".join(result.get("not_ready", [])),
            ),
            details,
        )

    assert result["success"], (
        f"iDRAC containers not ready: {', '.join(result.get('not_ready', []))}"
    )


@pytest.mark.source
@pytest.mark.order(42)
def test_idrac_kafka_topic(host):
    """TC_SR_003: Verify Kafka topic 'idrac' exists.

    Checks that the Kafka topic for iDRAC telemetry data has been created.
    """
    _skip_if_idrac_disabled(host)
    tc = TC["idrac_kafka_topic"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking Kafka topic 'idrac'")
    result = verify_idrac_kafka_topic(host)

    if result["success"]:
        tl.passed(
            LOG_MSGS["topic_exists"].format(topic=result["topic_name"]),
            f"All topics: {result.get('all_topics', [])}",
        )
    else:
        tl.failed(
            LOG_MSGS["topic_missing"].format(topic=result["topic_name"]),
            f"Available topics: {result.get('all_topics', [])}",
        )

    assert result["success"], ASSERT_MSGS["topic_missing"].format(
        topic=result["topic_name"],
    )


@pytest.mark.source
@pytest.mark.order(43)
def test_idrac_victoria_pump(host):
    """TC_SR_004: Verify iDRAC VictoriaPump metrics endpoint.

    Checks that the victoria-pump container in iDRAC pod exposes metrics
    at its /metrics endpoint, confirming data ingestion pipeline is active.
    """
    _skip_if_idrac_disabled(host)
    tc = TC["idrac_victoria_pump"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking VictoriaPump metrics endpoint in iDRAC pod")
    result = verify_idrac_victoriapump(host)

    if result["success"]:
        tl.passed(
            LOG_MSGS["health_ok"].format(component="iDRAC VictoriaPump"),
            "Metrics endpoint is responding",
        )
    else:
        tl.failed(
            LOG_MSGS["health_failed"].format(component="iDRAC VictoriaPump"),
            "Metrics endpoint not responding (data may take a few minutes to flow)",
        )

    # Soft assert: VictoriaPump may take time to start producing metrics
    assert result["success"], (
        "iDRAC VictoriaPump metrics endpoint not responding"
    )


@pytest.mark.source
@pytest.mark.order(44)
def test_idrac_service(host):
    """TC_SR_005: Verify iDRAC telemetry service exists.

    Checks that the idrac-telemetry-service exists in the telemetry namespace.
    """
    _skip_if_idrac_disabled(host)
    tc = TC["idrac_service"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check(f"Checking service '{IDRAC_SERVICE_NAME}'")
    result = verify_idrac_service(host)

    if result["success"]:
        tl.passed(
            LOG_MSGS["services_ok"].format(component="iDRAC"),
            f"Service: {IDRAC_SERVICE_NAME}",
        )
    else:
        tl.failed(
            LOG_MSGS["services_missing"].format(component="iDRAC"),
            f"Service '{IDRAC_SERVICE_NAME}' not found",
        )

    assert result["success"], (
        f"iDRAC service '{IDRAC_SERVICE_NAME}' not found in namespace {TELEMETRY_NAMESPACE}"
    )
