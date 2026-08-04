# slurm_config_rollback

Rollback Slurm configuration files from previous backups.

## Description

This role restores Slurm configuration files from timestamped backups created by the slurm_config_backup role. It supports selective rollback of specific configuration files and validation of restored configurations.

## Requirements

- Previous backups created by slurm_config_backup role
- Administrative privileges for Slurm configuration modification
- Slurm services should be stopped during rollback

## Role Variables

Available variables are listed below, along with default values (see `defaults/main.yml`):

```yaml
# Rollback configuration
backup_dir: "/opt/omnia/backups/slurm"
rollback_timestamp: ""  # Specific backup to restore (latest if empty)
validate_after_rollback: true

# Service management
restart_slurm_services: true
stop_services_before_rollback: true
service_restart_delay: 30
```

## Dependencies

- Requires backups created by `slurm_config_backup` role

## Example Playbook

```yaml
- hosts: slurm_controllers
  become: true
  roles:
    - role: slurm_config_rollback
      vars:
        backup_dir: "/opt/omnia/backups/slurm"
        rollback_timestamp: "2026-08-03_14-30-15"
        validate_after_rollback: true
        restart_slurm_services: true
```

## License

Apache 2.0

## Author Information

Dell Technologies Omnia Team
