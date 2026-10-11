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
Telemetry Deploy Sinks --- Post-Deploy Verification.

Verifies that sink infrastructure (Kafka, VictoriaMetrics, VictoriaLogs)
is running after ``deploy_sinks``.  Mirrors the tests in
``fvt/deploy/sinks/`` so that ``./run_validation.sh fvt_telemetry
deploy_sinks verify`` provides the same checks.

When ``deploy_sinks_enabled`` is configured in ``test_config.yml``,
verify tests for non-selected sinks are skipped.

Test cases:
    TEL_FVT_DEPLOY_V001: Verify Kafka broker/controller pods running
    TEL_FVT_DEPLOY_V002: Verify Kafka cluster Ready condition
    TEL_FVT_DEPLOY_V003: Verify Kafka bridge pod running
    TEL_FVT_DEPLOY_V004: Verify VictoriaMetrics cluster pods running
    TEL_FVT_DEPLOY_V005: Verify VMAgent pods running
    TEL_FVT_DEPLOY_V006: Verify VictoriaLogs cluster pods running
    TEL_FVT_DEPLOY_V007: Verify VLAgent pods running
"""

import pytest

from library.functions import TestLogger
from library.functions.telemetry_func import is_sink_enabled
from library.vars.test_case_vars import TEST_CASES as TC
from library.vars.common_vars import (
    KAFKA_POD_PREFIXES,
    KAFKA_BRIDGE_PREFIX,
    VM_POD_PREFIXES,
    VMAGENT_POD_PREFIX,
    VL_POD_PREFIXES,
    VLAGENT_POD_PREFIX,
)
from library.messages.telemetry_msgs import (
    TEST_LOG_MSGS as LOG_MSGS,
    TEST_ASSERT_MSGS as ASSERT_MSGS,
)
from library.functions.k8s_func import (
    verify_pods_by_prefix,
    verify_pods_by_prefix_with_retry,
    verify_kafka_ready,
)
from library.functions.cleanup_func import (
    deploy_sinks_enabled,
    is_sink_selected,
)


# -- Kafka -------------------------------------------------------------------

@pytest.mark.sink
@pytest.mark.sanity
@pytest.mark.order(10)
def test_kafka_pods(host):
    """TEL_FVT_DEPLOY_V001: Verify Kafka broker/controller pods running."""
    tc = TC["kafka_pods"]
    tl = TestLogger(tc["title"], tc["id"])

    if not is_sink_selected("kafka", deploy_sinks_enabled()):
        tl.skipped("Kafka not in deploy_sinks_enabled configuration")
        pytest.skip("Kafka not in deploy_sinks_enabled")

    all_ok = True
    for role, prefix in KAFKA_POD_PREFIXES.items():
        tl.check(f"Checking Kafka {role} pods (prefix: {prefix})")
        result = verify_pods_by_prefix(host, prefix, min_count=1)

        pod_count = result["running_count"]
        if result["success"]:
            tl.passed(
                LOG_MSGS["pods_running"].format(
                    component=f"Kafka {role}",
                    count=pod_count,
                    expected=pod_count,
                ),
                f"Running: {pod_count}",
            )
        else:
            tl.failed(
                LOG_MSGS["pods_not_running"].format(
                    component=f"Kafka {role}",
                    running=pod_count,
                    expected=result["total_count"],
                ),
                "",
            )
            all_ok = False

    assert all_ok, ASSERT_MSGS["pods_not_running"].format(
        component="Kafka broker/controller",
        expected=">=1",
        running=0,
    )


@pytest.mark.sink
@pytest.mark.sanity
@pytest.mark.order(11)
def test_kafka_ready(host):
    """TEL_FVT_DEPLOY_V002: Verify Kafka cluster Ready condition."""
    tc = TC["kafka_ready"]
    tl = TestLogger(tc["title"], tc["id"])

    if not is_sink_selected("kafka", deploy_sinks_enabled()):
        tl.skipped("Kafka not in deploy_sinks_enabled configuration")
        pytest.skip("Kafka not in deploy_sinks_enabled")

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
    """TEL_FVT_DEPLOY_V003: Verify Kafka bridge pod running."""
    tc = TC["kafka_bridge"]
    tl = TestLogger(tc["title"], tc["id"])

    if not is_sink_selected("kafka", deploy_sinks_enabled()):
        tl.skipped("Kafka not in deploy_sinks_enabled configuration")
        pytest.skip("Kafka not in deploy_sinks_enabled")

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


# -- VictoriaMetrics ---------------------------------------------------------

@pytest.mark.sink
@pytest.mark.sanity
@pytest.mark.order(20)
def test_vm_cluster_pods(host):
    """TEL_FVT_DEPLOY_V004: Verify VictoriaMetrics cluster pods running."""
    tc = TC["vm_cluster_pods"]
    tl = TestLogger(tc["title"], tc["id"])

    if not is_sink_selected("victoria_metrics", deploy_sinks_enabled()):
        tl.skipped("VictoriaMetrics not in deploy_sinks_enabled configuration")
        pytest.skip("VictoriaMetrics not in deploy_sinks_enabled")

    if not is_sink_enabled(host, "victoria_metrics"):
        tl.skipped("VictoriaMetrics sink is not enabled in telemetry configuration")
        pytest.skip("VictoriaMetrics sink is not enabled")

    all_ok = True
    for role, prefix in VM_POD_PREFIXES.items():
        tl.check(f"Checking VM {role} pods (prefix: {prefix})")
        result = verify_pods_by_prefix_with_retry(host, prefix, min_count=1)

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
    """TEL_FVT_DEPLOY_V005: Verify VMAgent pods running."""
    tc = TC["vmagent_pods"]
    tl = TestLogger(tc["title"], tc["id"])

    if not is_sink_selected("victoria_metrics", deploy_sinks_enabled()):
        tl.skipped("VictoriaMetrics not in deploy_sinks_enabled configuration")
        pytest.skip("VictoriaMetrics not in deploy_sinks_enabled")

    if not is_sink_enabled(host, "victoria_metrics"):
        tl.skipped("VictoriaMetrics sink is not enabled in telemetry configuration")
        pytest.skip("VictoriaMetrics sink is not enabled")

    tl.check(f"Checking VMAgent pods (prefix: {VMAGENT_POD_PREFIX})")
    result = verify_pods_by_prefix_with_retry(host, VMAGENT_POD_PREFIX, min_count=1)

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


# -- VictoriaLogs -----------------------------------------------------------

@pytest.mark.sink
@pytest.mark.sanity
@pytest.mark.order(25)
def test_vl_cluster_pods(host):
    """TEL_FVT_DEPLOY_V006: Verify VictoriaLogs cluster pods running."""
    tc = TC["vl_cluster_pods"]
    tl = TestLogger(tc["title"], tc["id"])

    if not is_sink_selected("victoria_logs", deploy_sinks_enabled()):
        tl.skipped("VictoriaLogs not in deploy_sinks_enabled configuration")
        pytest.skip("VictoriaLogs not in deploy_sinks_enabled")

    if not is_sink_enabled(host, "victoria_logs"):
        tl.skipped("VictoriaLogs sink is not enabled in telemetry configuration")
        pytest.skip("VictoriaLogs sink is not enabled")

    all_ok = True
    for role, prefix in VL_POD_PREFIXES.items():
        tl.check(f"Checking VL {role} pods (prefix: {prefix})")
        result = verify_pods_by_prefix_with_retry(host, prefix, min_count=1)

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
    """TEL_FVT_DEPLOY_V007: Verify VLAgent pods running."""
    tc = TC["vlagent_pods"]
    tl = TestLogger(tc["title"], tc["id"])

    if not is_sink_selected("victoria_logs", deploy_sinks_enabled()):
        tl.skipped("VictoriaLogs not in deploy_sinks_enabled configuration")
        pytest.skip("VictoriaLogs not in deploy_sinks_enabled")

    if not is_sink_enabled(host, "victoria_logs"):
        tl.skipped("VictoriaLogs sink is not enabled in telemetry configuration")
        pytest.skip("VictoriaLogs sink is not enabled")

    tl.check(f"Checking VLAgent pods (prefix: {VLAGENT_POD_PREFIX})")
    result = verify_pods_by_prefix_with_retry(host, VLAGENT_POD_PREFIX, min_count=1)

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
