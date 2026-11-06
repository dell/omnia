# Utils

Utils is an Ansible Galaxy collection that provides OIM utilities for cluster operations, including log collection, OS installation through iDRAC virtual media, and configuration backup/restore for Slurm and Omnia domains. These utilities run on-demand and are independent of the main deployment workflow.

## Overview

Utils provides operational utilities for HPC and AI clusters by:

- Collecting cluster logs from Kubernetes, Slurm, and login nodes
- Installing operating systems through iDRAC virtual media (x86_64 and aarch64)
- Backing up OIM log directories from all Omnia domains
- Managing Slurm controller configuration backup, cleanup, and rollback
- Providing targeted cleanup operations for utility artifacts
- Writing project-scoped `utils_status.yml` status files

## Key Utilities

### Cluster Log Collection
Collects logs from functional-group nodes over SSH:
- Builds dynamic inventory from `collect_pxe.yml`
- Collects predefined logs from Kubernetes, Slurm, and login nodes
- Creates timestamped archives with metadata
- Records unreachable nodes and missing sources as warnings

### OS Installation
Installs operating systems through Dell iDRAC virtual media:
- Creates or reuses NFS-hosted custom ISO
- Renders Kickstart configuration files
- Mounts ISO through iDRAC virtual media
- Supports both x86_64 and aarch64 targets
- Optionally verifies SSH connectivity after installation

### OIM Domain Log Backup
Archives log directories from selected Omnia domains:
- Directly compresses domain `log/` directories
- Writes `metadata.json` with included/skipped domains, warnings, and SHA256
- Supports local or NFS destination
- Configurable backup path precedence

### Slurm Configuration Utilities
Manages active Slurm controller configuration:
- **Backup**: Archives `etc/slurm`, `etc/munge`, `etc/my.cnf.d` from NFS share
- **Cleanup**: Deletes active configuration with optional pre-backup
- **Rollback**: Restores backup, fixes permissions, runs `scontrol reconfigure`
- Resolves controller from PXE mapping (auto-detects YAML/CSV format)

## Prerequisites

| Requirement | Minimum | Notes |
|-------------|---------|-------|
| OS | RHEL 10.x or compatible | Utilities run from the OIM |
| Python | 3.12+ | Shared Omnia virtual environment |
| Ansible | ansible-core 2.20+ | Declared in `requirements.txt` |
| Disk | 50 GB free | Recommended for ISO and log operations |
| SSH | Passwordless access | Required from OIM to nodes for log collection |
| iDRAC | Reachable with virtual media support | Required only for OS deployment |
| NFS | Reachable export | Required for OS artifacts and optional for OIM log backups |

## Quick Start

```bash
# From the repository root
cd src/main

# Configure the OIM, create the shared virtual environment, stage Utils inputs
vi omnia.env
sudo ./omnia.sh -s
source /etc/profile.d/omnia-env.sh

# Edit the staged input files
vi "$OMNIA_DATA_PATH/utils/input/$OMNIA_PROJECT_NAME/collect_pxe.yml"
vi "$OMNIA_DATA_PATH/utils/input/$OMNIA_PROJECT_NAME/install_os_config.yml"
vi "$OMNIA_DATA_PATH/utils/input/$OMNIA_PROJECT_NAME/backup_oim_logs_config.yml"
vi "$OMNIA_DATA_PATH/utils/input/$OMNIA_PROJECT_NAME/slurm_config_util_config.yml"

# Run one public utility tag at a time
cd ../utils
ansible-playbook playbooks/utils.yml --tags precheck
ansible-playbook playbooks/utils.yml --tags collect
ansible-playbook playbooks/utils.yml --tags install_os
ansible-playbook playbooks/utils.yml --tags backup_oim_logs
ansible-playbook playbooks/utils.yml --tags slurm_config_backup
ansible-playbook playbooks/utils.yml --tags slurm_config_cleanup
ansible-playbook playbooks/utils.yml --tags slurm_config_rollback
```

## Public Tags

| Tag | Description | Input required |
|-----|-------------|----------------|
| `precheck` | Validate the OIM hostname, domain, admin IP, data path, and setup state | Environment variables |
| `setup` | Run the common Utils setup only | None |
| `collect` | Collect configured Kubernetes, Slurm, and login-node logs | `collect_pxe.yml` |
| `install_os` | Run the OS installation playbook | `install_os_config.yml`; credentials are collected as needed |
| `backup_oim_logs` | Archive OIM log directories for selected Omnia domains | Optional `backup_oim_logs_config.yml` |
| `slurm_config_backup` | Back up the active Slurm controller configuration from the NFS share | `omnia_config.yml`, `storage_config.yml`, PXE mapping |
| `slurm_config_cleanup` | Delete the active Slurm configuration from the NFS share (with optional pre-backup) | Same as `slurm_config_backup` |
| `slurm_config_rollback` | Restore a Slurm configuration backup and run `scontrol reconfigure` | Same as `slurm_config_backup`; requires an existing backup |
| `cleanup` | Clean all utility artifacts and remove OS-install credentials by default | None |
| `cleanup_logs` | Apply retention cleanup to collected log bundles | None |
| `cleanup_install_os` | Remove temporary OS-installation artifacts and credentials by default | None |
| `cleanup_backup_oim_logs` | Remove all OIM log-backup run directories | Optional backup-path override |
| `cleanup_slurm_config_backups` | Remove all Slurm config-backup run directories | Optional backup-path override |
| `upgrade` / `rollback` | Reserved placeholders; no lifecycle action is implemented | None |

Run exactly one public tag at a time. With no tag, `utils.yml` runs the common setup and status writer only; utility flows are opt-in.

## Cleanup

```bash
# Full cleanup (removes artifacts and credentials)
sudo ./omnia.sh --run utils --tags cleanup

# Preserve credentials for redeployment
sudo ./omnia.sh --run utils --tags cleanup -e cleanup_credentials=false
```

## Documentation

- [Utilities Documentation](https://omnia.readthedocs.io/en/latest/HowTo/utils/index.html)
- [Architecture](docs/architecture.md)
- [Input Contract](docs/contracts/input-contract.md)
- [Output Contract](docs/contracts/output-contract.md)

## License

Apache License, Version 2.0
