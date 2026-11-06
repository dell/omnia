# Telemetry -- Security

## Credentials

- Telemetry credentials are stored in `<input project dir>/telemetry_credentials.yml` with mode `0600`, Ansible Vault encrypted, with the vault key in `.telemetry_credentials_key` in the same directory.
- Mandatory credentials cannot be left empty; conditional credentials are prompted for according to the enabled sources.
- Full `cleanup` removes the credential file and vault key by default; `-e cleanup_credentials=false` keeps them. A granular source cleanup (for example `cleanup_idrac`) blanks only that source's stored credential fields and preserves credentials for components that remain deployed.
- Tasks that handle credentials use `no_log`.

## Data retention

`cleanup` deletes source volumes and preserves sink volumes unless `-e delete_sinks_volume=true` is passed. Combining `delete_sinks_volume=true` with `cleanup_credentials=false` or `cleanup_logs=false` shows a warning and pauses; in that mode credentials and logs are deleted regardless of those flags.

## External access

The `external_kafka` and `external_victoria` tags print connection details, including TLS certificates, for external clients. Share them only with the intended clients.
