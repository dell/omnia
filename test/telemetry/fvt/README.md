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
| TC_SR_001 | Verify iDRAC StatefulSet pods ready | sanity |
| TC_SR_002 | Verify all iDRAC containers running | sanity |
| TC_SR_003 | Verify iDRAC Kafka topic exists | sanity |
| TC_SR_004 | Verify iDRAC VictoriaPump metrics endpoint | sanity |
| TC_SR_005 | Verify iDRAC telemetry service exists | sanity |
| TC_SR_020 | Verify iDRAC telemetry data in VictoriaMetrics | functional |

### Sources: LDMS

| TC ID | Test | Marker |
|-------|------|--------|
| TC_SR_006 | Verify Vector-LDMS bridge deployment ready | sanity |
| TC_SR_007 | Verify LDMS Kafka topic exists | sanity |

### Sources: PowerScale

| TC ID | Test | Marker |
|-------|------|--------|
| TC_SR_008 | Verify CSM Metrics PowerScale deployment ready | sanity |
| TC_SR_009 | Verify OTEL Collector deployment ready | sanity |
| TC_SR_010 | Verify isilon-creds secret has correct endpoint | sanity |
| TC_SR_011 | Verify PowerScale metrics in VictoriaMetrics | functional |
| TC_SR_012 | Verify PowerScale logs in VictoriaLogs | functional |
| TC_SR_013 | Verify PowerScale syslog forwarding configured | functional |

### Sources: OME

| TC ID | Test | Marker |
|-------|------|--------|
| TC_SR_014 | Verify Vector-OME bridge deployment ready | sanity |
| TC_SR_015 | Verify OME KafkaUser CR exists | sanity |
| TC_SR_021 | Verify OME Kafka forwarder connectivity status | functional |

### Sources: UFM

| TC ID | Test | Marker |
|-------|------|--------|
| TC_SR_016 | Verify UFM external service exists with correct endpoint | sanity |
| TC_SR_017 | Verify UFM VMServiceScrape CR exists | sanity |
| TC_SR_018 | Verify UFM credentials K8s secret exists | sanity |
| TC_SR_019 | Verify UFM InfiniBand metrics in VictoriaMetrics | functional |

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
