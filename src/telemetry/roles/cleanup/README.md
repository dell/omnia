# cleanup

Removes telemetry components deployed on the Kubernetes cluster.

Supports granular cleanup by source (iDRAC, LDMS, OME, PowerScale, UFM, VAST)
and full cleanup including shared sinks (Kafka, VictoriaMetrics, VictoriaLogs).

## Requirements

- Ansible >= 2.20
- RHEL/Rocky Linux 10.x

## Role Variables

See `vars/main.yml` for configurable variables.

## Cleanup Behavior

### Default Behavior (No Flags)
- **Source volumes** (iDRAC, LDMS, PowerScale, etc.): **DELETED**
- **Sink volumes** (Kafka, VictoriaMetrics, VictoriaLogs): **PRESERVED**

### Volume Cleanup Options

| Flag | Source Volumes | Sink Volumes |
|------|----------------|--------------|
| `delete_sinks_volume=true` | DELETED | DELETED |
| (no flags) | DELETED | PRESERVED |

### Usage Examples

```bash
# Default cleanup - delete source volumes, preserve sink volumes
ansible-playbook telemetry.yml --tags cleanup

# Delete all volumes including sink volumes
ansible-playbook telemetry.yml --tags cleanup -e delete_sinks_volume=true

# Cleanup specific source
ansible-playbook telemetry.yml --tags cleanup_idrac
```

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
