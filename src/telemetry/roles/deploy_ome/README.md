# deploy_ome

Reconciles the OME (OpenManage Enterprise) Vector telemetry bridge.

Metrics and logs are controlled independently by the matching flags under
`telemetry_sources.ome` and `telemetry_bridges.vector_ome`. An enabled bridge
channel requires its source channel to be enabled.

| Metrics | Logs | Reconciled state |
| --- | --- | --- |
| enabled | enabled | Metrics and logs routes run |
| enabled | disabled | Only the metrics route runs |
| disabled | enabled | Only the logs route runs |
| disabled | disabled | `vector-ome` is scaled to zero |

Disabling is non-destructive: Kafka users and secrets, generated manifests,
credentials, and external OME topics are retained. Re-enabling reapplies the
channel-specific configuration and restores each enabled Deployment to its
configured replica count. Shared Kafka and Victoria workloads are not stopped.

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
    - role: omnia.telemetry.deploy_ome
```

## License

Apache-2.0

## Author Information

Dell Technologies (<omnia-support@dell.com>)
