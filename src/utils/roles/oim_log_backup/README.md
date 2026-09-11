# oim_log_backup

Archives the log directories of every Omnia domain on the OIM into a single
timestamped `tar.gz` bundle with a `metadata.json` manifest.

## Description

This role runs entirely on the OIM (no remote nodes involved). It resolves a
backup destination, checks each domain's `log/` directory, and creates the
archive directly from the source directories (no intermediate uncompressed
copy). Domains without a `log/` directory are skipped and recorded as
warnings in `metadata.json` rather than failing the run.

## Role Variables

Available variables are listed below, along with default values (see
`vars/main.yml`):

```yaml
# Collection stages
oim_log_backup_stages:
  - setup
  - bundle

# Domains backed up when no config file / domain selection is supplied
backup_all_domains:
  - repo_manager
  - image_build_manager
  - orchestrator
  - discovery
  - telemetry
  - build_stream
  - utils
```

## Backup Path Resolution

Highest to lowest precedence:

1. `-e backup_path=<path>` (CLI extra-var)
2. `backup_path:` in `input/backup_oim_logs_config.yml`
3. `OMNIA_BACKUP_PATH` environment variable
4. Default: `OMNIA_DATA_PATH/utils/output/OMNIA_PROJECT_NAME/backup_oim_logs`

Any of the above may be a raw NFS export, e.g.
`nfs:/mnt/backup_dir`. This is detected
automatically and mounted at a fixed local mountpoint
(`/tmp/omnia_backup_oim_logs_nfs`) before the archive is written.

## Dependencies

None.

## Example Playbook

```yaml
- hosts: localhost
  gather_facts: false
  tags:
    - setup
  roles:
    - role: oim_log_backup
      vars:
        stage: setup

- hosts: localhost
  gather_facts: false
  tags:
    - bundle
  roles:
    - role: oim_log_backup
      vars:
        stage: bundle
```

## License

Apache 2.0

## Author Information

Dell Technologies Omnia Team
