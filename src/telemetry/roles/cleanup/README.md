# cleanup

Removes telemetry components deployed on the Kubernetes cluster.

Supports granular cleanup by source (iDRAC, LDMS, OME, PowerScale, UFM, VAST)
and full cleanup including shared sinks (Kafka, VictoriaMetrics, VictoriaLogs).

## Requirements

- Ansible >= 2.20
- RHEL/Rocky Linux 10.x

## Role Variables

See `vars/main.yml` for configurable variables.

## Dependencies

None.

## Example Playbook

```yaml
- hosts: localhost
  connection: local
  roles:
    - role: omnia.telemetry.cleanup
```

## License

Apache-2.0

## Author Information

Dell Technologies (<omnia-support@dell.com>)
