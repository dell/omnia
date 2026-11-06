# Omnia Telemetry

Telemetry is an Ansible Galaxy collection that deploys and manages a comprehensive telemetry stack for HPC and AI clusters. It collects metrics and logs from multiple sources (iDRAC, LDMS, OME, UFM, PowerScale, VAST, SFM) and stores them in sink backends (Kafka, VictoriaMetrics, VictoriaLogs) running on Kubernetes.

## Overview

Telemetry provides end-to-end observability for HPC and AI clusters by:

- Deploying telemetry sources: iDRAC, LDMS, OME, UFM, PowerScale, VAST, SFM
- Deploying telemetry sinks: Kafka (Strimzi), VictoriaMetrics, VictoriaLogs
- Running on Kubernetes as workloads on kube_vip
- Using Vector bridges to connect sources to sinks
- Supporting selective deployment of individual components
- Providing retention and cleanup management

## Architecture

Telemetry follows a Sources → Bridge (Vector) → Sinks architecture:

### Sources
- **iDRAC**: Dell server BMC hardware telemetry
- **LDMS**: Lightweight Distributed Metric Service for HPC metrics
- **OME**: OpenManage Enterprise monitoring
- **UFM**: Unified Fabric Manager (InfiniBand)
- **SFM**: Smart Fabric Manager (network)
- **PowerScale**: Dell PowerScale (Isilon) storage
- **VAST**: VAST Data storage

### Sinks
- **Kafka (Strimzi)**: Telemetry data streaming
- **VictoriaMetrics**: Time-series metrics storage and querying
- **VictoriaLogs**: Log aggregation and querying

## Prerequisites

| Requirement | Version |
|-------------|---------|
| Ansible     | >= 2.20 |
| Python      | >= 3.12 |
| OS          | RHEL/Rocky Linux 10.x |
| Kubernetes  | Required — telemetry runs as K8s workloads on kube_vip |

## Quick Start

```bash
# 1. Source omnia.env (sets OMNIA_DATA_PATH, OMNIA_PROJECT_NAME, etc.)
set -a; source src/main/omnia.env; set +a

# 2. Setup virtual environment (one-time)
./omnia.sh --setup-venv

# 3. Run telemetry (via omnia.sh — recommended)
./omnia.sh -r telemetry --tags deploy       # Full deployment
./omnia.sh -r telemetry --tags precheck     # Environment validation
./omnia.sh -r telemetry --tags validate     # Input config validation
./omnia.sh -r telemetry --tags cleanup      # Remove all telemetry

# Or from domain root
cd src/telemetry
ansible-playbook playbooks/telemetry.yml --tags deploy
```

## Tags

### Lifecycle Tags (mutually exclusive — pick ONE)

| Tag | Default? | Description |
|-----|----------|-------------|
| _(none)_ | Yes | Default flow: setup + validate + precheck + deploy |
| `precheck` | No | Run K8s and enabled Slurm prerequisite checks without deploying |
| `validate` | Yes | L1 schema + L2 logic validation of all input files |
| `deploy` / `execute` | Yes | Precheck, then deploy sinks + sources + kustomize apply |
| `deploy_sinks` | No | Deploy only selected sink infrastructure: Kafka, VictoriaMetrics, and/or VictoriaLogs |
| `cleanup` | No | Remove telemetry runtime resources; delete source volumes, preserve sink volumes by default |

### Granular Cleanup Tags (opt-in — requires `--tags`)

| Tag | Scope |
|-----|-------|
| `cleanup_sinks` | Selective sink cleanup with dependency checking |
| `cleanup_idrac` | iDRAC telemetry (receiver, pumps, DB) |
| `cleanup_ldms` | LDMS + Vector-LDMS bridge |
| `cleanup_ome` | OME + Vector-OME bridge |
| `cleanup_powerscale` | PowerScale telemetry |
| `cleanup_ufm` | UFM InfiniBand telemetry |
| `cleanup_vast` | VAST storage telemetry |

## Sink Deployment

Deploy one or more sinks independently of telemetry sources:

```bash
./omnia.sh -r telemetry --tags deploy_sinks -e kafka
./omnia.sh -r telemetry --tags deploy_sinks -e kafka,victoria_metrics
./omnia.sh -r telemetry --tags deploy_sinks -e kafka -e victoria_logs
```

## Cleanup

```bash
# Full cleanup (deletes source volumes, preserves sink volumes by default)
ansible-playbook playbooks/telemetry.yml --tags cleanup

# Preserve credentials for redeployment
ansible-playbook playbooks/telemetry.yml --tags cleanup -e cleanup_credentials=false

# Preserve both credentials and logs
ansible-playbook playbooks/telemetry.yml --tags cleanup -e cleanup_credentials=false -e cleanup_logs=false

# Explicitly delete sink PVCs during cleanup
ansible-playbook playbooks/telemetry.yml --tags cleanup -e delete_sinks_volume=true
```

## Documentation

- [Telemetry Documentation](https://omnia.readthedocs.io/en/latest/HowTo/Telemetry/index.html)
- [Architecture](docs/architecture.md)
- [Omnia GitHub](https://github.com/dell/omnia)
- [Issues](https://github.com/dell/omnia/issues)

## License

Apache-2.0

## Author Information

Dell Technologies (<omnia-support@dell.com>)
