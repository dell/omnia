# build_stream_setup

## Description

Domain setup role for Build Stream — resolves input/output directories, loads OIM metadata, and guards against upgrades

## Requirements

- Ansible >= 2.14
- Python >= 3.9

## Role Variables

See `vars/main.yml` for available variables.

## Dependencies

None.

## Example Playbook

```yaml
- hosts: localhost
  roles:
    - role: build_stream_setup
```

## License

Apache-2.0

## Author Information

Dell Technologies
