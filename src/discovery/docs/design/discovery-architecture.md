# Discovery Domain Architecture

## Overview

The Discovery domain (`omnia.discovery`) is responsible for discovering bare-metal
servers via Dell OpenManage Enterprise (OME) and producing mapping artifacts for
downstream domains. It does **not** provision or register nodes — it produces
mapping/report artifacts for an operator-mediated handoff to Orchestrator.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Discovery Domain                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                  │
│  │   Inputs     │    │   Playbooks  │    │   Outputs    │                  │
│  ├──────────────┤    ├──────────────┤    ├──────────────┤                  │
│  │ discovery_   │───▶│ discovery.yml│───▶│ pxe_mapping  │                  │
│  │ config.yml   │    │              │    │ _file.csv    │                  │
│  │              │    │ Tags:        │    │              │                  │
│  │ network_     │    │ - precheck   │    │ discovery_   │                  │
│  │ spec.yml     │    │ - validate   │    │ report.csv   │                  │
│  │              │    │ - credentials│    │              │                  │
│  │ discovery_   │    │ - prepare    │    │ discovery_   │                  │
│  │ credentials  │    │ - execute    │    │ status.yml   │                  │
│  │ .yml         │    │ - cleanup    │    │              │                  │
│  └──────────────┘    └──────────────┘    └──────────────┘                  │
│         │                   │                   │                           │
│         │                   ▼                   │                           │
│         │         ┌──────────────────┐          │                           │
│         │         │   OME API        │          │                           │
│         └────────▶│   Integration    │◀─────────┘                           │
│                   │                  │                                      │
│                   │ - Server list    │                                      │
│                   │ - NIC inventory  │                                      │
│                   │ - Static groups  │                                      │
│                   └──────────────────┘                                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │   Operator Handoff            │
                    │   (Manual Review & Edit)      │
                    └───────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │   Orchestrator Domain         │
                    │   (Consumes pxe_mapping.csv)  │
                    └───────────────────────────────┘
```

## Component Interactions

### 1. Input Processing

| Component | Description |
|-----------|-------------|
| `discovery_config.yml` | OME IP, project name, hostname settings |
| `network_spec.yml` | Network topology (admin, BMC, IB subnets) |
| `discovery_credentials.yml` | OME username/password (Ansible Vault encrypted) |

### 2. Roles

| Role | Purpose |
|------|---------|
| `discovery_setup` | Initialize environment, validate tags, set paths |
| `discovery_credentials` | Collect and encrypt OME credentials |
| `precheck_environment` | Validate system environment (hostname, IP, env vars) |
| `discovery_validate` | Validate input configuration against schemas |
| `ome_discovery` | Query OME API, generate PXE mapping and report |
| `discovery_cleanup` | Remove outputs, logs, and/or credentials |
| `discovery_common` | Shared utilities (encrypt/decrypt) |

### 3. Ansible Modules

| Module | Purpose |
|--------|---------|
| `ome_server_inventory` | Query OME for server list and NIC inventory |
| `generate_pxe_mapping` | Generate PXE mapping CSV from server data |
| `generate_discovery_report` | Generate discovery report CSV with NIC status |
| `validate_discovery_config` | Validate configuration against JSON schemas |
| `validate_credentials` | Validate credential format |
| `validate_system_environment` | Validate system environment variables |

## Data Flow

```
1. PRECHECK
   └── Validate: OMNIA_DATA_PATH, hostname, admin IP, OME connectivity

2. VALIDATE
   └── Validate: discovery_config.yml, network_spec.yml against schemas

3. CREDENTIALS
   └── Collect OME credentials → Encrypt with Ansible Vault

4. EXECUTE
   ├── Query OME API for server inventory
   ├── Extract NIC information (BMC, Ethernet, InfiniBand)
   ├── Map servers to functional groups based on OME static groups
   ├── Calculate ADMIN_IP and IB_IPV4 from network_spec
   ├── Generate hostnames (nid001, nid002, ...)
   ├── Write bmc_pxe_mapping_file_<timestamp>.csv
   ├── Write bmc_discovery_report_<timestamp>.csv
   └── Create symlink: bmc_pxe_mapping_file.csv → latest

5. CLEANUP
   └── Remove outputs, logs, and/or credentials (configurable)
```

## Functional Group Handling

Discovery determines `FUNCTIONAL_GROUP_NAME` for each server based on OME static groups:

### Valid Functional Group Pattern

All functional groups **MUST** follow this pattern:
```
<any_prefix>_rhel_<major>_<minor>_(x86_64|aarch64)
```

**Valid examples:**
- `slurm_node_rhel_10_0_x86_64`
- `slurm_control_node_rhel_10_2_aarch64`
- `login_node_rhel_10_0_x86_64`
- `my_custom_group_rhel_9_4_aarch64`

**Invalid examples:**
- `login_node` (missing `_rhel_<version>_<arch>`)
- `slurm_node_x86_64` (missing `_rhel_<version>_`)
- `slurm_node_rocky_10_0_x86_64` (only `rhel` supported)

### Resolution Logic

| Scenario | Result |
|----------|--------|
| Valid OME static group | Uses OME group name as-is |
| Invalid OME static group | Warning logged, falls back to default |
| No OME static group | Falls back to default |

**Default functional group:** `slurm_node_rhel_10_0_aarch64`

> **Note:** Discovery does NOT read from catalog. The default is a fixed value
> with no external dependencies.

## Output Artifacts

### PXE Mapping CSV (`bmc_pxe_mapping_file.csv`)

| Column | Description |
|--------|-------------|
| `FUNCTIONAL_GROUP_NAME` | From OME static group (if valid) or default `slurm_node_rhel_10_0_aarch64` |
| `SERVICE_TAG` | Dell service tag |
| `HOSTNAME` | Generated hostname (nidXXX) |
| `ADMIN_MAC` | First active non-iDRAC NIC MAC |
| `ADMIN_IP` | Calculated from admin subnet + BMC IP |
| `BMC_IP` | iDRAC IP address |
| `IB_IPV4` | Calculated InfiniBand IPv4 (optional) |
| `IB_IPV6` | InfiniBand IPv6 address (user-provided, empty by default) |
| `IB_NIC_NAME` | First active InfiniBand NIC name (optional) |
| `GROUP_NAME` | Slurm partition name (optional) |
| `PARENT_SERVICE_TAG` | Chassis service tag for blades (optional) |

### Discovery Report CSV (`bmc_discovery_report.csv`)

Contains NIC link status for each server:
- BMC NIC status
- Ethernet NIC status (all ports)
- InfiniBand NIC status (all ports)

## Upstream/Downstream Contracts

### Upstream Dependencies

| Dependency | Description |
|------------|-------------|
| `omnia.sh --setup-venv` | Environment setup (OMNIA_DATA_PATH, etc.) |
| OME Server | OpenManage Enterprise with discovered servers |

### Downstream Consumers

| Consumer | Artifact | Usage |
|----------|----------|-------|
| Orchestrator | `pxe_mapping_file.csv` | Node provisioning and configuration |
| BuildStream | `pxe_mapping_file.csv` | Image deployment pipeline |

## Security Considerations

1. **Credential Protection**: OME credentials are stored in Ansible Vault encrypted files
2. **No Hardcoded Secrets**: All credentials loaded from encrypted files at runtime
3. **Credential Cleanup**: `--tags cleanup_credentials` removes credential files
4. **Audit Logging**: All operations logged to `$OMNIA_DATA_PATH/discovery/log/`

## Configuration Reference

See `input/discovery_config.yml` for all configuration options with descriptions.
