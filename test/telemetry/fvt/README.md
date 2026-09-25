# Telemetry — FVT Test Cases

Telemetry uses the stable domain code `TEL`. FVT IDs follow
`TEL_FVT_<TAG>_<TYPE><SEQ>`, where `E` executes a playbook operation and `V`
verifies its result. Untagged full-stack execution uses the reserved `FULL`
tag.

## Tags

| Tag | Description | Playbook Tag |
|-----|-------------|--------------|
| precheck | Environment prechecks | precheck |
| validate | Validate inputs | validate |
| deploy | Deploy sinks + sources | deploy |
| cleanup | Cleanup resources | cleanup |

## Test Case Registry

### Precheck

| TC ID | Test | Marker |
|-------|------|--------|
| TEL_FVT_PRECHECK_E001 | Deploy telemetry (`--tags precheck`) | deploy, sanity |
| TEL_FVT_PRECHECK_V001 | Verify `omnia.env` variables present | sanity |
| TEL_FVT_PRECHECK_V002 | Verify Kubernetes nodes are Ready | sanity |
| TEL_FVT_PRECHECK_V003 | Verify `kube_vip` is reachable | sanity |
| TEL_FVT_PRECHECK_V004 | Verify PowerScale user privileges | sanity |

### Validate

| TC ID | Test | Marker |
|-------|------|--------|
| TEL_FVT_VALIDATE_E001 | Deploy telemetry (`--tags validate`) | deploy, sanity |
| TEL_FVT_VALIDATE_V001 | Verify `telemetry_config.yml` is valid and parseable | sanity |

### Namespace-Wide

| TC ID | Test | Marker |
|-------|------|--------|
| TEL_FVT_DEPLOY_V008 | Verify all telemetry pods running | sanity |

### Sinks

| TC ID | Test | Suite | Marker |
|-------|------|-------|--------|
| TEL_FVT_DEPLOY_V001 | Verify Kafka broker/controller pods running | kafka | sanity |
| TEL_FVT_DEPLOY_V002 | Verify Kafka cluster Ready condition | kafka | sanity |
| TEL_FVT_DEPLOY_V003 | Verify Kafka bridge pod running | kafka | sanity |
| TEL_FVT_DEPLOY_V004 | Verify VictoriaMetrics cluster pods running | victoriametrics | sanity |
| TEL_FVT_DEPLOY_V005 | Verify VMAgent pods running | victoriametrics | sanity |
| TEL_FVT_DEPLOY_V006 | Verify VictoriaLogs cluster pods running | victorialogs | sanity |
| TEL_FVT_DEPLOY_V007 | Verify VLAgent pods running | victorialogs | sanity |

### Sources: iDRAC

| TC ID | Test | Marker |
|-------|------|--------|
| TEL_FVT_DEPLOY_V010 | Verify iDRAC pod count matches bmc_group_data.csv | sanity |
| TEL_FVT_DEPLOY_V011 | Verify iDRAC StatefulSet pods ready | sanity |
| TEL_FVT_DEPLOY_V012 | Verify all iDRAC containers running | sanity |
| TEL_FVT_DEPLOY_V013 | Verify MySQL data in iDRAC telemetry pods | functional |
| TEL_FVT_DEPLOY_V014 | Verify iDRAC receiver is collecting metrics | functional |
| TEL_FVT_DEPLOY_V015 | Verify topic readiness and fresh iDRAC metrics in Kafka | sanity |
| TEL_FVT_DEPLOY_V016 | Verify iDRAC VictoriaPump metrics endpoint | sanity |
| TEL_FVT_DEPLOY_V017 | Verify iDRAC telemetry service exists | sanity |
| TEL_FVT_DEPLOY_V018 | Verify iDRAC telemetry data in VictoriaMetrics | functional |

### Sources: LDMS

| TC ID | Test | Marker |
|-------|------|--------|
| TEL_FVT_DEPLOY_V020 | Verify LDMS aggregator pod running | sanity |
| TEL_FVT_DEPLOY_V021 | Verify LDMS store pod running | sanity |
| TEL_FVT_DEPLOY_V022 | Verify Vector-LDMS bridge deployment ready | sanity |
| TEL_FVT_DEPLOY_V023 | Verify LDMS package installed on Slurm nodes | sanity |
| TEL_FVT_DEPLOY_V024 | Verify LDMS sampler service running on Slurm nodes | sanity |
| TEL_FVT_DEPLOY_V025 | Verify LDMS sampler plugins configured | sanity |
| TEL_FVT_DEPLOY_V026 | Verify LDMS Kafka topic exists | sanity |
| TEL_FVT_DEPLOY_V027 | Verify earliest LDMS data in Kafka | functional |
| TEL_FVT_DEPLOY_V028 | Verify latest LDMS data in Kafka | functional |

### Sources: PowerScale

| TC ID | Test | Marker |
|-------|------|--------|
| TEL_FVT_DEPLOY_V030 | Verify CSM Metrics PowerScale deployment ready | sanity |
| TEL_FVT_DEPLOY_V031 | Verify OTEL Collector deployment ready | sanity |
| TEL_FVT_DEPLOY_V032 | Verify isilon-creds secret has correct endpoint | sanity |
| TEL_FVT_DEPLOY_V033 | Verify PowerScale metrics in VictoriaMetrics | functional |
| TEL_FVT_DEPLOY_V035 | Verify/configure PowerScale syslog forwarding | functional |
| TEL_FVT_DEPLOY_V034 | Verify PowerScale logs in VictoriaLogs | functional |
| TEL_FVT_DEPLOY_V036 | Verify comprehensive PowerScale deployment | functional |
| TEL_FVT_DEPLOY_V037 | Verify PowerScale feature flags | functional |
| TEL_FVT_DEPLOY_V038 | Verify PowerScale health metrics | functional |
| TEL_FVT_DEPLOY_V040 | Verify PowerScale TLS enforcement | functional |
| TEL_FVT_DEPLOY_V041 | Verify PowerScale label compliance | functional |
| TEL_FVT_DEPLOY_V042 | Verify PowerScale scrape interval | functional |
| TEL_FVT_DEPLOY_V043 | Verify CSI authorization mode | functional |
| TEL_FVT_DEPLOY_V044 | Verify PowerScale deployment mode | functional |
| TEL_FVT_DEPLOY_V045 | Verify CSI Volume Exporter deployment | functional |
| TEL_FVT_DEPLOY_V046 | Verify CSI Volume Exporter metrics endpoint | functional |
| TEL_FVT_DEPLOY_V047 | Verify CSI Volume Exporter metrics in VictoriaMetrics | functional |
| TEL_FVT_DEPLOY_V048 | Verify CSI Driver for PowerScale deployment | functional |
| TEL_FVT_DEPLOY_V049 | Verify external health monitor container | functional |
| TEL_FVT_DEPLOY_V050 | Verify CSI exporter is skipped without health monitor | functional |
| TEL_FVT_DEPLOY_V051 | Verify missing-health-monitor warning | functional |
| TEL_FVT_DEPLOY_V052 | Verify CSM Metrics to OTEL Collector data flow | functional |
| TEL_FVT_DEPLOY_V053 | Verify OTEL Collector export to VictoriaMetrics | functional |
| TEL_FVT_DEPLOY_V054 | Verify cert-manager TLS certificate generation | functional |

Note: TEL_FVT_DEPLOY_V035 (syslog config) runs before TEL_FVT_DEPLOY_V034 (log check) to
ensure syslog is configured before verifying log ingestion.

### Sources: UFM

| TC ID | Test | Marker |
|-------|------|--------|
| TEL_FVT_DEPLOY_V060 | Verify UFM external service exists with correct endpoint | sanity + ufm |
| TEL_FVT_DEPLOY_V061 | Verify UFM VMServiceScrape CR exists | sanity + ufm |
| TEL_FVT_DEPLOY_V062 | Verify UFM credentials K8s secret exists | sanity + ufm |
| TEL_FVT_DEPLOY_V063 | Verify UFM InfiniBand metrics in VictoriaMetrics | functional + ufm |

Run only the UFM source verification:

```bash
./run_validation.sh fvt_telemetry deploy verify --suite sources --marker ufm
```

### Sources: VAST

| TC ID | Test | Marker | Condition |
|-------|------|--------|-----------|
| TEL_FVT_DEPLOY_V090 | Verify VAST external service and endpoint | sanity + vast | metrics enabled |
| TEL_FVT_DEPLOY_V091 | Verify VAST VMServiceScrape configuration | sanity + vast | metrics enabled |
| TEL_FVT_DEPLOY_V092 | Verify VAST credentials secret | sanity + vast | metrics enabled with basic auth |
| TEL_FVT_DEPLOY_V093 | Verify fresh VAST metrics in VictoriaMetrics | functional + vast | metrics enabled |
| TEL_FVT_DEPLOY_V095 | Configure VAST syslog and send a test event | functional + vast | logs enabled, `victoria_logs` target, and VAST management credentials available |
| TEL_FVT_DEPLOY_V094 | Verify fresh VAST test event in VictoriaLogs | functional + vast | logs enabled and TEL_FVT_DEPLOY_V095 completed in the same runner test invocation |

Run only VAST source verification:

```bash
# The focused marker run assumes the Telemetry stack is already deployed.
./run_validation.sh fvt_telemetry deploy verify --suite sources --marker vast
```

The metrics case verifies that the VAST scrape target is up, returns samples,
and produces fresh `source_subsystem="vast"` metrics. It discovers metric
names dynamically because VAST exporter names differ across releases. For the
log path, the first verification case reads the deployed VAST and VLAgent settings,
configures the appliance syslog target through the VAST API, verifies the API
readback, and sends one test notification. The verification case then polls
VictoriaLogs for that run's fresh event. Its report lists the event count,
source hosts, earliest and latest UTC timestamps, and up to five newest safe
RFC5424 header summaries; raw message bodies and credentials are never shown.
Both cases run in order under one `verify` command and share one report ID. A
fresh environment should first run the normal unfiltered `deploy` execution;
the `vast` marker deliberately does not select the general deployment case.

### Sources: OME

| TC ID | Test | Marker | Condition |
|-------|------|--------|-----------|
| TEL_FVT_DEPLOY_V070 | Verify Vector-OME bridge deployment ready | sanity | metrics or logs bridge enabled |
| TEL_FVT_DEPLOY_V071 | Verify OME KafkaUser CR exists | sanity | metrics or logs bridge enabled |
| TEL_FVT_DEPLOY_V072 | Verify external Kafka connection artifacts | functional | configure_ome=true, metrics or logs source enabled |
| TEL_FVT_DEPLOY_V073 | Verify user.pfx certificate created for OME mTLS | functional | configure_ome=true, metrics or logs source enabled |
| TEL_FVT_DEPLOY_V074 | Verify TLS certificates uploaded to OME | functional | configure_ome=true, metrics or logs source enabled |
| TEL_FVT_DEPLOY_V075 | Verify OME Kafka forwarder connectivity status | functional | configure_ome=true, metrics or logs source enabled |
| TEL_FVT_DEPLOY_V076 | Verify uploaded certificate matches generated certificate | functional | configure_ome=true, metrics or logs source enabled |
| TEL_FVT_DEPLOY_V077 | Verify enabled OME Kafka topics exist | functional | configure_ome=true, metrics or logs source enabled |
| TEL_FVT_DEPLOY_V078 | Verify OME telemetry data in Kafka | functional | configure_ome=true, metrics source enabled |
| TEL_FVT_DEPLOY_V079 | Verify OME inventory data in Kafka | functional | configure_ome=true, metrics source enabled |
| TEL_FVT_DEPLOY_V080 | Verify OME alerts data in Kafka | functional | configure_ome=true, logs source enabled |
| TEL_FVT_DEPLOY_V081 | Verify OME health data in Kafka | functional | configure_ome=true, metrics source enabled |
| TEL_FVT_DEPLOY_V082 | Verify OME audit logs data in Kafka | functional | configure_ome=true, logs source enabled |
| TEL_FVT_DEPLOY_V083 | Verify OME telemetry metrics in VictoriaMetrics | functional | configure_ome=true, metrics source and bridge enabled |
| TEL_FVT_DEPLOY_V084 | Verify OME inventory metrics in VictoriaMetrics | functional | configure_ome=true, metrics source and bridge enabled |
| TEL_FVT_DEPLOY_V085 | Verify OME health metrics in VictoriaMetrics | functional | configure_ome=true, metrics source and bridge enabled |
| TEL_FVT_DEPLOY_V086 | Verify OME alerts in VictoriaLogs | functional | configure_ome=true, logs source and bridge enabled |
| TEL_FVT_DEPLOY_V087 | Verify OME audit logs in VictoriaLogs | functional | configure_ome=true, logs source and bridge enabled |

When `configure_ome: false` in test_config.yml, only TEL_FVT_DEPLOY_V070 and TEL_FVT_DEPLOY_V071
run when at least one Vector-OME bridge channel is enabled. Set
`configure_ome: true` to run the applicable OME integration tests including
TLS cert extraction and connectivity verification. Metrics-only configuration
runs telemetry, inventory, and health checks; logs-only configuration runs
alerts and auditlogs checks; enabling both channels runs all five. Kafka tests
follow the source flags, while Victoria tests require both the matching source
and Vector-OME bridge flag.
The connectivity test allows up to 5 minutes for OME's asynchronous
reconnection. Topic discovery and each OME data-topic check allow up to
2 minutes. The VictoriaMetrics checks discover metric names dynamically and
report a `✓` row with the true earliest and latest sample timestamp for every
metric found in the telemetry, inventory, and health streams. The
VictoriaLogs checks cover the event-driven alerts and auditlogs streams. The
optional `ome.logs` route is not required because it is not one of the OME
Kafka topics created by the supported forwarding workflow.

### Sources: SFM

| TC ID | Test | Marker | Condition |
|-------|------|--------|-----------|
| TEL_FVT_DEPLOY_V100 | Verify required Omnia workloads and pods for SFM | sanity | configure_sfm=true |
| TEL_FVT_DEPLOY_V101 | Verify required Omnia services for SFM | sanity | configure_sfm=true |
| TEL_FVT_DEPLOY_V102 | Configure and verify the SFM switch data path | functional | configure_sfm=true |
| TEL_FVT_DEPLOY_V103 | Configure and verify SFM observability Remote Write | functional | configure_sfm=true |
| TEL_FVT_DEPLOY_V104 | Verify three SFM metrics and timestamps in VictoriaMetrics | functional | configure_sfm=true |

SFM integration is opt-in. Set `configure_sfm: true`, `sfm_api_ip`, and
`sfm_ssh_ip` in `test_config.yml`, then run `bash setup_env.sh --set-creds` to
store the required SFM API and SSH credentials in encrypted `test_creds.yml`.
The runner rejects unknown SSH host keys, so verify the SFM key in
`known_hosts` before executing these cases. The API address must be directly
reachable from the runner. The SFM instance is fixed to instance 1. This lab
integration has no configurable API CA bundle or API TLS-verification setting;
run it only on an authorized network.

The cases execute in dependency order: Victoria export plus Omnia workload and
pod readiness, Omnia service and endpoint readiness, the complete SFM switch
network configuration, transactional certificate/Remote Write configuration
with target health, and three-metric earliest/latest timestamp verification in
VictoriaMetrics.

Warning: these tests configure an external appliance. They may import a CA
certificate, create or update the `victoria` Remote Write target, and modify
`/etc/hosts` inside the SFM Prometheus pod. The pod-local mapping does not
survive pod recreation, so configuration and health helpers reapply it to the
current pod. Previous certificate imports are retained as rollback material.

```bash
./run_validation.sh fvt_telemetry deploy verify --suite sources --marker sfm
```

### Sources: Install Mode

| TC ID | Test | Marker |
|-------|------|--------|
| TEL_FVT_DEPLOY_V110 | Verify `telemetry_packages.yml` install mode | sanity |
| TEL_FVT_DEPLOY_V111 | Verify Python packages for the active mode | sanity |
| TEL_FVT_DEPLOY_V112 | Verify iDRAC deployment for the active mode | sanity |
| TEL_FVT_DEPLOY_V113 | Verify iDRAC pods for the active mode | sanity |
| TEL_FVT_DEPLOY_V114 | Verify PowerScale dependencies for the active mode | sanity |
| TEL_FVT_DEPLOY_V115 | Verify PowerScale deployment for the active mode | sanity |

### Cleanup

| TC ID | Test | Marker | Condition |
|-------|------|--------|-----------|
| TEL_FVT_CLEANUP_V001 | Verify telemetry pods removed | sanity | always |
| TEL_FVT_CLEANUP_V002 | Verify Kafka topics removed | sanity | `DELETE_SINKS_VOLUME=true` |
| TEL_FVT_CLEANUP_V003 | Verify Kafka pods removed | sanity | always |
| TEL_FVT_CLEANUP_V004 | Verify VictoriaMetrics pods removed | sanity | always |
| TEL_FVT_CLEANUP_V005 | Verify VictoriaLogs pods removed | sanity | always |
| TEL_FVT_CLEANUP_V006 | Verify iDRAC pods removed | sanity | source enabled |
| TEL_FVT_CLEANUP_V007 | Verify LDMS pods removed | sanity | source enabled |
| TEL_FVT_CLEANUP_V008 | Verify OME pods removed | sanity | source enabled |
| TEL_FVT_CLEANUP_V009 | Verify UFM resources removed | sanity | source enabled |
| TEL_FVT_CLEANUP_V010 | Verify VAST resources removed | sanity | source enabled |
| TEL_FVT_CLEANUP_V011 | Verify SFM pods removed | sanity | source enabled |
| TEL_FVT_CLEANUP_V012 | Verify no pods remain after full cleanup | sanity | always |
| TEL_FVT_CLEANUP_V013 | Verify no PVCs remain after full cleanup | sanity | `DELETE_SINKS_VOLUME=true` |
| TEL_FVT_CLEANUP_V014 | Verify PVCs preserved after cleanup | sanity | `DELETE_SINKS_VOLUME` unset/`false` (default) |

**Conditional Cleanup Tests**: When `DELETE_SINKS_VOLUME=true`, the cleanup
playbook is invoked with `-e Delete_sinks_volume=true`,
`TEL_FVT_CLEANUP_V013` is reported, and `TEL_FVT_CLEANUP_V002` runs. When the
variable is unset or `false`, `TEL_FVT_CLEANUP_V014` is reported and
`TEL_FVT_CLEANUP_V002` is skipped. See `status/test_cleanup_final.py` and the
`delete_sinks_volume` fixture defined in `conftest.py`.

TEL_FVT_CLEANUP_V002 is skipped when `DELETE_SINKS_VOLUME` is unset/`false`: per
`src/telemetry/roles/cleanup/tasks/kafka.yml`, KafkaTopic CRDs are only
deleted when `delete_sinks_volume=true` — otherwise topic metadata is kept
alongside the retained Kafka PVCs.

### Playbook Execution

| TC ID | Test | Tag |
|-------|------|-----|
| TEL_FVT_FULL_E001 | Deploy telemetry (full stack, no tags) | (none) |
| TEL_FVT_DEPLOY_E001 | Deploy telemetry (--tags deploy) | deploy |
| TEL_FVT_PRECHECK_E001 | Deploy telemetry (--tags precheck) | precheck |
| TEL_FVT_VALIDATE_E001 | Deploy telemetry (--tags validate) | validate |
| TEL_FVT_CLEANUP_E001 | Deploy telemetry (--tags cleanup) | cleanup |

### Legacy ID migration

Historical telemetry reports used `TC_*` IDs that were not domain-qualified
and sometimes reused the same ID for different cases. `LEGACY_ID_MAP` in
`library/vars/test_case_vars.py` records every old-to-current mapping; ambiguous
legacy IDs map to all valid current IDs.

## Execution

```bash
# Verify all (except cleanup)
./run_validation.sh fvt_telemetry verify

# Verify deploy tag only
./run_validation.sh fvt_telemetry deploy verify

# Exec playbook + verify
./run_validation.sh fvt_telemetry test

# Exec with specific tag + verify
./run_validation.sh fvt_telemetry deploy test

# Sanity only
./run_validation.sh fvt_telemetry verify --marker sanity

# Sources only
./run_validation.sh fvt_telemetry deploy verify --suite sources
```

## Related Documentation

- See `../nft/README.md` for NFT test cases (performance, idempotency, resilience)
- See `../README.md` for overall test automation documentation
