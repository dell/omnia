# Omnia Utils Collection

The `omnia.utils` collection provides utility roles and modules for Omnia HPC cluster management, including OS installation, log collection, PXE boot management, and Slurm configuration utilities.

## Features

- **OS Installation**: Bare-metal OS provisioning via ISO creation and delivery
- **Log Collection**: Centralized log gathering from cluster nodes for troubleshooting
- **Slurm Utilities**: Configuration backup, rollback, and cleanup operations
- **ARM Support**: ARM64/aarch64 architecture-specific provisioning
- **Credential Validation**: Custom modules for secure credential handling
- **Telemetry Integration**: Telemetry status monitoring and configuration

## Requirements

- Ansible 2.19+
- Python 3.12+
- RHEL 10.x or compatible
- Network access to target nodes
- Sufficient disk space for ISO and log operations

## Installation

Install from Ansible Galaxy:

```bash
ansible-galaxy collection install omnia.utils
```

Or install from source:

```bash
git clone https://github.com/dell/omnia.git
cd omnia/src/utils
ansible-galaxy collection install . --force
```

## Quick Start

### 1. Initialize Domain Environment

```bash
./domain-init.sh
./copy-input.sh
```

### 2. Run Setup Role

```yaml
- hosts: localhost
  connection: local
  gather_facts: true
  roles:
    - role: omnia.utils.utils_setup
      vars:
        validate_prerequisites: true
        validate_config_files: true
```

### 3. Execute Utility Playbooks

```bash
ansible-playbook playbooks/collect.yml
ansible-playbook playbooks/install_os.yml
ansible-playbook playbooks/slurm_config_util.yml
```

## Roles

| Role | Purpose |
|------|---------|
| `utils_setup` | Environment validation and initialization |
| `iso_creation` | Create custom OS installation ISOs |
| `iso_delivery` | Deliver ISOs via iDRAC virtual media |
| `pxe_buildstream_manager` | Manage PXE boot with BuildStream |
| `fetch_iso` | Download and validate OS ISOs |
| `log_collector` | Collect logs from cluster nodes |
| `create_container_group` | Create container groups for infrastructure |
| `fetch_arm_params` | Fetch ARM-specific parameters |
| `validate_arm_config` | Validate ARM configuration |
| `slurm_cleanup` | Clean up Slurm configuration |
| `slurm_config_backup` | Backup Slurm configuration |
| `slurm_config_rollback` | Rollback Slurm configuration |

## Modules

| Module | Purpose |
|--------|---------|
| `fetch_credential_rule` | Fetch credential validation rules |
| `fetch_telemetry_status` | Get enabled telemetry sources |
| `validate_credentials` | Validate credential inputs |

## Configuration

Configuration files are located in `/opt/omnia/input/project_default/`:

- `iso_config.yml` — ISO creation and delivery settings
- `telemetry_config.yml` — Telemetry source configuration
- `omnia_config.yml` — Main Omnia configuration
- `arm_config.yml` — ARM-specific settings (optional)
- `bmc_inventory.csv` — BMC inventory for iDRAC operations

## Playbooks

### collect.yml
Collects logs from all cluster nodes for troubleshooting.

```bash
ansible-playbook playbooks/collect.yml
```

### install_os.yml
Performs bare-metal OS installation on x86_64 nodes.

```bash
ansible-playbook playbooks/install_os.yml
```

### install_os_arm_node.yml
Performs OS installation on ARM64/aarch64 nodes.

```bash
ansible-playbook playbooks/install_os_arm_node.yml
```

### slurm_config_util.yml
Manages Slurm configuration backup and rollback.

```bash
ansible-playbook playbooks/slurm_config_util.yml
```

## Domain Integration

This collection integrates with the Omnia orchestration framework via:

- `domain-init.sh` — Initialize domain directories and permissions
- `copy-input.sh` — Stage input files for playbook execution
- `ansible.cfg` — Domain-specific Ansible configuration
- `meta/runtime.yml` — Ansible version requirements and action groups

## Documentation

- [Design Documentation](docs/design/) — Architecture and design decisions
- [Code Style Guide](docs/code-style/) — Python and Ansible coding standards
- [Role Documentation](roles/) — Individual role READMEs

## Support

For issues, questions, or contributions:

- GitHub Issues: https://github.com/dell/omnia/issues
- Documentation: https://dell.github.io/omnia

## License

Apache License 2.0 — See LICENSE file for details

## Author

Dell Technologies Omnia Team
