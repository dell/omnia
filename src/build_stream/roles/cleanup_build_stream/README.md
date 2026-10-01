# cleanup_build_stream

## Description

Cleans up Build Stream containers, services, credentials, and generated data.
The role removes project output, validation/watcher/API/playbook logs, active
and archived queues, TLS/runtime data, and Python bytecode caches. It preserves
initializer-owned application source and non-credential input files so the
domain can be redeployed. PostgreSQL data is preserved unless
`postgres_backup=false` is supplied.

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
