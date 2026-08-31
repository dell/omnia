# Telemetry — Input Contract

## Overview

The telemetry domain reads its configuration from three input files located in
the `input/` directory. These files are copied to the runtime data path by
`domain-init.sh` during setup.

## Cleanup extra variables

Cleanup accepts either spelling below as an Ansible extra variable. The value
must be a boolean (or `yes`/`no`, `1`/`0`).

| Variable | Default | Description |
|----------|---------|-------------|
| `Delete_volume` / `delete_volume` | `false` | When `true`, delete component PVCs and Kafka identity metadata. When `false`, preserve persistent data and the metadata required for safe redeployment. |

## Input Files

### telemetry_config.yml

Primary configuration file for the telemetry stack.

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| `cluster_inventory` | string | Yes | Path to the unified Ansible inventory file containing kube_vip_group |
| `telemetry_sources.<source>.metrics_enabled` | bool | No | Enable/disable metrics for a telemetry source |
| `telemetry_sources.<source>.logs_enabled` | bool | No | Enable/disable logs for a telemetry source |
| `telemetry_sources.<source>.collection_targets` | list | No | Sink targets per source (e.g., `[kafka, victoria_metrics]`) |
| `telemetry_bridges.vector_ome.metrics_enabled` | bool | No | Enable Vector-OME metrics bridge |
| `telemetry_bridges.vector_ome.logs_enabled` | bool | No | Enable Vector-OME logs bridge |
| `telemetry_bridges.vector_ldms.metrics_enabled` | bool | No | Enable Vector-LDMS metrics bridge |
| `powerscale_configurations` | dict | No | PowerScale-specific configuration (required when PowerScale enabled) |

### telemetry_storage_config.yml

Storage backend configuration for telemetry data retention and persistence.

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| `kafka_storage` | dict | Conditional | Kafka storage (required when any source targets Kafka) |
| `victoria_cluster_storage` | dict | Conditional | VM cluster storage (required when any source targets victoria_metrics) |
| `victoria_logs_cluster_storage` | dict | Conditional | VL cluster storage (required when any source targets victoria_logs) |
| `vector_storage` | dict | Conditional | Vector bridge storage (required when any bridge is enabled) |

### telemetry_packages.yml

Central package manifest for all telemetry stack dependencies.

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| `install_mode` | string | No | `"offline"` (default) or `"online"` |
| `repo_url` | string | Conditional | Pulp base URL (required for offline mode) |
| `cluster_mount` | string | Yes | NFS mount point on K8s cluster nodes |
| `container_registry` | string | No | Registry override for air-gapped clusters |
| `images.<subsystem>.<key>` | string | No | Container image references grouped by subsystem |
| `helm_charts.<chart>.package` | string | No | Pulp directory name for Helm chart tarball |
| `helm_charts.<chart>.filename` | string | No | Archive filename |
| `helm_charts.<chart>.online_url` | string | No | Upstream download URL |
| `git_repos.<repo>.package` | string | No | Pulp directory name for git archive |
| `git_repos.<repo>.version` | string | No | Tag or branch for online clone |
| `pip_modules.<module>.version` | string | No | Pip package version |

## Upstream Contracts

The telemetry domain may read the following upstream output files:

| Source Domain | File | Purpose |
|---------------|------|---------|
| orchestrator | `orchestrator_inventory.yml` | Kubernetes cluster inventory (kube_vip, slurm nodes) |

## File Location

- **Source (repository)**: `src/telemetry/input/`
- **Runtime (copied by domain-init.sh)**: `<OMNIA_DATA_PATH>/telemetry/input/<PROJECT_NAME>/`
- **Default runtime path**: `/opt/omnia/telemetry/input/project_default/`
- **Cluster Inventory**: Specified in `telemetry_config.yml` via `cluster_inventory` parameter

## Validation

All input files are validated by the `validate_input` module using:
- **L1 (Schema)**: JSON Schema validation against `plugins/module_utils/input_validation/schema/*.json`
- **L2 (Logic)**: Cross-field logical validation via `plugins/module_utils/input_validation/validators/telemetry_validation.py`
