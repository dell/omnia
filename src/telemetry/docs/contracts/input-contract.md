# Telemetry — Input Contract

## Overview

The telemetry domain reads its configuration from three input files located in
the `input/` directory. These files are copied to the runtime data path by
`domain-init.sh` during setup.

## Input Files

### telemetry_config.yml

Primary configuration file for the telemetry stack.

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| `kube_vip` | string | Yes | Kubernetes control plane VIP address |
| `bmc_group_data_path` | string | No | Path to BMC inventory CSV for iDRAC telemetry |
| `collection_targets` | string | Yes | Comma-separated sink targets (e.g., `victoria_metrics,victoria_logs`) |
| `telemetry_sources.<source>.metrics_enabled` | bool | No | Enable/disable metrics for a telemetry source |
| `telemetry_sources.<source>.logs_enabled` | bool | No | Enable/disable logs for a telemetry source |
| `powerscale_configurations` | dict | No | PowerScale-specific configuration (required when PowerScale enabled) |

### telemetry_storage_config.yml

Storage backend configuration for telemetry data retention and persistence.

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| `storage_class` | string | No | Kubernetes StorageClass for persistent volumes |
| `retention_period` | string | No | Data retention period |

### telemetry_packages.yml

Package and container image version references.

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| `telemetry_packages.<component>.version` | string | Yes | Version of the telemetry component |
| `telemetry_packages.<component>.image` | string | No | Container image reference |

## Upstream Contracts

The telemetry domain may read the following upstream output files:

| Source Domain | File | Purpose |
|---------------|------|---------|
| orchestrator | `orchestrator_status.yml` | Kubernetes cluster readiness confirmation |

## File Location

- **Source**: `src/telemetry/input/`
- **Runtime**: `<OMNIA_DATA_PATH>/telemetry/input/<project>/`

## Validation

All input files are validated by the `validate_input` module using:
- **L1 (Schema)**: JSON Schema validation against `plugins/module_utils/input_validation/schema/*.json`
- **L2 (Logic)**: Cross-field logical validation via `plugins/module_utils/input_validation/validation_flows/`
