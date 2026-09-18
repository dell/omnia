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
        "id": "TEL_FVT_FULL_E001",
        "title": "Deploy telemetry (full stack)",
    },
    "deploy_deploy": {
        "id": "TEL_FVT_DEPLOY_E001",
        "title": "Deploy telemetry (--tags deploy)",
    },
    "deploy_precheck": {
        "id": "TEL_FVT_PRECHECK_E001",
        "title": "Deploy telemetry (--tags precheck)",
    },
    "deploy_validate": {
        "id": "TEL_FVT_VALIDATE_E001",
        "title": "Deploy telemetry (--tags validate)",
    },
    "deploy_cleanup": {
        "id": "TEL_FVT_CLEANUP_E001",
        "title": "Deploy telemetry (--tags cleanup)",
    },
    # -- Precheck -----------------------------------------------------------
    "env_vars_present": {
        "id": "TEL_FVT_PRECHECK_V001",
        "title": "Verify omnia.env variables present",
    },
    "k8s_nodes_ready": {
        "id": "TEL_FVT_PRECHECK_V002",
        "title": "Verify K8s nodes are Ready",
    },
    "kube_vip_reachable": {
        "id": "TEL_FVT_PRECHECK_V003",
        "title": "Verify kube_vip is reachable",
    },
    "powerscale_privileges": {
        "id": "TEL_FVT_PRECHECK_V004",
        "title": "Verify PowerScale user has required privileges",
    },
    # -- Validate -----------------------------------------------------------
    "telemetry_config_parseable": {
        "id": "TEL_FVT_VALIDATE_V001",
        "title": "Verify telemetry_config.yml is valid and parseable",
    },
    # -- Sinks: Kafka -------------------------------------------------------
    "kafka_pods": {
        "id": "TEL_FVT_DEPLOY_V001",
        "title": "Verify Kafka broker/controller pods running",
    },
    "kafka_ready": {
        "id": "TEL_FVT_DEPLOY_V002",
        "title": "Verify Kafka cluster Ready condition",
    },
    "kafka_bridge": {
        "id": "TEL_FVT_DEPLOY_V003",
        "title": "Verify Kafka bridge pod running",
    },
    # -- Sinks: VictoriaMetrics ---------------------------------------------
    "vm_cluster_pods": {
        "id": "TEL_FVT_DEPLOY_V004",
        "title": "Verify VictoriaMetrics cluster pods running",
    },
    "vmagent_pods": {
        "id": "TEL_FVT_DEPLOY_V005",
        "title": "Verify VMAgent pods running",
    },
    # -- Sinks: VictoriaLogs ------------------------------------------------
    "vl_cluster_pods": {
        "id": "TEL_FVT_DEPLOY_V006",
        "title": "Verify VictoriaLogs cluster pods running",
    },
    "vlagent_pods": {
        "id": "TEL_FVT_DEPLOY_V007",
        "title": "Verify VLAgent pods running",
    },
    # -- Namespace-wide pod check -------------------------------------------
    "all_pods_running": {
        "id": "TEL_FVT_DEPLOY_V008",
        "title": "Verify all telemetry pods running",
    },
    # -- Sources: iDRAC -----------------------------------------------------
    "idrac_pod_count": {
        "id": "TEL_FVT_DEPLOY_V010",
        "title": "Verify iDRAC pod count matches bmc_group_data.csv",
    },
    "idrac_sts_ready": {
        "id": "TEL_FVT_DEPLOY_V011",
        "title": "Verify iDRAC StatefulSet pods ready",
    },
    "idrac_containers": {
        "id": "TEL_FVT_DEPLOY_V012",
        "title": "Verify all iDRAC containers running",
    },
    "idrac_mysql_data": {
        "id": "TEL_FVT_DEPLOY_V013",
        "title": "Verify MySQL data in iDRAC telemetry pods",
    },
    "idrac_receiver_collecting": {
        "id": "TEL_FVT_DEPLOY_V014",
        "title": "Verify iDRAC receiver is collecting metrics",
    },
    "idrac_kafka_topic": {
        "id": "TEL_FVT_DEPLOY_V015",
        "title": "Verify iDRAC Kafka topic exists",
    },
    "idrac_victoria_pump": {
        "id": "TEL_FVT_DEPLOY_V016",
        "title": "Verify iDRAC VictoriaPump metrics endpoint",
    },
    "idrac_service": {
        "id": "TEL_FVT_DEPLOY_V017",
        "title": "Verify iDRAC telemetry service exists",
    },
    "idrac_vm_data": {
        "id": "TEL_FVT_DEPLOY_V018",
        "title": "Verify iDRAC telemetry data in VictoriaMetrics",
    },
    # -- Sources: Install Mode (unified online/offline) -----------------------
    "install_mode_config": {
        "id": "TEL_FVT_DEPLOY_V110",
        "title": "Verify telemetry_packages.yml has a valid install_mode",
    },
    "install_mode_python_packages": {
        "id": "TEL_FVT_DEPLOY_V111",
        "title": "Verify Python packages installed for current mode",
    },
    "install_mode_idrac_deployment": {
        "id": "TEL_FVT_DEPLOY_V112",
        "title": "Verify iDRAC deployment succeeded in current mode",
    },
    "install_mode_idrac_pods": {
        "id": "TEL_FVT_DEPLOY_V113",
        "title": "Verify iDRAC pods running in current mode",
    },
    "install_mode_powerscale_deps": {
        "id": "TEL_FVT_DEPLOY_V114",
        "title": "Verify PowerScale dependencies for current mode",
    },
    "install_mode_powerscale_deployment": {
        "id": "TEL_FVT_DEPLOY_V115",
        "title": "Verify PowerScale deployment succeeded in current mode",
    },
    # -- Sources: LDMS ------------------------------------------------------
    "ldms_aggr_pod": {
        "id": "TEL_FVT_DEPLOY_V020",
        "title": "Verify LDMS aggregator pod running",
    },
    "ldms_store_pod": {
        "id": "TEL_FVT_DEPLOY_V021",
        "title": "Verify LDMS store pod running",
    },
    "ldms_vector_bridge": {
        "id": "TEL_FVT_DEPLOY_V022",
        "title": "Verify Vector-LDMS bridge deployment ready",
    },
    "ldms_package_installed": {
        "id": "TEL_FVT_DEPLOY_V023",
        "title": "Verify LDMS package installed on Slurm nodes",
    },
    "ldms_sampler_service": {
        "id": "TEL_FVT_DEPLOY_V024",
        "title": "Verify LDMS sampler service running on Slurm nodes",
    },
    "ldms_sampler_plugins": {
        "id": "TEL_FVT_DEPLOY_V025",
        "title": "Verify LDMS sampler plugins configured",
    },
    "ldms_kafka_topic": {
        "id": "TEL_FVT_DEPLOY_V026",
        "title": "Verify LDMS Kafka topic exists",
    },
    "ldms_earliest_data": {
        "id": "TEL_FVT_DEPLOY_V027",
        "title": "Verify earliest LDMS data in Kafka topic",
    },
    "ldms_kafka_data": {
        "id": "TEL_FVT_DEPLOY_V028",
        "title": "Verify latest LDMS data in Kafka topic",
    },
    # -- Sources: PowerScale ------------------------------------------------
    "powerscale_csm_deploy": {
        "id": "TEL_FVT_DEPLOY_V030",
        "title": "Verify CSM Metrics PowerScale deployment ready",
    },
    "powerscale_otel_deploy": {
        "id": "TEL_FVT_DEPLOY_V031",
        "title": "Verify OTEL Collector deployment ready",
    },
    "powerscale_secret_valid": {
        "id": "TEL_FVT_DEPLOY_V032",
        "title": "Verify isilon-creds secret has correct endpoint",
    },
    "powerscale_metrics_in_vm": {
        "id": "TEL_FVT_DEPLOY_V033",
        "title": "Verify PowerScale metrics in VictoriaMetrics",
    },
    "powerscale_logs_in_vl": {
        "id": "TEL_FVT_DEPLOY_V034",
        "title": "Verify PowerScale logs in VictoriaLogs",
    },
    "powerscale_syslog_config": {
        "id": "TEL_FVT_DEPLOY_V035",
        "title": "Verify PowerScale syslog forwarding configured",
    },
    "powerscale_comprehensive_deployment": {
        "id": "TEL_FVT_DEPLOY_V036",
        "title": "Verify comprehensive PowerScale deployment",
    },
    "powerscale_feature_flags": {
        "id": "TEL_FVT_DEPLOY_V037",
        "title": "Verify PowerScale feature flags",
    },
    "powerscale_health_metrics": {
        "id": "TEL_FVT_DEPLOY_V038",
        "title": "Verify PowerScale health metrics",
    },
    "powerscale_tls_enforcement": {
        "id": "TEL_FVT_DEPLOY_V040",
        "title": "Verify PowerScale TLS enforcement",
    },
    "powerscale_label_compliance": {
        "id": "TEL_FVT_DEPLOY_V041",
        "title": "Verify PowerScale pod label compliance",
    },
    "powerscale_scrape_interval": {
        "id": "TEL_FVT_DEPLOY_V042",
        "title": "Verify PowerScale scrape interval",
    },
    "powerscale_csi_auth_mode": {
        "id": "TEL_FVT_DEPLOY_V043",
        "title": "Verify PowerScale CSI authorization mode",
    },
    "powerscale_deployment_mode": {
        "id": "TEL_FVT_DEPLOY_V044",
        "title": "Verify PowerScale deployment mode",
    },
    "csi_volume_exporter_deploy": {
        "id": "TEL_FVT_DEPLOY_V045",
        "title": "Verify CSI Volume Exporter deployment",
    },
    "csi_volume_exporter_endpoint": {
        "id": "TEL_FVT_DEPLOY_V046",
        "title": "Verify CSI Volume Exporter metrics endpoint",
    },
    "csi_volume_exporter_metrics": {
        "id": "TEL_FVT_DEPLOY_V047",
        "title": "Verify CSI Volume Exporter metrics in VictoriaMetrics",
    },
    "csi_driver_powerscale_deploy": {
        "id": "TEL_FVT_DEPLOY_V048",
        "title": "Verify CSI Driver for PowerScale (isilon-controller) deployment",
    },
    "external_health_monitor_container": {
        "id": "TEL_FVT_DEPLOY_V049",
        "title": "Verify external-health-monitor-controller container is running",
    },
    "csi_exporter_skipped_without_health_monitor": {
        "id": "TEL_FVT_DEPLOY_V050",
        "title": "Verify CSI volume exporter deployment skipped when health monitor missing",
    },
    "health_monitor_warning_message": {
        "id": "TEL_FVT_DEPLOY_V051",
        "title": "Verify warning message displayed for missing health monitor",
    },
    "csm_otel_data_flow": {
        "id": "TEL_FVT_DEPLOY_V052",
        "title": "Verify CSM Metrics to OTEL Collector data flow",
    },
    "otel_vm_export": {
        "id": "TEL_FVT_DEPLOY_V053",
        "title": "Verify OTEL Collector to VictoriaMetrics export",
    },
    "cert_manager_tls_certs": {
        "id": "TEL_FVT_DEPLOY_V054",
        "title": "Verify cert-manager TLS certificate generation",
    },
    # -- Sources: UFM --------------------------------------------------------
    "ufm_external_svc": {
        "id": "TEL_FVT_DEPLOY_V060",
        "title": "Verify UFM external service exists with correct endpoint",
    },
    "ufm_vmscrape": {
        "id": "TEL_FVT_DEPLOY_V061",
        "title": "Verify UFM VMServiceScrape CR exists",
    },
    "ufm_credentials_secret": {
        "id": "TEL_FVT_DEPLOY_V062",
        "title": "Verify UFM credentials K8s secret exists",
    },
    "ufm_metrics_in_vm": {
        "id": "TEL_FVT_DEPLOY_V063",
        "title": "Verify UFM InfiniBand metrics in VictoriaMetrics",
    },
    # -- Sources: VAST -------------------------------------------------------
    "vast_external_svc": {
        "id": "TEL_FVT_DEPLOY_V090",
        "title": "Verify VAST external service exists with correct endpoint",
    },
    "vast_vmscrape": {
        "id": "TEL_FVT_DEPLOY_V091",
        "title": "Verify VAST VMServiceScrape CR exists",
    },
    "vast_credentials_secret": {
        "id": "TEL_FVT_DEPLOY_V092",
        "title": "Verify VAST credentials K8s secret exists",
    },
    "vast_metrics_in_vm": {
        "id": "TEL_FVT_DEPLOY_V093",
        "title": "Verify VAST storage metrics in VictoriaMetrics",
    },
    "vast_test_event_in_victoria_logs": {
        "id": "TEL_FVT_DEPLOY_V094",
        "title": "Verify fresh VAST test event in VictoriaLogs",
    },
    "vast_syslog_configuration": {
        "id": "TEL_FVT_DEPLOY_V095",
        "title": "Configure VAST syslog and send a test event",
    },
    # -- Sources: OME -------------------------------------------------------
    "ome_vector_bridge": {
        "id": "TEL_FVT_DEPLOY_V070",
        "title": "Verify Vector-OME bridge deployment ready",
    },
    "ome_kafka_user": {
        "id": "TEL_FVT_DEPLOY_V071",
        "title": "Verify OME KafkaUser CR exists",
    },
    "ome_external_kafka_certs": {
        "id": "TEL_FVT_DEPLOY_V072",
        "title": "Verify external Kafka connection artifacts",
    },
    "ome_pfx_conversion": {
        "id": "TEL_FVT_DEPLOY_V073",
        "title": "Verify user.pfx certificate created for OME mTLS",
    },
    "ome_upload_certs": {
        "id": "TEL_FVT_DEPLOY_V074",
        "title": "Verify TLS certificates uploaded to OME",
    },
    "ome_kafka_connectivity": {
        "id": "TEL_FVT_DEPLOY_V075",
        "title": "Verify OME Kafka forwarder connectivity status",
    },
    "ome_cert_verify": {
        "id": "TEL_FVT_DEPLOY_V076",
        "title": "Verify uploaded certificate matches generated certificate",
    },
    "ome_kafka_topics": {
        "id": "TEL_FVT_DEPLOY_V077",
        "title": "Verify OME Kafka topics exist",
    },
    "ome_telemetry_data": {
        "id": "TEL_FVT_DEPLOY_V078",
        "title": "Verify OME telemetry data in Kafka (ome.telemetry)",
    },
    "ome_inventory_data": {
        "id": "TEL_FVT_DEPLOY_V079",
        "title": "Verify OME inventory data in Kafka (ome.inventory)",
    },
    "ome_alerts_data": {
        "id": "TEL_FVT_DEPLOY_V080",
        "title": "Verify OME alerts data in Kafka (ome.alerts)",
    },
    "ome_health_data": {
        "id": "TEL_FVT_DEPLOY_V081",
        "title": "Verify OME health data in Kafka (ome.health)",
    },
    "ome_auditlogs_data": {
        "id": "TEL_FVT_DEPLOY_V082",
        "title": "Verify OME audit logs data in Kafka (ome.auditlogs)",
    },
    "ome_telemetry_metrics_in_vm": {
        "id": "TEL_FVT_DEPLOY_V083",
        "title": "Verify OME telemetry metrics in VictoriaMetrics",
    },
    "ome_inventory_metrics_in_vm": {
        "id": "TEL_FVT_DEPLOY_V084",
        "title": "Verify OME inventory metrics in VictoriaMetrics",
    },
    "ome_health_metrics_in_vm": {
        "id": "TEL_FVT_DEPLOY_V085",
        "title": "Verify OME health metrics in VictoriaMetrics",
    },
    "ome_alerts_logs_in_vl": {
        "id": "TEL_FVT_DEPLOY_V086",
        "title": "Verify OME alerts in VictoriaLogs",
    },
    "ome_auditlogs_logs_in_vl": {
        "id": "TEL_FVT_DEPLOY_V087",
        "title": "Verify OME audit logs in VictoriaLogs",
    },
    # -- Sources: SFM -------------------------------------------------------
    "sfm_omnia_pods": {
        "id": "TEL_FVT_DEPLOY_V100",
        "title": "Verify required Omnia workloads and pods for SFM",
    },
    "sfm_omnia_services": {
        "id": "TEL_FVT_DEPLOY_V101",
        "title": "Verify required Omnia services for SFM",
    },
    "sfm_switch_configuration": {
        "id": "TEL_FVT_DEPLOY_V102",
        "title": "Configure and verify the SFM switch data path",
    },
    "sfm_observability_configuration": {
        "id": "TEL_FVT_DEPLOY_V103",
        "title": "Configure and verify SFM observability Remote Write",
    },
    "sfm_metrics_in_victoria": {
        "id": "TEL_FVT_DEPLOY_V104",
        "title": "Verify three SFM metrics and timestamps in VictoriaMetrics",
    },
    # -- Cleanup ------------------------------------------------------------
    "cleanup_pods_removed": {
        "id": "TEL_FVT_CLEANUP_V001",
        "title": "Verify telemetry pods removed after cleanup",
    },
    "cleanup_topics_removed": {
        "id": "TEL_FVT_CLEANUP_V002",
        "title": "Verify Kafka topics removed after cleanup",
    },
    # -- Cleanup: Sinks -----------------------------------------------------
    "cleanup_kafka": {
        "id": "TEL_FVT_CLEANUP_V003",
        "title": "Verify Kafka pods removed after cleanup",
    },
    "cleanup_victoria_metrics": {
        "id": "TEL_FVT_CLEANUP_V004",
        "title": "Verify VictoriaMetrics pods removed after cleanup",
    },
    "cleanup_victoria_logs": {
        "id": "TEL_FVT_CLEANUP_V005",
        "title": "Verify VictoriaLogs pods removed after cleanup",
    },
    # -- Cleanup: Sources ---------------------------------------------------
    "cleanup_idrac": {
        "id": "TEL_FVT_CLEANUP_V006",
        "title": "Verify iDRAC pods removed after cleanup",
    },
    "cleanup_ldms": {
        "id": "TEL_FVT_CLEANUP_V007",
        "title": "Verify LDMS pods removed after cleanup",
    },
    "cleanup_ome": {
        "id": "TEL_FVT_CLEANUP_V008",
        "title": "Verify OME pods removed after cleanup",
    },
    "cleanup_ufm": {
        "id": "TEL_FVT_CLEANUP_V009",
        "title": "Verify UFM resources removed after cleanup",
    },
    "cleanup_vast": {
        "id": "TEL_FVT_CLEANUP_V010",
        "title": "Verify VAST resources removed after cleanup",
    },
    "cleanup_sfm": {
        "id": "TEL_FVT_CLEANUP_V011",
        "title": "Verify SFM pods removed after cleanup",
    },
    # -- Cleanup: Final State -----------------------------------------------
    "no_pods_after_full_cleanup": {
        "id": "TEL_FVT_CLEANUP_V012",
        "title": "Verify no pods remain after full cleanup",
    },
    "no_pvcs_after_full_cleanup": {
        "id": "TEL_FVT_CLEANUP_V013",
        "title": "Verify no PVCs remain after full cleanup (Delete_volume=true)",
    },
    "pvcs_preserved_after_cleanup": {
        "id": "TEL_FVT_CLEANUP_V014",
        "title": "Verify PVCs preserved after cleanup (Delete_volume=false)",
    },
    # -- NFT: Performance ---------------------------------------------------
    "nft_validate_perf": {
        "id": "TEL_NFT_001",
        "title": "Validate playbook performance (< 30s)",
    },
    "nft_deploy_perf": {
        "id": "TEL_NFT_002",
        "title": "Deploy playbook performance (< 600s)",
    },
    "nft_cleanup_perf": {
        "id": "TEL_NFT_003",
        "title": "Cleanup playbook performance (< 300s)",
    },
    # -- NFT: Idempotency ---------------------------------------------------
    "nft_deploy_idempotent": {
        "id": "TEL_NFT_004",
        "title": "Deploy playbook idempotency (second run exits 0)",
    },
    "nft_cleanup_idempotent": {
        "id": "TEL_NFT_005",
        "title": "Cleanup playbook idempotency (second run exits 0)",
    },
    "nft_cleanup_no_pods": {
        "id": "TEL_NFT_015",
        "title": "Verify no pods after idempotent cleanup",
    },
    "nft_cleanup_no_pvcs": {
        "id": "TEL_NFT_016",
        "title": "Verify no PVCs after idempotent cleanup",
    },
    "nft_cleanup_pvcs_preserved": {
        "id": "TEL_NFT_017",
        "title": "Verify PVCs preserved after idempotent cleanup",
    },
    # -- NFT: Resilience -----------------------------------------------------
    "nft_sink_pod_recovery": {
        "id": "TEL_NFT_006",
        "title": "Sink pod deletion & recovery (Kafka broker)",
    },
    "nft_source_pod_recovery": {
        "id": "TEL_NFT_007",
        "title": "Source pod deletion & recovery (enabled sources)",
    },
    "nft_sts_pod_recovery": {
        "id": "TEL_NFT_008",
        "title": "StatefulSet storage pod recovery (vmstorage/vlstorage)",
    },
    "nft_pvc_persistence": {
        "id": "TEL_NFT_009",
        "title": "PVC persistence after pod deletion",
    },
    "nft_service_endpoints": {
        "id": "TEL_NFT_010",
        "title": "Service endpoint availability after pod restart",
    },
    "nft_data_after_restart": {
        "id": "TEL_NFT_011",
        "title": "Data ingestion after sink restart",
    },
    "nft_node_reboot": {
        "id": "TEL_NFT_012",
        "title": "Node reboot recovery (all pods Running)",
    },
    "nft_full_lifecycle": {
        "id": "TEL_NFT_013",
        "title": "Full lifecycle (cleanup -> redeploy -> verify)",
    },
    "nft_operator_recovery": {
        "id": "TEL_NFT_014",
        "title": "Operator pod recovery (VM/Strimzi operators)",
    },
}


# Historical reports used unqualified FVT IDs and put the NFT level before
# the domain code. A tuple records every current target when a legacy ID was
# reused by more than one test case.
LEGACY_ID_MAP = {
    "TC_DP_001": "TEL_FVT_FULL_E001",
    "TC_DP_002": "TEL_FVT_DEPLOY_E001",
    "TC_PC_001": "TEL_FVT_PRECHECK_E001",
    "TC_PC_002": "TEL_FVT_PRECHECK_V001",
    "TC_PC_003": "TEL_FVT_PRECHECK_V002",
    "TC_PC_004": "TEL_FVT_PRECHECK_V003",
    "TC_PC_005": "TEL_FVT_PRECHECK_V004",
    "TC_VL_001": "TEL_FVT_VALIDATE_E001",
    "TC_VL_002": "TEL_FVT_VALIDATE_V001",
    "TC_NS_001": "TEL_FVT_DEPLOY_V008",
    "TC_CL_001": "TEL_FVT_CLEANUP_E001",
    "TC_CL_002": (
        "TEL_FVT_CLEANUP_V001",
        "TEL_FVT_CLEANUP_V003",
    ),
    "TC_CL_003": (
        "TEL_FVT_CLEANUP_V002",
        "TEL_FVT_CLEANUP_V004",
    ),
    "TC_CL_004": "TEL_FVT_CLEANUP_V005",
    "TC_CL_011-idem": "TEL_NFT_015",
    "TC_CL_012-idem": "TEL_NFT_016",
    "TC_CL_013-idem": "TEL_NFT_017",
    **{
        f"TC_SK_{sequence:03d}": f"TEL_FVT_DEPLOY_V{sequence:03d}"
        for sequence in range(1, 8)
    },
    **{
        f"TC_SR_{sequence:03d}": f"TEL_FVT_DEPLOY_V{sequence + 9:03d}"
        for sequence in range(1, 10)
    },
    **{
        f"TC_SR_{sequence:03d}": f"TEL_FVT_DEPLOY_V{sequence:03d}"
        for sequence in (*range(20, 29), *range(30, 39), *range(40, 55))
    },
    **{
        f"TC_SR_{sequence:03d}": f"TEL_FVT_DEPLOY_V{sequence:03d}"
        for sequence in range(70, 76)
    },
    **{
        f"TC_SR_{sequence:03d}": f"TEL_FVT_DEPLOY_V{sequence + 19:03d}"
        for sequence in range(64, 69)
    },
    **{
        f"TC_SR_{sequence:03d}": f"TEL_FVT_DEPLOY_V{sequence + 10:03d}"
        for sequence in (*range(80, 86), *range(90, 95), *range(100, 106))
    },
    **{
        f"TC_CL_{sequence:03d}": f"TEL_FVT_CLEANUP_V{sequence + 1:03d}"
        for sequence in range(5, 14)
    },
    **{f"NFT_TL_{sequence:03d}": f"TEL_NFT_{sequence:03d}" for sequence in range(1, 15)},
}

# These three IDs were reused by both UFM and OME. Preserve both destinations
# so migration tooling does not silently select the wrong historical case.
LEGACY_ID_MAP.update(
    {
        f"TC_SR_{sequence:03d}": (
            f"TEL_FVT_DEPLOY_V{sequence:03d}",
            f"TEL_FVT_DEPLOY_V{sequence + 20:03d}",
        )
        for sequence in range(60, 63)
    }
)
LEGACY_ID_MAP["TC_SR_063"] = "TEL_FVT_DEPLOY_V063"
for legacy_sequence, current_sequence in zip(range(56, 60), range(76, 80)):
    LEGACY_ID_MAP[f"TC_SR_{legacy_sequence:03d}"] = (
        f"TEL_FVT_DEPLOY_V{current_sequence:03d}"
    )
