# cleanup_build_stream

## Description

Cleans up Build Stream containers, services, credentials, and generated data.
The role removes project output, validation/watcher/API/playbook logs, active
and archived queues, TLS/runtime data, and Python bytecode caches. It preserves
initializer-owned application source and non-credential input files so the
domain can be redeployed. PostgreSQL data is preserved unless
`postgres_backup=false` is supplied. With a retained database, only the
artifact files whose keys are stored in `artifact_metadata` (under
`build_stream_root/artifacts`) are kept; everything else under
`build_stream_root` is removed. With the database deleted, `build_stream_root`
is removed completely. Build Stream credential files are removed
by default; supply `-e cleanup_credentials=false` to preserve the credential
files and vault keys.

Every run appends `STARTED` and `COMPLETED`/`FAILED` JSON-lines audit records to
`/var/log/omnia/build_stream_cleanup_audit/cleanup_audit.jsonl`.

Successful cleanup also removes host Ansible logs under
`/var/log/omnia/build_stream`. Before redeploying, run the supported domain
initializer and then the BuildStream deployment from `src/main`:

```bash
sudo ./omnia.sh --init build_stream
sudo ./omnia.sh --run build_stream
```

The initialization command invokes `src/build_stream/domain-init.sh` and
recreates the required runtime and log directories.

## Requirements

- Ansible >= 2.14
- Python >= 3.9

## Role Variables

See `vars/main.yml` for available variables.

## Dependencies

None.

## Example Playbook

```yaml
- hosts: oim_group
  roles:
    - role: cleanup_build_stream
```

## License

Apache-2.0

## Author Information

Dell Technologies
