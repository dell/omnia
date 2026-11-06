# validate_slurm_config_util_config

Validates `slurm_config_util_config.yml` before the Slurm configuration utilities run.

## What it does

- Resolves the config path as `<input_project_dir>/slurm_config_util_config.yml` (falling back to `$OMNIA_DATA_PATH/utils/input/$OMNIA_PROJECT_NAME`).
- Loads the file when it exists. When it does not, it continues with defaults that point `omnia_config_path`, `storage_config_path`, and `pxe_mapping_path` at the project's utils input directory.
- Asserts that `omnia_config_path`, `storage_config_path`, and `pxe_mapping_path`, when provided, are strings, and reports the result.

Backup destination precedence (`-e slurm_backup_path`, then `slurm_backup_path` in the config file, then `OMNIA_BACKUP_PATH`, then the project-scoped default) is applied by `slurm_config_common`.

## Used by

`playbooks/utils.yml`, when the `slurm_config_backup`, `slurm_config_cleanup`, or `slurm_config_rollback` tag is run.

## License

Apache-2.0
