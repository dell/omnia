# External Kafka Connect

Fetches the native Kafka mTLS endpoint, Kafka HTTP Bridge endpoint, and TLS
certificates from the Kubernetes cluster for external client integration
(for example, Dell OME).

## Requirements

- Telemetry must be deployed (`ansible-playbook telemetry.yml --tags deploy`)
- Kafka pods must be running in the `telemetry` namespace
- SSH access to `kube_vip` from the OIM host

## Output

Files are written to `{{ output_project_dir }}/external_kafka`:

| File | Description |
|------|-------------|
| `ca.crt` | Kafka cluster CA certificate (server cert for OME) |
| `user.crt` | Kafka client certificate |
| `user.key` | Kafka client private key |
| `external_kafka_connect_details.yml` | Connection details YAML |

The generated YAML exposes two distinct endpoints:

- `kafka.bootstrap_server` is the native mTLS Kafka listener used by OME.
- `kafka.bridge.endpoint` is the HTTP Bridge used by REST-based validation.

## Usage

```bash
ansible-playbook playbooks/telemetry.yml --tags external_kafka
```

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `kafka_namespace` | `telemetry` | Kubernetes namespace for Kafka |
| `kafka_bootstrap_service_name` | `kafka-kafka-external-bootstrap` | Native mTLS Kafka LoadBalancer service |
| `kafka_bridge_service_name` | `bridge-bridge-lb` | Kafka HTTP Bridge LoadBalancer service |
| `kafka_cluster_ca_secret` | `kafka-cluster-ca-cert` | K8s secret for cluster CA |
| `kafka_client_secret` | `kafkapump` | K8s secret for client TLS |

## Dependencies

None (uses `telemetry_prereq.yml` for config loading and kube_vip resolution).
