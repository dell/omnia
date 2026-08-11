# slurm_cleanup

Cleans up Slurm configuration files and removes cluster-specific settings.

## Description

This role performs cleanup operations on Slurm configuration files, removing cluster-specific settings, temporary files, and resetting configurations to default states. It supports both partial and complete cleanup modes.

## Requirements

- Slurm installation on target nodes
- Administrative privileges for Slurm configuration modification
- Backup of current configuration (recommended)

## Role Variables

Available variables are listed below, along with default values (see `defaults/main.yml`):

```yaml
# Cleanup scope
cleanup_mode: "partial"  # partial, complete
preserve_backups: true
remove_logs: false

# Configuration paths
slurm_conf_dir: "/etc/slurm"
slurm_log_dir: "/var/log/slurm"
slurm_spool_dir: "/var/spool/slurm"
```

## Dependencies

None.

## Example Playbook

```yaml
- hosts: slurm_controllers:slurm_nodes
  become: true
  roles:
    - role: slurm_cleanup
      vars:
        cleanup_mode: "partial"
        preserve_backups: true
        remove_logs: false
```

## License

Apache 2.0

## Author Information

Dell Technologies Omnia Team
