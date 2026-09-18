# External Victoria Connect

Fetches VictoriaMetrics and VictoriaLogs external connection details (endpoints, TLS certificates, syslog target) from the Kubernetes cluster for external client integration (e.g., SFM, PowerScale).

## Requirements

- Telemetry must be deployed (`ansible-playbook telemetry.yml --tags deploy`)
- VictoriaMetrics pods must be running in the `telemetry` namespace
- SSH access to `kube_vip` from the OIM host

## Output

Files are written to `{{ output_project_dir }}/external_victoria`:

| File | Description |
|------|-------------|
| `ca.crt` | Victoria TLS CA certificate (only if TLS enabled) |
| `external_victoria_connect_details.yml` | Connection details YAML |

The connection details file includes:

| Section | Contents |
|---------|----------|
| `victoria_metrics` | vminsert/vmselect endpoints, write/query URLs, SFM notes |
| `victoria_logs` | vlinsert/vlselect endpoints (if deployed) |
| `vlagent` | Syslog endpoint for PowerScale forwarding (if deployed) |
| `powerscale` | ISI audit commands for syslog configuration |

## Usage

```bash
ansible-playbook playbooks/telemetry.yml --tags external_victoria
```

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `victoria_namespace` | `telemetry` | Kubernetes namespace |
| `vm_vminsert_service` | `vminsert-victoria-cluster` | vminsert LoadBalancer service |
| `vm_vmselect_service` | `vmselect-victoria-cluster` | vmselect LoadBalancer service |
| `vm_vminsert_port` | `8480` | vminsert port |
| `vm_vmselect_port` | `8481` | vmselect port |
| `vl_vlinsert_service` | `vlinsert-victoria-logs-cluster` | vlinsert LoadBalancer service |
| `vl_vlselect_service` | `vlselect-victoria-logs-cluster` | vlselect LoadBalancer service |
| `vl_vlagent_service` | `vlagent` | VLAgent syslog LoadBalancer service |

## Dependencies

None (uses `telemetry_prereq.yml` for config loading and kube_vip resolution).
