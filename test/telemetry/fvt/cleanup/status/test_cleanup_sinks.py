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
Telemetry Cleanup — Sink Cleanup Verification Tests.

Verifies that shared sink infrastructure (Kafka, VictoriaMetrics,
VictoriaLogs) has been removed after a full cleanup.

Note: Sinks are shared infrastructure and are ONLY cleaned when
``--tags cleanup`` (full cleanup) is used, never individually.

Test cases:
    TC_CL_002: Verify cleanup_kafka removes Kafka resources
    TC_CL_003: Verify cleanup_victoria_metrics removes VM resources
    TC_CL_004: Verify cleanup_victoria_logs removes VL resources
"""

import pytest

from omnia_auto import TestLogger

from library.vars.test_case_vars import TEST_CASES as TC
from library.messages.telemetry_msgs import (
    TEST_LOG_MSGS as LOG_MSGS,
    TEST_ASSERT_MSGS as ASSERT_MSGS,
)
from library.functions.cleanup_func import (
    verify_kafka_cleaned,
    verify_victoria_metrics_cleaned,
    verify_victoria_logs_cleaned,
)


@pytest.mark.functional
@pytest.mark.sink
@pytest.mark.order(58)
def test_cleanup_kafka(host):
    """TC_CL_002: Verify Kafka resources removed after full cleanup.

    Checks that Kafka brokers, controllers, bridge, and Strimzi operator
    pods have been removed from the telemetry namespace.
    """
    tc = TC["cleanup_kafka"]
    tl = TestLogger(tc["title"], tc["id"])

    result = verify_kafka_cleaned(host)

    if result["success"]:
        tl.passed(LOG_MSGS["kafka_cleaned"], result["details"])
    else:
        tl.failed(LOG_MSGS["kafka_not_cleaned"], result["details"])

    assert result["success"], ASSERT_MSGS["kafka_not_cleaned"]


@pytest.mark.functional
@pytest.mark.sink
@pytest.mark.order(59)
def test_cleanup_victoria_metrics(host):
    """TC_CL_003: Verify VictoriaMetrics resources removed after full cleanup.

    Checks that vmstorage, vminsert, vmselect, vmagent, and the
    victoria-metrics-operator pods have been removed.
    """
    tc = TC["cleanup_victoria_metrics"]
    tl = TestLogger(tc["title"], tc["id"])

    result = verify_victoria_metrics_cleaned(host)

    if result["success"]:
        tl.passed(LOG_MSGS["vm_cleaned"], result["details"])
    else:
        tl.failed(LOG_MSGS["vm_not_cleaned"], result["details"])

    assert result["success"], ASSERT_MSGS["vm_not_cleaned"]


@pytest.mark.functional
@pytest.mark.sink
@pytest.mark.order(60)
def test_cleanup_victoria_logs(host):
    """TC_CL_004: Verify VictoriaLogs resources removed after full cleanup.

    Checks that vlstorage, vlinsert, vlselect, and vlagent pods have
    been removed from the telemetry namespace.
    """
    tc = TC["cleanup_victoria_logs"]
    tl = TestLogger(tc["title"], tc["id"])

    result = verify_victoria_logs_cleaned(host)

    if result["success"]:
        tl.passed(LOG_MSGS["vl_cleaned"], result["details"])
    else:
        tl.failed(LOG_MSGS["vl_not_cleaned"], result["details"])

    assert result["success"], ASSERT_MSGS["vl_not_cleaned"]
