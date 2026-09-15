# slurm_config_common

Shared setup logic used by `slurm_config_backup`, `slurm_cleanup`, and
`slurm_config_rollback`. Not intended to be invoked directly.

## Description

Resolves the optional `slurm_config_util_config.yml`, reads
`omnia_config.yml` and `storage_config.yml`, parses the PXE mapping (YAML or
CSV) to identify the Slurm controller, and resolves both the active Slurm
config path (on the NFS share) and the backup destination (local path or NFS
export). Each of the three operation roles includes this role as their first
task so every operation can be run standalone via its own tag.

## Role Variables

See `defaults/main.yml` and `vars/main.yml`. Key facts set for consumption by
the calling role:

| Fact | Description |
|---|---|
| `slurm_config_path_effective` | Active Slurm config dir on the NFS share |
| `slurm_backups_root_effective` | Resolved backup destination (local or NFS mountpoint) |
| `ctld_list` | List of Slurm controller hostnames |
| `slurm_controller_hostname` / `slurm_controller_ip` | Primary controller |
| `slurm_config_directories` | `[etc/slurm, etc/munge, etc/my.cnf.d]` |

`slurm_controller` is added as a dynamic inventory host (for `delegate_to`).

## Input Resolution Precedence

1. `-e <var>=<value>` (CLI extra-var)
2. `slurm_config_util_config.yml` (`input/slurm_config_util_config.yml`)
3. Domain defaults (`omnia_config.yml` / `storage_config.yml` / `nodes_slurm.yaml`)

## Backup Destination Precedence

Same as `oim_log_backup`:

1. `-e slurm_backup_path=<path>`
2. `slurm_backup_path:` in `slurm_config_util_config.yml`
3. `OMNIA_BACKUP_PATH` environment variable
4. Default: `OMNIA_DATA_PATH/utils/output/OMNIA_PROJECT_NAME/slurm_config_util`

A raw NFS export (`<server>:/<path>`) is detected and mounted at a fixed
local mountpoint (`/tmp/omnia_slurm_config_util_nfs`).

## Dependencies

None.

## License

Apache 2.0

## Author Information

Dell Technologies Omnia Team
