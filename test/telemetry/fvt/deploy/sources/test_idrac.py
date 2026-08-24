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

iDRAC Architecture:
    The iDRAC telemetry StatefulSet is scaled based on bmc_group_data.csv.
    Each pod runs 5 containers: receiver, kafka-pump, victoria-pump,
    mysqldb, and activemq.

    Data pipeline:
        iDRAC BMC (SSE) -> Receiver -> MySQL -> VictoriaPump -> VictoriaMetrics
                                     -> KafkaPump -> Kafka topic 'idrac'

Test cases:
    TC_SR_001: Verify iDRAC pod count matches bmc_group_data.csv
    TC_SR_002: Verify iDRAC StatefulSet pods ready
    TC_SR_003: Verify all iDRAC containers running
    TC_SR_004: Verify MySQL data in iDRAC telemetry pods
    TC_SR_005: Verify iDRAC receiver is collecting metrics
    TC_SR_006: Verify iDRAC Kafka topic exists
    TC_SR_007: Verify iDRAC VictoriaPump metrics endpoint
    TC_SR_008: Verify iDRAC telemetry service exists
    TC_SR_009: Verify iDRAC telemetry data in VictoriaMetrics
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
from library.functions.idrac_func import (
    verify_idrac_pod_count,
    verify_mysql_data_in_pods,
    verify_receiver_collecting,
)


def _skip_if_idrac_disabled(host):
    """Skip test if iDRAC source is not enabled or not deployed."""
    if not is_source_enabled(host, "idrac"):
        pytest.skip("iDRAC source not enabled in config")
    result = verify_sts_ready(host, IDRAC_STS_NAME)
    if result.get("not_found"):
        pytest.skip("iDRAC StatefulSet not found (no BMC inventory configured)")


# =========================================================================
# TC_SR_001: Verify iDRAC pod count matches bmc_group_data.csv
# =========================================================================

@pytest.mark.source
@pytest.mark.sanity
@pytest.mark.order(40)
def test_idrac_pod_count(host):
    """TC_SR_001: Verify iDRAC pod count matches bmc_group_data.csv."""
    _skip_if_idrac_disabled(host)
    tc = TC["idrac_pod_count"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Reading bmc_group_data.csv for expected pod count")
    result = verify_idrac_pod_count(host)

    if result.get("skip"):
        tl.skipped(result["skip_reason"], "")
        pytest.skip(result["skip_reason"])

    details_lines = [
        f"BMC entries      : {result.get('bmc_entries', 0)}",
        f"Parent nodes     : {len(result.get('parents', []))}",
        f"Expected pods    : {result['expected_count']}"
        f" ({len(result.get('parents', []))} parents + 1 MGMT)",
        f"Actual pods      : {result['actual_count']}",
    ]
    if result.get("pods"):
        details_lines.append("")
        for pod in result["pods"]:
            details_lines.append(f"  {pod}")
    details = "\n".join(details_lines)

    if result["success"]:
        tl.passed(
            LOG_MSGS["idrac_pod_count_match"].format(
                expected=result["expected_count"],
            ),
            details,
        )
    else:
        tl.failed(
            LOG_MSGS["idrac_pod_count_mismatch"],
            details,
        )

    assert result["success"], ASSERT_MSGS["idrac_pod_count_mismatch"].format(
        expected=result["expected_count"],
        actual=result["actual_count"],
    )


# =========================================================================
# TC_SR_002: Verify iDRAC StatefulSet pods ready
# =========================================================================

@pytest.mark.source
@pytest.mark.sanity
@pytest.mark.order(41)
def test_idrac_sts_ready(host):
    """TC_SR_002: Verify iDRAC StatefulSet pods ready."""
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


# =========================================================================
# TC_SR_003: Verify all iDRAC containers running
# =========================================================================

@pytest.mark.source
@pytest.mark.sanity
@pytest.mark.order(42)
def test_idrac_containers(host):
    """TC_SR_003: Verify all iDRAC containers running."""
    _skip_if_idrac_disabled(host)
    tc = TC["idrac_containers"]
    tl = TestLogger(tc["title"], tc["id"])

    # Find all iDRAC pods and check containers in each
    tl.check("Finding iDRAC pods")
    pods_result = verify_pods_by_prefix(host, IDRAC_POD_PREFIX, min_count=1)
    if not pods_result["success"] or not pods_result["pods"]:
        tl.failed(
            LOG_MSGS["pods_not_running"].format(
                component="iDRAC", running=0, expected=1,
            ),
            "",
        )
        pytest.fail("No iDRAC pods found")

    all_details = []
    all_ok = True

    for pod_info in pods_result["pods"]:
        pod_name = pod_info["name"]
        tl.check(f"Checking containers in pod {pod_name}")
        result = verify_pod_containers(host, pod_name)

        pod_lines = [f"Pod: {pod_name}"]
        for c in result["containers"]:
            icon = "\u2713" if c["ready"] else "\u2717"
            status = "Ready" if c["ready"] else c.get("state", "NotReady")
            pod_lines.append(f"  {icon} {c['name']}: {status}")
        all_details.extend(pod_lines)
        all_details.append("")

        if not result["success"]:
            all_ok = False

    details = "\n".join(all_details).rstrip()

    if all_ok:
        tl.passed(
            LOG_MSGS["containers_ready"].format(
                pod=f"{len(pods_result['pods'])} pod(s)",
                count="all",
            ),
            details,
        )
    else:
        tl.failed(
            LOG_MSGS["containers_not_ready"].format(
                pod=f"{len(pods_result['pods'])} pod(s)",
                not_ready="see details",
            ),
            details,
        )

    assert all_ok, ASSERT_MSGS["containers_not_ready"].format(
        not_ready="containers not ready in one or more pods",
        pod="iDRAC",
    )


# =========================================================================
# TC_SR_004: Verify MySQL data in iDRAC telemetry pods
# =========================================================================

@pytest.mark.source
@pytest.mark.functional
@pytest.mark.order(43)
def test_idrac_mysql_data(host):
    """TC_SR_004: Verify MySQL data in iDRAC telemetry pods."""
    _skip_if_idrac_disabled(host)
    tc = TC["idrac_mysql_data"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Querying MySQL services table in each iDRAC pod")
    result = verify_mysql_data_in_pods(host)

    if result.get("error") and not result.get("pod_results"):
        tl.failed(result["error"], "")
        pytest.fail(result["error"])

    details_lines = []
    pods_missing = 0
    for pr in result.get("pod_results", []):
        icon = "\u2713" if pr["has_data"] else "\u2717"
        details_lines.append(
            f"  {icon} {pr['pod_name']}: {pr['ip_count']} IP(s) in MySQL"
        )
        if pr["mysql_ips"]:
            for ip in pr["mysql_ips"][:5]:
                details_lines.append(f"      - {ip}")
            if len(pr["mysql_ips"]) > 5:
                details_lines.append(
                    f"      ... and {len(pr['mysql_ips']) - 5} more"
                )
        if not pr["has_data"]:
            pods_missing += 1
    details = "\n".join(details_lines)

    if result["success"]:
        tl.passed(
            LOG_MSGS["idrac_mysql_verified"].format(
                count=result.get("total_pods", 0),
            ),
            details,
        )
    else:
        tl.failed(
            LOG_MSGS["idrac_mysql_missing"].format(count=pods_missing),
            details,
        )

    assert result["success"], ASSERT_MSGS["idrac_mysql_missing"].format(
        count=pods_missing,
    )


# =========================================================================
# TC_SR_005: Verify iDRAC receiver is collecting metrics
# =========================================================================

@pytest.mark.source
@pytest.mark.functional
@pytest.mark.order(44)
def test_idrac_receiver_collecting(host):
    """TC_SR_005: Verify iDRAC receiver is collecting metrics."""
    _skip_if_idrac_disabled(host)
    tc = TC["idrac_receiver_collecting"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking iDRAC receiver container logs for metric reports")
    result = verify_receiver_collecting(host)

    details_lines = []
    not_collecting = 0
    for pr in result.get("pod_results", []):
        icon = "\u2713" if pr["collecting"] else "\u2717"
        details_lines.append(
            f"  {icon} {pr['pod_name']}: {pr['report_count']} report(s)"
        )
        if pr["sample_reports"]:
            for report in pr["sample_reports"]:
                details_lines.append(f"      - {report}")
        if pr["service_tags"]:
            details_lines.append(
                f"      ServiceTags: {', '.join(pr['service_tags'])}"
            )
        if not pr["collecting"]:
            not_collecting += 1
    details = "\n".join(details_lines)

    if result["success"]:
        tl.passed(
            LOG_MSGS["idrac_receiver_collecting"].format(
                count=result.get("total_pods", 0),
            ),
            details,
        )
    else:
        tl.failed(
            LOG_MSGS["idrac_receiver_not_collecting"].format(
                count=not_collecting,
            ),
            details,
        )

    assert result["success"], ASSERT_MSGS["idrac_receiver_not_collecting"].format(
        count=not_collecting,
    )


# =========================================================================
# TC_SR_006: Verify iDRAC Kafka topic exists
# =========================================================================

@pytest.mark.source
@pytest.mark.sanity
@pytest.mark.order(45)
def test_idrac_kafka_topic(host):
    """TC_SR_006: Verify iDRAC Kafka topic exists."""
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


# =========================================================================
# TC_SR_007: Verify iDRAC VictoriaPump container
# =========================================================================

@pytest.mark.source
@pytest.mark.sanity
@pytest.mark.order(46)
def test_idrac_victoria_pump(host):
    """TC_SR_007: Verify iDRAC VictoriaPump container is running."""
    _skip_if_idrac_disabled(host)
    tc = TC["idrac_victoria_pump"]
    tl = TestLogger(tc["title"], tc["id"])

    pods_result = verify_pods_by_prefix(host, IDRAC_POD_PREFIX, min_count=1)
    if not pods_result["success"] or not pods_result["pods"]:
        tl.failed(
            LOG_MSGS["pods_not_running"].format(
                component="iDRAC", running=0, expected=1,
            ),
            "",
        )
        pytest.fail("No iDRAC pods found")

    # Check victoria-pump in all pods
    details_lines = []
    all_ready = True
    for pod_info in pods_result["pods"]:
        pod_name = pod_info["name"]
        cmd = CMDS["victoriapump_container_running"].format(
            namespace=TELEMETRY_NAMESPACE, pod_name=pod_name,
        )
        result = run_on_kube_vip(host, cmd)
        is_ready = result.rc == 0 and result.stdout.strip().lower() == "true"
        icon = "\u2713" if is_ready else "\u2717"
        details_lines.append(
            f"  {icon} {pod_name}: {'Ready' if is_ready else result.stdout.strip()}"
        )
        if not is_ready:
            all_ready = False

    details = "\n".join(details_lines)

    if all_ready:
        tl.passed(
            LOG_MSGS["health_ok"].format(component="iDRAC VictoriaPump"),
            details,
        )
    else:
        tl.failed(
            LOG_MSGS["health_failed"].format(component="iDRAC VictoriaPump"),
            details,
        )

    assert all_ready, ASSERT_MSGS["pods_not_running"].format(
        component="iDRAC VictoriaPump container",
        expected="ready",
        running="not ready in some pods",
    )


# =========================================================================
# TC_SR_008: Verify iDRAC telemetry service exists
# =========================================================================

@pytest.mark.source
@pytest.mark.sanity
@pytest.mark.order(47)
def test_idrac_service(host):
    """TC_SR_008: Verify iDRAC telemetry service exists."""
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


# =========================================================================
# TC_SR_009: Verify iDRAC telemetry data in VictoriaMetrics
# =========================================================================

def _build_service_tag_lines(tag_result):
    """Build detail lines for a single service tag result."""
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
@pytest.mark.order(48)
def test_idrac_vm_data(host):
    """TC_SR_009: Verify iDRAC telemetry data in VictoriaMetrics."""
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
