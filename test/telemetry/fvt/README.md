# Telemetry — FVT Test Cases

## Tags

| Tag | Description | Playbook Tag |
|-----|-------------|--------------|
| precheck | Environment prechecks | precheck |
| validate | Validate inputs | validate |
| deploy | Deploy sinks + sources | deploy |
| cleanup | Cleanup resources | cleanup |

## Test Case Registry

### Namespace-Wide

| TC ID | Test | Marker |
|-------|------|--------|
| TC_NS_001 | Verify all telemetry pods running | sanity |

### Sinks

| TC ID | Test | Suite | Marker |
|-------|------|-------|--------|
| TC_SK_001 | Verify Kafka broker/controller pods running | kafka | sanity |
| TC_SK_002 | Verify Kafka cluster Ready condition | kafka | sanity |
| TC_SK_003 | Verify Kafka bridge pod running | kafka | sanity |
| TC_SK_004 | Verify VictoriaMetrics cluster pods running | victoriametrics | sanity |
| TC_SK_005 | Verify VMAgent pods running | victoriametrics | sanity |
| TC_SK_006 | Verify VictoriaLogs cluster pods running | victorialogs | sanity |
| TC_SK_007 | Verify VLAgent pods running | victorialogs | sanity |

### Sources: iDRAC

| TC ID | Test | Marker |
|-------|------|--------|
| TC_SR_001 | Verify iDRAC pod count matches bmc_group_data.csv | sanity |
| TC_SR_002 | Verify iDRAC StatefulSet pods ready | sanity |
| TC_SR_003 | Verify all iDRAC containers running | sanity |
| TC_SR_004 | Verify MySQL data in iDRAC telemetry pods | functional |
| TC_SR_005 | Verify iDRAC receiver is collecting metrics | functional |
| TC_SR_006 | Verify iDRAC Kafka topic exists | sanity |
| TC_SR_007 | Verify iDRAC VictoriaPump metrics endpoint | sanity |
| TC_SR_008 | Verify iDRAC telemetry service exists | sanity |
| TC_SR_009 | Verify iDRAC telemetry data in VictoriaMetrics | functional |

### Sources: LDMS

| TC ID | Test | Marker |
|-------|------|--------|
| TC_SR_020 | Verify LDMS aggregator pod running | sanity |
| TC_SR_021 | Verify LDMS store pod running | sanity |
| TC_SR_022 | Verify Vector-LDMS bridge deployment ready | sanity |
| TC_SR_023 | Verify LDMS Kafka topic exists | sanity |

### Sources: PowerScale

| TC ID | Test | Marker |
|-------|------|--------|
| TC_SR_030 | Verify CSM Metrics PowerScale deployment ready | sanity |
| TC_SR_031 | Verify OTEL Collector deployment ready | sanity |
| TC_SR_032 | Verify isilon-creds secret has correct endpoint | sanity |
| TC_SR_033 | Verify PowerScale metrics in VictoriaMetrics | functional |
| TC_SR_035 | Verify/configure PowerScale syslog forwarding | functional |
| TC_SR_034 | Verify PowerScale logs in VictoriaLogs | functional |
| TC_SR_036 | Verify comprehensive PowerScale deployment | functional |
| TC_SR_037 | Verify PowerScale feature flags | functional |
| TC_SR_038 | Verify PowerScale health metrics | functional |
| TC_SR_039 | Verify PowerScale TLS enforcement | functional |
| TC_SR_040 | Verify PowerScale label compliance | functional |
| TC_SR_041 | Verify PowerScale scrape interval | functional |
| TC_SR_042 | Verify CSI authorization mode | functional |
| TC_SR_043 | Verify PowerScale deployment mode | functional |
| TC_SR_044 | Verify CSI Volume Exporter deployment | functional |
| TC_SR_045 | Verify CSI Volume Exporter metrics endpoint | functional |
| TC_SR_046 | Verify CSI Volume Exporter metrics in VictoriaMetrics | functional |
| TC_SR_047 | Verify CSI Driver for PowerScale (isilon-controller) deployment | functional |

Note: TC_SR_035 (syslog config) runs before TC_SR_034 (log check) to
ensure syslog is configured before verifying log ingestion.

### Sources: UFM

| TC ID | Test | Marker |
|-------|------|--------|
| TC_SR_060 | Verify UFM external service exists with correct endpoint | sanity |
| TC_SR_061 | Verify UFM VMServiceScrape CR exists | sanity |
| TC_SR_062 | Verify UFM credentials K8s secret exists | sanity |
| TC_SR_063 | Verify UFM InfiniBand metrics in VictoriaMetrics | functional |

### Sources: OME

| TC ID | Test | Marker | Condition |
|-------|------|--------|-----------|
| TC_SR_070 | Verify Vector-OME bridge deployment ready | sanity | always |
| TC_SR_071 | Verify OME KafkaUser CR exists | sanity | always |
| TC_SR_072 | Verify external Kafka TLS certificates exist | functional | configure_ome=true |
| TC_SR_073 | Verify user.pfx certificate created for OME mTLS | functional | configure_ome=true |
| TC_SR_074 | Verify TLS certificates uploaded to OME | functional | configure_ome=true |
| TC_SR_075 | Verify OME Kafka forwarder connectivity status | functional | configure_ome=true |

When `configure_ome: false` in test_config.yml, only TC_SR_070 and
TC_SR_071 run. Set `configure_ome: true` to run the full OME integration
tests including TLS cert extraction and connectivity verification.

### Cleanup

| TC ID | Test | Marker |
|-------|------|--------|
| TC_CL_002 | Verify telemetry pods removed | sanity |
| TC_CL_003 | Verify Kafka topics removed | sanity |

### Playbook Execution

| TC ID | Test | Tag |
|-------|------|-----|
| TC_DP_001 | Deploy telemetry (full stack, no tags) | (none) |
| TC_DP_002 | Deploy telemetry (--tags deploy) | deploy |
| TC_PC_001 | Deploy telemetry (--tags precheck) | precheck |
| TC_VL_001 | Deploy telemetry (--tags validate) | validate |
| TC_CL_001 | Deploy telemetry (--tags cleanup) | cleanup |

## Execution

```bash
# Verify all (except cleanup)
./run_validation.sh telemetry verify

# Verify deploy tag only
./run_validation.sh telemetry deploy verify

# Exec playbook + verify
./run_validation.sh telemetry test

# Exec with specific tag + verify
./run_validation.sh telemetry deploy test

# Sanity only
./run_validation.sh telemetry verify --marker sanity

# Sources only
./run_validation.sh telemetry deploy verify --suite sources
```
