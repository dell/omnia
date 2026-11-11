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
- **Source volumes** (currently iDRAC and PowerScale): **DELETED**
- **Sink volumes** (Kafka, VictoriaMetrics, VictoriaLogs): **PRESERVED**
- **Credentials** (telemetry_credentials.yml + vault key): **DELETED**
- **Logs** (telemetry log directory + artifacts): **DELETED**

### Volume Cleanup Options (Full Cleanup Only)

| Flag | Source Volumes | Sink Volumes |
|------|----------------|--------------|
| `delete_sinks_volume=true` | DELETED | DELETED |
| (no flags) | DELETED | PRESERVED |

`delete_sinks_volume` is valid only with `--tags cleanup`. Granular source
cleanup tags never remove shared sink components or their PVCs.

### Credential and Log Preservation

| Flag | Credentials | Logs |
|------|-------------|------|
| (no flags) | DELETED | DELETED |
| `cleanup_credentials=false` | PRESERVED | DELETED |
| `cleanup_logs=false` | DELETED | PRESERVED |
| `cleanup_credentials=false cleanup_logs=false` | PRESERVED | PRESERVED |

`cleanup_credentials=false` works with both full cleanup (`--tags cleanup`) and
granular source cleanup (`--tags cleanup_idrac`, etc.). In full cleanup mode it
prevents deletion of the credential file and vault key. In granular mode it skips
blanking of the cleaned component's credential fields.

`cleanup_logs=false` applies only to full cleanup. Granular cleanup never removes
the shared log directory.

When `delete_sinks_volume=true` is combined with `cleanup_credentials=false`
or `cleanup_logs=false`, a warning is displayed and execution pauses for 30
seconds before proceeding. In cleanup with volume mode, credentials and logs
are **always deleted** regardless of these flags.

### Usage Examples

```bash
# Default cleanup - delete source volumes, preserve sink volumes
ansible-playbook telemetry.yml --tags cleanup

# Delete all volumes including sink volumes
ansible-playbook telemetry.yml --tags cleanup -e delete_sinks_volume=true

# Cleanup preserving credentials (for redeployment)
ansible-playbook telemetry.yml --tags cleanup -e cleanup_credentials=false

# Cleanup preserving both credentials and logs
ansible-playbook telemetry.yml --tags cleanup -e cleanup_credentials=false -e cleanup_logs=false

# Granular cleanup preserving credentials
ansible-playbook telemetry.yml --tags cleanup_idrac -e cleanup_credentials=false

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
