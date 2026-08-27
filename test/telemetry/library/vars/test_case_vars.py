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

    tc = TC["deploy_telemetry"]
    tl = TestLogger(tc["title"], tc["id"])
"""

TEST_CASES = {
    # -- Deploy (one per scenario) ------------------------------------------
    "deploy_telemetry": {
        "id": "TC_DP_001",
        "title": "Deploy telemetry (full stack)",
    },
    "deploy_deploy": {
        "id": "TC_DP_002",
        "title": "Deploy telemetry (--tags deploy)",
    },
    "deploy_precheck": {
        "id": "TC_PC_001",
        "title": "Deploy telemetry (--tags precheck)",
    },
    "deploy_validate": {
        "id": "TC_VL_001",
        "title": "Deploy telemetry (--tags validate)",
    },
    "deploy_cleanup": {
        "id": "TC_CL_001",
        "title": "Deploy telemetry (--tags cleanup)",
    },

    # -- Precheck -----------------------------------------------------------
    "env_vars_present": {
        "id": "TC_PC_002",
        "title": "Verify omnia.env variables present",
    },
    "k8s_nodes_ready": {
        "id": "TC_PC_003",
        "title": "Verify K8s nodes are Ready",
    },
    "kube_vip_reachable": {
        "id": "TC_PC_004",
        "title": "Verify kube_vip is reachable",
    },

    # -- Sinks: Kafka -------------------------------------------------------
    "kafka_pods": {
        "id": "TC_SK_001",
        "title": "Verify Kafka broker/controller pods running",
    },
    "kafka_ready": {
        "id": "TC_SK_002",
        "title": "Verify Kafka cluster Ready condition",
    },
    "kafka_bridge": {
        "id": "TC_SK_003",
        "title": "Verify Kafka bridge pod running",
    },

    # -- Sinks: VictoriaMetrics ---------------------------------------------
    "vm_cluster_pods": {
        "id": "TC_SK_004",
        "title": "Verify VictoriaMetrics cluster pods running",
    },
    "vmagent_pods": {
        "id": "TC_SK_005",
        "title": "Verify VMAgent pods running",
    },

    # -- Sinks: VictoriaLogs ------------------------------------------------
    "vl_cluster_pods": {
        "id": "TC_SK_006",
        "title": "Verify VictoriaLogs cluster pods running",
    },
    "vlagent_pods": {
        "id": "TC_SK_007",
        "title": "Verify VLAgent pods running",
    },

    # -- Namespace-wide pod check -------------------------------------------
    "all_pods_running": {
        "id": "TC_NS_001",
        "title": "Verify all telemetry pods running",
    },

    # -- Sources: iDRAC -----------------------------------------------------
    "idrac_pod_count": {
        "id": "TC_SR_001",
        "title": "Verify iDRAC pod count matches bmc_group_data.csv",
    },
    "idrac_sts_ready": {
        "id": "TC_SR_002",
        "title": "Verify iDRAC StatefulSet pods ready",
    },
    "idrac_containers": {
        "id": "TC_SR_003",
        "title": "Verify all iDRAC containers running",
    },
    "idrac_mysql_data": {
        "id": "TC_SR_004",
        "title": "Verify MySQL data in iDRAC telemetry pods",
    },
    "idrac_receiver_collecting": {
        "id": "TC_SR_005",
        "title": "Verify iDRAC receiver is collecting metrics",
    },
    "idrac_kafka_topic": {
        "id": "TC_SR_006",
        "title": "Verify iDRAC Kafka topic exists",
    },
    "idrac_victoria_pump": {
        "id": "TC_SR_007",
        "title": "Verify iDRAC VictoriaPump metrics endpoint",
    },
    "idrac_service": {
        "id": "TC_SR_008",
        "title": "Verify iDRAC telemetry service exists",
    },
    "idrac_vm_data": {
        "id": "TC_SR_009",
        "title": "Verify iDRAC telemetry data in VictoriaMetrics",
    },

    # -- Sources: LDMS ------------------------------------------------------
    "ldms_aggr_pod": {
        "id": "TC_SR_020",
        "title": "Verify LDMS aggregator pod running",
    },
    "ldms_store_pod": {
        "id": "TC_SR_021",
        "title": "Verify LDMS store pod running",
    },
    "ldms_vector_bridge": {
        "id": "TC_SR_022",
        "title": "Verify Vector-LDMS bridge deployment ready",
    },
    "ldms_kafka_topic": {
        "id": "TC_SR_023",
        "title": "Verify LDMS Kafka topic exists",
    },

    # -- Sources: PowerScale ------------------------------------------------
    "powerscale_csm_deploy": {
        "id": "TC_SR_030",
        "title": "Verify CSM Metrics PowerScale deployment ready",
    },
    "powerscale_otel_deploy": {
        "id": "TC_SR_031",
        "title": "Verify OTEL Collector deployment ready",
    },
    "powerscale_secret_valid": {
        "id": "TC_SR_032",
        "title": "Verify isilon-creds secret has correct endpoint",
    },
    "powerscale_metrics_in_vm": {
        "id": "TC_SR_033",
        "title": "Verify PowerScale metrics in VictoriaMetrics",
    },
    "powerscale_logs_in_vl": {
        "id": "TC_SR_034",
        "title": "Verify PowerScale logs in VictoriaLogs",
    },
    "powerscale_syslog_config": {
        "id": "TC_SR_035",
        "title": "Verify PowerScale syslog forwarding configured",
    },
    "powerscale_comprehensive_deployment": {
        "id": "TC_SR_036",
        "title": "Verify comprehensive PowerScale deployment",
    },
    "powerscale_feature_flags": {
        "id": "TC_SR_037",
        "title": "Verify PowerScale feature flags",
    },
    "powerscale_health_metrics": {
        "id": "TC_SR_038",
        "title": "Verify PowerScale health metrics",
    },
    "powerscale_tls_enforcement": {
        "id": "TC_SR_039",
        "title": "Verify PowerScale TLS enforcement",
    },
    "powerscale_label_compliance": {
        "id": "TC_SR_040",
        "title": "Verify PowerScale pod label compliance",
    },
    "powerscale_scrape_interval": {
        "id": "TC_SR_041",
        "title": "Verify PowerScale scrape interval",
    },
    "powerscale_csi_auth_mode": {
        "id": "TC_SR_042",
        "title": "Verify PowerScale CSI authorization mode",
    },
    "powerscale_deployment_mode": {
        "id": "TC_SR_043",
        "title": "Verify PowerScale deployment mode",
    },
    "csi_volume_exporter_deploy": {
        "id": "TC_SR_044",
        "title": "Verify CSI Volume Exporter deployment",
    },
    "csi_volume_exporter_endpoint": {
        "id": "TC_SR_045",
        "title": "Verify CSI Volume Exporter metrics endpoint",
    },
    "csi_volume_exporter_metrics": {
        "id": "TC_SR_046",
        "title": "Verify CSI Volume Exporter metrics in VictoriaMetrics",
    },

    # -- Sources: UFM --------------------------------------------------------
    "ufm_external_svc": {
        "id": "TC_SR_040",
        "title": "Verify UFM external service exists with correct endpoint",
    },
    "ufm_vmscrape": {
        "id": "TC_SR_041",
        "title": "Verify UFM VMServiceScrape CR exists",
    },
    "ufm_credentials_secret": {
        "id": "TC_SR_042",
        "title": "Verify UFM credentials K8s secret exists",
    },
    "ufm_metrics_in_vm": {
        "id": "TC_SR_043",
        "title": "Verify UFM InfiniBand metrics in VictoriaMetrics",
    },

    # -- Sources: VAST -------------------------------------------------------
    "vast_external_svc": {
        "id": "TC_SR_060",
        "title": "Verify VAST external service exists with correct endpoint",
    },
    "vast_vmscrape": {
        "id": "TC_SR_061",
        "title": "Verify VAST VMServiceScrape CR exists",
    },
    "vast_credentials_secret": {
        "id": "TC_SR_062",
        "title": "Verify VAST credentials K8s secret exists",
    },
    "vast_metrics_in_vm": {
        "id": "TC_SR_063",
        "title": "Verify VAST storage metrics in VictoriaMetrics",
    },
    "vast_logs_in_vl": {
        "id": "TC_SR_064",
        "title": "Verify VAST logs in VictoriaLogs",
    },

    # -- Sources: OME -------------------------------------------------------
    "ome_vector_bridge": {
        "id": "TC_SR_050",
        "title": "Verify Vector-OME bridge deployment ready",
    },
    "ome_kafka_user": {
        "id": "TC_SR_051",
        "title": "Verify OME KafkaUser CR exists",
    },
    "ome_external_kafka_certs": {
        "id": "TC_SR_052",
        "title": "Verify external Kafka TLS certificates exist",
    },
    "ome_pfx_conversion": {
        "id": "TC_SR_053",
        "title": "Verify user.pfx certificate created for OME mTLS",
    },
    "ome_upload_certs": {
        "id": "TC_SR_054",
        "title": "Verify TLS certificates uploaded to OME",
    },
    "ome_kafka_connectivity": {
        "id": "TC_SR_055",
        "title": "Verify OME Kafka forwarder connectivity status",
    },

    # -- Cleanup ------------------------------------------------------------
    "cleanup_pods_removed": {
        "id": "TC_CL_002",
        "title": "Verify telemetry pods removed after cleanup",
    },
    "cleanup_topics_removed": {
        "id": "TC_CL_003",
        "title": "Verify Kafka topics removed after cleanup",
    },

    # -- Cleanup: Sinks -----------------------------------------------------
    "cleanup_kafka": {
        "id": "TC_CL_002",
        "title": "Verify Kafka pods removed after cleanup",
    },
    "cleanup_victoria_metrics": {
        "id": "TC_CL_003",
        "title": "Verify VictoriaMetrics pods removed after cleanup",
    },
    "cleanup_victoria_logs": {
        "id": "TC_CL_004",
        "title": "Verify VictoriaLogs pods removed after cleanup",
    },

    # -- Cleanup: Sources ---------------------------------------------------
    "cleanup_idrac": {
        "id": "TC_CL_005",
        "title": "Verify iDRAC pods removed after cleanup",
    },
    "cleanup_ldms": {
        "id": "TC_CL_006",
        "title": "Verify LDMS pods removed after cleanup",
    },
    "cleanup_ome": {
        "id": "TC_CL_007",
        "title": "Verify OME pods removed after cleanup",
    },
    "cleanup_dcgm": {
        "id": "TC_CL_008",
        "title": "Verify DCGM pods removed after cleanup",
    },
    "cleanup_ufm": {
        "id": "TC_CL_009",
        "title": "Verify UFM resources removed after cleanup",
    },
    "cleanup_vast": {
        "id": "TC_CL_010",
        "title": "Verify VAST resources removed after cleanup",
    },
    "cleanup_sfm": {
        "id": "TC_CL_011",
        "title": "Verify SFM pods removed after cleanup",
    },

    # -- Cleanup: Final State -----------------------------------------------
    "no_pods_after_full_cleanup": {
        "id": "TC_CL_012",
        "title": "Verify no pods remain after full cleanup",
    },
    "no_pvcs_after_full_cleanup": {
        "id": "TC_CL_013",
        "title": "Verify no PVCs remain after full cleanup",
    },

    # -- NFT: Performance ---------------------------------------------------
    "nft_validate_perf": {
        "id": "NFT_TL_001",
        "title": "Validate playbook performance (< 30s)",
    },
    "nft_deploy_perf": {
        "id": "NFT_TL_002",
        "title": "Deploy playbook performance (< 600s)",
    },
    "nft_cleanup_perf": {
        "id": "NFT_TL_003",
        "title": "Cleanup playbook performance (< 300s)",
    },

    # -- NFT: Idempotency ---------------------------------------------------
    "nft_deploy_idempotent": {
        "id": "NFT_TL_004",
        "title": "Deploy playbook idempotency (second run exits 0)",
    },
    "nft_cleanup_idempotent": {
        "id": "NFT_TL_005",
        "title": "Cleanup playbook idempotency (second run exits 0)",
    },
}
