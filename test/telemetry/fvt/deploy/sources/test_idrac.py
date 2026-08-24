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
    TC_SR_003: Verify iDRAC Kafka topic exists
    TC_SR_004: Verify iDRAC VictoriaPump metrics endpoint
    TC_SR_005: Verify iDRAC telemetry service exists
    TC_SR_020: Verify iDRAC telemetry data in VictoriaMetrics
"""

from datetime import datetime

import pytest

from library.functions import TestLogger
from library.vars.test_case_vars import TEST_CASES as TC
from library.vars.common_vars import (
    IDRAC_STS_NAME,
    IDRAC_SERVICE_NAME,
    IDRAC_KAFKA_TOPIC,
    IDRAC_POD_PREFIX,
    TELEMETRY_NAMESPACE,
    CMDS,
)
from library.messages.telemetry_msgs import (
    TEST_LOG_MSGS as LOG_MSGS,
    TEST_ASSERT_MSGS as ASSERT_MSGS,
)
from library.functions.k8s_func import (
    verify_sts_ready,
    verify_pod_containers,
    verify_kafka_topic_ready,
    verify_services_exist,
    verify_pods_by_prefix,
)
from library.functions.telemetry_func import (
    is_source_enabled,
    run_on_kube_vip,
    verify_idrac_vm_data,
    get_idrac_service_tags,
)


def _skip_if_idrac_disabled(host):
    """Skip test if iDRAC source is not enabled or not deployed."""
    if not is_source_enabled(host, "idrac"):
        pytest.skip("iDRAC source not enabled in config")
    # Also skip if the StatefulSet doesn't exist (no BMC inventory)
    result = verify_sts_ready(host, IDRAC_STS_NAME)
    if result.get("not_found"):
        pytest.skip("iDRAC StatefulSet not found (no BMC inventory configured)")


@pytest.mark.source
@pytest.mark.sanity
@pytest.mark.order(40)
def test_idrac_sts_ready(host):
    """TC_SR_001: Verify iDRAC StatefulSet pods ready."""
    _skip_if_idrac_disabled(host)
    tc = TC["idrac_sts_ready"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying iDRAC telemetry StatefulSet")
    result = verify_sts_ready(host, IDRAC_STS_NAME)

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
        expected=result["expected"],
        running=result["ready_replicas"],
    )


@pytest.mark.source
@pytest.mark.sanity
@pytest.mark.order(41)
def test_idrac_containers(host):
    """TC_SR_002: Verify all iDRAC containers running."""
    _skip_if_idrac_disabled(host)
    tc = TC["idrac_containers"]
    tl = TestLogger(tc["title"], tc["id"])

    # Find iDRAC pod name first
    tl.check("Finding iDRAC pod")
    pods_result = verify_pods_by_prefix(host, IDRAC_POD_PREFIX, min_count=1)
    if not pods_result["success"] or not pods_result["pods"]:
        tl.failed(
            LOG_MSGS["pods_not_running"].format(
                component="iDRAC", running=0, expected=1,
            ),
            "",
        )
        pytest.fail("No iDRAC pods found")

    pod_name = pods_result["pods"][0]["name"]
    tl.check(f"Checking containers in pod {pod_name}")
    result = verify_pod_containers(host, pod_name)

    # Build ✓/✗ detail lines for each container
    details_lines = []
    for c in result["containers"]:
        status = "\u2713" if c["ready"] else "\u2717"
        details_lines.append(
            f"{status} {c['name']}: {'Ready' if c['ready'] else c.get('state', 'NotReady')}"
        )
    details = "\n".join(details_lines)

    if result["success"]:
        tl.passed(
            LOG_MSGS["containers_ready"].format(
                pod=pod_name,
                count=len(result["containers"]),
            ),
            details,
        )
    else:
        tl.failed(
            LOG_MSGS["containers_not_ready"].format(
                pod=pod_name,
                not_ready=", ".join(result["not_ready"]),
            ),
            details,
        )

    assert result["success"], ASSERT_MSGS["containers_not_ready"].format(
        not_ready=", ".join(result["not_ready"]),
        pod=pod_name,
    )


@pytest.mark.source
@pytest.mark.sanity
@pytest.mark.order(42)
def test_idrac_kafka_topic(host):
    """TC_SR_003: Verify iDRAC Kafka topic exists."""
    _skip_if_idrac_disabled(host)
    tc = TC["idrac_kafka_topic"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check(f"Checking Kafka topic '{IDRAC_KAFKA_TOPIC}'")
    result = verify_kafka_topic_ready(host, IDRAC_KAFKA_TOPIC)

    if result["success"]:
        tl.passed(
            LOG_MSGS["topic_exists"].format(topic=IDRAC_KAFKA_TOPIC),
            f"Status: {result['status']}",
        )
    else:
        tl.failed(
            LOG_MSGS["topic_missing"].format(topic=IDRAC_KAFKA_TOPIC),
            "",
        )

    assert result["success"], ASSERT_MSGS["topic_missing"].format(
        topic=IDRAC_KAFKA_TOPIC,
    )


@pytest.mark.source
@pytest.mark.sanity
@pytest.mark.order(43)
def test_idrac_victoria_pump(host):
    """TC_SR_004: Verify iDRAC VictoriaPump container is running."""
    _skip_if_idrac_disabled(host)
    tc = TC["idrac_victoria_pump"]
    tl = TestLogger(tc["title"], tc["id"])

    # Find iDRAC pod
    pods_result = verify_pods_by_prefix(host, IDRAC_POD_PREFIX, min_count=1)
    if not pods_result["success"] or not pods_result["pods"]:
        tl.failed(
            LOG_MSGS["pods_not_running"].format(
                component="iDRAC", running=0, expected=1,
            ),
            "",
        )
        pytest.fail("No iDRAC pods found")

    pod_name = pods_result["pods"][0]["name"]
    tl.check(f"Checking VictoriaPump container in {pod_name}")
    cmd = CMDS["victoriapump_container_running"].format(
        namespace=TELEMETRY_NAMESPACE, pod_name=pod_name,
    )
    result = run_on_kube_vip(host, cmd)
    is_ready = result.rc == 0 and result.stdout.strip().lower() == "true"

    if is_ready:
        tl.passed(
            LOG_MSGS["health_ok"].format(component="iDRAC VictoriaPump"),
            "\u2713 victoria-pump: Ready",
        )
    else:
        tl.failed(
            LOG_MSGS["health_failed"].format(component="iDRAC VictoriaPump"),
            f"\u2717 victoria-pump: {result.stdout.strip()}",
        )

    assert is_ready, ASSERT_MSGS["pods_not_running"].format(
        component="iDRAC VictoriaPump container",
        expected="ready",
        running=result.stdout.strip(),
    )


@pytest.mark.source
@pytest.mark.sanity
@pytest.mark.order(44)
def test_idrac_service(host):
    """TC_SR_005: Verify iDRAC telemetry service exists."""
    _skip_if_idrac_disabled(host)
    tc = TC["idrac_service"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check(f"Checking service '{IDRAC_SERVICE_NAME}'")
    result = verify_services_exist(host, [IDRAC_SERVICE_NAME])

    if result["success"]:
        tl.passed(
            LOG_MSGS["services_ok"].format(component="iDRAC"),
            f"\u2713 Service '{IDRAC_SERVICE_NAME}': exists",
        )
    else:
        tl.failed(
            LOG_MSGS["services_missing"].format(component="iDRAC"),
            f"\u2717 Service '{IDRAC_SERVICE_NAME}': MISSING",
        )

    assert result["success"], ASSERT_MSGS["service_missing"].format(
        service=IDRAC_SERVICE_NAME,
        namespace=TELEMETRY_NAMESPACE,
    )


def _build_service_tag_lines(tag_result):
    """Build ✓/✗ detail lines for a single service tag result."""
    lines = []
    stag = tag_result["service_tag"]
    if tag_result["found"]:
        lines.append(f"  \u2713 {stag}")
        lines.append(f"      Metrics     : {tag_result['metric_count']} found")
        latest_ts = tag_result.get("latest_timestamp", 0)
        if latest_ts:
            try:
                human_ts = datetime.fromtimestamp(
                    int(latest_ts)
                ).strftime("%Y-%m-%d %H:%M:%S")
                lines.append(f"      VM Time     : {latest_ts} ({human_ts})")
            except (ValueError, OSError):
                lines.append(f"      VM Time     : {latest_ts}")
        for sample in tag_result.get("sample_metrics", []):
            lines.append(f"        - {sample['metric_name']}: {sample['value']}")
    else:
        lines.append(f"  \u2717 {stag}: NO DATA FOUND")
    return lines


@pytest.mark.source
@pytest.mark.functional
@pytest.mark.order(45)
def test_idrac_vm_data(host):
    """TC_SR_020: Verify iDRAC telemetry data in VictoriaMetrics."""
    _skip_if_idrac_disabled(host)
    tc = TC["idrac_vm_data"]
    tl = TestLogger(tc["title"], tc["id"])

    # Get activated service tags
    tl.check("Discovering activated iDRAC service tags")
    service_tags = get_idrac_service_tags(host)
    if not service_tags:
        tl.skipped(
            "No activated iDRAC service tags found",
            "Test skipped - no telemetry activation to verify",
        )
        pytest.skip("No activated iDRAC service tags found")

    tl.check(f"Querying VictoriaMetrics for {len(service_tags)} service tag(s)")
    result = verify_idrac_vm_data(host, service_tags)

    if result.get("error") and not result.get("service_tag_results"):
        tl.failed("Failed to verify iDRAC data", result["error"])
        pytest.fail(result["error"])

    # Build details
    details_lines = [
        f"VictoriaMetrics: http://{result.get('vmselect_ip')}:{result.get('vmselect_port')}",
        f"Activated service tags: {service_tags}",
        "",
        "Service tag verification:",
    ]
    for tag_result in result.get("service_tag_results", []):
        details_lines.extend(_build_service_tag_lines(tag_result))

    details = "\n".join(details_lines)

    if result["success"]:
        tl.passed(
            LOG_MSGS["idrac_vm_data_found"].format(
                count=len(result["found_tags"]),
            ),
            details,
        )
    else:
        tl.failed(
            LOG_MSGS["idrac_vm_data_missing"].format(
                count=len(result["missing_tags"]),
            ),
            details,
        )

    assert result["success"], ASSERT_MSGS["idrac_vm_data_missing"].format(
        missing=result["missing_tags"],
    )
