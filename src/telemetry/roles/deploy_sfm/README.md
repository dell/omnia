# deploy_sfm

Deploys SFM (Smart Fabric Manager) telemetry for network fabric monitoring

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
    - role: omnia.telemetry.deploy_sfm
```

## License

Apache-2.0

## Author Information

Dell Technologies (<omnia-support@dell.com>)
