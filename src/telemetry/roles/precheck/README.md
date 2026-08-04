# precheck

Validates telemetry prerequisites — checks kube_vip connectivity, SSH access, and cluster readiness

## Requirements

- Ansible >= 2.20
- RHEL/Rocky Linux 9.x or 10.x

## Role Variables

See `vars/main.yml` and `defaults/main.yml` for configurable variables.

## Dependencies

None.

## Example Playbook

```yaml
- hosts: localhost
  connection: local
  roles:
    - role: omnia.telemetry.precheck
```

## License

Apache-2.0

## Author Information

Dell Technologies (<omnia-support@dell.com>)
