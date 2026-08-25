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
Telemetry — Test Case Registry.

Central registry mapping every test to its TC ID and title.
Test files reference ``TEST_CASES["key"]`` to get a consistent
test-case identifier and display name.

Usage in test files::

    from library.vars.test_case_vars import TEST_CASES as TC

    tc = TC["deploy_precheck"]
    tl = TestLogger(tc["title"], tc["id"])
"""

TEST_CASES = {
    # ── Precheck Scenario ─────────────────────────────────────────────────
    "deploy_precheck": {
        "id": "TC_PC_001",
        "title": "Deploy telemetry (precheck)",
    },
    "kube_vip_defined": {
        "id": "TC_PC_002",
        "title": "Verify kube_vip is defined in telemetry_config.yml",
    },
    "kube_vip_reachable": {
        "id": "TC_PC_003",
        "title": "Verify kube_vip is reachable (ICMP + SSH)",
    },
    "control_plane_ready": {
        "id": "TC_PC_004",
        "title": "Verify K8s control plane nodes are Ready",
    },
    "worker_nodes_ready": {
        "id": "TC_PC_005",
        "title": "Verify worker nodes meet minimum readiness threshold",
    },
    "pods_healthy": {
        "id": "TC_PC_006",
        "title": "Verify all pods (outside telemetry ns) are healthy",
    },
    "kubectl_available": {
        "id": "TC_PC_007",
        "title": "Verify kubectl is available on kube_vip",
    },

    # ── Validate Scenario ─────────────────────────────────────────────────
    "deploy_validate": {
        "id": "TC_VL_001",
        "title": "Deploy telemetry (validate)",
    },
    "config_file_exists": {
        "id": "TC_VL_002",
        "title": "Verify telemetry_config.yml exists on target",
    },
    "storage_config_exists": {
        "id": "TC_VL_003",
        "title": "Verify telemetry_storage_config.yml exists on target",
    },
    "packages_config_exists": {
        "id": "TC_VL_004",
        "title": "Verify telemetry_packages.yml exists on target",
    },
    "l1_schema_valid": {
        "id": "TC_VL_005",
        "title": "Verify L1 JSON schema validation passes for all input files",
    },
    "l2_logic_valid": {
        "id": "TC_VL_006",
        "title": "Verify L2 cross-field logic validation passes",
    },

    # ── Deploy Scenario ───────────────────────────────────────────────────
    "deploy_telemetry": {
        "id": "TC_DP_001",
        "title": "Deploy telemetry (execute/deploy)",
    },

    # ── Sink Verification ─────────────────────────────────────────────────
    "vm_cluster_pods": {
        "id": "TC_SK_001",
        "title": "Verify VictoriaMetrics cluster pods running",
    },
    "vm_persistence_size": {
        "id": "TC_SK_002",
        "title": "Verify VictoriaMetrics PVC sizes match config",
    },
    "vmagent_pods": {
        "id": "TC_SK_003",
        "title": "Verify vmagent pods running",
    },
    "vm_tls_secret": {
        "id": "TC_SK_004",
        "title": "Verify VictoriaMetrics TLS secret exists",
    },
    "vm_health": {
        "id": "TC_SK_005",
        "title": "Verify VictoriaMetrics health endpoint responds",
    },
    "vm_services": {
        "id": "TC_SK_006",
        "title": "Verify VictoriaMetrics services have endpoints",
    },
    "vl_cluster_pods": {
        "id": "TC_SK_007",
        "title": "Verify VictoriaLogs cluster pods running",
    },
    "vlagent_pods": {
        "id": "TC_SK_008",
        "title": "Verify VictoriaLogs vlagent pods running",
    },
    "kafka_pods": {
        "id": "TC_SK_009",
        "title": "Verify Kafka broker + controller pods running",
    },
    "kafka_ready": {
        "id": "TC_SK_010",
        "title": "Verify Kafka CR is Ready",
    },
    "kafka_bridge": {
        "id": "TC_SK_011",
        "title": "Verify Kafka bridge service running",
    },
    "kafka_persistence": {
        "id": "TC_SK_012",
        "title": "Verify Kafka persistence (PVCs exist)",
    },

    # ── Source Verification — iDRAC ───────────────────────────────────────
    "idrac_sts_ready": {
        "id": "TC_SR_001",
        "title": "Verify iDRAC StatefulSet pods ready",
    },
    "idrac_containers": {
        "id": "TC_SR_002",
        "title": "Verify all iDRAC containers running",
    },
    "idrac_kafka_topic": {
        "id": "TC_SR_003",
        "title": "Verify iDRAC Kafka topic 'idrac' exists",
    },
    "idrac_victoria_pump": {
        "id": "TC_SR_004",
        "title": "Verify iDRAC VictoriaPump metrics endpoint",
    },
    "idrac_service": {
        "id": "TC_SR_005",
        "title": "Verify iDRAC telemetry service exists",
    },

    # ── Source Verification — LDMS ────────────────────────────────────────
    "ldms_aggregator": {
        "id": "TC_SR_006",
        "title": "Verify LDMS aggregator StatefulSet ready",
    },
    "ldms_store": {
        "id": "TC_SR_007",
        "title": "Verify LDMS store daemon pod running",
    },
    "vector_ldms": {
        "id": "TC_SR_008",
        "title": "Verify Vector-LDMS bridge deployment ready",
    },
    "ldms_kafka_topic": {
        "id": "TC_SR_009",
        "title": "Verify LDMS Kafka topic exists",
    },
    "ldms_sampler_config": {
        "id": "TC_SR_010",
        "title": "Verify LDMS sampler config on NFS",
    },

    # ── Source Verification — OME ─────────────────────────────────────────
    "vector_ome": {
        "id": "TC_SR_011",
        "title": "Verify Vector-OME bridge deployment ready",
    },
    "ome_kafka_user": {
        "id": "TC_SR_012",
        "title": "Verify OME KafkaUser CR exists",
    },
    "ome_sink_prereqs": {
        "id": "TC_SR_013",
        "title": "Verify OME bridge sink prerequisites",
    },

    # ── Source Verification — DCGM (placeholder — excluded from Phase 3) ─
    "dcgm_pods_running": {
        "id": "TC_SR_014",
        "title": "Verify DCGM exporter pods running",
    },
    "dcgm_metrics_in_vm": {
        "id": "TC_SR_015",
        "title": "Verify DCGM metrics queryable from VictoriaMetrics",
    },

    # ── Source Verification — PowerScale ──────────────────────────────────
    "powerscale_csi_exporter": {
        "id": "TC_SR_016",
        "title": "Verify CSI volume exporter pods running",
    },
    "powerscale_metrics": {
        "id": "TC_SR_017",
        "title": "Verify PowerScale metrics in VictoriaMetrics",
    },

    # ── Source Verification — UFM ─────────────────────────────────────────
    "ufm_pods_running": {
        "id": "TC_SR_018",
        "title": "Verify UFM telemetry pods running",
    },
    "ufm_service": {
        "id": "TC_SR_019",
        "title": "Verify UFM external service created",
    },

    # ── Source Verification — VAST ────────────────────────────────────────
    "vast_pods_running": {
        "id": "TC_SR_020",
        "title": "Verify VAST telemetry pods running",
    },
    "vast_service": {
        "id": "TC_SR_021",
        "title": "Verify VAST external service created",
    },

    # ── Source Verification — SFM ─────────────────────────────────────────
    "sfm_pods_running": {
        "id": "TC_SR_022",
        "title": "Verify SFM telemetry pods running",
    },
    "sfm_manifests": {
        "id": "TC_SR_023",
        "title": "Verify SFM manifests generated",
    },

    # ── Cleanup Scenario ──────────────────────────────────────────────────
    "deploy_cleanup": {
        "id": "TC_CL_001",
        "title": "Deploy telemetry (cleanup)",
    },
    "cleanup_kafka": {
        "id": "TC_CL_002",
        "title": "Verify cleanup_kafka removes Kafka resources",
    },
    "cleanup_victoria_metrics": {
        "id": "TC_CL_003",
        "title": "Verify cleanup_victoria_metrics removes VM resources",
    },
    "cleanup_victoria_logs": {
        "id": "TC_CL_004",
        "title": "Verify cleanup_victoria_logs removes VL resources",
    },
    "cleanup_idrac": {
        "id": "TC_CL_005",
        "title": "Verify cleanup_idrac removes iDRAC resources",
    },
    "cleanup_ldms": {
        "id": "TC_CL_006",
        "title": "Verify cleanup_ldms removes LDMS + Vector-LDMS",
    },
    "cleanup_ome": {
        "id": "TC_CL_007",
        "title": "Verify cleanup_ome removes OME + Vector-OME",
    },
    "cleanup_dcgm": {
        "id": "TC_CL_008",
        "title": "Verify cleanup_dcgm removes DCGM resources",
    },
    "cleanup_ufm": {
        "id": "TC_CL_009",
        "title": "Verify cleanup_ufm removes UFM resources",
    },
    "cleanup_vast": {
        "id": "TC_CL_010",
        "title": "Verify cleanup_vast removes VAST resources",
    },
    "cleanup_sfm": {
        "id": "TC_CL_011",
        "title": "Verify cleanup_sfm removes SFM resources",
    },
    "no_pods_after_full_cleanup": {
        "id": "TC_CL_012",
        "title": "Verify no pods remain after full cleanup",
    },
    "no_pvcs_after_full_cleanup": {
        "id": "TC_CL_013",
        "title": "Verify no PVCs remain after full cleanup",
    },

    # ── Full E2E Scenario ─────────────────────────────────────────────────
    "deploy_full": {
        "id": "TC_TL_001",
        "title": "Deploy telemetry (full end-to-end)",
    },

    # ── NFT ───────────────────────────────────────────────────────────────
    "nft_validate_perf": {
        "id": "NFT_TL_001",
        "title": "Validate performance (< 30s)",
    },
    "nft_deploy_perf": {
        "id": "NFT_TL_002",
        "title": "Deploy performance (< 600s)",
    },
    "nft_cleanup_perf": {
        "id": "NFT_TL_003",
        "title": "Cleanup performance (< 300s)",
    },
    "nft_deploy_idempotent": {
        "id": "NFT_TL_004",
        "title": "Deploy idempotency (second run exits 0)",
    },
    "nft_cleanup_idempotent": {
        "id": "NFT_TL_005",
        "title": "Cleanup idempotency (second run exits 0)",
    },
}
