# Telemetry FVT — Test Case Registry

## Overview

Functional Verification Tests for the `telemetry` domain.
Tests verify the telemetry stack deployment, validation, and cleanup.

**Source under test**: `src/telemetry/`
**Entry point**: `ansible-playbook playbooks/telemetry.yml --tags <tag>`

## Scenarios

| Scenario | Directory | Tag | Phase |
|----------|-----------|-----|-------|
| Precheck | `fvt/precheck/` | `precheck` | Phase 1 |
| Validate | `fvt/validate/` | `validate` | Phase 1 |
| Deploy | `fvt/deploy/` | `execute/deploy` | Phase 2-4 |
| Cleanup | `fvt/cleanup/` | `cleanup` | Phase 5 |
| Full E2E | `fvt/telemetry/` | (none) | Phase 2-5 |

## Test Case Registry

### Phase 1 — Precheck (7 TCs)

| TC ID | Test Function | Title | Marker |
|-------|--------------|-------|--------|
| TC_PC_001 | `test_deploy_precheck` | Deploy telemetry (precheck) | deploy, sanity |
| TC_PC_002 | `test_kube_vip_defined` | Verify kube_vip is defined in telemetry_config.yml | sanity |
| TC_PC_003 | `test_kube_vip_reachable` | Verify kube_vip is reachable (ICMP + SSH) | sanity |
| TC_PC_004 | `test_control_plane_ready` | Verify K8s control plane nodes are Ready | sanity |
| TC_PC_005 | `test_worker_nodes_ready` | Verify worker nodes meet minimum readiness threshold | sanity |
| TC_PC_006 | `test_pods_healthy` | Verify all pods (outside telemetry ns) are healthy | sanity |
| TC_PC_007 | `test_kubectl_available` | Verify kubectl is available on kube_vip | sanity |

### Phase 1 — Validate (6 TCs)

| TC ID | Test Function | Title | Marker |
|-------|--------------|-------|--------|
| TC_VL_001 | `test_deploy_validate` | Deploy telemetry (validate) | deploy, sanity |
| TC_VL_002 | `test_config_file_exists` | Verify telemetry_config.yml exists on target | sanity |
| TC_VL_003 | `test_storage_config_exists` | Verify telemetry_storage_config.yml exists on target | sanity |
| TC_VL_004 | `test_packages_config_exists` | Verify telemetry_packages.yml exists on target | sanity |
| TC_VL_005 | `test_l1_schema_valid` | Verify L1 JSON schema validation passes | sanity |
| TC_VL_006 | `test_l2_logic_valid` | Verify L2 cross-field logic validation passes | sanity |

### Phase 2 — Deploy / Sinks (13 TCs)

| TC ID | Test Function | Title | Marker | File |
|-------|--------------|-------|--------|------|
| TC_DP_001 | `test_deploy_telemetry` | Deploy telemetry (execute/deploy) | deploy | `deploy/test_playbook.py` |
| TC_SK_001 | `test_vm_cluster_pods` | Verify VictoriaMetrics cluster pods running | sink, sanity | `deploy/sinks/vm/test_victoria_metrics.py` |
| TC_SK_002 | `test_vm_persistence_size` | Verify VictoriaMetrics PVC sizes | sink | `deploy/sinks/vm/test_victoria_metrics.py` |
| TC_SK_003 | `test_vmagent_pods` | Verify vmagent pods running | sink, sanity | `deploy/sinks/vm/test_victoria_metrics.py` |
| TC_SK_004 | `test_vm_tls_secret` | Verify VictoriaMetrics TLS secret exists | sink | `deploy/sinks/vm/test_victoria_metrics.py` |
| TC_SK_005 | `test_vm_health` | Verify VictoriaMetrics operator running | sink | `deploy/sinks/vm/test_victoria_metrics.py` |
| TC_SK_006 | `test_vm_services` | Verify VictoriaMetrics services exist | sink | `deploy/sinks/vm/test_victoria_metrics.py` |
| TC_SK_007 | `test_vl_cluster_pods` | Verify VictoriaLogs cluster pods running | sink, sanity | `deploy/sinks/vl/test_victoria_logs.py` |
| TC_SK_008 | `test_vlagent_pods` | Verify VictoriaLogs vlagent pods running | sink, sanity | `deploy/sinks/vl/test_victoria_logs.py` |
| TC_SK_009 | `test_kafka_pods` | Verify Kafka broker pods running | sink, sanity | `deploy/sinks/kafka/test_kafka.py` |
| TC_SK_010 | `test_kafka_ready` | Verify Kafka CR is Ready | sink, sanity | `deploy/sinks/kafka/test_kafka.py` |
| TC_SK_011 | `test_kafka_bridge` | Verify Kafka bridge pods (optional) | sink | `deploy/sinks/kafka/test_kafka.py` |
| TC_SK_012 | `test_kafka_persistence` | Verify Kafka PVCs exist | sink | `deploy/sinks/kafka/test_kafka.py` |

### Phase 3 — Sources: iDRAC, LDMS, OME (13 TCs)

| TC ID | Test Function | Title | Marker | File |
|-------|--------------|-------|--------|------|
| TC_SR_001 | `test_idrac_sts_ready` | Verify iDRAC StatefulSet pods ready | source, sanity | `deploy/sources/idrac/test_idrac.py` |
| TC_SR_002 | `test_idrac_containers` | Verify all iDRAC containers running | source, sanity | `deploy/sources/idrac/test_idrac.py` |
| TC_SR_003 | `test_idrac_kafka_topic` | Verify Kafka topic 'idrac' exists | source | `deploy/sources/idrac/test_idrac.py` |
| TC_SR_004 | `test_idrac_victoria_pump` | Verify iDRAC VictoriaPump metrics endpoint | source | `deploy/sources/idrac/test_idrac.py` |
| TC_SR_005 | `test_idrac_service` | Verify iDRAC telemetry service exists | source | `deploy/sources/idrac/test_idrac.py` |
| TC_SR_006 | `test_ldms_aggregator` | Verify LDMS aggregator StatefulSet ready | source, sanity | `deploy/sources/ldms/test_ldms.py` |
| TC_SR_007 | `test_ldms_store` | Verify LDMS store daemon pod running | source, sanity | `deploy/sources/ldms/test_ldms.py` |
| TC_SR_008 | `test_vector_ldms` | Verify Vector-LDMS bridge deployment ready | source | `deploy/sources/ldms/test_ldms.py` |
| TC_SR_009 | `test_ldms_kafka_topic` | Verify LDMS Kafka topic exists | source | `deploy/sources/ldms/test_ldms.py` |
| TC_SR_010 | `test_ldms_sampler_config` | Verify LDMS sampler config on NFS | source | `deploy/sources/ldms/test_ldms.py` |
| TC_SR_011 | `test_vector_ome` | Verify Vector-OME bridge deployment ready | source, sanity | `deploy/sources/ome/test_ome.py` |
| TC_SR_012 | `test_ome_kafka_user` | Verify OME KafkaUser CR exists | source | `deploy/sources/ome/test_ome.py` |
| TC_SR_013 | `test_ome_sink_prerequisites` | Verify OME bridge sink prerequisites | source | `deploy/sources/ome/test_ome.py` |

> **Note**: DCGM tests excluded from Phase 3 (per project requirements).

### Phase 4 — Sources: PowerScale, UFM, VAST, SFM (8 TCs) — *planned*

| TC ID | Test Function | Title | Marker |
|-------|--------------|-------|--------|
| TC_SR_016 | `test_powerscale_csi_exporter` | Verify CSI volume exporter pods running | source |
| TC_SR_017 | `test_powerscale_metrics` | Verify PowerScale metrics in VictoriaMetrics | source |
| TC_SR_018 | `test_ufm_pods_running` | Verify UFM telemetry pods running | source |
| TC_SR_019 | `test_ufm_service` | Verify UFM external service created | source |
| TC_SR_020 | `test_vast_pods_running` | Verify VAST telemetry pods running | source |
| TC_SR_021 | `test_vast_service` | Verify VAST external service created | source |
| TC_SR_022 | `test_sfm_pods_running` | Verify SFM telemetry pods running | source |
| TC_SR_023 | `test_sfm_manifests` | Verify SFM manifests generated | source |

### Phase 5 — Cleanup (12 TCs) — *planned*

| TC ID | Test Function | Title | Marker |
|-------|--------------|-------|--------|
| TC_CL_001 | `test_deploy_cleanup` | Deploy telemetry (cleanup) | deploy |
| TC_CL_002 | `test_cleanup_kafka` | Verify cleanup_kafka removes Kafka resources | sanity |
| TC_CL_003 | `test_cleanup_victoria_metrics` | Verify cleanup_victoria_metrics removes VM resources | sanity |
| TC_CL_004 | `test_cleanup_victoria_logs` | Verify cleanup_victoria_logs removes VL resources | sanity |
| TC_CL_005 | `test_cleanup_idrac` | Verify cleanup_idrac removes iDRAC resources | sanity |
| TC_CL_006 | `test_cleanup_ldms` | Verify cleanup_ldms removes LDMS + Vector-LDMS | sanity |
| TC_CL_007 | `test_cleanup_ome` | Verify cleanup_ome removes OME + Vector-OME | sanity |
| TC_CL_008 | `test_cleanup_dcgm` | Verify cleanup_dcgm removes DCGM resources | sanity |
| TC_CL_009 | `test_cleanup_ufm` | Verify cleanup_ufm removes UFM resources | sanity |
| TC_CL_010 | `test_cleanup_vast` | Verify cleanup_vast removes VAST resources | sanity |
| TC_CL_011 | `test_no_pods_after_full_cleanup` | Verify no pods remain after full cleanup | sanity |
| TC_CL_012 | `test_no_pvcs_after_full_cleanup` | Verify no PVCs remain after full cleanup | sanity |

## Running Tests

```bash
# One-time setup
source setup_env.sh

# Run precheck scenario
./run_validation.sh precheck test

# Run validate scenario
./run_validation.sh validate test

# Run a specific scenario (deploy-only)
./run_validation.sh precheck deploy

# Run verification-only (no playbook execution)
./run_validation.sh precheck verify

# Run with marker filter
./run_validation.sh precheck test --marker sanity

# Run all FVT scenarios
./run_validation.sh all test

# Run batch from config
./run_validation.sh --config

# List scenarios
./run_validation.sh list
```

## Summary

| Phase | Scenarios | TCs | Status |
|-------|-----------|-----|--------|
| Phase 1 | precheck, validate | 13 | **Implemented** |
| Phase 2 | deploy (sinks: VM, VL, Kafka) | 13 | **Implemented** |
| Phase 3 | deploy (sources: iDRAC, LDMS, OME) | 13 | **Implemented** |
| Phase 4 | deploy (sources: PowerScale, UFM, VAST, SFM) | 8 | Planned |
| Phase 5 | cleanup | 12 | Planned |
| **Total** | | **59 FVT** | |
