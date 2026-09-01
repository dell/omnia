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
    "powerscale_privileges": {
        "id": "TC_PC_005",
        "title": "Verify PowerScale user has required privileges",
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

    # -- Sources: Install Mode (unified online/offline) -----------------------
    "install_mode_config": {
        "id": "TC_SR_100",
        "title": "Verify telemetry_packages.yml has a valid install_mode",
    },
    "install_mode_python_packages": {
        "id": "TC_SR_101",
        "title": "Verify Python packages installed for current mode",
    },
    "install_mode_idrac_deployment": {
        "id": "TC_SR_102",
        "title": "Verify iDRAC deployment succeeded in current mode",
    },
    "install_mode_idrac_pods": {
        "id": "TC_SR_103",
        "title": "Verify iDRAC pods running in current mode",
    },
    "install_mode_powerscale_deps": {
        "id": "TC_SR_104",
        "title": "Verify PowerScale dependencies for current mode",
    },
    "install_mode_powerscale_deployment": {
        "id": "TC_SR_105",
        "title": "Verify PowerScale deployment succeeded in current mode",
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
    "ldms_package_installed": {
        "id": "TC_SR_023",
        "title": "Verify LDMS package installed on Slurm nodes",
    },
    "ldms_sampler_service": {
        "id": "TC_SR_024",
        "title": "Verify LDMS sampler service running on Slurm nodes",
    },
    "ldms_sampler_plugins": {
        "id": "TC_SR_025",
        "title": "Verify LDMS sampler plugins configured",
    },
    "ldms_kafka_topic": {
        "id": "TC_SR_026",
        "title": "Verify LDMS Kafka topic exists",
    },
    "ldms_earliest_data": {
        "id": "TC_SR_027",
        "title": "Verify earliest LDMS data in Kafka topic",
    },
    "ldms_kafka_data": {
        "id": "TC_SR_028",
        "title": "Verify latest LDMS data in Kafka topic",
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
        "id": "TC_SR_040",
        "title": "Verify PowerScale TLS enforcement",
    },
    "powerscale_label_compliance": {
        "id": "TC_SR_041",
        "title": "Verify PowerScale pod label compliance",
    },
    "powerscale_scrape_interval": {
        "id": "TC_SR_042",
        "title": "Verify PowerScale scrape interval",
    },
    "powerscale_csi_auth_mode": {
        "id": "TC_SR_043",
        "title": "Verify PowerScale CSI authorization mode",
    },
    "powerscale_deployment_mode": {
        "id": "TC_SR_044",
        "title": "Verify PowerScale deployment mode",
    },
    "csi_volume_exporter_deploy": {
        "id": "TC_SR_045",
        "title": "Verify CSI Volume Exporter deployment",
    },
    "csi_volume_exporter_endpoint": {
        "id": "TC_SR_046",
        "title": "Verify CSI Volume Exporter metrics endpoint",
    },
    "csi_volume_exporter_metrics": {
        "id": "TC_SR_047",
        "title": "Verify CSI Volume Exporter metrics in VictoriaMetrics",
    },
    "csi_driver_powerscale_deploy": {
        "id": "TC_SR_048",
        "title": "Verify CSI Driver for PowerScale (isilon-controller) deployment",
    },
    "external_health_monitor_container": {
        "id": "TC_SR_049",
        "title": "Verify external-health-monitor-controller container is running",
    },
    "csi_exporter_skipped_without_health_monitor": {
        "id": "TC_SR_050",
        "title": "Verify CSI volume exporter deployment skipped when health monitor missing",
    },
    "health_monitor_warning_message": {
        "id": "TC_SR_051",
        "title": "Verify warning message displayed for missing health monitor",
    },
    "csm_otel_data_flow": {
        "id": "TC_SR_052",
        "title": "Verify CSM Metrics to OTEL Collector data flow",
    },
    "otel_vm_export": {
        "id": "TC_SR_053",
        "title": "Verify OTEL Collector to VictoriaMetrics export",
    },
    "cert_manager_tls_certs": {
        "id": "TC_SR_054",
        "title": "Verify cert-manager TLS certificate generation",
    },

    # -- Sources: UFM --------------------------------------------------------
    "ufm_external_svc": {
        "id": "TC_SR_060",
        "title": "Verify UFM external service exists with correct endpoint",
    },
    "ufm_vmscrape": {
        "id": "TC_SR_061",
        "title": "Verify UFM VMServiceScrape CR exists",
    },
    "ufm_credentials_secret": {
        "id": "TC_SR_062",
        "title": "Verify UFM credentials K8s secret exists",
    },
    "ufm_metrics_in_vm": {
        "id": "TC_SR_063",
        "title": "Verify UFM InfiniBand metrics in VictoriaMetrics",
    },

    # -- Sources: VAST -------------------------------------------------------
    "vast_external_svc": {
        "id": "TC_SR_080",
        "title": "Verify VAST external service exists with correct endpoint",
    },
    "vast_vmscrape": {
        "id": "TC_SR_081",
        "title": "Verify VAST VMServiceScrape CR exists",
    },
    "vast_credentials_secret": {
        "id": "TC_SR_082",
        "title": "Verify VAST credentials K8s secret exists",
    },
    "vast_metrics_in_vm": {
        "id": "TC_SR_083",
        "title": "Verify VAST storage metrics in VictoriaMetrics",
    },
    "vast_logs_in_vl": {
        "id": "TC_SR_084",
        "title": "Verify VAST logs in VictoriaLogs",
    },

    # -- Sources: OME -------------------------------------------------------
    "ome_vector_bridge": {
        "id": "TC_SR_070",
        "title": "Verify Vector-OME bridge deployment ready",
    },
    "ome_kafka_user": {
        "id": "TC_SR_071",
        "title": "Verify OME KafkaUser CR exists",
    },
    "ome_external_kafka_certs": {
        "id": "TC_SR_072",
        "title": "Verify external Kafka TLS certificates exist",
    },
    "ome_pfx_conversion": {
        "id": "TC_SR_073",
        "title": "Verify user.pfx certificate created for OME mTLS",
    },
    "ome_upload_certs": {
        "id": "TC_SR_074",
        "title": "Verify TLS certificates uploaded to OME",
    },
    "ome_kafka_connectivity": {
        "id": "TC_SR_075",
        "title": "Verify OME Kafka forwarder connectivity status",
    },
    "ome_cert_verify": {
        "id": "TC_SR_056",
        "title": "Verify uploaded certificate matches generated certificate",
    },
    "ome_kafka_topics": {
        "id": "TC_SR_057",
        "title": "Verify OME Kafka topics exist",
    },
    "ome_telemetry_data": {
        "id": "TC_SR_058",
        "title": "Verify OME telemetry data in Kafka (ome.telemetry)",
    },
    "ome_inventory_data": {
        "id": "TC_SR_059",
        "title": "Verify OME inventory data in Kafka (ome.inventory)",
    },
    "ome_alerts_data": {
        "id": "TC_SR_060",
        "title": "Verify OME alerts data in Kafka (ome.alerts)",
    },
    "ome_health_data": {
        "id": "TC_SR_061",
        "title": "Verify OME health data in Kafka (ome.health)",
    },
    "ome_auditlogs_data": {
        "id": "TC_SR_062",
        "title": "Verify OME audit logs data in Kafka (ome.auditlogs)",
    },

    # -- Sources: SFM -------------------------------------------------------
    "sfm_omnia_pods": {
        "id": "TC_SR_090",
        "title": "Verify required Omnia workloads and pods for SFM",
    },
    "sfm_omnia_services": {
        "id": "TC_SR_091",
        "title": "Verify required Omnia services for SFM",
    },
    "sfm_switch_configuration": {
        "id": "TC_SR_092",
        "title": "Configure and verify the SFM switch data path",
    },
    "sfm_observability_configuration": {
        "id": "TC_SR_093",
        "title": "Configure and verify SFM observability Remote Write",
    },
    "sfm_metrics_in_victoria": {
        "id": "TC_SR_094",
        "title": "Verify three SFM metrics and timestamps in VictoriaMetrics",
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
    "cleanup_ufm": {
        "id": "TC_CL_008",
        "title": "Verify UFM resources removed after cleanup",
    },
    "cleanup_vast": {
        "id": "TC_CL_009",
        "title": "Verify VAST resources removed after cleanup",
    },
    "cleanup_sfm": {
        "id": "TC_CL_010",
        "title": "Verify SFM pods removed after cleanup",
    },

    # -- Cleanup: Final State -----------------------------------------------
    "no_pods_after_full_cleanup": {
        "id": "TC_CL_011",
        "title": "Verify no pods remain after full cleanup",
    },
    "no_pvcs_after_full_cleanup": {
        "id": "TC_CL_012",
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
