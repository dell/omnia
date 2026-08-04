# deploy_kafka

Deploys Apache Kafka (Strimzi operator) for telemetry data streaming

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
    - role: omnia.telemetry.deploy_kafka
```

## License

Apache-2.0

## Author Information

Dell Technologies (<omnia-support@dell.com>)
