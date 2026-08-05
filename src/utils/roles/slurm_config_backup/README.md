# slurm_config_backup

Creates backups of Slurm configuration files for recovery and rollback operations.

## Description

This role creates timestamped backups of Slurm configuration files including slurm.conf, slurmdbd.conf, and other critical configuration files. It supports incremental backups and configurable retention policies.

## Requirements

- Slurm installation on target nodes
- Sufficient disk space for backup storage
- Read access to Slurm configuration directories

## Role Variables

Available variables are listed below, along with default values (see `defaults/main.yml`):

```yaml
# Backup configuration
backup_dir: "/opt/omnia/backups/slurm"
backup_retention_days: 30
compress_backups: true

# Source paths
slurm_conf_dir: "/etc/slurm"
slurmdbd_conf_file: "/etc/slurm/slurmdbd.conf"
include_logs: false
```

## Dependencies

None.

## Example Playbook

```yaml
- hosts: slurm_controllers
  become: true
  roles:
    - role: slurm_config_backup
      vars:
        backup_dir: "/opt/omnia/backups/slurm"
        backup_retention_days: 60
        compress_backups: true
```

## License

Apache 2.0

## Author Information

Dell Technologies Omnia Team
