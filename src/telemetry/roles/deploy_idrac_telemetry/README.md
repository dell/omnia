# deploy_idrac_telemetry

Reconciles iDRAC telemetry collection for Dell server hardware monitoring.

- When `telemetry_sources.idrac.metrics_enabled` is `true`, the role deploys
  iDRAC telemetry or restores a retained, scaled-down StatefulSet.
- When it is `false`, the role scales only `idrac-telemetry` to zero and waits
  for its pods to terminate. The StatefulSet, PVCs, MySQL data, Services,
  Secrets, credentials, and generated configuration are preserved.
- Repeated enable and disable runs are idempotent.

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
