# Omnia Discovery

Discovery is an Ansible Galaxy collection that discovers bare-metal nodes via Dell OpenManage Enterprise (OME) and produces mapping and report artifacts for cluster provisioning. It does not provision or register nodes itself—those responsibilities belong to the Orchestrator domain.

## Overview

Discovery automates hardware inventory discovery for HPC and AI clusters by:

- Connecting to Dell OpenManage Enterprise (OME) to query BMC endpoints
- Collecting server inventory including hardware specifications and network information
- Generating PXE mapping files that map physical nodes to functional groups and network configurations
- Creating discovery reports for operator review and validation
- Assigning functional group names based on OME static groups or default patterns

## What Discovery Does

Discovery is a **read-only** domain that:
- Discovers BMC endpoints through OME API
- Generates `pxe_mapping_file.csv` for downstream consumption by Orchestrator
- Produces discovery reports with inventory details
- Validates OME connectivity and data path readiness

Discovery does **not**:
- Provision nodes
- Register nodes in OpenCHAMI
- Configure network settings
- Install operating systems

## Key Components

### Roles

| Role | Description |
|------|-------------|
| `discovery_setup` | Setup project dirs, config loading, tag validation |
| `precheck_environment` | Validate the data path and OME HTTPS endpoint readiness |
| `validate_discovery_input` | L1 schema + L2 logic validation |
| `discovery_credentials` | Credential prompting, encryption, vault |
| `discovery_common` | Shared task library (vault and OME endpoint helpers) |
| `ome_discovery` | OME-specific discovery, inventory, PXE mapping |
| `discovery_cleanup` | Project output, runtime-log, and credential cleanup |

### Modules

| Module | Description |
|--------|-------------|
| `validate_discovery_config` | Validate discovery configuration (L1+L2) |
| `validate_system_environment` | Validate selected OIM environment values and paths |
| `validate_credentials` | Validate credential input against rules |
| `ome_server_inventory` | Collect server inventory from OME |
| `generate_pxe_mapping` | Generate PXE mapping CSV from inventory |
| `generate_discovery_report` | Generate BMC discovery report |

## Prerequisites

| Requirement | Minimum |
|-------------|---------|
| Ansible | >= 2.14 |
| Python | >= 3.9 |
| OME | Dell OpenManage Enterprise with HTTPS access |
| Collection | `community.general` >= 5.0.0 |

## Quick Start

```bash
# Validate the Discovery input only; do not load credentials
ansible-playbook playbooks/discovery.yml --tags validate

# Load stored credentials or collect any missing OME username/password
ansible-playbook playbooks/discovery.yml --tags credentials

# Validate input, collect missing credentials, and run OME discovery
ansible-playbook playbooks/discovery.yml --tags execute
```

## Functional Groups

Discovery assigns `FUNCTIONAL_GROUP_NAME` based on OME static groups:

| Scenario | Result |
|----------|--------|
| Valid OME static group | Uses OME group name |
| Invalid OME static group | Default: `slurm_node_rhel_10_0_aarch64` |
| No OME static group | Default: `slurm_node_rhel_10_0_aarch64` |

**Valid pattern:** `<prefix>_rhel_<major>_<minor>_(x86_64|aarch64)`

Examples:
- ✅ `slurm_node_rhel_10_0_x86_64`
- ✅ `login_node_rhel_10_2_aarch64`
- ❌ `login_node` (missing `_rhel_<version>_<arch>`)

## Cleanup

```bash
# Full cleanup (removes output, logs, and credentials)
ansible-playbook playbooks/discovery.yml --tags cleanup

# Preserve credentials
ansible-playbook playbooks/discovery.yml --tags cleanup \
  -e cleanup_credentials=false

# Preserve logs
ansible-playbook playbooks/discovery.yml --tags cleanup \
  -e cleanup_logs=false
```

## Documentation

- [Discovery Documentation](https://omnia.readthedocs.io/en/latest/HowTo/discovery/index.html)
- [Architecture](docs/architecture.md)
- [Omnia GitHub](https://github.com/dell/omnia)
- [Issues](https://github.com/dell/omnia/issues)

## License

Apache-2.0
