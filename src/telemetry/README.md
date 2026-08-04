# Omnia Telemetry

Dell Omnia Telemetry deploys and manages a comprehensive telemetry stack for
HPC and AI clusters. It supports multiple telemetry sources with tag-based
deployment, cleanup, upgrade, and rollback operations.

## Prerequisites

| Requirement | Version |
|-------------|---------|
| Ansible     | >= 2.20 |
| Python      | >= 3.12 |
| OS          | RHEL/Rocky Linux 10.x |
| Kubernetes  | Required for sink deployments (VictoriaMetrics, Kafka) |

## Quick Start

```bash
# 1. Initialize the domain (copies input files, creates log dirs)
./domain-init.sh

# 2. Run telemetry deployment
ansible-playbook telemetry.yml --tags deploy

# 3. Run with specific tags
ansible-playbook telemetry.yml --tags precheck
ansible-playbook telemetry.yml --tags validation
ansible-playbook telemetry.yml --tags cleanup
```

## Input Files

| File | Description |
|------|-------------|
| `input/telemetry_config.yml` | Main telemetry configuration — sources, sinks, credentials |
| `input/telemetry_storage_config.yml` | Storage backend configuration for telemetry data |
| `input/telemetry_packages.yml` | Package versions and container image references |

## Tags

| Tag | Description |
|-----|-------------|
| `precheck` | Validate telemetry prerequisites (kube_vip, SSH) |
| `validation` | L1 + L2 input validation for all telemetry config files |
| `deploy` | Deploy all enabled telemetry sources |
| `cleanup` | Remove all telemetry components |
| `upgrade` | Upgrade telemetry components |
| `rollback` | Rollback telemetry components |
| `cleanup_kafka` | Clean up Kafka only |
| `cleanup_victoria_metrics` | Clean up VictoriaMetrics only |
| `cleanup_victoria_logs` | Clean up VictoriaLogs only |
| `cleanup_ldms` | Clean up LDMS only |
| `cleanup_ome` | Clean up OME telemetry only |
| `cleanup_dcgm` | Clean up DCGM only |
| `cleanup_ufm` | Clean up UFM only |
| `cleanup_vast` | Clean up VAST only |
| `cleanup_sfm` | Clean up SFM only |
| `cleanup_skyway` | Clean up Skyway only |
| `cleanup_powervault` | Clean up PowerVault only |

## Telemetry Sources

| Source | Description |
|--------|-------------|
| VictoriaMetrics | Time-series metrics storage and querying |
| VictoriaLogs | Log aggregation and querying |
| Kafka (Strimzi) | Telemetry data streaming |
| LDMS | Lightweight Distributed Metric Service for HPC |
| iDRAC | Dell server hardware telemetry |
| DCGM | NVIDIA GPU telemetry |
| OME | OpenManage Enterprise infrastructure monitoring |
| UFM | Unified Fabric Manager (InfiniBand) |
| PowerScale | Dell PowerScale storage telemetry |
| VAST | VAST Data storage telemetry |
| SFM | Smart Fabric Manager network telemetry |
| Skyway | Skyway telemetry |
| PowerVault | Dell PowerVault storage telemetry |

## Collection Structure

```
telemetry/
  galaxy.yml                  # Galaxy collection metadata
  meta/runtime.yml            # Ansible version compatibility
  requirements.txt            # Python dependencies
  requirements.yml            # Galaxy collection dependencies
  domain-init.sh              # Domain initialization script
  ansible.cfg                 # Ansible configuration
  telemetry.yml               # Entry point playbook
  README.md                   # This file
  plugins/
    modules/                  # Custom Ansible modules
    module_utils/             # Module utility libraries
    callback/                 # Callback plugins
  playbooks/                  # Sub-playbooks for each operation
  roles/                      # Ansible roles
  input/                      # Input configuration files
  output/                     # Runtime output (status files)
  containers/                 # Container build files (LDMS)
  docs/                       # Domain documentation
```

## Runtime Paths

| Path | Purpose |
|------|---------|
| `/var/log/omnia/telemetry/` | Ansible playbook execution logs |
| `<OMNIA_DATA_PATH>/telemetry/input/` | Runtime input configuration |
| `<OMNIA_DATA_PATH>/telemetry/output/` | Status files and output |
| `<OMNIA_DATA_PATH>/telemetry/log/` | Domain runtime logs (validation, etc.) |

## License

Apache-2.0

## Author Information

Dell Technologies (<omnia-support@dell.com>)
