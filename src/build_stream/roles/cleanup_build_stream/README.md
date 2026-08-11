# cleanup_build_stream

## Description

Cleans up Build Stream containers, services, credentials, and data directories

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
