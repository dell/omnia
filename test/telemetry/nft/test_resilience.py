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
Telemetry -- Non-Functional Resilience Tests.

Verifies that the telemetry stack recovers gracefully from failures:
  - Pod deletion and automatic recreation by controllers
  - PVC persistence after pod restarts
  - Service endpoint availability after pod recreation
  - Data queryability after sink restart
  - Node reboot recovery
  - Full lifecycle (cleanup -> redeploy -> verify)
  - Operator pod recovery and CR reconciliation

Test cases:
    NFT_TL_006: Sink pod deletion & recovery (Kafka broker)
    NFT_TL_007: Source pod deletion & recovery (enabled sources)
    NFT_TL_008: StatefulSet storage pod recovery (vmstorage/vlstorage)
    NFT_TL_009: PVC persistence after pod deletion
    NFT_TL_010: Service endpoint availability after pod restart
    NFT_TL_011: Data ingestion after sink restart
    NFT_TL_012: Node reboot recovery
    NFT_TL_013: Full lifecycle (cleanup -> redeploy -> verify)
    NFT_TL_014: Operator pod recovery
"""

import pytest

from omnia_auto import TestLogger, run_playbook

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
    TELEMETRY_NAMESPACE,
)
from library.messages.telemetry_msgs import (
    TEST_LOG_MSGS as LOG_MSGS,
    TEST_ASSERT_MSGS as ASSERT_MSGS,
)
from library.functions.telemetry_func import (
    is_source_enabled,
    resolve_kube_vip_ip,
)
from library.functions.k8s_func import verify_all_pods_running
from library.functions.resilience_func import (
    verify_pod_recreation,
    verify_all_pvcs_bound,
    verify_service_endpoints_available,
    verify_data_queryable_after_restart,
    reboot_node_and_wait,
    verify_pods_after_reboot,
    verify_operator_recovery,
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
# NFT_TL_006: Sink Pod Deletion & Recovery
# =========================================================================

@pytest.mark.nft
@pytest.mark.resilience
@pytest.mark.order(120)
def test_sink_pod_deletion_recovery(host):
    """NFT_TL_006: Delete Kafka broker pods and verify automatic recovery.

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
# NFT_TL_007: Source Pod Deletion & Recovery
# =========================================================================

@pytest.mark.nft
@pytest.mark.resilience
@pytest.mark.order(121)
def test_source_pod_deletion_recovery(host):
    """NFT_TL_007: Delete enabled source pods and verify recovery.

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
# NFT_TL_008: StatefulSet Storage Pod Recovery
# =========================================================================

@pytest.mark.nft
@pytest.mark.resilience
@pytest.mark.order(122)
def test_sts_storage_pod_recovery(host):
    """NFT_TL_008: Delete VictoriaMetrics/Logs storage pods & verify recovery.

    Storage pods (vmstorage, vlstorage) are backed by PVCs and managed
    by StatefulSets. They must be recreated with the same identity and
    re-attach their persistent volumes.
    """
    tc = TC["nft_sts_pod_recovery"]
    tl = TestLogger(tc["title"], tc["id"])

    sts_prefixes = [
        (VM_POD_PREFIXES["vmstorage"], 3),
        (VL_POD_PREFIXES["vlstorage"], 3),
    ]

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

    if all_success:
        tl.passed(
            LOG_MSGS["sts_recovery_passed"].format(
                prefixes="vmstorage, vlstorage",
            ),
            combined,
        )
    else:
        tl.failed(
            LOG_MSGS["sts_recovery_failed"].format(
                prefixes="vmstorage, vlstorage",
            ),
            combined,
        )

    assert all_success, ASSERT_MSGS["sts_recovery_failed"].format(
        details=combined,
    )


# =========================================================================
# NFT_TL_009: PVC Persistence After Pod Deletion
# =========================================================================

@pytest.mark.nft
@pytest.mark.resilience
@pytest.mark.order(123)
def test_pvc_persistence_after_pod_deletion(host):
    """NFT_TL_009: Verify all PVCs remain Bound after pod deletions.

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
# NFT_TL_010: Service Endpoint Availability After Pod Restart
# =========================================================================

@pytest.mark.nft
@pytest.mark.resilience
@pytest.mark.order(124)
def test_service_endpoints_after_restart(host):
    """NFT_TL_010: Verify core services have endpoints after pod restart.

    After pod deletion and recreation, LoadBalancer and ClusterIP
    services must have active endpoints (backing pods registered).
    """
    tc = TC["nft_service_endpoints"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying service endpoints for core services")
    result = verify_service_endpoints_available(host, CORE_SERVICES)

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
# NFT_TL_011: Data Ingestion After Sink Restart
# =========================================================================

@pytest.mark.nft
@pytest.mark.resilience
@pytest.mark.order(125)
def test_data_queryable_after_sink_restart(host):
    """NFT_TL_011: Verify VictoriaMetrics data is queryable after restart.

    After vmstorage pods were deleted and recreated (NFT_TL_008),
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
# NFT_TL_012: Node Reboot Recovery
# =========================================================================

@pytest.mark.nft
@pytest.mark.resilience
@pytest.mark.order(126)
def test_node_reboot_recovery(host):
    """NFT_TL_012: Verify all pods recover after kube_vip node reboot.

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
# NFT_TL_013: Full Lifecycle (Cleanup -> Redeploy -> Verify)
# =========================================================================

@pytest.mark.nft
@pytest.mark.resilience
@pytest.mark.order(127)
def test_full_lifecycle(host):
    """NFT_TL_013: Complete cleanup and redeployment cycle.

    Runs cleanup to tear down the telemetry stack, then redeploys
    and verifies all pods return to Running state.
    """
    tc = TC["nft_full_lifecycle"]
    tl = TestLogger(tc["title"], tc["id"])

    # Step 1: Cleanup
    tl.check("Running cleanup playbook")
    cleanup = run_playbook(
        playbook=PLAYBOOK_ENTRY_POINT,
        playbook_workdir=PLAYBOOK_WORKDIR,
        tag="cleanup",
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

    # Step 2: Redeploy
    tl.check("Running deploy playbook after cleanup")
    deploy = run_playbook(
        playbook=PLAYBOOK_ENTRY_POINT,
        playbook_workdir=PLAYBOOK_WORKDIR,
        tag="execute",
        timeout=LIFECYCLE_DEPLOY_TIMEOUT,
    )

    if deploy["rc"] != 0:
        output_lines = deploy.get("output", "").strip().split("\n")
        tail = "\n".join(output_lines[-30:])
        tl.failed(
            LOG_MSGS["deploy_failed"],
            f"Redeploy failed (rc={deploy['rc']})\nLast output:\n{tail}",
        )
        pytest.fail(f"Redeploy phase failed (rc={deploy['rc']})")

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
# NFT_TL_014: Operator Pod Recovery
# =========================================================================

@pytest.mark.nft
@pytest.mark.resilience
@pytest.mark.order(128)
def test_operator_pod_recovery(host):
    """NFT_TL_014: Delete operator pods and verify CR reconciliation.

    Deletes the VictoriaMetrics operator and Strimzi operator pods,
    then verifies they are recreated and their CRs remain healthy.
    """
    tc = TC["nft_operator_recovery"]
    tl = TestLogger(tc["title"], tc["id"])

    operators = [
        {
            "prefix": "victoria-metrics-operator",
            "cr_cmd": (
                f"kubectl get vmcluster -n {TELEMETRY_NAMESPACE} "
                f"-o jsonpath='{{.items[0].status.clusterStatus}}' 2>/dev/null"
            ),
            "name": "VictoriaMetrics Operator",
        },
        {
            "prefix": "strimzi-cluster-operator",
            "cr_cmd": (
                f"kubectl get kafka kafka -n {TELEMETRY_NAMESPACE} "
                f"-o jsonpath='{{.status.conditions[?(@.type==\"Ready\")].status}}'"
                f" 2>/dev/null"
            ),
            "name": "Strimzi Cluster Operator",
        },
    ]

    all_success = True
    all_details = []

    for op in operators:
        tl.check(f"Testing recovery for {op['name']}")
        result = verify_operator_recovery(
            host, op["prefix"], op["cr_cmd"],
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
