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
    TC_SK_009: Verify Kafka broker pods running
    TC_SK_010: Verify Kafka CR is Ready
    TC_SK_011: Verify Kafka bridge pods (if deployed)
    TC_SK_012: Verify Kafka persistence sizes
"""

import pytest

from omnia_auto import TestLogger

from library.vars.test_case_vars import TEST_CASES as TC
from library.vars.common_vars import TELEMETRY_NAMESPACE
from library.messages.telemetry_msgs import (
    TEST_LOG_MSGS as LOG_MSGS,
    TEST_ASSERT_MSGS as ASSERT_MSGS,
)
from library.functions.sink_func import (
    verify_kafka_pods,
    verify_kafka_ready,
    verify_kafka_bridge,
    verify_kafka_persistence,
)
from library.functions.k8s_func import get_pod_count
from library.functions.telemetry_func import is_sink_enabled


def _skip_if_kafka_disabled(host):
    """Skip test if kafka sink is not enabled."""
    if not is_sink_enabled(host, "kafka"):
        pytest.skip("Kafka sink not enabled in config")


@pytest.mark.sink
@pytest.mark.sanity
@pytest.mark.order(29)
def test_kafka_pods(host):
    """TC_SK_009: Verify Kafka broker pods running.

    Checks that Kafka broker (and controller, if separate) pods are Running.
    """
    _skip_if_kafka_disabled(host)
    tc = TC["kafka_pods"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying Kafka pods")
    result = verify_kafka_pods(host)

    details_lines = []
    for role, info in result.get("components", {}).items():
        status = "OK" if info["all_running"] else "FAIL"
        details_lines.append(
            f"  {role}: {info['running_count']}/{info['total_count']} running [{status}]"
        )
    details = "\n".join(details_lines)

    if result["success"]:
        tl.passed(
            LOG_MSGS["pods_running"].format(
                component="Kafka",
                count=result["total_running"],
                expected=result["total_running"],
            ),
            details,
        )
    else:
        tl.failed(
            LOG_MSGS["pods_not_running"].format(
                component="Kafka",
                running=result["total_running"],
                expected="all",
            ),
            details,
        )

    assert result["success"], ASSERT_MSGS["pods_not_running"].format(
        component="Kafka",
        running=result["total_running"],
        expected="all",
    )


@pytest.mark.sink
@pytest.mark.sanity
@pytest.mark.order(30)
def test_kafka_ready(host):
    """TC_SK_010: Verify Kafka CR is Ready.

    Uses ``kubectl wait kafka/kafka --for=condition=Ready`` to verify
    the Strimzi Kafka custom resource reports Ready.
    """
    _skip_if_kafka_disabled(host)
    tc = TC["kafka_ready"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking Kafka CR Ready condition")
    result = verify_kafka_ready(host)

    if result["success"]:
        tl.passed(
            LOG_MSGS["health_ok"].format(component="Kafka CR"),
            f"Status: {result['status']}",
        )
    else:
        tl.failed(
            LOG_MSGS["health_failed"].format(component="Kafka CR"),
            f"Status: {result['status']}",
        )

    assert result["success"], ASSERT_MSGS["health_failed"].format(
        component="Kafka CR",
    )


@pytest.mark.sink
@pytest.mark.order(31)
def test_kafka_bridge(host):
    """TC_SK_011: Verify Kafka bridge pods (if deployed).

    Checks that the Kafka HTTP bridge deployment is running
    if the bridge is deployed. This test passes if the bridge is
    not deployed (optional component).
    """
    _skip_if_kafka_disabled(host)
    tc = TC["kafka_bridge"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking Kafka bridge deployment")
    result = verify_kafka_bridge(host)

    if not result.get("deployed"):
        tl.passed(
            "Kafka bridge not deployed (optional component)",
            "Skipped — bridge not part of this deployment",
        )
    elif result["success"]:
        tl.passed(
            LOG_MSGS["pods_running"].format(
                component="Kafka bridge",
                count=result["running_count"],
                expected=result["running_count"],
            ),
            "",
        )
    else:
        tl.failed(
            LOG_MSGS["pods_not_running"].format(
                component="Kafka bridge",
                running=result["running_count"],
                expected="all",
            ),
            "",
        )

    assert result["success"], ASSERT_MSGS["pods_not_running"].format(
        component="Kafka bridge",
        running=result.get("running_count", 0),
        expected="all",
    )


@pytest.mark.sink
@pytest.mark.order(32)
def test_kafka_persistence(host):
    """TC_SK_012: Verify Kafka persistence (PVCs exist).

    Checks that Kafka data PVCs exist in the telemetry namespace.
    """
    _skip_if_kafka_disabled(host)
    tc = TC["kafka_persistence"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking Kafka PVCs")
    result = verify_kafka_persistence(host)

    if result["success"]:
        pvc_info = ", ".join(
            f"{p['name']}={p['capacity']}" for p in result["pvcs"]
        )
        tl.passed(
            LOG_MSGS["pvc_size_match"].format(size=pvc_info),
            f"PVCs found: {len(result['pvcs'])}",
        )
    else:
        tl.failed(LOG_MSGS["pvc_size_mismatch"], result.get("error", "No PVCs found"))

    assert result["success"], ASSERT_MSGS["pvc_size_mismatch"].format(
        component="Kafka",
        expected="1+",
        actual="0",
    )
