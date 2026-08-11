# common

Shared telemetry utilities — loads telemetry config, validates prerequisites, common variables

## Requirements

- Ansible >= 2.20
- RHEL/Rocky Linux 10.x

## Role Variables

See `vars/main.yml` and `defaults/main.yml` for configurable variables.

## Dependencies

None.

## Example Playbook

```yaml
- hosts: localhost
  connection: local
  roles:
    - role: omnia.telemetry.common
```

## License

Apache-2.0

## Author Information

Dell Technologies (<omnia-support@dell.com>)
