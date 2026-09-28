# slurm_cleanup

Deletes the active Slurm configuration directory from the Slurm NFS share.

## Description

Includes `slurm_config_common` to resolve the active config path, prompts
for an optional pre-cleanup backup (delegates to `slurm_config_backup`), then
requires an explicit confirmation token before deleting the whole
`{slurm_config_path}` directory (all controllers) from the NFS share.

## Role Variables

Role-local (see `defaults/main.yml`):

```yaml
# Optional: pre-set to skip the interactive prompts (e.g. for automation)
pre_cleanup_backup_choice_input: "y"    # y|yes|n|no
cleanup_confirm_input: "YES"            # must match slurm_cleanup_confirm_token
```

Shared (see `slurm_config_common`):

```yaml
slurm_cleanup_confirm_token: "YES"       # confirmation token required
slurm_cleanup_pre_backup_default: "y"
```

## Dependencies

- `slurm_config_common` (included automatically)
- `slurm_config_backup` (included conditionally, if pre-cleanup backup is requested)

## Example Playbook

```yaml
- hosts: localhost
  gather_facts: true
  roles:
    - role: slurm_cleanup
```

```bash
cd src/utils
ansible-playbook playbooks/slurm_config_util/slurm_config_util.yml --tags slurm_config_cleanup
```

## License

Apache 2.0

## Author Information

Dell Technologies Omnia Team
