# Omnia Telemetry

Dell Omnia Telemetry deploys and manages a comprehensive telemetry stack for
HPC and AI clusters. It collects metrics and logs from multiple sources
(iDRAC, LDMS, DCGM, OME, UFM, PowerScale, VAST, SFM)
and stores them in sink backends (Kafka, VictoriaMetrics, VictoriaLogs).

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

# Default (no tags) = validate + deploy (safe — cleanup never runs by default)
ansible-playbook playbooks/telemetry.yml
```

## Environment Variables (from omnia.env)

| Variable | Default | Description |
|----------|---------|-------------|
| `OMNIA_DATA_PATH` | `/opt/omnia` | Root data directory for all Omnia data |
| `OMNIA_PROJECT_NAME` | `project_default` | Project name (maps to input/output subdirs) |
| `OMNIA_VENV_PATH` | `/opt/omnia/venv` | Shared Python virtual environment |
| `SYSTEM_ADMIN_NIC_IPV4` | _(required)_ | OIM host admin NIC IP |
| `SYSTEM_HOSTNAME` | `oim` | OIM short hostname |
| `SYSTEM_DOMAIN_NAME` | `omnia.cluster` | OIM domain name |
| `TELEMETRY_DATA_PATH` | `$OMNIA_DATA_PATH/telemetry` | Override telemetry data path |

## Input Files

| File | Description |
|------|-------------|
| `input/telemetry_config.yml` | Main configuration — kube_vip, sources, sinks, bridges, credentials |
| `input/telemetry_storage_config.yml` | Storage backend configuration (PVC sizes, retention) |
| `input/telemetry_packages.yml` | Container registry, image versions, cluster_mount |

## Tags

### Lifecycle Tags (mutually exclusive — pick ONE)

| Tag | Default? | Description |
|-----|----------|-------------|
| _(none)_ | Yes | Default flow: setup + validate + deploy |
| `precheck` | No | Validate K8s prerequisites (kube_vip, nodes, pods) |
| `validate` | Yes | L1 schema + L2 logic validation of all input files |
| `deploy` / `execute` | Yes | Deploy sinks + sources + kustomize apply |
| `cleanup` | No | Remove all telemetry components (opt-in only) |
| `upgrade` | No | Upgrade telemetry (placeholder) |
| `rollback` | No | Rollback telemetry (placeholder) |

### Granular Cleanup Tags (opt-in — requires `--tags`)

| Tag | Scope |
|-----|-------|
| `cleanup_kafka` | Kafka cluster + Strimzi operator |
| `cleanup_victoria_metrics` | VictoriaMetrics + vmagent-vector |
| `cleanup_victoria_logs` | VictoriaLogs + vlagent-vector |
| `cleanup_idrac` | iDRAC telemetry (receiver, pumps, DB) |
| `cleanup_ldms` | LDMS + Vector-LDMS bridge |
| `cleanup_ome` | OME + Vector-OME bridge |
| `cleanup_dcgm` | DCGM GPU exporter |
| `cleanup_powerscale` | PowerScale telemetry |
| `cleanup_ufm` | UFM InfiniBand telemetry |
| `cleanup_vast` | VAST storage telemetry |
| `cleanup_sfm` | SFM network telemetry |

**Tag safety**: `cleanup`, `precheck`, `upgrade`, `rollback` use Ansible's `never`
tag — they NEVER execute unless explicitly requested with `--tags`.

## Telemetry Components

| Category | Source | Description |
|----------|--------|-------------|
| **Sinks** | Kafka (Strimzi) | Telemetry data streaming |
| | VictoriaMetrics | Time-series metrics storage and querying |
| | VictoriaLogs | Log aggregation and querying |
| **Compute** | iDRAC | Dell server BMC hardware telemetry |
| | LDMS | Lightweight Distributed Metric Service (HPC) |
| | DCGM | NVIDIA GPU telemetry |
| **Infrastructure** | OME | OpenManage Enterprise monitoring |
| | UFM | Unified Fabric Manager (InfiniBand) |
| | SFM | Smart Fabric Manager (network) |
| **Storage** | PowerScale | Dell PowerScale (Isilon) |
| | VAST | VAST Data storage |

## Directory Structure

```
telemetry/
├── ansible.cfg                    # Domain-root Ansible config
├── galaxy.yml                     # Galaxy collection metadata
├── meta/runtime.yml               # Ansible version compatibility
├── requirements.txt               # Python dependencies
├── requirements.yml               # Galaxy collection dependencies
├── domain-init.sh                 # Domain initialization script
├── README.md                      # This file
│
├── plugins/
│   ├── modules/                   # Custom Ansible modules
│   ├── module_utils/              # Module utility libraries
│   └── callback/                  # Callback plugins
│
├── playbooks/
│   ├── telemetry.yml              # Entry point — Step 0 setup + tag-based orchestrator
│   ├── ansible.cfg                # Playbook-level Ansible config
│   ├── precheck/
│   │   └── precheck.yml           # K8s cluster readiness checks
│   ├── validate/
│   │   └── validation.yml         # L1 + L2 input file validation
│   ├── deploy/
│   │   ├── deploy.yml             # Deploy orchestrator (phases 0-4)
│   │   ├── telemetry_prereq.yml   # Prerequisites (config, flags, kube_vip)
│   │   ├── sinks/                 # Sink deployment playbooks
│   │   │   └── deploy_sinks.yml   # Sink orchestrator (Kafka, VM, VL)
│   │   └── sources/               # Per-source deploy playbooks
│   │       ├── deploy_idrac_telemetry.yml
│   │       ├── deploy_ldms.yml
│   │       ├── deploy_dcgm.yml
│   │       ├── deploy_ome.yml
│   │       ├── deploy_ufm.yml
│   │       ├── deploy_powerscale.yml
│   │       ├── deploy_vast.yml
│   │       └── deploy_sfm.yml
│   ├── cleanup/
│   │   ├── cleanup.yml            # Cleanup orchestrator
│   │   ├── sinks/                 # Sink cleanup playbooks
│   │   │   ├── cleanup_kafka.yml
│   │   │   ├── cleanup_victoria_metrics.yml
│   │   │   └── cleanup_victoria_logs.yml
│   │   └── sources/               # Per-source cleanup playbooks
│   │       ├── cleanup_idrac.yml
│   │       ├── cleanup_ldms.yml
│   │       └── ...
│   ├── credentials/
│   │   └── get_telemetry_credentials.yml
│   ├── upgrade/
│   │   ├── upgrade.yml            # Upgrade orchestrator (placeholder)
│   │   └── sources/               # Per-source upgrade playbooks
│   └── rollback/
│       ├── rollback.yml           # Rollback orchestrator (placeholder)
│       └── sources/               # Per-source rollback playbooks
│
├── vars/                          # Shared cross-playbook variables
│   ├── cleanup.yml                # Cleanup resource definitions (namespaces, labels, resources)
│   └── deploy_sinks.yml           # Sink deployment summary template
│
├── roles/
│   ├── telemetry_setup/           # Step 0: omnia.env loading, path derivation, dir creation
│   ├── common/                    # Shared: config loading, flags, kustomization
│   ├── precheck/                  # K8s readiness checks
│   ├── deploy_kafka/              # Kafka (Strimzi) deployment
│   ├── deploy_victoria/           # VictoriaMetrics + VictoriaLogs
│   ├── deploy_idrac_telemetry/    # iDRAC telemetry
│   ├── deploy_ldms/               # LDMS telemetry
│   ├── deploy_dcgm/               # DCGM GPU telemetry
│   ├── deploy_ome/                # OME telemetry
│   ├── deploy_ufm/                # UFM telemetry
│   ├── deploy_powerscale/         # PowerScale telemetry
│   ├── deploy_vast/               # VAST telemetry
│   ├── deploy_sfm/                # SFM telemetry
│   └── collect_telemetry_credentials/
│
├── input/                         # Default input configuration files
├── output/                        # Runtime output (status files)
├── containers/                    # Container build files (LDMS)
└── docs/                          # Domain documentation
```

## Deploy Execution Order

```
Step 0: Setup (always) — read omnia.env, derive paths, create dirs
Step 1: Validate       — L1 schema + L2 logic validation
Step 2: Deploy
  Phase 0: Prerequisites — load config, derive flags, resolve kube_vip
  Phase 1: Sink infrastructure — Kafka, VictoriaMetrics, VictoriaLogs
  Phase 2: Source components — each enabled source generates K8s manifests
  Phase 3: Root kustomization — generate root kustomization.yaml
  Phase 4: Full-stack apply — kubectl apply -k deployments/
```

## Runtime Paths

All paths are derived from `OMNIA_DATA_PATH` and `OMNIA_PROJECT_NAME`:

| Path | Purpose |
|------|---------|
| `/var/log/omnia/telemetry/` | Ansible playbook execution logs |
| `$OMNIA_DATA_PATH/telemetry/input/$PROJECT/` | Runtime input configuration |
| `$OMNIA_DATA_PATH/telemetry/output/$PROJECT/` | Status files and output |
| `$OMNIA_DATA_PATH/telemetry/log/$PROJECT/` | Domain runtime logs |

## License

Apache-2.0

## Author Information

Dell Technologies (<omnia-support@dell.com>)
