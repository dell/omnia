# deploy_ome

Deploys OME (OpenManage Enterprise) telemetry collection for infrastructure monitoring

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
    - role: omnia.telemetry.deploy_ome
```

## License

Apache-2.0

## Author Information

Dell Technologies (<omnia-support@dell.com>)
