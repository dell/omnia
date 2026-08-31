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
    TC_SR_024: Verify LDMS data in Kafka topic
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
@pytest.mark.ldms
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
@pytest.mark.ldms
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
@pytest.mark.ldms
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
                expected=result["ready_replicas"],  # Show actual count
            ),
            f"Ready: {result['ready_replicas']} replicas",
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
# TC_SR_023: Verify LDMS package installed on Slurm nodes
# =========================================================================

@pytest.mark.source
@pytest.mark.functional
@pytest.mark.ldms
@pytest.mark.order(53)
def test_ldms_package_installed(host):
    """TC_SR_023: Verify LDMS package installed on Slurm nodes.

    Checks that ovis-ldms package (ldmsd binary) is installed on all nodes
    in the LDMS functional groups.
    """
    from library.functions.ldms_func import verify_ldms_package_installed

    _skip_if_ldms_disabled(host)
    tc = TC["ldms_package_installed"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying LDMS package installed on Slurm nodes")
    result = verify_ldms_package_installed(host)

    if result.get("error") and result["total"] == 0:
        tl.skipped(result["error"])
        pytest.skip(result["error"])

    # Build details output by group
    details_lines = [
        f"Total nodes: {result['total']}",
        f"Installed: {result['installed']}",
        f"Not installed: {result['failed']}",
        "",
        "Package status per node (by group):",
    ]

    # Group results by functional group
    by_group = {}
    for nr in result.get("node_results", []):
        grp = nr.get("group", "unknown")
        if grp not in by_group:
            by_group[grp] = []
        by_group[grp].append(nr)

    for group, nodes in by_group.items():
        details_lines.append(f"  [{group}]")
        for nr in nodes:
            icon = "\u2713" if nr["installed"] else "\u2717"
            version = nr.get("version", "")
            if version:
                details_lines.append(f"    {icon} {nr['hostname']}: {version}")
            else:
                status = "installed" if nr["installed"] else "NOT INSTALLED"
                details_lines.append(f"    {icon} {nr['hostname']}: {status}")
            if nr.get("error"):
                details_lines.append(f"        Error: {nr['error']}")

    details = "\n".join(details_lines)

    if result["success"]:
        tl.passed(
            f"LDMS package installed on all {result['installed']} nodes",
            details,
        )
    else:
        tl.failed(
            f"LDMS package not installed on {result['failed']} nodes",
            details,
        )

    assert result["success"], f"LDMS package not installed on: {result['failed_nodes']}"


# =========================================================================
# TC_SR_024: Verify LDMS sampler service running on Slurm nodes
# =========================================================================

@pytest.mark.source
@pytest.mark.functional
@pytest.mark.ldms
@pytest.mark.order(54)
def test_ldms_sampler_service(host):
    """TC_SR_023: Verify LDMS sampler service running on Slurm nodes.

    Checks that ldmsd.sampler.service is active on all nodes in the
    LDMS functional groups (slurm_control_node, slurm_node, etc.).
    """
    from library.functions.ldms_func import verify_ldms_sampler_service

    _skip_if_ldms_disabled(host)
    tc = TC["ldms_sampler_service"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying LDMS sampler service on Slurm nodes")
    result = verify_ldms_sampler_service(host)

    if result.get("error") and result["total"] == 0:
        tl.skipped(result["error"])
        pytest.skip(result["error"])

    # Build details output by group
    details_lines = [
        f"Total nodes: {result['total']}",
        f"Running: {result['running']}",
        f"Failed: {result['failed']}",
        "",
        "Service status per node (by group):",
    ]

    # Group results by functional group
    by_group = {}
    for nr in result.get("node_results", []):
        grp = nr.get("group", "unknown")
        if grp not in by_group:
            by_group[grp] = []
        by_group[grp].append(nr)

    for group, nodes in by_group.items():
        details_lines.append(f"  [{group}]")
        for nr in nodes:
            icon = "\u2713" if nr["active"] else "\u2717"
            status = nr.get("status", "unknown")
            details_lines.append(f"    {icon} {nr['hostname']}: {status}")
            if nr.get("error"):
                details_lines.append(f"        Error: {nr['error']}")

    details = "\n".join(details_lines)

    if result["success"]:
        tl.passed(
            f"LDMS sampler service active on all {result['running']} nodes",
            details,
        )
    else:
        tl.failed(
            f"LDMS sampler service not running on {result['failed']} nodes",
            details,
        )

    assert result["success"], f"LDMS service failed on: {result['failed_nodes']}"


# =========================================================================
# TC_SR_024: Verify LDMS sampler plugins configured on Slurm nodes
# =========================================================================

@pytest.mark.source
@pytest.mark.functional
@pytest.mark.ldms
@pytest.mark.order(55)
def test_ldms_sampler_plugins(host):
    """TC_SR_024: Verify LDMS sampler plugins configured on Slurm nodes.

    Verifies that sampler.conf on each Slurm node has exactly the plugins
    defined in telemetry_config.yml ldms_configurations.sampler_plugins.
    """
    from library.functions.ldms_func import verify_ldms_sampler_plugins

    _skip_if_ldms_disabled(host)
    tc = TC["ldms_sampler_plugins"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying LDMS sampler plugins configuration")
    result = verify_ldms_sampler_plugins(host)

    if result.get("error") and not result.get("node_results"):
        tl.skipped(result["error"])
        pytest.skip(result["error"])

    # Build details output
    details_lines = [
        f"Expected plugins: {', '.join(result.get('expected_plugins', []))}",
        "",
        "Plugin configuration per node (by group):",
    ]

    # Group results by functional group
    by_group = {}
    for nr in result.get("node_results", []):
        grp = nr.get("group", "unknown")
        if grp not in by_group:
            by_group[grp] = []
        by_group[grp].append(nr)

    for group, nodes in by_group.items():
        details_lines.append(f"  [{group}]")
        for nr in nodes:
            icon = "\u2713" if nr["success"] else "\u2717"
            details_lines.append(f"    {icon} {nr['hostname']}")
            details_lines.append(
                f"        Configured: {', '.join(nr.get('configured_plugins', []))}"
            )
            if nr.get("missing_plugins"):
                details_lines.append(
                    f"        Missing: {', '.join(nr['missing_plugins'])}"
                )
            if nr.get("extra_plugins"):
                details_lines.append(
                    f"        Extra: {', '.join(nr['extra_plugins'])}"
                )
            if nr.get("error"):
                details_lines.append(f"        Error: {nr['error']}")

    details = "\n".join(details_lines)

    if result["success"]:
        tl.passed("LDMS plugins configured correctly on all nodes", details)
    else:
        failed_nodes = [n["hostname"] for n in result["node_results"] if not n["success"]]
        tl.failed(
            f"LDMS plugin mismatch on {len(failed_nodes)} nodes",
            details,
        )

    assert result["success"], f"LDMS plugin mismatch on: {', '.join(failed_nodes)}"


# =========================================================================
# TC_SR_025: Verify LDMS Kafka topic exists
# =========================================================================

@pytest.mark.source
@pytest.mark.functional
@pytest.mark.ldms
@pytest.mark.order(56)
def test_ldms_kafka_topic(host):
    """TC_SR_026: Verify LDMS Kafka topic exists."""
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


# =========================================================================
# LDMS Output Formatting Helpers (matching omnia-containers 2.2 format)
# =========================================================================

def _build_ldms_summary_lines(result):
    """Build common summary header lines for LDMS test details."""
    return [
        f"Kafka bridge IP: {result.get('bridge_ip', '')}",
        f"Domain: {result.get('domain_name', '')}",
        f"Expected plugins: {result.get('expected_plugins', [])}",
        f"Expected hostnames: {result.get('expected_hostnames', [])}",
    ]


def _format_unix_timestamp(ts):
    """Convert Unix timestamp to human-readable format."""
    from datetime import datetime
    try:
        if isinstance(ts, (int, float)):
            dt = datetime.fromtimestamp(ts)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(ts, str) and ts:
            dt = datetime.fromtimestamp(float(ts))
            return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, OSError, OverflowError):
        pass
    return str(ts) if ts else ""


def _build_ldms_host_lines(host_result):
    """Build detail lines for a single LDMS host result (omnia-containers 2.2 format)."""
    lines = []
    found = host_result.get("found", False)
    all_plugins = host_result.get("all_plugins_found", False)
    plugins_found = host_result.get("plugins_found", [])
    plugins_expected = host_result.get("plugins_expected", [])

    # Status icon and summary
    icon = "\u2713" if all_plugins else ("\u26a0" if found else "\u2717")
    if all_plugins:
        text = f"all {len(plugins_expected)} plugins found"
    elif found:
        text = f"{len(plugins_found)}/{len(plugins_expected)} plugins"
    else:
        text = "NO DATA in Kafka"
    lines.append(f"    {icon} {host_result.get('hostname', '')} ({text})")

    # Show each plugin with timestamp and sample metrics
    exclude_keys = {"timestamp", "hostname", "instance", "component_id", "job_id", "app_id"}
    for pd in plugins_found:
        plugin = pd.get("plugin", "")
        record = pd.get("record", {})
        value = record.get("value", {}) if isinstance(record, dict) else {}
        ldms_ts = value.get("timestamp", "")
        ts_formatted = _format_unix_timestamp(ldms_ts)
        if ts_formatted:
            lines.append(f"        \u2713 {plugin}: {ts_formatted}")
        else:
            lines.append(f"        \u2713 {plugin}")
        # Show first 3 metric values
        for k in [k for k in value if k not in exclude_keys][:3]:
            lines.append(f"            - {k}: {value[k]}")

    # Show missing plugins
    for mp in host_result.get("plugins_missing", []):
        lines.append(f"        \u2717 {mp}: MISSING")

    return lines


# =========================================================================
# TC_SR_026: Verify earliest LDMS data in Kafka topic
# =========================================================================

@pytest.mark.source
@pytest.mark.functional
@pytest.mark.ldms
@pytest.mark.order(57)
def test_ldms_earliest_data(host):
    """TC_SR_027: Verify earliest LDMS data in Kafka topic.

    Uses 'earliest' offset (--from-beginning) to get the oldest data from
    the beginning of the topic. Shows when each hostname first started
    sending data to Kafka.
    """
    from library.functions.ldms_func import verify_ldms_earliest_data_in_kafka

    _skip_if_ldms_disabled(host)
    tc = TC["ldms_earliest_data"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying earliest LDMS data in Kafka topic")
    result = verify_ldms_earliest_data_in_kafka(host, timeout_seconds=60)

    if result.get("skipped"):
        tl.skipped(result.get("reason", "LDMS earliest data verification skipped"))
        pytest.skip(result.get("reason", "LDMS earliest data verification skipped"))

    # Build details output (omnia-containers 2.2 format)
    details_lines = _build_ldms_summary_lines(result)
    details_lines.extend([
        f"Total records read: {result.get('total_records_read', 0)}",
        f"Found instances: {result.get('found_instance_count', 0)}",
        f"Found hostnames: {result.get('found_hostnames', [])}",
        f"Missing hostnames: {result.get('missing_hostnames', [])}",
        "",
        "Earliest data per hostname (by functional group):",
    ])

    # Group by functional_group
    for func_group, hosts in result.get("results_by_group", {}).items():
        details_lines.append(f"  [{func_group}]")
        for hr in hosts:
            details_lines.extend(_build_ldms_host_lines(hr))

    details = "\n".join(details_lines)

    # Pass if we found any data
    found_count = result.get("found_instance_count", 0)
    if found_count > 0:
        tl.passed(
            f"LDMS earliest data found for {len(result.get('found_hostnames', []))} hosts",
            details,
        )
    else:
        tl.failed("No LDMS earliest data found in Kafka topic", details)

    assert found_count > 0, "No LDMS earliest data found in Kafka topic"


# =========================================================================
# TC_SR_027: Verify latest LDMS data in Kafka topic
# =========================================================================

@pytest.mark.source
@pytest.mark.functional
@pytest.mark.ldms
@pytest.mark.order(58)
def test_ldms_kafka_data(host):
    """TC_SR_028: Verify latest LDMS data in Kafka topic.

    Uses 'latest' offset to get the most recent data from the topic.
    Verifies that data from all LDMS-enabled nodes with all configured
    plugins is present in the ldms Kafka topic.
    """
    from library.functions.ldms_func import verify_ldms_data_in_kafka

    _skip_if_ldms_disabled(host)
    tc = TC["ldms_kafka_data"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying latest LDMS data in Kafka topic")
    result = verify_ldms_data_in_kafka(host, timeout_seconds=60)

    if result.get("skipped"):
        tl.skipped(result.get("reason", "LDMS data verification skipped"))
        pytest.skip(result.get("reason", "LDMS data verification skipped"))

    # Build details output (omnia-containers 2.2 format)
    expected_count = result.get("expected_instance_count", 0)
    found_count = result.get("found_instance_count", 0)
    details_lines = _build_ldms_summary_lines(result)
    details_lines.extend([
        f"Expected instances (hostname\u00d7plugin): {expected_count}",
        f"Found instances: {found_count}/{expected_count}",
        "",
        "Latest data per hostname (by functional group):",
    ])

    # Group by functional_group
    for func_group, hosts in result.get("results_by_group", {}).items():
        details_lines.append(f"  [{func_group}]")
        for hr in hosts:
            details_lines.extend(_build_ldms_host_lines(hr))

    details = "\n".join(details_lines)

    if result["success"]:
        tl.passed(
            f"LDMS latest data verified for all {len(result.get('found_hostnames', []))} hosts",
            details,
        )
    else:
        missing_hosts = result.get("missing_hostnames", [])
        if missing_hosts:
            tl.failed(
                f"LDMS data missing from {len(missing_hosts)} hostnames",
                details,
            )
        else:
            missing_inst = result.get("missing_instances", [])
            tl.failed(
                f"LDMS data missing {len(missing_inst)} plugin instances",
                details,
            )

    assert result["success"], result.get("error", "LDMS data verification failed")
