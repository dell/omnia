# Omnia Telemetry

Telemetry (`omnia.telemetry`) deploys telemetry sources, Vector bridges, and sinks as Kubernetes workloads on the service Kubernetes cluster. It collects metrics and logs from iDRAC, LDMS, OME, UFM, PowerScale, and VAST, and stores them in Kafka, VictoriaMetrics, and VictoriaLogs.

## Overview

Telemetry follows a Sources -> Bridge (Vector) -> Sinks model, with each enabled source generating Kubernetes manifests that are applied together.

### Related modules

| Direction | Module | Contract |
|-----------|--------|----------|
| Upstream | Orchestrator | Provisioned service Kubernetes cluster (`kube_vip`) |

## Architecture

Telemetry follows a Sources → Bridge (Vector) → Sinks architecture:

### Sources
- **iDRAC**: Dell server BMC hardware telemetry
- **LDMS**: Lightweight Distributed Metric Service for HPC metrics
- **OME**: OpenManage Enterprise monitoring
- **UFM**: Unified Fabric Manager (InfiniBand)
- **PowerScale**: Dell PowerScale (Isilon) storage
- **VAST**: VAST Data storage

### External integrations

Smart Fabric Manager (SFM) and other external clients are not deployed by Telemetry. The `external_kafka` and `external_victoria` utility tags print the Kafka and VictoriaMetrics/VictoriaLogs connection details (endpoints, TLS certificates) that those clients need; see [Tags](#tags).

### Sinks
- **Kafka (Strimzi)**: Telemetry data streaming
- **VictoriaMetrics**: Time-series metrics storage and querying
- **VictoriaLogs**: Log aggregation and querying

### Deploy execution order

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

### Directory structure

```
telemetry/
├── ansible.cfg                    # Domain-root Ansible config
├── galaxy.yml                     # Galaxy collection metadata
├── meta/runtime.yml               # Ansible version compatibility
├── requirements.txt               # Python dependencies
├── requirements.yml               # Galaxy collection dependencies
├── domain-init.sh                 # Domain initialization script
├── input/                         # telemetry_config.yml, telemetry_storage_config.yml, telemetry_packages.yml
├── samples/                       # Reference files (not used at runtime)
├── vars/                          # cleanup.yml, deploy_sinks.yml, telemetry_common.yml
├── plugins/                       # modules, module_utils, callback
├── playbooks/
│   ├── telemetry.yml              # Entry point
│   ├── precheck/precheck.yml      # Kubernetes readiness checks
│   ├── validate/validation.yml    # L1 + L2 input validation
│   ├── credentials/get_telemetry_credentials.yml
│   ├── deploy/
│   │   ├── deploy.yml             # Deploy orchestrator
│   │   ├── telemetry_prereq.yml   # Prerequisites (config, flags, kube_vip)
│   │   ├── sinks/deploy_sinks.yml
│   │   └── sources/               # deploy_{idrac_telemetry,ldms,ome,ufm,powerscale,vast}.yml
│   ├── cleanup/
│   │   ├── cleanup.yml            # Cleanup orchestrator
│   │   └── sources/               # cleanup_{idrac,ldms,ome,ufm,powerscale,vast}.yml
│   └── utils/                     # external_kafka_connect.yml, external_victoria_connect.yml
├── roles/
│   ├── telemetry_setup/           # omnia.env loading, path derivation, directory creation
│   ├── common/                    # Config loading, flags, kustomization
│   ├── precheck/                  # Kubernetes readiness checks
│   ├── collect_telemetry_credentials/
│   ├── deploy_kafka/              # Kafka (Strimzi)
│   ├── deploy_victoria/           # VictoriaMetrics + VictoriaLogs
│   ├── deploy_idrac_telemetry/    # iDRAC
│   ├── deploy_ldms/               # LDMS
│   ├── deploy_ome/                # OME
│   ├── deploy_ufm/                # UFM
│   ├── deploy_powerscale/         # PowerScale
│   ├── deploy_vast/               # VAST
│   ├── cleanup/                   # Cleanup tasks
│   ├── external_kafka_connect/    # External Kafka connection details
│   └── external_victoria_connect/ # External VictoriaMetrics/VictoriaLogs connection details
├── containers/                    # LDMS container build files
├── rpm_build/                     # LDMS RPM build scripts (build_rpm.sh, ldms/)
├── docs/                          # architecture.md, contracts/
└── output/                        # Runtime output (status files)
```

### Roles

Roles are invoked as `omnia.telemetry.<role>`.

| Role | Description |
|------|-------------|
| [`cleanup`](roles/cleanup/README.md) | Cleanup telemetry resources (all components) |
| [`collect_telemetry_credentials`](roles/collect_telemetry_credentials/README.md) | Collects and manages credentials for telemetry sources (iDRAC, OME, etc.) |
| [`common`](roles/common/README.md) | Shared telemetry utilities — loads telemetry config, validates prerequisites, common variables |
| [`deploy_idrac_telemetry`](roles/deploy_idrac_telemetry/README.md) | Deploys iDRAC telemetry collection for Dell server hardware monitoring |
| [`deploy_kafka`](roles/deploy_kafka/README.md) | Deploys Apache Kafka (Strimzi operator) for telemetry data streaming |
| [`deploy_ldms`](roles/deploy_ldms/README.md) | Deploys LDMS (Lightweight Distributed Metric Service) for HPC telemetry collection |
| [`deploy_ome`](roles/deploy_ome/README.md) | Deploys OME (OpenManage Enterprise) telemetry collection for infrastructure monitoring |
| [`deploy_powerscale`](roles/deploy_powerscale/README.md) | Deploys PowerScale telemetry collection for Dell PowerScale storage monitoring |
| [`deploy_ufm`](roles/deploy_ufm/README.md) | Deploys UFM (Unified Fabric Manager) telemetry for InfiniBand fabric monitoring |
| [`deploy_vast`](roles/deploy_vast/README.md) | Deploys VAST Data telemetry collection for VAST storage monitoring |
| [`deploy_victoria`](roles/deploy_victoria/README.md) | Deploys VictoriaMetrics and VictoriaLogs for telemetry data storage and querying |
| [`external_kafka_connect`](roles/external_kafka_connect/README.md) | Fetches Kafka external connection details (mTLS and HTTP endpoints, TLS certs) from the Kubernetes cluster for external client integration (e.g., OME) |
| [`external_victoria_connect`](roles/external_victoria_connect/README.md) | Fetches VictoriaMetrics and VictoriaLogs external connection details (endpoints, TLS certs, syslog target) from the Kubernetes cluster for external client integration (e.g., SFM, PowerScale) |
| [`precheck`](roles/precheck/README.md) | Validates telemetry prerequisites — checks kube_vip connectivity, SSH access, and cluster readiness |
| [`telemetry_setup`](roles/telemetry_setup/README.md) | Initial setup for telemetry domain — creates directories, loads config, sets guard fact |

### Modules

Modules are invoked as `omnia.telemetry.<module>`.

| Module | Description |
|--------|-------------|
| `delete_idracips_from_mysqldb` | Delete iDRAC IPs from MySQL database in Kubernetes |
| `enable_telemetry_service` | Enable all telemetry reports on iDRAC nodes via Redfish |
| `fetch_idrac_ips` | Map iDRAC pod names to their associated BMC IPs |
| `idrac_telemetry_filter` | Filter iDRAC BMCs by firmware and license eligibility |
| `insert_idracips_mysqldb` | Insert iDRAC IPs into MySQL database in Kubernetes |
| `read_idracips_from_mysqldb` | Read iDRAC IPs from MySQL database in Kubernetes |
| `update_bmc_group_entry` | Add, delete, or verify BMC entries in a group CSV file |
| `validate_bmc_group_data` | Validate BMC group data CSV structure and content |
| `validate_input` | Validates telemetry input configuration files |
| `validate_system_environment` | Validate Omnia environment variables against system state |

### Plugins

| Plugin | Type | Description |
|--------|------|-------------|
| `omnia_default` | Callback | Custom Ansible stdout callback plugin for Omnia |

## Prerequisites

| Requirement | Minimum | Notes |
|-------------|---------|-------|
| OS | RHEL 10.0, 10.2; Rocky 10.x | Runs on the OIM; see the [support matrix](https://omnia.readthedocs.io/en/latest/Reference/SupportMatrix/index.html) |
| Python | 3.12+ | Shared Omnia virtual environment |
| Ansible | ansible-core 2.20+ | Pinned in `requirements.txt` |
| Kubernetes | Service Kubernetes cluster | Telemetry runs as Kubernetes workloads on the `kube_vip` host |

## Installation

Run the shared setup once from the repository root. It creates the Omnia virtual environment, runs every domain's `domain-init.sh` (dependencies, log directories, input staging) and installs the default catalog if none is active.

```bash
cd src/main
vi omnia.env                       # first run only; afterwards edit /etc/omnia/omnia.env
sudo ./omnia.sh --setup-venv
source /etc/profile.d/omnia-env.sh
```

To re-run only this module's initializer (for example after editing source inputs):

```bash
sudo ./omnia.sh --init telemetry
```

## Configuration

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OMNIA_DATA_PATH` | `/opt/omnia` | Root data directory for all Omnia data |
| `OMNIA_PROJECT_NAME` | `project_default` | Project name (maps to input/output subdirs) |
| `OMNIA_VENV_PATH` | `/opt/omnia/venv` | Shared Python virtual environment |
| `SYSTEM_ADMIN_NIC_IPV4` | _(required)_ | OIM host admin NIC IP |
| `SYSTEM_HOSTNAME` | `oim` | OIM short hostname |
| `SYSTEM_DOMAIN_NAME` | `omnia.cluster` | OIM domain name |
| `TELEMETRY_DATA_PATH` | `$OMNIA_DATA_PATH/telemetry` | Override telemetry data path |

### Input files

| File | Description |
|------|-------------|
| `input/telemetry_config.yml` | Main configuration — kube_vip, sources, sinks, bridges, credentials |
| `input/telemetry_storage_config.yml` | Storage backend configuration (PVC sizes, retention) |
| `input/telemetry_packages.yml` | Container registry, image versions, cluster_mount |

## Usage

Run this module through `omnia.sh`; it activates the virtual environment and runs `src/telemetry/playbooks/telemetry.yml`. All `./omnia.sh` commands in this document are run from `src/main` on the OIM. See [Tags](#tags) for the supported tags and combinations.

```bash
cd src/main
./omnia.sh --run telemetry --tags <tag> [-e <extra_var>=<value>]
```

To run the playbook directly, activate `$OMNIA_VENV_PATH/bin/activate`, source `/etc/profile.d/omnia-env.sh`, and run from the module root so its `ansible.cfg` is loaded:

```bash
cd src/telemetry
ansible-playbook playbooks/telemetry.yml --tags <tag>
```

Typical flow:

```bash
cd src/main
./omnia.sh --run telemetry --tags validate    # validate input files
./omnia.sh --run telemetry --tags precheck    # Kubernetes and enabled Slurm prerequisites
./omnia.sh --run telemetry --tags deploy      # sinks, sources, kustomize apply
```

Running without a tag runs setup, validate, precheck, and deploy; `cleanup` never runs by default.

## Tags

### Lifecycle tags (mutually exclusive: pick one)

| Tag | Default? | Description |
|-----|----------|-------------|
| _(none)_ | Yes | Default flow: setup + validate + precheck + deploy |
| `precheck` | No | Run K8s and enabled Slurm prerequisite checks without deploying |
| `validate` / `validation` / `prepare` | Yes | L1 schema + L2 logic validation of all input files, and credential collection (the three tags are aliases) |
| `credentials` | No | Collect telemetry credentials only (opt-in) |
| `deploy` / `execute` | Yes | Precheck, then deploy sinks + sources + kustomize apply |
| `deploy_sinks` | No | Deploy only selected sink infrastructure: Kafka, VictoriaMetrics, and/or VictoriaLogs |
| `cleanup` | No | Remove telemetry runtime resources and stored credentials; delete source volumes, preserve sink volumes by default |
| `external_kafka` | No | Print external Kafka mTLS/HTTP Bridge endpoints and certificates (utility, opt-in) |
| `external_victoria` | No | Print external VictoriaMetrics/VictoriaLogs endpoints, certificates, and syslog target (utility, opt-in) |

### Granular cleanup tags (opt-in: requires `--tags`)

| Tag | Scope |
|-----|-------|
| `cleanup_sinks` | Selective sink cleanup with dependency checking (`-e sinks=kafka,victoria_metrics,victoria_logs` or short-form `-e kafka -e victoria_logs`) |
| `cleanup_idrac` | iDRAC telemetry (receiver, pumps, DB) |
| `cleanup_ldms` | LDMS + Vector-LDMS bridge |
| `cleanup_ome` | OME + Vector-OME bridge |
| `cleanup_powerscale` | PowerScale telemetry |
| `cleanup_ufm` | UFM InfiniBand telemetry |
| `cleanup_vast` | VAST storage telemetry |

**Tag safety**: `cleanup` uses Ansible's `never` tag;
it never executes unless explicitly requested with `--tags`. `precheck` runs
automatically for the default, `deploy`, and `execute` flows, and can also be
requested alone for a check-only run.

Deploy one or more sinks independently of telemetry sources:

```bash
./omnia.sh --run telemetry --tags deploy_sinks -e kafka
./omnia.sh --run telemetry --tags deploy_sinks -e kafka,victoria_metrics
./omnia.sh --run telemetry --tags deploy_sinks -e kafka -e victoria_logs
```

When invoking Ansible directly from `src/telemetry`, use the `sinks` variable, for example:
`ansible-playbook playbooks/telemetry.yml --tags deploy_sinks -e sinks=kafka,victoria_logs`.

## Inputs and Outputs

### Inputs

See [Configuration](#configuration) for the three input files (`telemetry_config.yml`, `telemetry_storage_config.yml`, `telemetry_packages.yml`) and the [input contract](docs/contracts/input-contract.md).

### Outputs

Status files and generated output are written to `$OMNIA_DATA_PATH/telemetry/output/<project>/`. See the [output contract](docs/contracts/output-contract.md).

## Runtime Paths

All paths are derived from `OMNIA_DATA_PATH` and `OMNIA_PROJECT_NAME`:

| Path | Purpose |
|------|---------|
| `/var/log/omnia/telemetry/` | Ansible playbook execution logs |
| `$OMNIA_DATA_PATH/telemetry/input/$PROJECT/` | Runtime input configuration |
| `$OMNIA_DATA_PATH/telemetry/output/$PROJECT/` | Status files and output |
| `$OMNIA_DATA_PATH/telemetry/log/$PROJECT/` | Domain runtime logs |

## Cleanup

Full `cleanup` deletes `telemetry_credentials.yml` and its vault key by default.
Use `-e cleanup_credentials=false` to preserve credentials during cleanup, which
is useful when redeploying immediately after cleanup. Use `-e cleanup_logs=false`
to preserve telemetry log directories and artifacts during cleanup.

When `Delete_sinks_volume=true` is combined with either `cleanup_credentials=false`
or `cleanup_logs=false`, a warning is displayed and execution pauses for 30 seconds.
In cleanup with volume mode, credentials and logs are always deleted regardless of
these flags.

A granular source cleanup blanks only that source's stored credential fields and
preserves credentials for components that remain deployed. Use
`-e cleanup_credentials=false` with granular tags to skip field blanking as well:

```bash
cd src/main
sudo ./omnia.sh --run telemetry --tags cleanup
sudo ./omnia.sh --cleanup --all

# Preserve credentials for redeployment
sudo ./omnia.sh --run telemetry --tags cleanup -e cleanup_credentials=false

# Preserve both credentials and logs
sudo ./omnia.sh --run telemetry --tags cleanup -e cleanup_credentials=false -e cleanup_logs=false

# Granular cleanup preserving credentials
sudo ./omnia.sh --run telemetry --tags cleanup_idrac -e cleanup_credentials=false
```

`src/telemetry/domain-init.sh --cleanup` is non-interactive and removes only
initializer-owned staged input and domain log paths; it does not remove
Kubernetes resources or persistent volumes. Both global cleanup modes prompt
for `yes`; trusted automation can add `--skip-approval`. Source volumes are
deleted by default; sink volumes are preserved unless the telemetry cleanup is
run with `-e delete_sinks_volume=true`.

## Troubleshooting

- Ansible log: `/var/log/omnia/telemetry/telemetry.log` (top-level playbook execution).
- Runtime logs: `$OMNIA_DATA_PATH/telemetry/log/<project>/`.
- Run `--tags precheck` to check Kubernetes readiness without deploying.
- Re-run `sudo ./omnia.sh --init telemetry` if inputs or dependencies were not staged.

## Security

- Telemetry credentials are stored in `telemetry_credentials.yml` with a vault key; full `cleanup` deletes both by default (`-e cleanup_credentials=false` keeps them).
- A granular source cleanup blanks only that source's stored credential fields and preserves credentials for components that remain deployed.

## Documentation

- [Read the Docs: Telemetry guides](https://omnia.readthedocs.io/en/latest/HowTo/Telemetry/index.html)
- [Architecture](docs/architecture.md)
- [Input contract](docs/contracts/input-contract.md)
- [Output contract](docs/contracts/output-contract.md)
- [LDMS container build](containers/README.md)
- [Omnia on GitHub](https://github.com/dell/omnia)
- [Report an issue](https://github.com/dell/omnia/issues)

## License

Apache-2.0

Dell Technologies (<omnia-support@dell.com>)
