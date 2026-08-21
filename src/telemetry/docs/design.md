# Telemetry — Design Overview

## Architecture

The telemetry domain deploys a modular telemetry stack on top of a Kubernetes
cluster. It consists of:

1. **Sinks** — Data storage and querying backends:
   - Kafka / Strimzi (data streaming)
   - VictoriaMetrics (time-series metrics)
   - VictoriaLogs (log aggregation)

2. **Sources** — Telemetry collectors:
   - iDRAC (Dell server hardware BMC)
   - DCGM (NVIDIA GPU)
   - LDMS (Lightweight Distributed Metric Service, HPC)
   - OME (OpenManage Enterprise)
   - UFM (Unified Fabric Manager, InfiniBand)
   - PowerScale (Dell Isilon storage)
   - VAST (VAST Data storage)
   - SFM (Smart Fabric Manager, network)
   - Skyway
   - PowerVault (Dell PowerVault storage)

3. **Bridges** — Data ingestion pipelines:
   - Vector-LDMS (Kafka-to-VictoriaMetrics for LDMS)
   - Vector-OME (Kafka-to-VictoriaMetrics for OME)

## Execution Flow

```
playbooks/telemetry.yml (entry point)
  |
  |  STEP 0 (always): telemetry_setup role
  |    - Read omnia.env (OMNIA_DATA_PATH, OMNIA_PROJECT_NAME, OMNIA_VENV_PATH, ...)
  |    - Derive input_project_dir, output_project_dir, log_dir
  |    - Auto-copy input files from source if runtime dir is missing
  |    - Create runtime directories
  |
  |  DEFAULT FLOW (no tags = validate + deploy):
  |
  +-- validate/validation.yml          [tag: validate]      L1 + L2 validation
  +-- deploy/deploy.yml                [tag: deploy]
  |     +-- telemetry_prereq.yml       Phase 0: config, flags, kube_vip
  |     +-- sinks/deploy_sinks.yml     Phase 1: Kafka, VM, VL
  |     +-- sources/deploy_*.yml       Phase 2: per-source (conditional)
  |     +-- (kustomize apply)          Phase 3-4: root kustomization + apply
  |     +-- write_telemetry_status     Phase 5: write output/telemetry_status.yml
  |
  |  OPT-IN FLOWS (require explicit --tags):
  |
  +-- precheck/precheck.yml            [tag: precheck]      K8s readiness
  +-- cleanup/cleanup.yml              [tag: cleanup]       Component removal
  |     +-- sources/cleanup_*.yml      Per-source cleanup (vars from ../../vars/cleanup.yml)
  |     +-- sinks/cleanup_kafka.yml    Per-sink cleanup (vars from ../../vars/cleanup.yml)
  |     +-- sinks/cleanup_victoria_*.yml
  +-- upgrade/upgrade.yml              [tag: upgrade]       Placeholder
  +-- rollback/rollback.yml            [tag: rollback]      Placeholder
```

### Tag Safety

Opt-in flows (`precheck`, `cleanup`, `upgrade`, `rollback`) use Ansible's
`never` tag — they **never** execute unless explicitly requested with `--tags`.
Running `telemetry.yml` without tags is always safe: setup + validate + deploy.

## Environment Configuration (omnia.env)

The `telemetry_setup` role reads environment variables from `omnia.env` at
runtime, matching the `image_build_setup` pattern used by image_build_manager.

| Variable | Default | Used For |
|----------|---------|----------|
| `OMNIA_DATA_PATH` | `/opt/omnia` | Root for `input_project_dir`, `output_project_dir` |
| `OMNIA_PROJECT_NAME` | `project_default` | Project subdirectory name |
| `OMNIA_VENV_PATH` | `/opt/omnia/venv` | Shared Python virtual environment |
| `SYSTEM_ADMIN_NIC_IPV4` | _(required)_ | OIM host IP |
| `SYSTEM_HOSTNAME` | `oim` | Host identification |
| `SYSTEM_DOMAIN_NAME` | `omnia.cluster` | Domain identification |
| `TELEMETRY_DATA_PATH` | `$OMNIA_DATA_PATH/telemetry` | Override telemetry data root |

Derived paths:
- `input_project_dir` = `$TELEMETRY_DATA_PATH/input/$OMNIA_PROJECT_NAME`
- `output_project_dir` = `$TELEMETRY_DATA_PATH/output/$OMNIA_PROJECT_NAME`
- `log_dir` = `$TELEMETRY_DATA_PATH/log/$OMNIA_PROJECT_NAME`

## Deploy Phases

| Phase | Playbook | Description |
|-------|----------|-------------|
| 0 | `telemetry_prereq.yml` | Load config, derive sink flags, resolve kube_vip |
| 1 | `deploy_sinks.yml` | Deploy Kafka, VictoriaMetrics, VictoriaLogs |
| 2 | `sources/deploy_<source>.yml` | Per-source manifest generation (conditional) |
| 3 | (inline play) | Generate root `kustomization.yaml` |
| 4 | (inline play) | `kubectl apply -k deployments/` + pod stabilization |
| 5 | `write_telemetry_status` | Write `telemetry_status.yml` to output dir |

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
