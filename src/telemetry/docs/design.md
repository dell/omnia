# Telemetry — Design Overview

## Architecture

The telemetry domain deploys a modular telemetry stack on top of a Kubernetes
cluster. It consists of:

1. **Sinks** — Data storage and querying backends:
   - VictoriaMetrics (time-series metrics)
   - VictoriaLogs (log aggregation)
   - Kafka / Strimzi (data streaming)

2. **Sources** — Telemetry collectors:
   - iDRAC (Dell server hardware)
   - DCGM (NVIDIA GPU)
   - LDMS (HPC node metrics)
   - OME (OpenManage Enterprise)
   - UFM (InfiniBand fabric)
   - PowerScale (storage)
   - VAST (storage)
   - SFM (network fabric)
   - Skyway
   - PowerVault (storage)

## Execution Flow

```
telemetry.yml (entry point)
  |
  +-- playbooks/precheck.yml       [tag: precheck]
  +-- playbooks/validation.yml     [tag: validation]
  +-- playbooks/cleanup.yml        [tag: cleanup]
  +-- playbooks/deploy.yml         [tag: deploy]
  |     +-- deploy_sinks.yml       (Kafka, VictoriaMetrics, VictoriaLogs)
  |     +-- deploy_<source>.yml    (per-source deployment)
  +-- playbooks/upgrade.yml        [tag: upgrade]
  +-- playbooks/rollback.yml       [tag: rollback]
```

## Configuration

All configuration is read from `input/telemetry_config.yml`. Only sources with
`metrics_enabled: true` (or `logs_enabled: true`) are deployed.

## Kubernetes Integration

All Kubernetes tasks (kubectl, helm) execute on the `kube_vip` host via SSH
delegation. The domain requires a functioning Kubernetes cluster with Helm
support.

## Input Validation

The domain implements two-level input validation:
- **L1 (Schema)**: JSON Schema validation of all three input files
- **L2 (Logic)**: Cross-field logical validation (e.g., PowerScale requires
  VictoriaMetrics when metrics_enabled is true)
