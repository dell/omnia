# slurm_config_rollback

Restores a previous Slurm configuration backup and reconfigures the running
Slurm controller.

## Description

Includes `slurm_config_common` to resolve the controller and backup
destination, lists available backups (latest first), validates backup
integrity (`slurm.conf`, `slurmdbd.conf`, `cgroup.conf`, `gres.conf`,
`munge.key`), optionally creates a safety backup, restores the config
directories, detects and remounts any stale NFS mounts on the controller
(`/etc/slurm`, `/etc/munge`, `/etc/my.cnf.d`) caused by directory recreation
during restore (using `ansible.posix.mount` with `state: remount`), fixes file
permissions on the controller (`slurmdbd.conf`: `0600`, `munge.key`: `0400`),
restarts `slurmdbd` if its config changed, and runs `scontrol reconfigure`.

## Role Variables

Role-local (see `defaults/main.yml`):

```yaml
# Optional: pre-set to skip the interactive prompts (e.g. for automation)
backup_choice_input: "1"                  # index into the displayed backup list
continue_missing_confs_input: "y"
continue_missing_munge_key_input: "y"
continue_missing_input: "y"
pre_rollback_backup_choice_input: "y"
```

Shared (see `slurm_config_common`):

```yaml
rollback_backup_list_limit: 20            # max backups shown (latest first)
```

## Failure Handling

- Fails fast if the selected backup is missing `slurm.conf`.
- Warns (with continue prompt) for other missing files/directories.
- If a controller NFS mount is still stale after the automatic remount
  attempt, the task fails with guidance to remount manually and re-run.
- If `slurmctld` is not running, or `scontrol reconfigure` fails, the task
  fails with recovery guidance — the on-disk restore has already completed.

## Dependencies

- `slurm_config_common` (included automatically)
- `slurm_config_backup` (included conditionally, for the pre-rollback safety backup)

## Example Playbook

```yaml
- hosts: localhost
  gather_facts: true
  roles:
    - role: slurm_config_rollback
```

```bash
cd src/utils
ansible-playbook playbooks/slurm_config_util/slurm_config_util.yml --tags slurm_config_rollback
```

## License

Apache 2.0

## Author Information

Dell Technologies Omnia Team
