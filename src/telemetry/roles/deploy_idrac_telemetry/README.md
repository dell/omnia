# deploy_idrac_telemetry

Deploys iDRAC telemetry collection for Dell server hardware monitoring

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
    - role: omnia.telemetry.deploy_idrac_telemetry
```

## License

Apache-2.0

## Author Information

Dell Technologies (<omnia-support@dell.com>)
