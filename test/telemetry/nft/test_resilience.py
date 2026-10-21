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

# pylint: disable=too-many-lines

"""
Telemetry -- Non-Functional Resilience Tests.

Verifies that the telemetry stack recovers gracefully from failures:
  - Setup deploy to ensure the stack is running before resilience tests
  - Pod deletion and automatic recreation by controllers
  - PVC persistence after pod restarts
  - Service endpoint availability after pod recreation
  - Data queryability after sink restart
  - Node reboot recovery
  - Full lifecycle (cleanup -> redeploy -> verify)
  - Operator pod recovery and CR reconciliation

Execution order (110-119):
  Runs AFTER deploy idempotency (105) and BEFORE cleanup tests (130+).
  Cleanup is intentionally placed last because it deletes credentials
  from the src flow — any deploy after cleanup would fail.

Test cases:
    TEL_NFT_018: Resilience setup deploy (order 110)
    TEL_NFT_006: Sink pod deletion & recovery (order 111)
    TEL_NFT_007: Source pod deletion & recovery (order 112)
    TEL_NFT_008: StatefulSet storage pod recovery (order 113)
    TEL_NFT_009: PVC persistence after pod deletion (order 114)
    TEL_NFT_010: Service endpoint availability (order 115)
    TEL_NFT_011: Data ingestion after sink restart (order 116)
    TEL_NFT_012: Node reboot recovery (order 117)
    TEL_NFT_023: iDRAC enable/disable/re-enable data lifecycle (order 118)
    TEL_NFT_024: OME metrics/logs channel lifecycle (order 119)
    TEL_NFT_013: Full lifecycle (cleanup -> redeploy) (order 120)
    TEL_NFT_014: Operator pod recovery (order 121)
"""

import time
from uuid import uuid4

import pytest

from omnia_auto import TestLogger, run_on_host, run_playbook

from library.vars.test_case_vars import TEST_CASES as TC
from library.vars.common_vars import (
    PLAYBOOK_ENTRY_POINT,
    PLAYBOOK_WORKDIR,
    KAFKA_POD_PREFIXES,
    VM_POD_PREFIXES,
    VL_POD_PREFIXES,
    IDRAC_POD_PREFIX,
    VECTOR_LDMS_APP_NAME,
    VECTOR_OME_APP_NAME,
)
from library.messages.telemetry_msgs import (
    TEST_LOG_MSGS as LOG_MSGS,
    TEST_ASSERT_MSGS as ASSERT_MSGS,
)
from library.functions.telemetry_func import (
    is_source_enabled,
    is_sink_enabled,
    is_sink_enabled_for_source,
    load_telemetry_config_from_target,
    resolve_kube_vip_ip,
)
from library.functions.k8s_func import verify_all_pods_running
from library.functions.idrac_func import (
    get_idrac_lifecycle_state,
    get_idrac_telemetry_config_path,
    probe_fresh_idrac_kafka_records,
    query_idrac_vm_samples,
    set_idrac_metrics_enabled,
    wait_for_fresh_idrac_vm_samples,
    wait_for_idrac_replicas,
)
from library.functions.ome_lifecycle_func import (
    get_ome_lifecycle_state,
    get_ome_telemetry_config_path,
    publish_ome_lifecycle_records,
    query_ome_lifecycle_data,
    set_ome_channel_state,
    wait_for_ome_lifecycle_data,
    wait_for_ome_workloads,
)
from library.functions.ome_func import get_ome_pipeline_context
from library.functions.resilience_func import (
    verify_pod_recreation,
    verify_all_pvcs_bound,
    verify_service_endpoints_available,
    verify_data_queryable_after_restart,
    reboot_node_and_wait,
    verify_pods_after_reboot,
    verify_operator_recovery,
    delete_pods_by_prefix,
)

# Recovery timeouts (seconds)
SINK_RECOVERY_TIMEOUT = 300       # 5 minutes
SOURCE_RECOVERY_TIMEOUT = 300     # 5 minutes
STS_RECOVERY_TIMEOUT = 600        # 10 minutes (storage pods take longer)
OPERATOR_RECOVERY_TIMEOUT = 300   # 5 minutes
NODE_REBOOT_TIMEOUT = 600         # 10 minutes for node + pods
POD_READY_AFTER_REBOOT = 600      # 10 minutes for all pods after reboot
LIFECYCLE_DEPLOY_TIMEOUT = 720    # 12 minutes (cleanup + deploy)

# Core services that must have endpoints after recovery
CORE_SERVICES = [
    "kafka-kafka-bootstrap",
    "vmselect-victoria-cluster",
    "vminsert-victoria-cluster",
    "vlselect-victoria-logs-cluster",
]


# =========================================================================
# Helpers
# =========================================================================

def _get_enabled_source_prefixes(host):
    """Return pod prefixes for enabled telemetry sources."""
    prefixes = []
    if is_source_enabled(host, "idrac"):
        prefixes.append(IDRAC_POD_PREFIX)
    if is_source_enabled(host, "ldms"):
        prefixes.append(VECTOR_LDMS_APP_NAME)
    if is_source_enabled(host, "ome"):
        prefixes.append(VECTOR_OME_APP_NAME)
    return prefixes


# =========================================================================
# TEL_NFT_018: Resilience Setup Deploy
# =========================================================================

@pytest.mark.nft
@pytest.mark.resilience
@pytest.mark.order(110)
def test_resilience_setup_deploy(host):
    """TEL_NFT_018: Deploy telemetry stack before resilience tests.

    Ensures all telemetry components are deployed and pods are Running
    before any pod-deletion or recovery tests begin.  Deploy
    idempotency (order 105) leaves the stack deployed, but this step
    acts as a safety net to guarantee a known-good state — just like
    FVT deploy runs before verify tests.
    """
    tc = TC["nft_resilience_setup"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Deploying telemetry stack for resilience tests")
    result = run_playbook(
        playbook=PLAYBOOK_ENTRY_POINT,
        playbook_workdir=PLAYBOOK_WORKDIR,
        tag="execute",
        timeout=LIFECYCLE_DEPLOY_TIMEOUT,
    )

    if result["rc"] != 0:
        output_lines = result.get("output", "").strip().split("\n")
        tail = "\n".join(output_lines[-30:])
        tl.failed(
            LOG_MSGS["deploy_failed"],
            f"Resilience setup deploy failed (rc={result['rc']}). "
            f"All subsequent resilience tests require a deployed stack.\n"
            f"Last output:\n{tail}",
        )
        pytest.fail(
            f"Resilience setup deploy failed (rc={result['rc']}). "
            f"Cannot run resilience tests without a deployed stack."
        )

    # Verify all pods are Running after deploy
    tl.check("Verifying all pods are Running after setup deploy")
    pod_result = verify_all_pods_running(host)

    if pod_result["success"]:
        tl.passed(
            LOG_MSGS["all_pods_running"].format(
                total=pod_result["total_pods"],
            ),
            f"Deploy: rc={result['rc']} ({result.get('duration', 'N/A')}s)\n"
            f"Pods: {pod_result['running_count']}/{pod_result['total_pods']} Running",
        )
    else:
        not_running = [p["name"] for p in pod_result.get("not_running_pods", [])]
        tl.failed(
            LOG_MSGS["some_pods_not_running"].format(
                not_running=pod_result["not_running_count"],
                total=pod_result["total_pods"],
            ),
            f"Not running: {', '.join(not_running[:10])}",
        )

    assert result["rc"] == 0, (
        f"Resilience setup deploy failed (rc={result['rc']})"
    )
    assert pod_result["success"], (
        f"After setup deploy: {pod_result['not_running_count']}/"
        f"{pod_result['total_pods']} pods not Running"
    )


# =========================================================================
# TEL_NFT_006: Sink Pod Deletion & Recovery
# =========================================================================

@pytest.mark.nft
@pytest.mark.resilience
@pytest.mark.order(111)
def test_sink_pod_deletion_recovery(host):
    """TEL_NFT_006: Delete Kafka broker pods and verify automatic recovery.

    Validates that Kubernetes controllers (StatefulSet) automatically
    recreate deleted sink pods within the recovery timeout.
    """
    tc = TC["nft_sink_pod_recovery"]
    tl = TestLogger(tc["title"], tc["id"])
    prefix = KAFKA_POD_PREFIXES["broker"]

    tl.check(f"Deleting pods with prefix '{prefix}' and waiting for recovery")
    result = verify_pod_recreation(
        host, prefix, expected=3, timeout=SINK_RECOVERY_TIMEOUT,
    )

    if result["success"]:
        tl.passed(
            LOG_MSGS["pod_recovery_passed"].format(
                prefix=prefix,
                elapsed=result["recovery"].get("elapsed", "N/A"),
            ),
            result["details"],
        )
    else:
        tl.failed(
            LOG_MSGS["pod_recovery_failed"].format(
                prefix=prefix,
                error=result.get("error", ""),
            ),
            result["details"],
        )

    assert result["success"], ASSERT_MSGS["pod_recovery_failed"].format(
        prefix=prefix,
        error=result.get("error", ""),
    )


# =========================================================================
# TEL_NFT_007: Source Pod Deletion & Recovery
# =========================================================================

@pytest.mark.nft
@pytest.mark.resilience
@pytest.mark.order(112)
def test_source_pod_deletion_recovery(host):
    """TEL_NFT_007: Delete enabled source pods and verify recovery.

    Skipped if no sources are enabled. Validates that source pods
    (iDRAC, Vector bridges) are recreated by their controllers.
    """
    tc = TC["nft_source_pod_recovery"]
    tl = TestLogger(tc["title"], tc["id"])

    prefixes = _get_enabled_source_prefixes(host)
    if not prefixes:
        pytest.skip("No telemetry sources enabled -- nothing to test")

    all_success = True
    all_details = []

    for prefix in prefixes:
        tl.check(f"Testing recovery for source pod prefix '{prefix}'")
        result = verify_pod_recreation(
            host, prefix, expected=1, timeout=SOURCE_RECOVERY_TIMEOUT,
        )
        all_details.append(f"{prefix}: {result['details']}")
        if not result["success"]:
            all_success = False

    combined = "\n".join(all_details)

    if all_success:
        tl.passed(
            LOG_MSGS["pod_recovery_passed"].format(
                prefix=", ".join(prefixes), elapsed="all recovered",
            ),
            combined,
        )
    else:
        tl.failed(
            LOG_MSGS["pod_recovery_failed"].format(
                prefix=", ".join(prefixes), error="some sources failed",
            ),
            combined,
        )

    assert all_success, ASSERT_MSGS["pod_recovery_failed"].format(
        prefix=", ".join(prefixes),
        error=f"Recovery failures:\n{combined}",
    )


# =========================================================================
# TEL_NFT_008: StatefulSet Storage Pod Recovery
# =========================================================================

@pytest.mark.nft
@pytest.mark.resilience
@pytest.mark.order(113)
def test_sts_storage_pod_recovery(host):
    """TEL_NFT_008: Delete VictoriaMetrics/Logs storage pods & verify recovery.

    Storage pods (vmstorage, vlstorage) are backed by PVCs and managed
    by StatefulSets. They must be recreated with the same identity and
    re-attach their persistent volumes.

    Skips disabled sinks (e.g., if victoria_logs is not enabled, vlstorage
    pods won't exist and the test skips that part).
    """
    tc = TC["nft_sts_pod_recovery"]
    tl = TestLogger(tc["title"], tc["id"])

    # Check which sinks are enabled
    sts_prefixes = []
    if is_sink_enabled(host, "victoria_metrics"):
        sts_prefixes.append((VM_POD_PREFIXES["vmstorage"], 3))
    if is_sink_enabled(host, "victoria_logs"):
        sts_prefixes.append((VL_POD_PREFIXES["vlstorage"], 3))

    if not sts_prefixes:
        pytest.skip("No storage sinks (VictoriaMetrics/Logs) enabled")

    all_success = True
    all_details = []

    for prefix, expected in sts_prefixes:
        tl.check(f"Testing STS pod recovery for '{prefix}'")
        result = verify_pod_recreation(
            host, prefix, expected=expected, timeout=STS_RECOVERY_TIMEOUT,
        )
        all_details.append(f"{prefix}: {result['details']}")
        if not result["success"]:
            all_success = False

    combined = "\n".join(all_details)
    enabled_sinks = ", ".join([p[0] for p in sts_prefixes])

    if all_success:
        tl.passed(
            LOG_MSGS["sts_recovery_passed"].format(
                prefixes=enabled_sinks,
            ),
            combined,
        )
    else:
        tl.failed(
            LOG_MSGS["sts_recovery_failed"].format(
                prefixes=enabled_sinks,
            ),
            combined,
        )

    assert all_success, ASSERT_MSGS["sts_recovery_failed"].format(
        details=combined,
    )


# =========================================================================
# TEL_NFT_009: PVC Persistence After Pod Deletion
# =========================================================================

@pytest.mark.nft
@pytest.mark.resilience
@pytest.mark.order(114)
def test_pvc_persistence_after_pod_deletion(host):
    """TEL_NFT_009: Verify all PVCs remain Bound after pod deletions.

    After the preceding pod deletion tests, PVCs must remain in
    Bound state, proving that persistent data survives pod restarts.
    """
    tc = TC["nft_pvc_persistence"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying all PVCs remain in Bound state")
    result = verify_all_pvcs_bound(host)

    if result["success"]:
        tl.passed(
            LOG_MSGS["pvcs_bound"].format(
                total=result["total"], bound=result["bound"],
            ),
            result["details"],
        )
    else:
        tl.failed(
            LOG_MSGS["pvcs_not_bound"].format(
                not_bound=result["not_bound"],
                total=result["total"],
            ),
            result["details"],
        )

    assert result["success"], ASSERT_MSGS["pvcs_not_bound"].format(
        not_bound=result["not_bound"],
        names=", ".join(result.get("not_bound_names", [])),
    )


# =========================================================================
# TEL_NFT_010: Service Endpoint Availability After Pod Restart
# =========================================================================

@pytest.mark.nft
@pytest.mark.resilience
@pytest.mark.order(115)
def test_service_endpoints_after_restart(host):
    """TEL_NFT_010: Verify core services have endpoints after pod restart.

    After pod deletion and recreation, LoadBalancer and ClusterIP
    services must have active endpoints (backing pods registered).

    Skips disabled sinks (e.g., if victoria_logs is not enabled,
    vlselect service won't have endpoints).
    """
    tc = TC["nft_service_endpoints"]
    tl = TestLogger(tc["title"], tc["id"])

    # Filter services by enabled sinks
    enabled_services = []
    for svc in CORE_SERVICES:
        if "kafka" in svc and is_sink_enabled(host, "kafka"):
            enabled_services.append(svc)
        elif "vmselect" in svc and is_sink_enabled(host, "victoria_metrics"):
            enabled_services.append(svc)
        elif "vminsert" in svc and is_sink_enabled(host, "victoria_metrics"):
            enabled_services.append(svc)
        elif "vlselect" in svc and is_sink_enabled(host, "victoria_logs"):
            enabled_services.append(svc)

    if not enabled_services:
        pytest.skip("No core services enabled (all sinks disabled)")

    tl.check(f"Verifying service endpoints for {len(enabled_services)} enabled service(s)")
    result = verify_service_endpoints_available(host, enabled_services)

    if result["success"]:
        tl.passed(
            LOG_MSGS["services_available"].format(
                count=len(result["available"]),
            ),
            result["details"],
        )
    else:
        tl.failed(
            LOG_MSGS["services_unavailable"].format(
                unavailable=", ".join(result["unavailable"]),
            ),
            result["details"],
        )

    assert result["success"], ASSERT_MSGS["services_unavailable"].format(
        unavailable=", ".join(result["unavailable"]),
    )


# =========================================================================
# TEL_NFT_011: Data Ingestion After Sink Restart
# =========================================================================

@pytest.mark.nft
@pytest.mark.resilience
@pytest.mark.order(116)
def test_data_queryable_after_sink_restart(host):
    """TEL_NFT_011: Verify VictoriaMetrics data is queryable after restart.

    After vmstorage pods were deleted and recreated (TEL_NFT_008),
    historical metric data must still be queryable via vmselect.
    """
    tc = TC["nft_data_after_restart"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Querying VictoriaMetrics for data after pod restart")
    result = verify_data_queryable_after_restart(
        host, query="up", min_results=1,
    )

    if result["success"]:
        tl.passed(
            LOG_MSGS["data_queryable"].format(
                count=result["result_count"], query=result["query"],
            ),
            result["details"],
        )
    else:
        tl.failed(
            LOG_MSGS["data_not_queryable"].format(
                query=result["query"],
                error=result.get("error", ""),
            ),
            result["details"],
        )

    assert result["success"], ASSERT_MSGS["data_not_queryable"].format(
        query=result["query"],
        error=result.get("error", ""),
    )


# =========================================================================
# TEL_NFT_012: Node Reboot Recovery
# =========================================================================

@pytest.mark.nft
@pytest.mark.resilience
@pytest.mark.order(117)
def test_node_reboot_recovery(host):
    """TEL_NFT_012: Verify all pods recover after kube_vip node reboot.

    Reboots the kube_vip node via SSH and waits for all telemetry
    pods to return to Running state.

    WARNING: This test causes real downtime. It is skipped if the
    kube_vip IP cannot be resolved (e.g., in CI environments).
    """
    tc = TC["nft_node_reboot"]
    tl = TestLogger(tc["title"], tc["id"])

    kube_vip_ip = resolve_kube_vip_ip(host)
    if not kube_vip_ip:
        pytest.skip("kube_vip IP not resolved -- cannot test node reboot")

    # Step 1: Reboot the node
    tl.check(f"Rebooting kube_vip node ({kube_vip_ip})")
    reboot_result = reboot_node_and_wait(
        host, kube_vip_ip, wait_timeout=NODE_REBOOT_TIMEOUT,
    )

    if not reboot_result["success"]:
        tl.failed(
            LOG_MSGS["node_reboot_failed"].format(
                node_ip=kube_vip_ip,
            ),
            reboot_result.get("error", "Node did not come back"),
        )
        pytest.fail(
            f"Node {kube_vip_ip} did not come back after reboot: "
            f"{reboot_result['error']}"
        )

    # Step 2: Wait for all pods to recover
    tl.check("Waiting for all telemetry pods to return to Running")
    pod_result = verify_pods_after_reboot(
        host, timeout=POD_READY_AFTER_REBOOT,
    )

    if pod_result["success"]:
        tl.passed(
            LOG_MSGS["node_reboot_passed"].format(
                node_ip=kube_vip_ip,
                elapsed=pod_result["elapsed"],
                total=pod_result["total_pods"],
            ),
            pod_result["details"],
        )
    else:
        tl.failed(
            LOG_MSGS["node_reboot_pods_failed"].format(
                running=pod_result["running_count"],
                total=pod_result["total_pods"],
            ),
            pod_result["details"],
        )

    assert pod_result["success"], ASSERT_MSGS["node_reboot_failed"].format(
        running=pod_result["running_count"],
        total=pod_result["total_pods"],
        details=pod_result["details"],
    )


# =========================================================================
# TEL_NFT_023: iDRAC Enable -> Disable -> Re-enable Data Lifecycle
# =========================================================================


def _assert_idrac_storage_identity(baseline, current, phase):
    """Assert the StatefulSet, PVCs, and bound PV names were reused."""
    assert current["statefulset"]["uid"] == baseline["statefulset"]["uid"], (
        f"iDRAC StatefulSet UID changed during {phase}"
    )
    assert current["pvcs"] == baseline["pvcs"], (
        f"iDRAC PVC UID/PV identity changed during {phase}: "
        f"before={baseline['pvcs']}, after={current['pvcs']}"
    )
    assert current["kafka_topic"] == baseline["kafka_topic"], (
        f"iDRAC Kafka topic identity changed during {phase}"
    )
    assert current["pvcs"], "No iDRAC MySQL PVCs were found"
    assert all(
        pvc["phase"] == "Bound" and pvc["volume_name"]
        for pvc in current["pvcs"].values()
    ), f"One or more iDRAC PVCs are not Bound during {phase}"


@pytest.mark.nft
@pytest.mark.resilience
@pytest.mark.order(118)
def test_idrac_data_lifecycle(host):  # pylint: disable=too-many-locals,too-many-statements,too-many-function-args
    """Verify data flow stops and resumes without replacing iDRAC storage.

    The test starts Kafka consumers at ``latest`` so historical records cannot
    satisfy fresh-data checks. VictoriaMetrics is queried through the raw
    export API so only stored samples in the requested wall-clock window are
    counted. The original config file is restored byte-for-byte in ``finally``.
    """
    if not is_source_enabled(host, "idrac"):
        pytest.skip("iDRAC must initially be enabled for lifecycle validation")
    if not is_sink_enabled_for_source(host, "idrac", "kafka"):
        pytest.skip("iDRAC Kafka collection target is not enabled")
    if not is_sink_enabled_for_source(host, "idrac", "victoria_metrics"):
        pytest.skip("iDRAC VictoriaMetrics collection target is not enabled")

    tc = TC["nft_idrac_data_lifecycle"]
    tl = TestLogger(tc["title"], tc["id"])
    config_path = get_idrac_telemetry_config_path(host)
    backup_path = f"{config_path}.idrac-lifecycle-{uuid4().hex}.bak"

    baseline = get_idrac_lifecycle_state(host)
    assert baseline["success"], baseline["error"]
    expected_replicas = baseline["statefulset"]["replicas"]
    assert expected_replicas > 0, "iDRAC has no enabled replicas at test start"
    _assert_idrac_storage_identity(baseline, baseline, "baseline")

    backup = run_on_host(  # pylint: disable=too-many-function-args
        host, "cp --preserve=all -- %s %s", config_path, backup_path,
    )
    assert backup.rc == 0, f"Unable to back up {config_path}: {backup.stderr}"

    baseline_vm_start = time.time()
    restored = False
    success_details = ""
    try:
        tl.check("Confirming fresh iDRAC records in Kafka before disable")
        kafka_before = probe_fresh_idrac_kafka_records(host, timeout_seconds=90)
        assert kafka_before["success"], (
            "No fresh iDRAC Kafka record before disable: "
            f"{kafka_before.get('error', '')}"
        )

        tl.check("Confirming fresh iDRAC samples in VictoriaMetrics before disable")
        vm_before = wait_for_fresh_idrac_vm_samples(
            host, baseline_vm_start, timeout_seconds=90,
        )
        assert vm_before["success"], vm_before["error"]
        baseline_vm_end = time.time()

        tl.check("Disabling iDRAC through telemetry reconciliation")
        update = set_idrac_metrics_enabled(host, False)
        assert update["success"], update["error"]
        disable_run = run_playbook(
            playbook=PLAYBOOK_ENTRY_POINT,
            playbook_workdir=PLAYBOOK_WORKDIR,
            tag="execute",
            timeout=LIFECYCLE_DEPLOY_TIMEOUT,
        )
        assert disable_run["rc"] == 0, (
            f"iDRAC disable deploy failed: {disable_run.get('output', '')[-2000:]}"
        )

        disabled_wait = wait_for_idrac_replicas(host, 0, timeout=300)
        assert disabled_wait["success"], disabled_wait["error"]
        disabled = disabled_wait["state"]
        assert (
            disabled["statefulset"]["desired_replicas_annotation"]
            == expected_replicas
        ), "Saved iDRAC replica annotation does not match the enabled state"
        _assert_idrac_storage_identity(baseline, disabled, "disable")

        # Allow any records already buffered before pod termination to drain.
        time.sleep(30)
        disabled_vm_start = time.time()

        tl.check("Confirming no new iDRAC Kafka records while disabled")
        kafka_disabled = probe_fresh_idrac_kafka_records(
            host, timeout_seconds=60,
        )
        assert not kafka_disabled["error"], kafka_disabled["error"]
        assert not kafka_disabled["records"], (
            "Fresh iDRAC Kafka records arrived while the source was disabled: "
            f"{kafka_disabled['records'][:3]}"
        )

        tl.check("Confirming no new iDRAC VictoriaMetrics samples while disabled")
        vm_disabled = query_idrac_vm_samples(
            host, disabled_vm_start, time.time(),
        )
        assert vm_disabled["success"], vm_disabled["error"]
        assert vm_disabled["sample_count"] == 0, (
            f"{vm_disabled['sample_count']} new iDRAC VM samples arrived "
            "while disabled"
        )

        historical_disabled = query_idrac_vm_samples(
            host, baseline_vm_start, baseline_vm_end,
        )
        assert historical_disabled["success"], historical_disabled["error"]
        assert historical_disabled["sample_count"] > 0, (
            "Pre-disable VictoriaMetrics history was not queryable after disable"
        )

        tl.check("Re-enabling iDRAC through telemetry reconciliation")
        update = set_idrac_metrics_enabled(host, True)
        assert update["success"], update["error"]
        reenable_started = time.time()
        enable_run = run_playbook(
            playbook=PLAYBOOK_ENTRY_POINT,
            playbook_workdir=PLAYBOOK_WORKDIR,
            tag="execute",
            timeout=LIFECYCLE_DEPLOY_TIMEOUT,
        )
        assert enable_run["rc"] == 0, (
            f"iDRAC re-enable deploy failed: {enable_run.get('output', '')[-2000:]}"
        )

        enabled_wait = wait_for_idrac_replicas(
            host, expected_replicas, timeout=600,
        )
        assert enabled_wait["success"], enabled_wait["error"]
        reenabled = enabled_wait["state"]
        _assert_idrac_storage_identity(baseline, reenabled, "re-enable")

        tl.check("Confirming fresh Kafka records after iDRAC re-enable")
        kafka_after = probe_fresh_idrac_kafka_records(host, timeout_seconds=90)
        assert kafka_after["success"], (
            "No fresh iDRAC Kafka record after re-enable: "
            f"{kafka_after.get('error', '')}"
        )

        assert (
            kafka_after["records"][0]["offset"]
            > kafka_before["records"][0]["offset"]
        ), "iDRAC Kafka offset did not advance after re-enable"

        tl.check("Confirming fresh and historical VictoriaMetrics data")
        vm_after = wait_for_fresh_idrac_vm_samples(
            host, reenable_started, timeout_seconds=90,
        )
        assert vm_after["success"], vm_after["error"]
        historical_after = query_idrac_vm_samples(
            host, baseline_vm_start, baseline_vm_end,
        )
        assert historical_after["success"], historical_after["error"]
        assert historical_after["sample_count"] > 0, (
            "Pre-disable VictoriaMetrics history disappeared after re-enable"
        )

        restored = True
        success_details = (
            f"StatefulSet UID: {baseline['statefulset']['uid']}\n"
            f"PVCs: {baseline['pvcs']}\n"
            f"Kafka topic: {baseline['kafka_topic']}\n"
            f"Kafka before offset: {kafka_before['records'][0]['offset']}\n"
            f"Kafka after offset: {kafka_after['records'][0]['offset']}\n"
            f"VM historical samples: {historical_after['sample_count']}\n"
            f"VM new samples: {vm_after['sample_count']}"
        )
    finally:
        restore = run_on_host(  # pylint: disable=too-many-function-args
            host, "cp --preserve=all -- %s %s", backup_path, config_path,
        )
        remove_backup_rc = -1
        restore_run_rc = -1
        if restore.rc == 0:
            remove_backup = run_on_host(  # pylint: disable=too-many-function-args
                host, "rm -f -- %s", backup_path,
            )
            remove_backup_rc = remove_backup.rc
            restore_run = run_playbook(
                playbook=PLAYBOOK_ENTRY_POINT,
                playbook_workdir=PLAYBOOK_WORKDIR,
                tag="execute",
                timeout=LIFECYCLE_DEPLOY_TIMEOUT,
            )
            restore_run_rc = restore_run["rc"]
        # Keep the backup for manual recovery when the copy itself failed.
        if restore.rc != 0 or remove_backup_rc != 0 or restore_run_rc != 0:
            pytest.fail(
                "Failed to restore original telemetry configuration/state: "
                f"copy_rc={restore.rc}, remove_rc={remove_backup_rc}, "
                f"deploy_rc={restore_run_rc}, backup={backup_path}"
            )

    assert restored, "iDRAC lifecycle did not complete"
    tl.passed(
        "iDRAC disable/re-enable preserved storage and data continuity",
        success_details,
    )


# =========================================================================
# TEL_NFT_024: OME Metrics/Logs Channel Lifecycle
# =========================================================================


def _assert_ome_resource_identity(baseline, current, phase):
    """Assert OME retained resources and shared infrastructure were reused."""
    assert current["retained"] == baseline["retained"], (
        f"OME retained resource identity changed during {phase}: "
        f"before={baseline['retained']}, after={current['retained']}"
    )
    assert current["shared_resources"] == baseline["shared_resources"], (
        f"Shared Kafka/Victoria resource identity changed during {phase}: "
        f"before={baseline['shared_resources']}, "
        f"after={current['shared_resources']}"
    )


@pytest.mark.nft
@pytest.mark.resilience
@pytest.mark.order(119)
@pytest.mark.ome
def test_ome_channel_data_lifecycle(host):  # pylint: disable=too-many-locals,too-many-statements
    """Exercise all OME channel states with unique records on every topic.

    OME is external, so disabling an Omnia channel stops Vector routing rather
    than stopping OME's Kafka producer. Each phase publishes a unique fixture
    record to all five pre-existing OME topics, then verifies only enabled
    channels reach Victoria. The original input is restored byte-for-byte.
    """
    context = get_ome_pipeline_context(host)
    if not context["metrics_pipeline_enabled"]:
        pytest.skip("OME metrics pipeline must initially be enabled")
    if not context["logs_pipeline_enabled"]:
        pytest.skip("OME logs pipeline must initially be enabled")

    tc = TC["nft_ome_channel_lifecycle"]
    tl = TestLogger(tc["title"], tc["id"])
    config_path = get_ome_telemetry_config_path(host)
    backup_path = f"{config_path}.ome-lifecycle-{uuid4().hex}.bak"

    baseline = get_ome_lifecycle_state(host)
    assert baseline["success"], baseline["error"]
    vector_replicas = baseline["deployments"]["vector-ome"]["replicas"]
    metrics_replicas = baseline["deployments"]["vmagent-vector"]["replicas"]
    logs_replicas = baseline["deployments"]["vlagent-vector"]["replicas"]
    assert vector_replicas > 0, "vector-ome is not enabled at test start"
    assert metrics_replicas > 0, "vmagent-vector is not enabled at test start"
    assert logs_replicas > 0, "vlagent-vector is not enabled at test start"

    config = load_telemetry_config_from_target(host)
    ldms_source = config.get("telemetry_sources", {}).get("ldms", {})
    ldms_bridge = config.get("telemetry_bridges", {}).get(
        "vector_ldms", {},
    )
    ldms_uses_vmagent = (
        ldms_source.get("metrics_enabled") is True
        and ldms_bridge.get("metrics_enabled") is True
    )

    backup = run_on_host(  # pylint: disable=too-many-function-args
        host, "cp --preserve=all -- %s %s", config_path, backup_path,
    )
    assert backup.rc == 0, f"Unable to back up {config_path}: {backup.stderr}"

    previous_config = baseline["vector_config"]
    stage_results = {}
    completed = False

    def exercise_stage(label, metrics_enabled, logs_enabled):  # pylint: disable=too-many-locals
        nonlocal previous_config
        tl.check(
            f"Reconciling OME {label}: metrics={metrics_enabled}, "
            f"logs={logs_enabled}"
        )
        update = set_ome_channel_state(
            host, metrics_enabled, logs_enabled,
        )
        assert update["success"], update["error"]
        deploy = run_playbook(
            playbook=PLAYBOOK_ENTRY_POINT,
            playbook_workdir=PLAYBOOK_WORKDIR,
            tag="execute",
            timeout=LIFECYCLE_DEPLOY_TIMEOUT,
        )
        assert deploy["rc"] == 0, (
            f"OME {label} deploy failed: "
            f"{deploy.get('output', '')[-2000:]}"
        )

        desired_vector = vector_replicas if (
            metrics_enabled or logs_enabled
        ) else 0
        desired_metrics = metrics_replicas if (
            metrics_enabled or ldms_uses_vmagent
        ) else 0
        desired_logs = logs_replicas if logs_enabled else 0
        wait = wait_for_ome_workloads(
            host,
            desired_vector,
            desired_metrics,
            desired_logs,
            timeout=600,
        )
        assert wait["success"], wait["error"]
        state = wait["state"]
        _assert_ome_resource_identity(baseline, state, label)

        if metrics_enabled or logs_enabled:
            assert (
                ("[sinks.victoria_metrics]" in state["vector_config"])
                is metrics_enabled
            ), f"Unexpected OME metrics sink in {label} configuration"
            assert (
                ("[sinks.victoria_logs]" in state["vector_config"])
                is logs_enabled
            ), f"Unexpected OME logs sink in {label} configuration"
        else:
            assert state["vector_config"] == previous_config, (
                "Fully disabled OME must retain the last generated ConfigMap"
            )

        marker = f"ome-nft-{label}-{uuid4().hex}"
        marker_started = time.time() - 1
        published = publish_ome_lifecycle_records(host, marker)
        assert published["success"], published["error"]
        assert len(published["topics"]) == 5, (
            f"Expected all five OME topics, got {published['topics']}"
        )
        assert all(
            result["success"] for result in published["topics"].values()
        ), f"One or more OME Kafka topic writes failed: {published['topics']}"

        if metrics_enabled or logs_enabled:
            routed = wait_for_ome_lifecycle_data(
                host,
                marker,
                marker_started,
                expect_metrics=metrics_enabled,
                expect_logs=logs_enabled,
                timeout=120,
            )
            assert routed["success"], routed["error"]

        # Give an incorrectly retained route enough time to expose itself.
        time.sleep(20)
        observed = query_ome_lifecycle_data(
            host, marker, marker_started, time.time(),
        )
        assert observed["success"], observed["error"]
        if metrics_enabled:
            assert all(observed["metric_counts"].values()), (
                f"Not all OME metric topics reached VictoriaMetrics in {label}: "
                f"{observed['metric_counts']}"
            )
        else:
            assert not any(observed["metric_counts"].values()), (
                f"Disabled OME metrics reached VictoriaMetrics in {label}: "
                f"{observed['metric_counts']}"
            )
        if logs_enabled:
            assert all(observed["log_counts"].values()), (
                f"Not all OME log topics reached VictoriaLogs in {label}: "
                f"{observed['log_counts']}"
            )
        else:
            assert not any(observed["log_counts"].values()), (
                f"Disabled OME logs reached VictoriaLogs in {label}: "
                f"{observed['log_counts']}"
            )

        previous_config = state["vector_config"]
        stage_results[label] = {
            "marker": marker,
            "started": marker_started,
            "published_topics": sorted(published["topics"]),
            "observed": observed,
            "replicas": {
                name: value["replicas"]
                for name, value in state["deployments"].items()
            },
        }
        return state

    try:
        # Same-state apply proves idempotent reconciliation before transitions.
        exercise_stage("both", True, True)
        exercise_stage("metrics-only", True, False)
        exercise_stage("logs-only", False, True)
        disabled = exercise_stage("disabled", False, False)
        assert disabled["deployments"]["vector-ome"]["replicas"] == 0

        baseline_marker = stage_results["both"]
        historical = query_ome_lifecycle_data(
            host,
            baseline_marker["marker"],
            baseline_marker["started"],
            time.time(),
        )
        assert historical["success"], historical["error"]
        assert all(historical["metric_counts"].values()), (
            "OME metric history disappeared while fully disabled"
        )
        assert all(historical["log_counts"].values()), (
            "OME log history disappeared while fully disabled"
        )

        restored_state = exercise_stage("restored", True, True)
        assert (
            restored_state["deployments"]["vector-ome"]["replicas"]
            == vector_replicas
        ), "vector-ome did not return to its configured replica count"
        completed = True
    finally:
        restore = run_on_host(  # pylint: disable=too-many-function-args
            host, "cp --preserve=all -- %s %s", backup_path, config_path,
        )
        remove_backup_rc = -1
        restore_run_rc = -1
        if restore.rc == 0:
            remove_backup = run_on_host(  # pylint: disable=too-many-function-args
                host, "rm -f -- %s", backup_path,
            )
            remove_backup_rc = remove_backup.rc
            restore_run = run_playbook(
                playbook=PLAYBOOK_ENTRY_POINT,
                playbook_workdir=PLAYBOOK_WORKDIR,
                tag="execute",
                timeout=LIFECYCLE_DEPLOY_TIMEOUT,
            )
            restore_run_rc = restore_run["rc"]
        if restore.rc != 0 or remove_backup_rc != 0 or restore_run_rc != 0:
            pytest.fail(
                "Failed to restore original OME configuration/state: "
                f"copy_rc={restore.rc}, remove_rc={remove_backup_rc}, "
                f"deploy_rc={restore_run_rc}, backup={backup_path}"
            )

    assert completed, "OME channel lifecycle did not complete"
    tl.passed(
        "OME channel disable/re-enable preserved identities and routing",
        str(stage_results),
    )


# =========================================================================
# TEL_NFT_013: Full Lifecycle (Cleanup -> Redeploy -> Verify)
# =========================================================================

@pytest.mark.nft
@pytest.mark.resilience
@pytest.mark.order(120)
def test_full_lifecycle(host):
    """TEL_NFT_013: Complete cleanup and redeployment cycle.

    Runs cleanup to tear down the telemetry stack, then redeploys
    and verifies all pods return to Running state.

    NOTE: This test is sensitive to cluster state after cleanup.
    If cleanup leaves credentials or config in a bad state, redeploy
    may fail with rc=2 (config error). This is expected behavior and
    indicates the cleanup playbook needs to be more thorough.
    """
    tc = TC["nft_full_lifecycle"]
    tl = TestLogger(tc["title"], tc["id"])

    # Step 1: Cleanup (preserve credentials so redeploy can reuse them)
    tl.check("Running cleanup playbook with credential preservation")
    cleanup = run_playbook(
        playbook=PLAYBOOK_ENTRY_POINT,
        playbook_workdir=PLAYBOOK_WORKDIR,
        tag="cleanup",
        extra_vars={"cleanup_credentials": "false"},
        timeout=300,
    )

    if cleanup["rc"] != 0:
        output_lines = cleanup.get("output", "").strip().split("\n")
        tail = "\n".join(output_lines[-20:])
        tl.failed(
            LOG_MSGS["cleanup_failed"],
            f"Cleanup failed (rc={cleanup['rc']})\nLast output:\n{tail}",
        )
        pytest.fail(f"Cleanup phase failed (rc={cleanup['rc']})")

    # Step 2: Redeploy (with retry for transient failures)
    tl.check("Running deploy playbook after cleanup")
    deploy = None
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        tl.check(f"Deploy attempt {attempt}/{max_retries}")
        deploy = run_playbook(
            playbook=PLAYBOOK_ENTRY_POINT,
            playbook_workdir=PLAYBOOK_WORKDIR,
            tag="execute",
            timeout=LIFECYCLE_DEPLOY_TIMEOUT,
        )
        if deploy["rc"] == 0:
            break
        if attempt < max_retries:
            tl.check(f"Deploy attempt {attempt} failed (rc={deploy['rc']}), retrying...")
            # Wait a bit before retry to allow cluster to stabilize
            time.sleep(10)

    if deploy["rc"] != 0:
        output_lines = deploy.get("output", "").strip().split("\n")
        tail = "\n".join(output_lines[-30:])
        tl.failed(
            LOG_MSGS["deploy_failed"],
            f"Redeploy failed after {max_retries} attempt(s) (rc={deploy['rc']})\n"
            f"Last output:\n{tail}",
        )
        pytest.fail(f"Redeploy phase failed (rc={deploy['rc']}) after {max_retries} retries")

    # Step 3: Verify all pods running
    tl.check("Verifying all pods are Running after redeploy")
    pod_result = verify_all_pods_running(host)

    if pod_result["success"]:
        tl.passed(
            LOG_MSGS["lifecycle_passed"].format(
                cleanup_dur=cleanup.get("duration", "N/A"),
                deploy_dur=deploy.get("duration", "N/A"),
                total=pod_result["total_pods"],
            ),
            f"Cleanup: rc={cleanup['rc']} ({cleanup.get('duration', 'N/A')}s)\n"
            f"Deploy: rc={deploy['rc']} ({deploy.get('duration', 'N/A')}s)\n"
            f"Pods: {pod_result['running_count']}/{pod_result['total_pods']} Running",
        )
    else:
        not_running = [p["name"] for p in pod_result.get("not_running_pods", [])]
        tl.failed(
            LOG_MSGS["lifecycle_failed"].format(
                not_running=len(not_running),
            ),
            f"Not running: {', '.join(not_running[:10])}",
        )

    assert pod_result["success"], ASSERT_MSGS["lifecycle_failed"].format(
        running=pod_result["running_count"],
        total=pod_result["total_pods"],
    )


# =========================================================================
# TEL_NFT_014: Operator Pod Recovery
# =========================================================================

@pytest.mark.nft
@pytest.mark.resilience
@pytest.mark.order(121)
def test_operator_pod_recovery(host):
    """TEL_NFT_014: Delete operator pods and verify CR reconciliation.

    Deletes the VictoriaMetrics operator and Strimzi operator pods,
    then verifies they are recreated and their CRs remain healthy.

    Skips operators that are not actually deployed in the cluster.
    """
    tc = TC["nft_operator_recovery"]
    tl = TestLogger(tc["title"], tc["id"])

    # Check which operators are actually deployed (by checking if pods exist)
    # We use delete_pods_by_prefix to list pods, but don't actually delete them
    operators = []

    # Check for VictoriaMetrics operator
    vm_check = delete_pods_by_prefix(host, "victoria-metrics-operator")
    if vm_check["count"] > 0:
        operators.append({
            "kind": "victoria_metrics",
            "name": "VictoriaMetrics Operator",
        })

    # Check for Strimzi operator
    strimzi_check = delete_pods_by_prefix(host, "strimzi-cluster-operator")
    if strimzi_check["count"] > 0:
        operators.append({
            "kind": "strimzi",
            "name": "Strimzi Cluster Operator",
        })

    if not operators:
        pytest.skip("No operators deployed in cluster")

    all_success = True
    all_details = []

    for op in operators:
        tl.check(f"Testing recovery for {op['name']}")
        result = verify_operator_recovery(
            host, op["kind"],
            timeout=OPERATOR_RECOVERY_TIMEOUT,
        )
        all_details.append(f"{op['name']}: {result['details']}")
        if not result["success"]:
            all_success = False

    combined = "\n".join(all_details)

    if all_success:
        tl.passed(
            LOG_MSGS["operator_recovery_passed"],
            combined,
        )
    else:
        tl.failed(
            LOG_MSGS["operator_recovery_failed"],
            combined,
        )

    assert all_success, ASSERT_MSGS["operator_recovery_failed"].format(
        details=combined,
    )
