# validate_backup_oim_logs_config

Validates `backup_oim_logs_config.yml` before the OIM log backup flow runs.

## What it does

- Resolves the config path as `<input_project_dir>/backup_oim_logs_config.yml` (falling back to `$OMNIA_DATA_PATH/utils/input/$OMNIA_PROJECT_NAME`).
- Loads the file when it exists. When it does not, it continues with a default configuration that selects all Omnia domains and uses `OMNIA_BACKUP_PATH` for the destination, and reports that the defaults are in use.
- Asserts that `domains` is a list of valid Omnia domain names (failing on unknown names) and that `backup_path`, when set, is a string.

Backup destination precedence at run time is resolved by `oim_log_backup`: `-e backup_path`, then `backup_path` in the config file, then `OMNIA_BACKUP_PATH`, then the project-scoped default under `$OMNIA_DATA_PATH/utils/output/`.

## Used by

`playbooks/utils.yml`, when the `backup_oim_logs` tag is run.

## License

Apache-2.0
