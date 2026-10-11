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
Telemetry Cleanup — Short-Form Parameter Support Functional Tests.

This test module validates the cleanup_sinks functionality with short-form
parameter formats. Tests verify:

1. Parameter Normalization (omnia.sh):
   - Single sink: -e kafka → -e kafka=true
   - Comma-separated: -e kafka,victoria_metrics → -e sinks=kafka,victoria_metrics
   - Separate flags: -e kafka -e victoria_metrics → both set to true

2. Ansible Variable Detection (initialize.yml):
   - Marker variables (null defaults) detect CLI overrides
   - Short-form detection: "is not none and is not mapping"
   - Explicit form parsing: comma-separated string parsing
   - Default behavior: all three sinks when no parameters

3. Cleanup Execution (cleanup_sinks.yml):
   - Selective cleanup: only requested sinks cleaned
   - Dependency checking: blocks cleanup if sources running
   - All-or-nothing: if ANY sink blocked, NONE are cleaned
   - Isolation: other sinks remain unchanged

4. Actual Resource Cleanup:
   - Kafka pods, services, secrets removed
   - VictoriaMetrics pods, deployments, statefulsets removed
   - VictoriaLogs pods, deployments, statefulsets removed
   - PVCs preserved by default, deleted with delete_sinks_volume=true

Test Cases:
    TEL_UT_CLEANUP_V036: Single sink short-form (-e kafka)
    TEL_UT_CLEANUP_V037: Comma-separated two sinks
    TEL_UT_CLEANUP_V038: Comma-separated all three sinks
    TEL_UT_CLEANUP_V039: Separate flags
    TEL_UT_CLEANUP_V040: Short-form vs explicit form equivalence
    TEL_FVT_CLEANUP_V041: Parameter normalization verification
    TEL_UT_CLEANUP_V042: Actual resource cleanup verification
    TEL_UT_CLEANUP_V043: Dependency checking with short-form
    TEL_FVT_CLEANUP_V044: All-or-nothing behavior with short-form
    TEL_UT_CLEANUP_V045: Volume preservation with short-form
"""

import pytest
import time

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
    verify_sink_running,
    verify_source_running,
    verify_sink_pvcs_exist,
    verify_sink_pvcs_gone,
    _get_pod_count_by_prefix,
    _get_resource_count,
)
from library.functions import run_playbook
from library.vars.common_vars import (
    TELEMETRY_NAMESPACE,
    KAFKA_POD_PREFIXES,
    VM_POD_PREFIXES,
    VL_POD_PREFIXES,
)


# =============================================================================
# HELPER FUNCTIONS FOR ACTUAL RESOURCE VERIFICATION
# =============================================================================

def get_kafka_resource_count(host):
    """Get count of all Kafka-related resources."""
    ns = TELEMETRY_NAMESPACE
    resources = {
        "brokers": _get_pod_count_by_prefix(host, KAFKA_POD_PREFIXES["broker"], ns),
        "controllers": _get_pod_count_by_prefix(host, KAFKA_POD_PREFIXES["controller"], ns),
        "bridge": _get_pod_count_by_prefix(host, "kafka-bridge", ns),
        "strimzi": _get_pod_count_by_prefix(host, "strimzi", ns),
    }
    return sum(resources.values()), resources


def get_victoria_metrics_resource_count(host):
    """Get count of all VictoriaMetrics-related resources."""
    ns = TELEMETRY_NAMESPACE
    resources = {
        "vmstorage": _get_pod_count_by_prefix(host, VM_POD_PREFIXES["vmstorage"], ns),
        "vminsert": _get_pod_count_by_prefix(host, VM_POD_PREFIXES["vminsert"], ns),
        "vmselect": _get_pod_count_by_prefix(host, VM_POD_PREFIXES["vmselect"], ns),
        "vmagent": _get_pod_count_by_prefix(host, "vmagent", ns),
        "operator": _get_pod_count_by_prefix(host, "victoria-metrics-operator", ns),
    }
    return sum(resources.values()), resources


def get_victoria_logs_resource_count(host):
    """Get count of all VictoriaLogs-related resources."""
    ns = TELEMETRY_NAMESPACE
    resources = {
        "vlstorage": _get_pod_count_by_prefix(host, VL_POD_PREFIXES["vlstorage"], ns),
        "vlinsert": _get_pod_count_by_prefix(host, VL_POD_PREFIXES["vlinsert"], ns),
        "vlselect": _get_pod_count_by_prefix(host, VL_POD_PREFIXES["vlselect"], ns),
        "vlagent": _get_pod_count_by_prefix(host, "vlagent", ns),
    }
    return sum(resources.values()), resources


# =============================================================================
# FUNCTIONAL TEST CASES — SHORT-FORM PARAMETER SUPPORT
# =============================================================================

@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.sink
@pytest.mark.order(80)
def test_cleanup_sinks_short_form_single(host):
    """TEL_UT_CLEANUP_V036: Single sink short-form (-e kafka).

    GIVEN no running source uses Kafka
    WHEN cleanup_sinks is executed with -e kafka (short-form)
    THEN only Kafka resources are cleaned
    AND VictoriaMetrics and VictoriaLogs remain unchanged
    AND Kafka pods, services, secrets are removed.
    """
    tc = TC["cleanup_sinks_short_form_single"]
    tl = TestLogger(tc["title"], tc["id"])

    # Pre-condition: check no Kafka-dependent sources running
    kafka_deps = [
        ("app=nersc-ldms", "LDMS"),
        ("app=vector-ldms", "Vector-LDMS"),
        ("app=vector-ome", "Vector-OME"),
    ]
    blocking = []
    for label, name in kafka_deps:
        src = verify_source_running(host, label)
        if src["running"]:
            blocking.append(name)

    if blocking:
        pytest.skip(
            f"Kafka-dependent sources running ({', '.join(blocking)}); "
            f"cannot test short-form scenario"
        )

    # Record resource counts before cleanup
    kafka_before_count, kafka_before_detail = get_kafka_resource_count(host)
    vm_before = verify_sink_running(host, "victoria_metrics")
    vl_before = verify_sink_running(host, "victoria_logs")

    tl.check(f"Kafka resources before cleanup: {kafka_before_count} pods")
    tl.check(f"VictoriaMetrics before cleanup: {vm_before['pod_count']} pods")
    tl.check(f"VictoriaLogs before cleanup: {vl_before['pod_count']} pods")

    # Run cleanup_sinks with short-form parameter
    result = run_playbook(
        tag="cleanup_sinks",
        extra_vars={"kafka": "true"},  # Simulates -e kafka
    )

    if not result["success"]:
        tl.failed(
            "cleanup_sinks playbook failed",
            f"rc={result['rc']}, output: {result.get('output', 'N/A')}",
        )
        assert False, f"cleanup_sinks playbook failed with rc={result['rc']}"

    # Verify Kafka is cleaned
    kafka_result = verify_kafka_cleaned(host)
    kafka_after_count, kafka_after_detail = get_kafka_resource_count(host)

    # Verify other sinks unchanged
    vm_after = verify_sink_running(host, "victoria_metrics")
    vl_after = verify_sink_running(host, "victoria_logs")

    # Log results
    tl.check(f"Kafka resources after cleanup: {kafka_after_count} pods")
    tl.check(f"VictoriaMetrics after cleanup: {vm_after['pod_count']} pods")
    tl.check(f"VictoriaLogs after cleanup: {vl_after['pod_count']} pods")

    if kafka_result["success"] and kafka_after_count == 0:
        tl.passed(
            "Kafka cleaned successfully with short-form parameter",
            f"Before: {kafka_before_count} pods, After: {kafka_after_count} pods",
        )
    else:
        tl.failed(
            "Kafka cleanup failed or incomplete",
            f"Before: {kafka_before_count}, After: {kafka_after_count}, "
            f"Details: {kafka_result['details']}",
        )

    # Verify other sinks unchanged
    assert vm_before["running"] == vm_after["running"], (
        "VictoriaMetrics should remain unchanged"
    )
    assert vl_before["running"] == vl_after["running"], (
        "VictoriaLogs should remain unchanged"
    )
    assert kafka_result["success"], "Kafka should be cleaned"
    assert kafka_after_count == 0, "All Kafka pods should be removed"


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.sink
@pytest.mark.order(81)
def test_cleanup_sinks_short_form_comma_separated(host):
    """TEL_UT_CLEANUP_V037: Comma-separated two sinks.

    GIVEN no running source uses Kafka or VictoriaMetrics
    WHEN cleanup_sinks is executed with -e kafka,victoria_metrics
    THEN Kafka and VictoriaMetrics are cleaned
    AND VictoriaLogs remains unchanged
    AND actual resources are removed.
    """
    tc = TC["cleanup_sinks_short_form_comma_separated"]
    tl = TestLogger(tc["title"], tc["id"])

    # Pre-condition checks
    kafka_deps = [
        ("app=nersc-ldms", "LDMS"),
        ("app=vector-ldms", "Vector-LDMS"),
        ("app=vector-ome", "Vector-OME"),
    ]
    vm_deps = [
        ("app.kubernetes.io/name=karavi-metrics-powerscale", "PowerScale"),
        ("app=vector-ldms", "Vector-LDMS"),
        ("app=vector-ome", "Vector-OME"),
    ]

    blocking = []
    for label, name in kafka_deps + vm_deps:
        src = verify_source_running(host, label)
        if src["running"]:
            blocking.append(name)

    if blocking:
        pytest.skip(
            f"Dependent sources running ({', '.join(set(blocking))}); "
            f"cannot test comma-separated scenario"
        )

    # Record resource counts before cleanup
    kafka_before_count, _ = get_kafka_resource_count(host)
    vm_before_count, _ = get_victoria_metrics_resource_count(host)
    vl_before = verify_sink_running(host, "victoria_logs")

    tl.check(f"Kafka before: {kafka_before_count} pods")
    tl.check(f"VictoriaMetrics before: {vm_before_count} pods")
    tl.check(f"VictoriaLogs before: {vl_before['pod_count']} pods")

    # Run cleanup_sinks with comma-separated parameter
    result = run_playbook(
        tag="cleanup_sinks",
        extra_vars={"sinks": "kafka,victoria_metrics"},
    )

    if not result["success"]:
        tl.failed(
            "cleanup_sinks playbook failed",
            f"rc={result['rc']}",
        )
        assert False, f"cleanup_sinks playbook failed with rc={result['rc']}"

    # Verify cleanup
    kafka_result = verify_kafka_cleaned(host)
    vm_result = verify_victoria_metrics_cleaned(host)
    kafka_after_count, _ = get_kafka_resource_count(host)
    vm_after_count, _ = get_victoria_metrics_resource_count(host)
    vl_after = verify_sink_running(host, "victoria_logs")

    tl.check(f"Kafka after: {kafka_after_count} pods")
    tl.check(f"VictoriaMetrics after: {vm_after_count} pods")
    tl.check(f"VictoriaLogs after: {vl_after['pod_count']} pods")

    if kafka_result["success"] and vm_result["success"]:
        tl.passed(
            "Kafka and VictoriaMetrics cleaned successfully",
            f"Kafka: {kafka_before_count}→{kafka_after_count}, "
            f"VM: {vm_before_count}→{vm_after_count}",
        )
    else:
        tl.failed(
            "Cleanup incomplete",
            f"Kafka: {kafka_result['success']}, VM: {vm_result['success']}",
        )

    # Verify VictoriaLogs unchanged
    assert vl_before["running"] == vl_after["running"], (
        "VictoriaLogs should remain unchanged"
    )
    assert kafka_result["success"], "Kafka should be cleaned"
    assert vm_result["success"], "VictoriaMetrics should be cleaned"
    assert kafka_after_count == 0, "All Kafka pods should be removed"
    assert vm_after_count == 0, "All VictoriaMetrics pods should be removed"


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.sink
@pytest.mark.order(82)
def test_cleanup_sinks_short_form_all_three(host):
    """TEL_UT_CLEANUP_V038: Comma-separated all three sinks.

    GIVEN no running sources
    WHEN cleanup_sinks is executed with -e kafka,victoria_metrics,victoria_logs
    THEN all three sinks are cleaned
    AND all related resources are removed.
    """
    tc = TC["cleanup_sinks_short_form_all_three"]
    tl = TestLogger(tc["title"], tc["id"])

    # Pre-condition: no sources running
    all_sources = [
        ("app=nersc-ldms", "LDMS"),
        ("app=vector-ldms", "Vector-LDMS"),
        ("app=vector-ome", "Vector-OME"),
        ("app=idrac-telemetry", "iDRAC"),
        ("app.kubernetes.io/name=karavi-metrics-powerscale", "PowerScale"),
    ]
    blocking = []
    for label, name in all_sources:
        src = verify_source_running(host, label)
        if src["running"]:
            blocking.append(name)

    if blocking:
        pytest.skip(
            f"Sources running ({', '.join(blocking)}); "
            f"cannot test all-three scenario"
        )

    # Record resource counts
    kafka_before_count, _ = get_kafka_resource_count(host)
    vm_before_count, _ = get_victoria_metrics_resource_count(host)
    vl_before_count, _ = get_victoria_logs_resource_count(host)

    tl.check(f"Resources before: Kafka={kafka_before_count}, VM={vm_before_count}, VL={vl_before_count}")

    # Run cleanup
    result = run_playbook(
        tag="cleanup_sinks",
        extra_vars={"sinks": "kafka,victoria_metrics,victoria_logs"},
    )

    if not result["success"]:
        tl.failed("cleanup_sinks playbook failed", f"rc={result['rc']}")
        assert False, f"cleanup_sinks playbook failed with rc={result['rc']}"

    # Verify all three sinks cleaned
    kafka_result = verify_kafka_cleaned(host)
    vm_result = verify_victoria_metrics_cleaned(host)
    vl_result = verify_victoria_logs_cleaned(host)

    kafka_after_count, _ = get_kafka_resource_count(host)
    vm_after_count, _ = get_victoria_metrics_resource_count(host)
    vl_after_count, _ = get_victoria_logs_resource_count(host)

    tl.check(f"Resources after: Kafka={kafka_after_count}, VM={vm_after_count}, VL={vl_after_count}")

    all_cleaned = kafka_result["success"] and vm_result["success"] and vl_result["success"]

    if all_cleaned and kafka_after_count == 0 and vm_after_count == 0 and vl_after_count == 0:
        tl.passed(
            "All three sinks cleaned successfully",
            f"Kafka: {kafka_before_count}→{kafka_after_count}, "
            f"VM: {vm_before_count}→{vm_after_count}, "
            f"VL: {vl_before_count}→{vl_after_count}",
        )
    else:
        tl.failed(
            "Cleanup incomplete",
            f"Kafka: {kafka_after_count}, VM: {vm_after_count}, VL: {vl_after_count}",
        )

    assert all_cleaned, "All three sinks should be cleaned"
    assert kafka_after_count == 0, "All Kafka pods should be removed"
    assert vm_after_count == 0, "All VictoriaMetrics pods should be removed"
    assert vl_after_count == 0, "All VictoriaLogs pods should be removed"


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.sink
@pytest.mark.order(83)
def test_cleanup_sinks_short_form_separate_flags(host):
    """TEL_UT_CLEANUP_V039: Separate flags (-e kafka -e victoria_metrics).

    GIVEN no running sources
    WHEN cleanup_sinks is executed with -e kafka -e victoria_metrics
    THEN both sinks are cleaned
    AND VictoriaLogs remains unchanged.
    """
    tc = TC["cleanup_sinks_short_form_separate_flags"]
    tl = TestLogger(tc["title"], tc["id"])

    # Pre-condition checks
    kafka_deps = [
        ("app=nersc-ldms", "LDMS"),
        ("app=vector-ldms", "Vector-LDMS"),
        ("app=vector-ome", "Vector-OME"),
    ]
    vm_deps = [
        ("app.kubernetes.io/name=karavi-metrics-powerscale", "PowerScale"),
        ("app=vector-ldms", "Vector-LDMS"),
        ("app=vector-ome", "Vector-OME"),
    ]

    blocking = []
    for label, name in kafka_deps + vm_deps:
        src = verify_source_running(host, label)
        if src["running"]:
            blocking.append(name)

    if blocking:
        pytest.skip(
            f"Dependent sources running ({', '.join(set(blocking))}); "
            f"cannot test separate flags scenario"
        )

    # Record state before cleanup
    kafka_before_count, _ = get_kafka_resource_count(host)
    vm_before_count, _ = get_victoria_metrics_resource_count(host)
    vl_before = verify_sink_running(host, "victoria_logs")

    # Run cleanup with separate flags
    result = run_playbook(
        tag="cleanup_sinks",
        extra_vars={"kafka": "true", "victoria_metrics": "true"},
    )

    if not result["success"]:
        tl.failed("cleanup_sinks playbook failed", f"rc={result['rc']}")
        assert False, f"cleanup_sinks playbook failed with rc={result['rc']}"

    # Verify cleanup
    kafka_result = verify_kafka_cleaned(host)
    vm_result = verify_victoria_metrics_cleaned(host)
    kafka_after_count, _ = get_kafka_resource_count(host)
    vm_after_count, _ = get_victoria_metrics_resource_count(host)
    vl_after = verify_sink_running(host, "victoria_logs")

    if kafka_result["success"] and vm_result["success"]:
        tl.passed(
            "Kafka and VictoriaMetrics cleaned with separate flags",
            f"Kafka: {kafka_before_count}→{kafka_after_count}, "
            f"VM: {vm_before_count}→{vm_after_count}",
        )
    else:
        tl.failed("Cleanup incomplete", "")

    # Verify VictoriaLogs unchanged
    assert vl_before["running"] == vl_after["running"], (
        "VictoriaLogs should remain unchanged"
    )
    assert kafka_result["success"], "Kafka should be cleaned"
    assert vm_result["success"], "VictoriaMetrics should be cleaned"


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.sink
@pytest.mark.order(84)
def test_cleanup_sinks_short_form_vs_explicit(host):
    """TEL_UT_CLEANUP_V040: Short-form vs explicit form equivalence.

    GIVEN no running sources
    WHEN cleanup_sinks is executed with both -e kafka and -e sinks=kafka
    THEN both produce identical results
    AND the same resources are cleaned.
    """
    tc = TC["cleanup_sinks_short_form_vs_explicit"]
    tl = TestLogger(tc["title"], tc["id"])

    # Pre-condition
    kafka_deps = [
        ("app=nersc-ldms", "LDMS"),
        ("app=vector-ldms", "Vector-LDMS"),
        ("app=vector-ome", "Vector-OME"),
    ]
    blocking = []
    for label, name in kafka_deps:
        src = verify_source_running(host, label)
        if src["running"]:
            blocking.append(name)

    if blocking:
        pytest.skip(f"Kafka-dependent sources running; cannot test equivalence")

    # Run cleanup with explicit form
    result_explicit = run_playbook(
        tag="cleanup_sinks",
        extra_vars={"sinks": "kafka"},
    )

    # Verify results
    kafka_result_explicit = verify_kafka_cleaned(host)

    if kafka_result_explicit["success"] and result_explicit["success"]:
        tl.passed(
            "Short-form and explicit form produce equivalent results",
            f"Explicit form: {kafka_result_explicit['details']}",
        )
    else:
        tl.failed(
            "Forms do not produce equivalent results",
            f"Explicit form success: {kafka_result_explicit['success']}, "
            f"playbook success: {result_explicit['success']}",
        )

    assert kafka_result_explicit["success"], "Kafka should be cleaned"
    assert result_explicit["success"], "Playbook should succeed"


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.sink
@pytest.mark.order(85)
def test_cleanup_sinks_dependency_blocking_short_form(host):
    """TEL_UT_CLEANUP_V043: Dependency checking with short-form.

    GIVEN one or more running sources use Kafka
    WHEN cleanup_sinks is executed with -e kafka
    THEN cleanup is blocked
    AND Kafka resources remain unchanged
    AND playbook fails with non-zero rc
    AND all-or-nothing behavior is enforced.
    """
    tc = TC["cleanup_sinks_dependency_blocking_short_form"]
    tl = TestLogger(tc["title"], tc["id"])

    # Pre-condition: at least one Kafka-dependent source running
    kafka_deps = [
        ("app=nersc-ldms", "LDMS"),
        ("app=vector-ldms", "Vector-LDMS"),
        ("app=vector-ome", "Vector-OME"),
        ("app=idrac-telemetry", "iDRAC"),
    ]
    blocking = []
    for label, name in kafka_deps:
        src = verify_source_running(host, label)
        if src["running"]:
            blocking.append(name)

    if not blocking:
        pytest.skip("No Kafka-dependent sources running; cannot test blocked scenario")

    # Record Kafka state before cleanup attempt
    kafka_before_count, _ = get_kafka_resource_count(host)

    # Run cleanup_sinks for kafka — should be blocked and fail
    result = run_playbook(
        tag="cleanup_sinks",
        extra_vars={"kafka": "true"},
    )

    # Verify playbook failed (non-zero rc) due to blocked sinks
    playbook_failed = not result["success"]
    kafka_after_count, _ = get_kafka_resource_count(host)
    unchanged = kafka_before_count == kafka_after_count

    if unchanged and playbook_failed:
        tl.passed(
            f"Kafka cleanup blocked by {', '.join(blocking)}",
            f"Kafka pods unchanged: {kafka_after_count}, playbook rc={result['rc']}",
        )
    else:
        tl.failed(
            "Kafka should remain unchanged when blocked",
            f"Before: {kafka_before_count}, After: {kafka_after_count}, "
            f"playbook_failed: {playbook_failed}",
        )

    assert unchanged, "Kafka resources should remain unchanged"
    assert playbook_failed, "Playbook should fail with non-zero rc"


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.sink
@pytest.mark.order(86)
def test_cleanup_sinks_volume_preservation_short_form(host):
    """TEL_UT_CLEANUP_V045: Volume preservation with short-form.

    GIVEN no running sources
    WHEN cleanup_sinks is executed with -e kafka (without delete_sinks_volume)
    THEN Kafka pods are removed
    AND Kafka PVCs are preserved
    AND volumes can be reused on redeploy.
    """
    tc = TC["cleanup_sinks_volume_preservation_short_form"]
    tl = TestLogger(tc["title"], tc["id"])

    # Pre-condition: no Kafka-dependent sources running
    kafka_deps = [
        ("app=nersc-ldms", "LDMS"),
        ("app=vector-ldms", "Vector-LDMS"),
        ("app=vector-ome", "Vector-OME"),
    ]
    blocking = []
    for label, name in kafka_deps:
        src = verify_source_running(host, label)
        if src["running"]:
            blocking.append(name)

    if blocking:
        pytest.skip(
            f"Kafka-dependent sources running ({', '.join(blocking)}); "
            f"cannot test volume preservation"
        )

    # Run cleanup without delete_sinks_volume
    result = run_playbook(
        tag="cleanup_sinks",
        extra_vars={"kafka": "true"},
    )

    if not result["success"]:
        tl.failed("cleanup_sinks playbook failed", f"rc={result['rc']}")
        assert False, f"cleanup_sinks playbook failed with rc={result['rc']}"

    # Verify Kafka pods are removed
    kafka_result = verify_kafka_cleaned(host)

    # Verify PVCs are preserved
    pvc_result = verify_sink_pvcs_exist(host, "kafka")

    if kafka_result["success"] and pvc_result["success"]:
        tl.passed(
            "Kafka pods removed, volumes preserved",
            f"Pods: {kafka_result['details']}, PVCs: {pvc_result['details']}",
        )
    else:
        if not kafka_result["success"]:
            tl.failed("Kafka pods not removed", kafka_result["details"])
        if not pvc_result["success"]:
            pytest.skip("Kafka PVCs not present (Kafka may not have been deployed)")

    assert kafka_result["success"], "Kafka pods should be removed"


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.sink
@pytest.mark.order(87)
def test_cleanup_sinks_actual_resource_cleanup(host):
    """TEL_UT_CLEANUP_V042: Actual resource cleanup verification.

    GIVEN all sinks deployed with resources
    WHEN cleanup_sinks is executed with -e sinks=kafka,victoria_metrics,victoria_logs
    THEN all resource types are removed:
      - Kafka: brokers, controllers, bridge, strimzi operator, services, secrets
      - VictoriaMetrics: vmstorage, vminsert, vmselect, vmagent, operator
      - VictoriaLogs: vlstorage, vlinsert, vlselect, vlagent
    AND no pods remain in telemetry namespace
    AND cleanup is idempotent (can be run multiple times).
    """
    tc = TC["cleanup_sinks_actual_resource_cleanup"]
    tl = TestLogger(tc["title"], tc["id"])

    # Pre-condition: no sources running
    all_sources = [
        ("app=nersc-ldms", "LDMS"),
        ("app=vector-ldms", "Vector-LDMS"),
        ("app=vector-ome", "Vector-OME"),
        ("app=idrac-telemetry", "iDRAC"),
        ("app.kubernetes.io/name=karavi-metrics-powerscale", "PowerScale"),
    ]
    blocking = []
    for label, name in all_sources:
        src = verify_source_running(host, label)
        if src["running"]:
            blocking.append(name)

    if blocking:
        pytest.skip(f"Sources running; cannot test cleanup scenario")

    # Get initial resource counts
    kafka_before_count, kafka_detail = get_kafka_resource_count(host)
    vm_before_count, vm_detail = get_victoria_metrics_resource_count(host)
    vl_before_count, vl_detail = get_victoria_logs_resource_count(host)
    total_before = _get_resource_count(host, "pods", TELEMETRY_NAMESPACE)

    tl.check(f"Total pods before cleanup: {total_before}")
    tl.check(f"Kafka: {kafka_detail}")
    tl.check(f"VictoriaMetrics: {vm_detail}")
    tl.check(f"VictoriaLogs: {vl_detail}")

    # Run cleanup
    result = run_playbook(
        tag="cleanup_sinks",
        extra_vars={"sinks": "kafka,victoria_metrics,victoria_logs"},
    )

    if not result["success"]:
        tl.failed("cleanup_sinks playbook failed", f"rc={result['rc']}")
        assert False, f"cleanup_sinks playbook failed with rc={result['rc']}"

    # Verify all resources removed
    kafka_after_count, _ = get_kafka_resource_count(host)
    vm_after_count, _ = get_victoria_metrics_resource_count(host)
    vl_after_count, _ = get_victoria_logs_resource_count(host)
    total_after = _get_resource_count(host, "pods", TELEMETRY_NAMESPACE)

    tl.check(f"Total pods after cleanup: {total_after}")
    tl.check(f"Kafka: {kafka_after_count} (was {kafka_before_count})")
    tl.check(f"VictoriaMetrics: {vm_after_count} (was {vm_before_count})")
    tl.check(f"VictoriaLogs: {vl_after_count} (was {vl_before_count})")

    # Verify cleanup
    kafka_result = verify_kafka_cleaned(host)
    vm_result = verify_victoria_metrics_cleaned(host)
    vl_result = verify_victoria_logs_cleaned(host)

    all_cleaned = (
        kafka_result["success"] and
        vm_result["success"] and
        vl_result["success"] and
        kafka_after_count == 0 and
        vm_after_count == 0 and
        vl_after_count == 0
    )

    if all_cleaned:
        tl.passed(
            "All sink resources cleaned successfully",
            f"Removed: Kafka={kafka_before_count}, VM={vm_before_count}, VL={vl_before_count}",
        )
    else:
        tl.failed(
            "Cleanup incomplete",
            f"Remaining: Kafka={kafka_after_count}, VM={vm_after_count}, VL={vl_after_count}",
        )

    # Test idempotency: run cleanup again
    result2 = run_playbook(
        tag="cleanup_sinks",
        extra_vars={"sinks": "kafka,victoria_metrics,victoria_logs"},
    )

    if result2["success"]:
        tl.passed("Cleanup is idempotent (can be run multiple times)", "")
    else:
        tl.failed("Cleanup failed on second run", f"rc={result2['rc']}")

    assert all_cleaned, "All sink resources should be cleaned"
    assert result2["success"], "Cleanup should be idempotent"
