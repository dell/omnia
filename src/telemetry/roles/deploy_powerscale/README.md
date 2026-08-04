# deploy_powerscale

Deploys PowerScale telemetry collection for Dell PowerScale storage monitoring

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
    - role: omnia.telemetry.deploy_powerscale
```

## License

Apache-2.0

## Author Information

Dell Technologies (<omnia-support@dell.com>)
