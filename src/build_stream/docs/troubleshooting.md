# Build Stream -- Troubleshooting

Run `./omnia.sh --run build_stream --tags precheck` to check that the Repository Manager and Image Build Manager containers are running, credentials are present, and output files exist. Run `--tags validate` to validate `build_stream_config.yml`.

## Common issues

| Symptom (message) | Cause | Action |
|-------------------|-------|--------|
| `Invalid tag usage detected` / `Invalid tag combination detected` | Unsupported tag, or a disallowed combination such as `prepare` + `cleanup` | Use one supported tag; see the README Tags section |
| `The project directory at ... does not exist` | Inputs were not staged | Run `sudo ./omnia.sh --init build_stream` |
| `gitlab_host ... contains invalid characters or template syntax` | `gitlab_host` is not a plain hostname | Use a valid hostname |
| `Failed to decrypt or load ... build_stream_credentials.yml` | Vault key does not match the credential file | Verify `.build_stream_credentials_key`, or remove both files and re-run `--tags credentials` |
| `Directory <path>/build_stream is missing; ensure oim_shared_path is mounted and populated correctly` | Runtime data path is not mounted or not initialized | Mount the shared path and run `sudo ./omnia.sh --init build_stream` |
| `The deployment of the <build stream> container has failed` | Container start failed | Run the `utility/oim_cleanup.yml` playbook to clean up existing OIM resources, then re-run the original playbook |
| `The deployment of the <postgres> container has failed` | Typically database initialization issues when data from a previous deployment exists | Option 1: re-run with the same PostgreSQL credentials used before to reuse the existing database. Option 2 (permanently deletes the preserved database): run `playbooks/cleanup/cleanup_build_stream.yml -e postgres_backup=false --skip-tags credentials` from `src/build_stream`, then `sudo ./omnia.sh --init build_stream`, then re-run `--tags prepare` |
| `OMNIA_SRC_PATH ... is inside the Omnia data path` | The data path is mounted read-write into the Build Stream API container and the root playbook watcher runs from `OMNIA_SRC_PATH` | Keep the Omnia source tree outside the data path |
| NFS data path warning during precheck | The data path is on NFS, and the playbook queue under it drives root playbook execution | Export it with `root_squash` and only to trusted clients (`exportfs -ra`); see [Security](security.md) |

Credentials: `--tags credentials` runs setup, validation, and the credential prompt only.

## Log locations

| Log | Location |
|-----|----------|
| Top-level playbook | `/var/log/omnia/build_stream/build_stream.log` |
| Job, stage, cadence, and validation logs | `<data_path>/build_stream/log/` |
| Playbook queue | `<data_path>/build_stream/playbook_queue/` |
