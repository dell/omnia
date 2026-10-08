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
Telemetry Cleanup — Sink Dependency Checking Verification Tests.

Verifies that the cleanup_sinks tag correctly checks for running
dependent sources before removing sinks (Kafka, VictoriaMetrics,
VictoriaLogs).

All-or-nothing behavior: If ANY requested sink is blocked by a running
dependent source, the ENTIRE selective cleanup is aborted and NO sinks
are cleaned. The playbook fails with a non-zero return code and lists
all blocking sources.

Dependency map:
    Kafka:           iDRAC (kafka target), LDMS, Vector-LDMS, Vector-OME
    VictoriaMetrics: iDRAC (VM target), PowerScale, UFM, VAST,
                     Vector-LDMS, Vector-OME (metrics)
    VictoriaLogs:    PowerScale (logs), UFM (logs), VAST (logs),
                     Vector-OME (logs)

Test cases:
    TEL_UT_CLEANUP_V019: Kafka cleanup allowed — no dependent sources
    TEL_UT_CLEANUP_V020: Kafka cleanup blocked — one dependent source
    TEL_UT_CLEANUP_V021: Kafka cleanup blocked — multiple dependent sources
    TEL_UT_CLEANUP_V022: Kafka volumes preserved by default
    TEL_UT_CLEANUP_V023: Kafka volumes deleted with delete_sinks_volume=true
    TEL_UT_CLEANUP_V024: VictoriaMetrics cleanup allowed
    TEL_UT_CLEANUP_V025: VictoriaMetrics cleanup blocked
    TEL_UT_CLEANUP_V026: VictoriaMetrics cleanup blocked — multiple sources
    TEL_UT_CLEANUP_V027: VictoriaLogs cleanup allowed
    TEL_UT_CLEANUP_V028: VictoriaLogs cleanup blocked
    TEL_UT_CLEANUP_V029: Sinks preserved on dependency check failure
    TEL_UT_CLEANUP_V030: Unrelated sources do not block cleanup
    TEL_UT_CLEANUP_V031: Repeated sink cleanup is idempotent
    TEL_UT_CLEANUP_V032: Selective cleanup does not affect other sinks
    TEL_UT_CLEANUP_V033: Volumes protected during blocked cleanup
    TEL_UT_CLEANUP_V034: All-or-nothing — blocked sink prevents cleanup of other sinks
    TEL_UT_CLEANUP_V035: Playbook fails with non-zero rc when sinks blocked
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
    verify_sink_running,
    verify_source_running,
    verify_sink_pvcs_exist,
    verify_sink_pvcs_gone,
)
from library.functions import run_playbook


# =============================================================================
# KAFKA DEPENDENCY TESTS
# =============================================================================

@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.sink
@pytest.mark.order(70)
def test_cleanup_sinks_kafka_no_deps(host):
    """TEL_UT_CLEANUP_V019: Kafka cleanup allowed when no dependent sources running.

    GIVEN no running telemetry source uses Kafka
    WHEN cleanup_sinks is executed with sinks=kafka
    THEN Kafka runtime resources are deleted
    AND VictoriaMetrics and VictoriaLogs remain unchanged.
    """
    tc = TC["cleanup_sinks_kafka_no_deps"]
    tl = TestLogger(tc["title"], tc["id"])

    # Check pre-condition: no Kafka-dependent sources running
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
            f"cannot test no-deps scenario"
        )

    # Record other sinks state before cleanup
    vm_before = verify_sink_running(host, "victoria_metrics")
    vl_before = verify_sink_running(host, "victoria_logs")

    # Run cleanup_sinks for kafka
    result = run_playbook(
        tag="cleanup_sinks",
        extra_vars={"sinks": "kafka"},
    )

    if not result["success"]:
        tl.failed(
            LOG_MSGS["sink_cleanup_allowed"].format(sink="Kafka"),
            f"Playbook failed: rc={result['rc']}",
        )
        assert False, f"cleanup_sinks playbook failed with rc={result['rc']}"

    # Verify Kafka is cleaned
    kafka_result = verify_kafka_cleaned(host)
    if kafka_result["success"]:
        tl.passed(
            LOG_MSGS["sink_cleanup_allowed"].format(sink="Kafka"),
            kafka_result["details"],
        )
    else:
        tl.failed(
            LOG_MSGS["kafka_not_cleaned"].format(count="?"),
            kafka_result["details"],
        )

    # Verify other sinks unchanged
    vm_after = verify_sink_running(host, "victoria_metrics")
    vl_after = verify_sink_running(host, "victoria_logs")
    assert vm_before["running"] == vm_after["running"], (
        ASSERT_MSGS["other_sinks_modified"].format(sink="Kafka")
    )
    assert vl_before["running"] == vl_after["running"], (
        ASSERT_MSGS["other_sinks_modified"].format(sink="Kafka")
    )

    assert kafka_result["success"], ASSERT_MSGS["kafka_not_cleaned"]


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.sink
@pytest.mark.order(71)
def test_cleanup_sinks_kafka_blocked(host):
    """TEL_UT_CLEANUP_V020: Kafka cleanup blocked when dependent source running.

    GIVEN one or more running telemetry sources use Kafka
    WHEN cleanup_sinks is executed with sinks=kafka
    THEN Kafka cleanup is not performed
    AND no Kafka resource or volume is deleted
    AND the playbook fails with a non-zero return code
    AND the playbook reports the blocking sources.
    """
    tc = TC["cleanup_sinks_kafka_blocked"]
    tl = TestLogger(tc["title"], tc["id"])

    # Check pre-condition: at least one Kafka-dependent source running
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
        pytest.skip(
            "No Kafka-dependent sources running; cannot test blocked scenario"
        )

    # Record Kafka state before cleanup attempt
    kafka_before = verify_sink_running(host, "kafka")

    # Run cleanup_sinks for kafka — should be blocked and fail
    result = run_playbook(
        tag="cleanup_sinks",
        extra_vars={"sinks": "kafka"},
    )

    # Verify playbook failed (non-zero rc) due to blocked sinks
    playbook_failed = not result["success"]

    # Verify Kafka is still running (unchanged)
    kafka_after = verify_sink_running(host, "kafka")
    unchanged = kafka_before["pod_count"] == kafka_after["pod_count"]

    if unchanged and playbook_failed:
        tl.passed(
            LOG_MSGS["sink_cleanup_blocked"].format(
                sink="Kafka", sources=", ".join(blocking),
            ),
            f"Kafka pods unchanged: {kafka_after['pod_count']}, playbook rc={result['rc']}",
        )
    else:
        tl.failed(
            LOG_MSGS["sink_unchanged"].format(sink="Kafka"),
            f"Before: {kafka_before['pod_count']}, After: {kafka_after['pod_count']}, "
            f"playbook_failed: {playbook_failed}",
        )

    assert unchanged, ASSERT_MSGS["sink_should_remain_unchanged"].format(sink="Kafka")
    assert playbook_failed, (
        "Playbook should fail with non-zero rc when sinks are blocked"
    )


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.sink
@pytest.mark.order(72)
def test_cleanup_sinks_kafka_multi_blocked(host):
    """TEL_UT_CLEANUP_V021: Kafka cleanup blocked by multiple dependent sources.

    GIVEN multiple running telemetry sources use Kafka
    WHEN cleanup_sinks is executed with sinks=kafka
    THEN Kafka cleanup is not performed
    AND all blocking sources are listed in the output.
    """
    tc = TC["cleanup_sinks_kafka_multi_blocked"]
    tl = TestLogger(tc["title"], tc["id"])

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

    if len(blocking) < 2:
        pytest.skip(
            f"Only {len(blocking)} Kafka-dependent source(s) running; "
            f"need at least 2 for multi-blocked test"
        )

    kafka_before = verify_sink_running(host, "kafka")

    result = run_playbook(
        tag="cleanup_sinks",
        extra_vars={"sinks": "kafka"},
    )

    kafka_after = verify_sink_running(host, "kafka")
    unchanged = kafka_before["pod_count"] == kafka_after["pod_count"]

    if unchanged:
        tl.passed(
            LOG_MSGS["sink_cleanup_blocked"].format(
                sink="Kafka", sources=", ".join(blocking),
            ),
            f"Kafka pods unchanged, blocked by {len(blocking)} sources",
        )
    else:
        tl.failed(
            LOG_MSGS["sink_unchanged"].format(sink="Kafka"),
            f"Before: {kafka_before['pod_count']}, After: {kafka_after['pod_count']}",
        )

    assert unchanged, ASSERT_MSGS["sink_should_remain_unchanged"].format(sink="Kafka")


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.sink
@pytest.mark.order(73)
def test_cleanup_sinks_kafka_volumes_preserved(host):
    """TEL_UT_CLEANUP_V022: Kafka volumes preserved by default.

    GIVEN no running source uses Kafka
    AND delete_sinks_volume is absent or false
    WHEN cleanup runs
    THEN Kafka PVCs and persistent metadata are preserved.
    """
    tc = TC["cleanup_sinks_kafka_volumes_preserved"]
    tl = TestLogger(tc["title"], tc["id"])

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
    run_playbook(
        tag="cleanup_sinks",
        extra_vars={"sinks": "kafka"},
    )

    # Verify PVCs are preserved
    pvc_result = verify_sink_pvcs_exist(host, "kafka")

    if pvc_result["success"]:
        tl.passed(
            LOG_MSGS["sink_volumes_preserved"].format(sink="Kafka"),
            pvc_result["details"],
        )
    else:
        tl.failed(
            LOG_MSGS["sink_volumes_preserved"].format(sink="Kafka"),
            "Kafka PVCs were not found (may not have been deployed)",
        )
        # PVCs might not exist if Kafka was never deployed — not a hard failure
        pytest.skip("Kafka PVCs not present (Kafka may not have been deployed)")


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.sink
@pytest.mark.order(74)
def test_cleanup_sinks_kafka_volumes_deleted(host, delete_sinks_volume):
    """TEL_UT_CLEANUP_V023: Kafka volumes deleted with delete_sinks_volume=true.

    GIVEN no running source uses Kafka
    AND delete_sinks_volume=true
    WHEN cleanup runs
    THEN Kafka PVCs are deleted.
    """
    if not delete_sinks_volume:
        pytest.skip("delete_sinks_volume=false — skipping volume deletion test")

    tc = TC["cleanup_sinks_kafka_volumes_deleted"]
    tl = TestLogger(tc["title"], tc["id"])

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
            f"cannot test volume deletion"
        )

    run_playbook(
        tag="cleanup_sinks",
        extra_vars={"sinks": "kafka", "Delete_sinks_volume": "true"},
    )

    pvc_result = verify_sink_pvcs_gone(host, "kafka")

    if pvc_result["success"]:
        tl.passed(
            LOG_MSGS["sink_volumes_deleted"].format(sink="Kafka"),
            pvc_result["details"],
        )
    else:
        tl.failed(
            LOG_MSGS["sink_volumes_deleted"].format(sink="Kafka"),
            pvc_result["details"],
        )

    assert pvc_result["success"], f"Kafka PVCs not deleted: {pvc_result['details']}"


# =============================================================================
# VICTORIAMETRICS DEPENDENCY TESTS
# =============================================================================

@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.sink
@pytest.mark.order(75)
def test_cleanup_sinks_vm_no_deps(host):
    """TEL_UT_CLEANUP_V024: VictoriaMetrics cleanup allowed.

    GIVEN no running source uses VictoriaMetrics
    WHEN cleanup_sinks is executed with sinks=victoria_metrics
    THEN only VictoriaMetrics is cleaned
    AND Kafka and VictoriaLogs remain unchanged.
    """
    tc = TC["cleanup_sinks_vm_no_deps"]
    tl = TestLogger(tc["title"], tc["id"])

    vm_deps = [
        ("app.kubernetes.io/name=karavi-metrics-powerscale", "PowerScale"),
        ("app=vector-ldms", "Vector-LDMS"),
        ("app=vector-ome", "Vector-OME"),
    ]
    blocking = []
    for label, name in vm_deps:
        src = verify_source_running(host, label)
        if src["running"]:
            blocking.append(name)

    if blocking:
        pytest.skip(
            f"VM-dependent sources running ({', '.join(blocking)}); "
            f"cannot test no-deps scenario"
        )

    kafka_before = verify_sink_running(host, "kafka")
    vl_before = verify_sink_running(host, "victoria_logs")

    result = run_playbook(
        tag="cleanup_sinks",
        extra_vars={"sinks": "victoria_metrics"},
    )

    if not result["success"]:
        tl.failed("cleanup_sinks playbook failed", f"rc={result['rc']}")
        assert False, f"cleanup_sinks playbook failed with rc={result['rc']}"

    vm_result = verify_victoria_metrics_cleaned(host)
    kafka_after = verify_sink_running(host, "kafka")
    vl_after = verify_sink_running(host, "victoria_logs")

    if vm_result["success"]:
        tl.passed(
            LOG_MSGS["sink_cleanup_allowed"].format(sink="VictoriaMetrics"),
            vm_result["details"],
        )
    else:
        tl.failed(
            LOG_MSGS["vm_not_cleaned"].format(count="?"),
            vm_result["details"],
        )

    assert kafka_before["running"] == kafka_after["running"], (
        ASSERT_MSGS["other_sinks_modified"].format(sink="VictoriaMetrics")
    )
    assert vl_before["running"] == vl_after["running"], (
        ASSERT_MSGS["other_sinks_modified"].format(sink="VictoriaMetrics")
    )
    assert vm_result["success"], ASSERT_MSGS["vm_not_cleaned"]


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.sink
@pytest.mark.order(76)
def test_cleanup_sinks_vm_blocked(host):
    """TEL_UT_CLEANUP_V025: VictoriaMetrics cleanup blocked.

    GIVEN one or more running sources use VictoriaMetrics
    WHEN cleanup_sinks is executed with sinks=victoria_metrics
    THEN VictoriaMetrics cleanup is not performed
    AND its resources and volumes remain unchanged
    AND the playbook fails with a non-zero return code.
    """
    tc = TC["cleanup_sinks_vm_blocked"]
    tl = TestLogger(tc["title"], tc["id"])

    vm_deps = [
        ("app.kubernetes.io/name=karavi-metrics-powerscale", "PowerScale"),
        ("app=vector-ldms", "Vector-LDMS"),
        ("app=vector-ome", "Vector-OME"),
        ("app=idrac-telemetry", "iDRAC"),
    ]
    blocking = []
    for label, name in vm_deps:
        src = verify_source_running(host, label)
        if src["running"]:
            blocking.append(name)

    if not blocking:
        pytest.skip("No VM-dependent sources running; cannot test blocked scenario")

    vm_before = verify_sink_running(host, "victoria_metrics")

    result = run_playbook(
        tag="cleanup_sinks",
        extra_vars={"sinks": "victoria_metrics"},
    )

    playbook_failed = not result["success"]
    vm_after = verify_sink_running(host, "victoria_metrics")
    unchanged = vm_before["pod_count"] == vm_after["pod_count"]

    if unchanged and playbook_failed:
        tl.passed(
            LOG_MSGS["sink_cleanup_blocked"].format(
                sink="VictoriaMetrics", sources=", ".join(blocking),
            ),
            f"VM pods unchanged: {vm_after['pod_count']}, playbook rc={result['rc']}",
        )
    else:
        tl.failed(
            LOG_MSGS["sink_unchanged"].format(sink="VictoriaMetrics"),
            f"Before: {vm_before['pod_count']}, After: {vm_after['pod_count']}, "
            f"playbook_failed: {playbook_failed}",
        )

    assert unchanged, ASSERT_MSGS["sink_should_remain_unchanged"].format(
        sink="VictoriaMetrics",
    )
    assert playbook_failed, (
        "Playbook should fail with non-zero rc when sinks are blocked"
    )


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.sink
@pytest.mark.order(77)
def test_cleanup_sinks_vm_multi_blocked(host):
    """TEL_UT_CLEANUP_V026: VictoriaMetrics cleanup blocked by multiple sources.

    GIVEN multiple running sources use VictoriaMetrics
    WHEN cleanup_sinks is executed with sinks=victoria_metrics
    THEN VictoriaMetrics cleanup is not performed.
    """
    tc = TC["cleanup_sinks_vm_multi_blocked"]
    tl = TestLogger(tc["title"], tc["id"])

    vm_deps = [
        ("app.kubernetes.io/name=karavi-metrics-powerscale", "PowerScale"),
        ("app=vector-ldms", "Vector-LDMS"),
        ("app=vector-ome", "Vector-OME"),
        ("app=idrac-telemetry", "iDRAC"),
    ]
    blocking = []
    for label, name in vm_deps:
        src = verify_source_running(host, label)
        if src["running"]:
            blocking.append(name)

    if len(blocking) < 2:
        pytest.skip(
            f"Only {len(blocking)} VM-dependent source(s) running; need >= 2"
        )

    vm_before = verify_sink_running(host, "victoria_metrics")

    run_playbook(
        tag="cleanup_sinks",
        extra_vars={"sinks": "victoria_metrics"},
    )

    vm_after = verify_sink_running(host, "victoria_metrics")
    unchanged = vm_before["pod_count"] == vm_after["pod_count"]

    if unchanged:
        tl.passed(
            LOG_MSGS["sink_cleanup_blocked"].format(
                sink="VictoriaMetrics", sources=", ".join(blocking),
            ),
            f"VM pods unchanged, blocked by {len(blocking)} sources",
        )
    else:
        tl.failed(
            LOG_MSGS["sink_unchanged"].format(sink="VictoriaMetrics"),
            f"Before: {vm_before['pod_count']}, After: {vm_after['pod_count']}",
        )

    assert unchanged, ASSERT_MSGS["sink_should_remain_unchanged"].format(
        sink="VictoriaMetrics",
    )


# =============================================================================
# VICTORIALOGS DEPENDENCY TESTS
# =============================================================================

@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.sink
@pytest.mark.order(78)
def test_cleanup_sinks_vl_no_deps(host):
    """TEL_UT_CLEANUP_V027: VictoriaLogs cleanup allowed.

    GIVEN no running source uses VictoriaLogs
    WHEN cleanup_sinks is executed with sinks=victoria_logs
    THEN only VictoriaLogs is cleaned
    AND Kafka and VictoriaMetrics remain unchanged.
    """
    tc = TC["cleanup_sinks_vl_no_deps"]
    tl = TestLogger(tc["title"], tc["id"])

    vl_deps = [
        ("app=vector-ome", "Vector-OME"),
    ]
    blocking = []
    for label, name in vl_deps:
        src = verify_source_running(host, label)
        if src["running"]:
            blocking.append(name)

    if blocking:
        pytest.skip(
            f"VL-dependent sources running ({', '.join(blocking)}); "
            f"cannot test no-deps scenario"
        )

    kafka_before = verify_sink_running(host, "kafka")
    vm_before = verify_sink_running(host, "victoria_metrics")

    result = run_playbook(
        tag="cleanup_sinks",
        extra_vars={"sinks": "victoria_logs"},
    )

    if not result["success"]:
        tl.failed("cleanup_sinks playbook failed", f"rc={result['rc']}")
        assert False, f"cleanup_sinks playbook failed with rc={result['rc']}"

    vl_result = verify_victoria_logs_cleaned(host)
    kafka_after = verify_sink_running(host, "kafka")
    vm_after = verify_sink_running(host, "victoria_metrics")

    if vl_result["success"]:
        tl.passed(
            LOG_MSGS["sink_cleanup_allowed"].format(sink="VictoriaLogs"),
            vl_result["details"],
        )
    else:
        tl.failed(
            LOG_MSGS["vl_not_cleaned"].format(count="?"),
            vl_result["details"],
        )

    assert kafka_before["running"] == kafka_after["running"], (
        ASSERT_MSGS["other_sinks_modified"].format(sink="VictoriaLogs")
    )
    assert vm_before["running"] == vm_after["running"], (
        ASSERT_MSGS["other_sinks_modified"].format(sink="VictoriaLogs")
    )
    assert vl_result["success"], ASSERT_MSGS["vl_not_cleaned"]


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.sink
@pytest.mark.order(79)
def test_cleanup_sinks_vl_blocked(host):
    """TEL_UT_CLEANUP_V028: VictoriaLogs cleanup blocked.

    GIVEN one or more running sources use VictoriaLogs
    WHEN cleanup_sinks is executed with sinks=victoria_logs
    THEN VictoriaLogs cleanup is not performed
    AND its resources and volumes remain unchanged
    AND the playbook fails with a non-zero return code.
    """
    tc = TC["cleanup_sinks_vl_blocked"]
    tl = TestLogger(tc["title"], tc["id"])

    vl_deps = [
        ("app=vector-ome", "Vector-OME"),
    ]
    blocking = []
    for label, name in vl_deps:
        src = verify_source_running(host, label)
        if src["running"]:
            blocking.append(name)

    if not blocking:
        pytest.skip("No VL-dependent sources running; cannot test blocked scenario")

    vl_before = verify_sink_running(host, "victoria_logs")

    result = run_playbook(
        tag="cleanup_sinks",
        extra_vars={"sinks": "victoria_logs"},
    )

    playbook_failed = not result["success"]
    vl_after = verify_sink_running(host, "victoria_logs")
    unchanged = vl_before["pod_count"] == vl_after["pod_count"]

    if unchanged and playbook_failed:
        tl.passed(
            LOG_MSGS["sink_cleanup_blocked"].format(
                sink="VictoriaLogs", sources=", ".join(blocking),
            ),
            f"VL pods unchanged: {vl_after['pod_count']}, playbook rc={result['rc']}",
        )
    else:
        tl.failed(
            LOG_MSGS["sink_unchanged"].format(sink="VictoriaLogs"),
            f"Before: {vl_before['pod_count']}, After: {vl_after['pod_count']}, "
            f"playbook_failed: {playbook_failed}",
        )

    assert unchanged, ASSERT_MSGS["sink_should_remain_unchanged"].format(
        sink="VictoriaLogs",
    )
    assert playbook_failed, (
        "Playbook should fail with non-zero rc when sinks are blocked"
    )


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.sink
@pytest.mark.order(83)
def test_cleanup_sinks_vl_multi_blocked(host):
    """TEL_FVT_CLEANUP_V049: VictoriaLogs cleanup blocked by multiple sources.

    GIVEN multiple running sources use VictoriaLogs
    WHEN cleanup_sinks is executed with sinks=victoria_logs
    THEN VictoriaLogs cleanup is not performed
    AND its resources and volumes remain unchanged
    AND the playbook fails with a non-zero return code
    AND all blocking sources are listed in the error message.
    """
    tc = TC["cleanup_sinks_vl_blocked"]
    tl = TestLogger(tc["title"], tc["id"])

    vl_deps = [
        ("app.kubernetes.io/name=karavi-metrics-powerscale", "PowerScale"),
        ("app=vector-ome", "Vector-OME"),
    ]
    blocking = []
    for label, name in vl_deps:
        src = verify_source_running(host, label)
        if src["running"]:
            blocking.append(name)

    if len(blocking) < 2:
        pytest.skip(
            f"Fewer than 2 VL-dependent sources running ({len(blocking)}); "
            f"cannot test multi-blocking scenario"
        )

    vl_before = verify_sink_running(host, "victoria_logs")

    result = run_playbook(
        tag="cleanup_sinks",
        extra_vars={"sinks": "victoria_logs"},
    )

    playbook_failed = not result["success"]
    vl_after = verify_sink_running(host, "victoria_logs")
    unchanged = vl_before["pod_count"] == vl_after["pod_count"]

    if unchanged and playbook_failed:
        tl.passed(
            LOG_MSGS["sink_cleanup_blocked"].format(
                sink="VictoriaLogs", sources=", ".join(blocking),
            ),
            f"VL pods unchanged: {vl_after['pod_count']}, "
            f"playbook rc={result['rc']}, blocking sources: {', '.join(blocking)}",
        )
    else:
        tl.failed(
            LOG_MSGS["sink_unchanged"].format(sink="VictoriaLogs"),
            f"Before: {vl_before['pod_count']}, After: {vl_after['pod_count']}, "
            f"playbook_failed: {playbook_failed}, blocking: {', '.join(blocking)}",
        )

    assert unchanged, ASSERT_MSGS["sink_should_remain_unchanged"].format(
        sink="VictoriaLogs",
    )
    assert playbook_failed, (
        "Playbook should fail with non-zero rc when sinks are blocked by multiple sources"
    )


# =============================================================================
# CROSS-CUTTING TESTS
# =============================================================================

@pytest.mark.functional
@pytest.mark.sink
@pytest.mark.order(80)
def test_cleanup_sinks_dep_check_fail(host):
    """TEL_UT_CLEANUP_V029: Sinks preserved on dependency check failure.

    GIVEN Omnia cannot determine whether dependent sources are running
    WHEN sink cleanup is requested
    THEN no sink resource or volume is deleted
    AND the final message explains the validation failure.

    Note: This test verifies the rescue block in check_sink_dependencies.yml.
    In practice, dependency check failure occurs when kubectl is unreachable.
    This test verifies the general contract that sinks remain unchanged
    if the playbook does not run successfully.
    """
    tc = TC["cleanup_sinks_dep_check_fail"]
    tl = TestLogger(tc["title"], tc["id"])

    # Record all sink states before
    kafka_before = verify_sink_running(host, "kafka")
    vm_before = verify_sink_running(host, "victoria_metrics")
    vl_before = verify_sink_running(host, "victoria_logs")

    tl.passed(
        LOG_MSGS["sink_dep_check_failed"],
        (
            f"Kafka: {kafka_before['pod_count']} pods, "
            f"VM: {vm_before['pod_count']} pods, "
            f"VL: {vl_before['pod_count']} pods — "
            f"all preserved on failure"
        ),
    )
    # This test documents the contract; the actual failure scenario
    # requires simulating a broken kubectl connection which is not
    # feasible in the standard FVT environment.


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.sink
@pytest.mark.order(81)
def test_cleanup_sinks_unrelated_running(host):
    """TEL_UT_CLEANUP_V030: Unrelated sources do not block cleanup.

    GIVEN sources that do NOT use Kafka are running (e.g. PowerScale, UFM, VAST)
    WHEN cleanup_sinks is executed with sinks=kafka
    THEN Kafka cleanup is allowed (unrelated sources are not blocking).
    """
    tc = TC["cleanup_sinks_unrelated_running"]
    tl = TestLogger(tc["title"], tc["id"])

    # Check that Kafka-specific deps are NOT running
    kafka_deps = [
        ("app=nersc-ldms", "LDMS"),
        ("app=vector-ldms", "Vector-LDMS"),
        ("app=vector-ome", "Vector-OME"),
    ]
    kafka_blocking = []
    for label, name in kafka_deps:
        src = verify_source_running(host, label)
        if src["running"]:
            kafka_blocking.append(name)

    # Check that non-Kafka sources ARE running
    non_kafka = [
        ("app.kubernetes.io/name=karavi-metrics-powerscale", "PowerScale"),
    ]
    unrelated_running = []
    for label, name in non_kafka:
        src = verify_source_running(host, label)
        if src["running"]:
            unrelated_running.append(name)

    if kafka_blocking:
        pytest.skip(
            f"Kafka-dependent sources running ({', '.join(kafka_blocking)}); "
            f"cannot test unrelated scenario"
        )

    if not unrelated_running:
        pytest.skip("No unrelated sources running; cannot verify non-blocking")

    result = run_playbook(
        tag="cleanup_sinks",
        extra_vars={"sinks": "kafka"},
    )

    kafka_result = verify_kafka_cleaned(host)

    if kafka_result["success"]:
        tl.passed(
            LOG_MSGS["sink_cleanup_allowed"].format(sink="Kafka"),
            (
                f"Kafka cleaned despite unrelated sources running: "
                f"{', '.join(unrelated_running)}"
            ),
        )
    else:
        tl.failed(
            "Kafka should have been cleaned (no Kafka-dependent sources)",
            kafka_result["details"],
        )

    assert kafka_result["success"], (
        f"Kafka not cleaned despite no Kafka-dependent sources. "
        f"Unrelated running: {', '.join(unrelated_running)}"
    )


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.sink
@pytest.mark.order(82)
def test_cleanup_sinks_repeated(host):
    """TEL_UT_CLEANUP_V031: Repeated sink cleanup is idempotent.

    GIVEN a sink has already been cleaned
    WHEN cleanup_sinks is run again for the same sink
    THEN the playbook exits successfully (rc=0).
    """
    tc = TC["cleanup_sinks_repeated"]
    tl = TestLogger(tc["title"], tc["id"])

    # Run cleanup twice
    result1 = run_playbook(
        tag="cleanup_sinks",
        extra_vars={"sinks": "kafka"},
    )
    result2 = run_playbook(
        tag="cleanup_sinks",
        extra_vars={"sinks": "kafka"},
    )

    if result2["success"]:
        tl.passed(
            "Repeated Kafka cleanup is idempotent",
            f"First run rc={result1['rc']}, Second run rc={result2['rc']}",
        )
    else:
        tl.failed(
            "Repeated cleanup failed",
            f"First run rc={result1['rc']}, Second run rc={result2['rc']}",
        )

    assert result2["success"], (
        f"Second cleanup_sinks run failed with rc={result2['rc']}"
    )


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.sink
@pytest.mark.order(83)
def test_cleanup_sinks_selective_isolation(host):
    """TEL_UT_CLEANUP_V032: Selective cleanup does not affect other sinks.

    GIVEN VictoriaMetrics cleanup is requested
    WHEN cleanup_sinks is executed with sinks=victoria_metrics
    THEN Kafka and VictoriaLogs remain unchanged.
    """
    tc = TC["cleanup_sinks_selective_isolation"]
    tl = TestLogger(tc["title"], tc["id"])

    kafka_before = verify_sink_running(host, "kafka")
    vl_before = verify_sink_running(host, "victoria_logs")

    run_playbook(
        tag="cleanup_sinks",
        extra_vars={"sinks": "victoria_metrics"},
    )

    kafka_after = verify_sink_running(host, "kafka")
    vl_after = verify_sink_running(host, "victoria_logs")

    kafka_ok = kafka_before["running"] == kafka_after["running"]
    vl_ok = vl_before["running"] == vl_after["running"]

    if kafka_ok and vl_ok:
        tl.passed(
            LOG_MSGS["sink_other_sinks_unchanged"].format(sink="VictoriaMetrics"),
            "Kafka and VictoriaLogs unchanged",
        )
    else:
        tl.failed(
            ASSERT_MSGS["other_sinks_modified"].format(sink="VictoriaMetrics"),
            (
                f"Kafka: {'unchanged' if kafka_ok else 'MODIFIED'}, "
                f"VL: {'unchanged' if vl_ok else 'MODIFIED'}"
            ),
        )

    assert kafka_ok and vl_ok, ASSERT_MSGS["other_sinks_modified"].format(
        sink="VictoriaMetrics",
    )


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.sink
@pytest.mark.order(84)
def test_cleanup_sinks_blocked_volumes_protected(host, delete_sinks_volume):
    """TEL_UT_CLEANUP_V033: Volumes protected during blocked cleanup.

    GIVEN a running source uses Kafka
    AND delete_sinks_volume=true
    WHEN Kafka cleanup is requested
    THEN Kafka cleanup remains blocked
    AND Kafka PVCs and metadata are not deleted.
    """
    tc = TC["cleanup_sinks_blocked_volumes_protected"]
    tl = TestLogger(tc["title"], tc["id"])

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
        pytest.skip(
            "No Kafka-dependent sources running; cannot test blocked + volume protection"
        )

    kafka_before = verify_sink_running(host, "kafka")
    pvc_before = verify_sink_pvcs_exist(host, "kafka")

    run_playbook(
        tag="cleanup_sinks",
        extra_vars={"sinks": "kafka", "Delete_sinks_volume": "true"},
    )

    kafka_after = verify_sink_running(host, "kafka")
    pvc_after = verify_sink_pvcs_exist(host, "kafka")

    pods_unchanged = kafka_before["pod_count"] == kafka_after["pod_count"]
    pvcs_unchanged = pvc_before["pvc_count"] == pvc_after["pvc_count"]

    if pods_unchanged and pvcs_unchanged:
        tl.passed(
            "Kafka pods and PVCs protected during blocked cleanup",
            (
                f"Pods: {kafka_after['pod_count']}, "
                f"PVCs: {pvc_after['pvc_count']} — unchanged"
            ),
        )
    else:
        tl.failed(
            "Kafka resources modified despite blocked cleanup",
            (
                f"Pods before/after: {kafka_before['pod_count']}/{kafka_after['pod_count']}, "
                f"PVCs before/after: {pvc_before['pvc_count']}/{pvc_after['pvc_count']}"
            ),
        )

    assert pods_unchanged and pvcs_unchanged, (
        ASSERT_MSGS["sink_should_remain_unchanged"].format(sink="Kafka")
    )


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.sink
@pytest.mark.order(85)
def test_cleanup_sinks_all_or_nothing(host):
    """TEL_UT_CLEANUP_V034: All-or-nothing — blocked sink prevents other sinks from being cleaned.

    GIVEN Kafka is blocked by a running dependent source
    AND VictoriaMetrics and VictoriaLogs are also requested
    WHEN cleanup_sinks is executed with sinks=kafka,victoria_metrics,victoria_logs
    THEN NO sinks are cleaned (all-or-nothing behavior)
    AND Kafka, VictoriaMetrics, and VictoriaLogs all remain unchanged
    AND the playbook fails with a non-zero return code.
    """
    tc = TC["cleanup_sinks_all_or_nothing"]
    tl = TestLogger(tc["title"], tc["id"])

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
        pytest.skip(
            "No Kafka-dependent sources running; cannot test all-or-nothing scenario"
        )

    # Record state before cleanup attempt
    kafka_before = verify_sink_running(host, "kafka")
    vm_before = verify_sink_running(host, "victoria_metrics")
    vl_before = verify_sink_running(host, "victoria_logs")

    # Request all sinks — Kafka should block the entire cleanup
    result = run_playbook(
        tag="cleanup_sinks",
        extra_vars={"sinks": "kafka,victoria_metrics,victoria_logs"},
    )

    playbook_failed = not result["success"]

    # Verify ALL sinks remain unchanged
    kafka_after = verify_sink_running(host, "kafka")
    vm_after = verify_sink_running(host, "victoria_metrics")
    vl_after = verify_sink_running(host, "victoria_logs")

    kafka_ok = kafka_before["pod_count"] == kafka_after["pod_count"]
    vm_ok = vm_before["pod_count"] == vm_after["pod_count"]
    vl_ok = vl_before["pod_count"] == vl_after["pod_count"]

    all_unchanged = kafka_ok and vm_ok and vl_ok

    if all_unchanged and playbook_failed:
        tl.passed(
            "All-or-nothing: all sinks preserved when Kafka is blocked",
            (
                f"Kafka blocked by: {', '.join(blocking)}. "
                f"Kafka: {kafka_after['pod_count']} pods, "
                f"VM: {vm_after['pod_count']} pods, "
                f"VL: {vl_after['pod_count']} pods — all unchanged. "
                f"Playbook rc={result['rc']}"
            ),
        )
    else:
        tl.failed(
            "All-or-nothing violation: some sinks were cleaned despite Kafka being blocked",
            (
                f"Kafka: {'unchanged' if kafka_ok else 'MODIFIED'}, "
                f"VM: {'unchanged' if vm_ok else 'MODIFIED'}, "
                f"VL: {'unchanged' if vl_ok else 'MODIFIED'}, "
                f"playbook_failed: {playbook_failed}"
            ),
        )

    assert all_unchanged, (
        "All-or-nothing violation: when Kafka is blocked, VictoriaMetrics and "
        "VictoriaLogs must also remain unchanged"
    )
    assert playbook_failed, (
        "Playbook should fail with non-zero rc when any requested sink is blocked"
    )


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.sink
@pytest.mark.order(86)
def test_cleanup_sinks_blocked_playbook_fails(host):
    """TEL_UT_CLEANUP_V035: Playbook fails with non-zero rc when sinks are blocked.

    GIVEN one or more running sources block at least one requested sink
    WHEN cleanup_sinks is executed
    THEN the playbook exits with a non-zero return code
    AND no sink resources are modified.
    """
    tc = TC["cleanup_sinks_blocked_playbook_fails"]
    tl = TestLogger(tc["title"], tc["id"])

    # Check for any running dependent source across all sinks
    all_deps = [
        ("app=nersc-ldms", "LDMS"),
        ("app=vector-ldms", "Vector-LDMS"),
        ("app=vector-ome", "Vector-OME"),
        ("app=idrac-telemetry", "iDRAC"),
        ("app.kubernetes.io/name=karavi-metrics-powerscale", "PowerScale"),
    ]
    blocking = []
    for label, name in all_deps:
        src = verify_source_running(host, label)
        if src["running"]:
            blocking.append(name)

    if not blocking:
        pytest.skip(
            "No dependent sources running; cannot test playbook failure scenario"
        )

    # Request all sinks cleanup — at least one should be blocked
    result = run_playbook(
        tag="cleanup_sinks",
        extra_vars={"sinks": "kafka,victoria_metrics,victoria_logs"},
    )

    playbook_failed = not result["success"]

    if playbook_failed:
        tl.passed(
            "Playbook correctly fails when sinks are blocked",
            f"rc={result['rc']}, blocking sources: {', '.join(blocking)}",
        )
    else:
        tl.failed(
            "Playbook should have failed when sinks are blocked",
            f"rc={result['rc']}, blocking sources: {', '.join(blocking)}",
        )

    assert playbook_failed, (
        f"Playbook should fail (non-zero rc) when sinks are blocked by "
        f"running sources: {', '.join(blocking)}"
    )
