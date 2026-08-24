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

    Data pipeline:
        OME -> Kafka (DataForwardingService) -> Vector-OME -> VictoriaMetrics

Test cases:
    TC_SR_050: Verify Vector-OME bridge deployment ready
    TC_SR_051: Verify OME KafkaUser CR exists
    TC_SR_052: Verify OME Kafka forwarder connectivity status
"""

import pytest

from library.functions import TestLogger, load_test_config, load_test_credentials
from library.vars.test_case_vars import TEST_CASES as TC
from library.vars.common_vars import (
    VECTOR_OME_APP_NAME,
    OME_KAFKA_USER,
    TELEMETRY_NAMESPACE,
    CMDS,
)
from library.messages.telemetry_msgs import (
    TEST_LOG_MSGS as LOG_MSGS,
    TEST_ASSERT_MSGS as ASSERT_MSGS,
)
from library.functions.k8s_func import verify_deploy_ready
from library.functions.telemetry_func import (
    is_source_enabled,
    run_on_kube_vip,
)
from library.functions import verify_ome_kafka_connectivity


def _skip_if_ome_disabled(host):
    """Skip test if OME source is not enabled."""
    if not is_source_enabled(host, "ome"):
        pytest.skip("OME source not enabled in config")


# =========================================================================
# TC_SR_050: Verify Vector-OME bridge deployment ready
# =========================================================================

@pytest.mark.source
@pytest.mark.sanity
@pytest.mark.order(60)
def test_ome_vector_bridge(host):
    """TC_SR_050: Verify Vector-OME bridge deployment ready."""
    _skip_if_ome_disabled(host)
    tc = TC["ome_vector_bridge"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying Vector-OME bridge deployment")
    result = verify_deploy_ready(host, VECTOR_OME_APP_NAME)

    if result["success"]:
        tl.passed(
            LOG_MSGS["pods_running"].format(
                component="Vector-OME bridge",
                count=result["ready_replicas"],
                expected=result["expected"],
            ),
            f"\u2713 Ready: {result['ready_replicas']}/{result['expected']}",
        )
    else:
        tl.failed(
            LOG_MSGS["pods_not_running"].format(
                component="Vector-OME bridge",
                running=result["ready_replicas"],
                expected=result["expected"],
            ),
            f"\u2717 Ready: {result['ready_replicas']}/{result['expected']}",
        )

    assert result["success"], ASSERT_MSGS["pods_not_running"].format(
        component="Vector-OME bridge",
        expected=result["expected"],
        running=result["ready_replicas"],
    )


# =========================================================================
# TC_SR_051: Verify OME KafkaUser CR exists
# =========================================================================

@pytest.mark.source
@pytest.mark.sanity
@pytest.mark.order(61)
def test_ome_kafka_user(host):
    """TC_SR_051: Verify OME KafkaUser CR exists."""
    _skip_if_ome_disabled(host)
    tc = TC["ome_kafka_user"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check(f"Checking KafkaUser '{OME_KAFKA_USER}'")
    cmd = CMDS["kubectl_get_kafkauser"].format(
        name=OME_KAFKA_USER, namespace=TELEMETRY_NAMESPACE,
    )
    result = run_on_kube_vip(host, cmd)
    exists = result.rc == 0 and "exists" in result.stdout

    if exists:
        tl.passed(
            LOG_MSGS["health_ok"].format(component="OME KafkaUser"),
            f"\u2713 KafkaUser '{OME_KAFKA_USER}': exists",
        )
    else:
        tl.failed(
            LOG_MSGS["health_failed"].format(component="OME KafkaUser"),
            f"\u2717 KafkaUser '{OME_KAFKA_USER}': MISSING",
        )

    assert exists, ASSERT_MSGS["service_missing"].format(
        service=OME_KAFKA_USER,
        namespace=TELEMETRY_NAMESPACE,
    )


# =========================================================================
# TC_SR_052: Verify OME Kafka forwarder connectivity status
# =========================================================================

@pytest.mark.source
@pytest.mark.functional
@pytest.mark.order(62)
def test_ome_kafka_connectivity(host):
    """TC_SR_052: Verify OME Kafka forwarder connectivity status.

    Uses the OME REST API:
    GET /api/DataForwardingService/Forwarders({id})/ConnectivityStatus
    to verify the Kafka forwarder is connected.
    """
    _skip_if_ome_disabled(host)
    tc = TC["ome_kafka_connectivity"]
    tl = TestLogger(tc["title"], tc["id"])

    # Get OME IP from test_config.yml (user-provided)
    test_cfg = load_test_config()
    ome_ip = test_cfg.get("ome_ip", "")
    if not ome_ip:
        tl.skipped(
            "OME IP not configured in test_config.yml",
            "Test skipped - set ome_ip in test_config.yml",
        )
        pytest.skip("OME IP not configured in test_config.yml")

    # Get OME credentials from test_creds.yml
    try:
        creds = load_test_credentials()
        ome_user = creds.get("ome_user", "admin")
        ome_password = creds.get("ome_password", "")
    except Exception:
        ome_user = "admin"
        ome_password = ""

    if not ome_password:
        tl.skipped(
            "OME credentials not configured in test_creds.yml",
            "Test skipped - set ome_user/ome_password in test_creds.yml",
        )
        pytest.skip("OME credentials not configured in test_creds.yml")

    tl.check(f"Checking OME Kafka forwarder connectivity at {ome_ip}")
    result = verify_ome_kafka_connectivity(host, ome_ip, ome_user, ome_password)

    # Build details
    status_icon = "\u2713" if result["success"] else "\u2717"
    details_lines = [
        f"{status_icon} Kafka connectivity: {result.get('status')}",
        f"OME endpoint: https://{ome_ip}",
        f"Forwarder: {result.get('forwarder_name', 'N/A')}",
        f"Enabled: {result.get('forwarder_enabled', 'N/A')}",
        f"Status: {result.get('status', 'Unknown')}",
    ]
    time_connected = result.get("time_last_connected", "")
    if time_connected:
        details_lines.append(f"Last connected: {time_connected}")
    if result.get("error"):
        details_lines.append(f"Error: {result['error']}")
    details = "\n".join(details_lines)

    if result["success"]:
        tl.passed(
            LOG_MSGS["ome_kafka_connected"].format(
                name=result.get("forwarder_name", ""),
            ),
            details,
        )
    else:
        tl.failed(
            LOG_MSGS["ome_kafka_disconnected"].format(
                status=result.get("status", "Unknown"),
            ),
            details,
        )

    assert result["success"], ASSERT_MSGS["ome_kafka_not_connected"].format(
        status=result.get("status", "Unknown"),
    )
