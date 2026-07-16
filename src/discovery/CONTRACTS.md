# Discovery Domain – Input/Output Contracts

## Overview

The Discovery domain is responsible for discovering hardware (servers) via
management platforms (e.g., Dell OME) and producing a PXE mapping file that
serves as the primary data contract between Discovery and the Orchestrator.

## Inputs

All inputs are read from:

```
/opt/omnia/input/<project_name>/discovery/
```

### discovery_config.yml

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `enable_bmc_discovery` | bool | Yes | Enable BMC discovery via OME |
| `ome_ip` | string | Yes (when OME) | IP address of Dell OME instance |

### network_spec.yml

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `Networks[].admin_network.subnet` | string | Yes | Admin network subnet for IP derivation |
| `Networks[].ib_network.subnet` | string | No | InfiniBand subnet for IB IP derivation |

### Credentials (from shared credential utility)

| Parameter | Source | Description |
|-----------|--------|-------------|
| `ome_username` | omnia_config_credentials.yml | OME login username |
| `ome_password` | omnia_config_credentials.yml | OME login password (vault-encrypted) |

## Outputs

All outputs are written to:

```
/opt/omnia/output/<project_name>/discovery/
```

### bmc_pxe_mapping_file.csv (Primary Contract)

This is the **primary output** consumed by the Orchestrator domain.

| Column | Type | Description |
|--------|------|-------------|
| `FUNCTIONAL_GROUP_NAME` | string | Node functional group (e.g., `slurm_node_aarch64`) |
| `GROUP_NAME` | string | Scalable Unit / group identifier |
| `SERVICE_TAG` | string | Dell server service tag |
| `PARENT_SERVICE_TAG` | string | Parent node service tag (for slurm child nodes) |
| `HOSTNAME` | string | Generated hostname (e.g., `nid00001`) |
| `ADMIN_MAC` | string | Admin NIC MAC address |
| `ADMIN_IP` | string | Admin IP (derived from admin_subnet + BMC IP) |
| `BMC_MAC` | string | BMC/iDRAC MAC address |
| `BMC_IP` | string | BMC/iDRAC IP address |
| `IB_NIC_NAME` | string | InfiniBand NIC FQDD (if present) |
| `IB_IP` | string | InfiniBand IP (derived from ib_subnet + BMC IP) |

### bmc_discovery_report.csv (Informational)

NIC link status report for operator review. Not consumed programmatically.

## Data Flow

```
Discovery Input                    Discovery Output                    Orchestrator Input
─────────────────                  ─────────────────                   ──────────────────
discovery_config.yml ─┐
                      ├─► OME ─► bmc_pxe_mapping_file.csv ──copy──► pxe_mapping_file.csv
network_spec.yml ─────┘            bmc_discovery_report.csv
```

The mapping file must be **manually reviewed and copied** to the orchestrator
input directory before running orchestrator.yml. This deliberate handoff point
ensures operators can review/edit node assignments before provisioning.
