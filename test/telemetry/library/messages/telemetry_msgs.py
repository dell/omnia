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
Telemetry — Centralized Log and Assert Messages.

All user-facing messages used in test output and assertions.
Test files import these instead of hardcoding strings.
"""

# =============================================================================
# LOG MESSAGES (for TestLogger.passed / .failed / .check)
# =============================================================================

TEST_LOG_MSGS = {
    # ── Precheck ──────────────────────────────────────────────────────────
    "precheck_passed": "Telemetry precheck playbook completed successfully",
    "precheck_failed": "Telemetry precheck playbook failed",
    "kube_vip_defined": "kube_vip is defined: {kube_vip}",
    "kube_vip_not_defined": "kube_vip is not defined in telemetry_config.yml",
    "kube_vip_reachable": "kube_vip {kube_vip} is reachable (ping + SSH)",
    "kube_vip_not_reachable": "kube_vip {kube_vip} is not reachable",
    "ping_ok": "Ping to {host} succeeded",
    "ping_failed": "Ping to {host} failed",
    "ssh_ok": "SSH to {host} succeeded",
    "ssh_failed": "SSH to {host} failed",
    "control_plane_ready": "All {count} control plane nodes are Ready",
    "control_plane_not_ready": (
        "{not_ready} of {total} control plane nodes are NOT Ready"
    ),
    "workers_ready": "Worker nodes meet readiness threshold ({ready}/{total})",
    "workers_not_ready": (
        "Worker nodes below readiness threshold ({ready}/{total})"
    ),
    "pods_healthy": "All {count} pods (outside telemetry ns) are healthy",
    "pods_unhealthy": "{unhealthy} of {total} pods are NOT healthy",
    "kubectl_available": "kubectl is available on kube_vip",
    "kubectl_not_available": "kubectl is not available on kube_vip",

    # ── Validate ──────────────────────────────────────────────────────────
    "validate_passed": "Telemetry validation playbook completed successfully",
    "validate_failed": "Telemetry validation playbook failed",
    "file_exists": "{filename} exists on target at {path}",
    "file_missing": "{filename} NOT found on target at {path}",
    "l1_valid": "L1 schema validation passed for all input files",
    "l1_invalid": "L1 schema validation failed",
    "l2_valid": "L2 logic validation passed",
    "l2_invalid": "L2 logic validation failed",

    # ── Deploy ────────────────────────────────────────────────────────────
    "deploy_passed": "Telemetry deploy playbook completed successfully",
    "deploy_failed": "Telemetry deploy playbook failed",

    # ── Sinks ─────────────────────────────────────────────────────────────
    "pods_running": "All {component} pods are running ({count}/{expected})",
    "pods_not_running": (
        "{component} pods not fully running ({running}/{expected})"
    ),
    "pvc_size_match": "PVC sizes match config: {size}",
    "pvc_size_mismatch": "PVC size mismatch detected",
    "tls_secret_exists": "TLS secret '{secret}' exists in {namespace}",
    "tls_secret_missing": "TLS secret '{secret}' NOT found in {namespace}",
    "health_ok": "{component} health endpoint responded OK",
    "health_failed": "{component} health endpoint did not respond",
    "services_ok": "{component} services have endpoints",
    "services_missing": "{component} services missing endpoints",
    "kafka_topics_ok": "Expected Kafka topics found: {topics}",
    "kafka_topics_missing": "Kafka topics missing: {missing}",

    # ── Sources ────────────────────────────────────────────────────────────
    "containers_ready": "All containers in pod '{pod}' are ready ({count} containers)",
    "containers_not_ready": (
        "Containers not ready in pod '{pod}': {not_ready}"
    ),
    "topic_exists": "Kafka topic '{topic}' exists",
    "topic_missing": "Kafka topic '{topic}' NOT found",

    # ── Cleanup ───────────────────────────────────────────────────────────
    "cleanup_passed": "Telemetry cleanup playbook completed successfully",
    "cleanup_failed": "Telemetry cleanup playbook failed",
    "component_cleaned": "{component} resources removed successfully",
    "component_not_cleaned": "{component} resources still present after cleanup",
    "no_pods_remaining": "No pods remain in telemetry namespace",
    "pods_remaining": "{count} pods still present in telemetry namespace",
    "no_pvcs_remaining": "No PVCs remain in telemetry namespace",
    "pvcs_remaining": "{count} PVCs still present in telemetry namespace",

    # ── Cleanup — granular source/sink ─────────────────────────────────
    "idrac_cleaned": "iDRAC telemetry resources removed successfully",
    "idrac_not_cleaned": "iDRAC telemetry resources still present",
    "ldms_cleaned": "LDMS + Vector-LDMS resources removed successfully",
    "ldms_not_cleaned": "LDMS + Vector-LDMS resources still present",
    "ome_cleaned": "OME + Vector-OME resources removed successfully",
    "ome_not_cleaned": "OME + Vector-OME resources still present",
    "dcgm_cleaned": "DCGM resources removed successfully",
    "dcgm_not_cleaned": "DCGM resources still present",
    "ufm_cleaned": "UFM resources removed successfully",
    "ufm_not_cleaned": "UFM resources still present",
    "vast_cleaned": "VAST resources removed successfully",
    "vast_not_cleaned": "VAST resources still present",
    "sfm_cleaned": "SFM resources removed successfully",
    "sfm_not_cleaned": "SFM resources still present",
    "kafka_cleaned": "Kafka resources removed successfully",
    "kafka_not_cleaned": "Kafka resources still present",
    "vm_cleaned": "VictoriaMetrics resources removed successfully",
    "vm_not_cleaned": "VictoriaMetrics resources still present",
    "vl_cleaned": "VictoriaLogs resources removed successfully",
    "vl_not_cleaned": "VictoriaLogs resources still present",

    # ── Idempotency ────────────────────────────────────────────────────
    "idempotent_passed": (
        "Cleanup idempotency verified: second run exited 0 "
        "(duration={duration}s)"
    ),
    "idempotent_failed": (
        "Cleanup idempotency failed: second run exited {rc}"
    ),
}

# =============================================================================
# ASSERT MESSAGES (for pytest assert statements)
# =============================================================================

TEST_ASSERT_MSGS = {
    # ── Precheck ──────────────────────────────────────────────────────────
    "precheck_failed": (
        "Telemetry precheck failed with exit code {rc}. "
        "Check the playbook output for details."
    ),
    "kube_vip_not_defined": (
        "kube_vip is not defined in telemetry_config.yml. "
        "Add 'kube_vip: <VIP_IP>' to the config file."
    ),
    "kube_vip_not_reachable": (
        "kube_vip {kube_vip} is not reachable. "
        "Verify the IP is correct and the host is up."
    ),
    "control_plane_not_ready": (
        "K8s control plane nodes not all Ready: "
        "{not_ready} of {total} are NOT Ready. "
        "Check node status with: kubectl get nodes"
    ),
    "workers_not_ready": (
        "Worker nodes below minimum readiness threshold: "
        "{ready}/{total} Ready (need at least {minimum}). "
        "Check node status with: kubectl get nodes"
    ),
    "pods_unhealthy": (
        "Pods outside telemetry namespace are unhealthy: "
        "{unhealthy} of {total} are NOT Running/Succeeded."
    ),
    "kubectl_not_available": (
        "kubectl is not available on kube_vip. "
        "Ensure K8s is properly installed."
    ),

    # ── Validate ──────────────────────────────────────────────────────────
    "validate_failed": (
        "Telemetry validation failed with exit code {rc}. "
        "Check the playbook output for validation errors."
    ),
    "file_missing": (
        "{filename} not found at {path}. "
        "Run domain-init.sh to stage input files."
    ),
    "l1_invalid": (
        "L1 schema validation failed: {errors}. "
        "Fix the input files to match the JSON schema."
    ),
    "l2_invalid": (
        "L2 logic validation failed: {errors}. "
        "Fix cross-field validation errors in the input files."
    ),

    # ── Deploy ────────────────────────────────────────────────────────────
    "deploy_failed": (
        "Telemetry deploy failed with exit code {rc}."
    ),

    # ── Sinks ─────────────────────────────────────────────────────────────
    "pods_not_running": (
        "{component} pods not running: {running}/{expected}. "
        "Check: kubectl get pods -n telemetry"
    ),
    "pvc_size_mismatch": (
        "PVC size mismatch for {component}: "
        "expected {expected}, actual {actual}."
    ),
    "tls_secret_missing": (
        "TLS secret '{secret}' not found in namespace {namespace}."
    ),
    "health_failed": (
        "{component} health check failed. Service may not be ready."
    ),
    "kafka_topics_missing": (
        "Expected Kafka topics missing: {missing}."
    ),
    "topic_missing": (
        "Kafka topic '{topic}' not found."
    ),

    # ── Cleanup ───────────────────────────────────────────────────────────
    "cleanup_failed": (
        "Telemetry cleanup failed with exit code {rc}."
    ),
    "component_not_cleaned": (
        "{component} resources still present after cleanup."
    ),
    "pods_remaining": (
        "{count} pods still present in telemetry namespace after cleanup."
    ),
    "pvcs_remaining": (
        "{count} PVCs still present in telemetry namespace after cleanup."
    ),
    "idrac_not_cleaned": (
        "iDRAC resources still present after cleanup. "
        "Check: kubectl get pods -n telemetry -l app=idrac-telemetry"
    ),
    "ldms_not_cleaned": (
        "LDMS/Vector-LDMS resources still present after cleanup. "
        "Check: kubectl get pods -n telemetry | grep -E 'nersc-ldms|vector-ldms'"
    ),
    "ome_not_cleaned": (
        "OME/Vector-OME resources still present after cleanup. "
        "Check: kubectl get pods -n telemetry | grep vector-ome"
    ),
    "dcgm_not_cleaned": (
        "DCGM resources still present after cleanup. "
        "Check: kubectl get pods -n telemetry | grep dcgm"
    ),
    "ufm_not_cleaned": (
        "UFM resources still present after cleanup. "
        "Check: kubectl get pods -n telemetry | grep ufm"
    ),
    "vast_not_cleaned": (
        "VAST resources still present after cleanup. "
        "Check: kubectl get pods -n telemetry | grep vast"
    ),
    "sfm_not_cleaned": (
        "SFM resources still present after cleanup. "
        "Check: kubectl get pods -n telemetry | grep sfm"
    ),
    "kafka_not_cleaned": (
        "Kafka resources still present after cleanup. "
        "Check: kubectl get pods -n telemetry | grep -E 'kafka|strimzi'"
    ),
    "vm_not_cleaned": (
        "VictoriaMetrics resources still present after cleanup. "
        "Check: kubectl get pods -n telemetry | grep -E 'vm|victoria-metrics'"
    ),
    "vl_not_cleaned": (
        "VictoriaLogs resources still present after cleanup. "
        "Check: kubectl get pods -n telemetry | grep -E 'vl|vlagent'"
    ),
    "idempotent_failed": (
        "Cleanup idempotency check failed. Second cleanup run returned "
        "exit code {rc}. A cleanup playbook must be safe to run multiple "
        "times without errors."
    ),
}
