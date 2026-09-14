# slurm_config_backup

Creates a timestamped backup of the active Slurm controller configuration
(`etc/slurm`, `etc/munge`, `etc/my.cnf.d`) from the Slurm NFS share.

## Description

Includes `slurm_config_common` to resolve the Slurm controller and the
backup destination, prompts for an optional backup name, copies the
controller's config directories into a new timestamped backup directory, and
writes a `metadata.json` manifest (with SHA256 checksums of every backed-up
file) alongside it.

## Role Variables

See `slurm_config_common/defaults/main.yml` and `vars/main.yml` for path
resolution. Role-local:

```yaml
# Optional: pre-set to skip the interactive "backup base name" prompt
backup_base_name: ""
```

## Backup Output

```
{slurm_backups_root}/{backup_base_name}_{timestamp}/     # or {timestamp}/ if no base name
├── {controller_hostname}/
│   ├── etc/slurm/
│   ├── etc/munge/
│   └── etc/my.cnf.d/
└── metadata.json
```

## Dependencies

- `slurm_config_common` (included automatically)

## Example Playbook

```yaml
- hosts: localhost
  gather_facts: true
  roles:
    - role: slurm_config_backup
```

```bash
cd src/utils
ansible-playbook playbooks/slurm_config_util/slurm_config_util.yml --tags config_backup
```

## License

Apache 2.0

## Author Information

Dell Technologies Omnia Team
