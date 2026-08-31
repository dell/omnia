# Telemetry — Output Contract

**Domain**: `telemetry` | **Collection**: `omnia.telemetry`

---

## 1. telemetry_status.yml

**Purpose**: Reports telemetry deployment results with per-component status and
LDMS reachability warnings.

**Location**: `<OMNIA_DATA_PATH>/telemetry/output/<project>/telemetry_status.yml`

**Producer**: `common` role — `write_telemetry_status` task (Phase 5 of deploy)

**Consumer**: `omnia-cli check`, operators

### Structure

```yaml
domain: "telemetry"
type: "deploy"
project_name: "project_default"
overall_status: "success"
generated_at: "2026-08-04T12:00:00Z"
namespace: "telemetry"
kube_vip: "192.168.13.150"

packages:
  install_mode: "offline"
  repo_url: "https://192.168.13.111:2225/pulp/content/.../rhel/10.0"

sinks:
  kafka: "deployed"
  victoria_metrics: "deployed"
  victoria_logs: "deployed"

sources:
  idrac:
    metrics: "deployed"
  ldms:
    metrics: "deployed"
  powerscale:
    metrics: "deployed"
    logs: "deployed"
  ufm:
    metrics: "deployed"
    logs: "skipped"
  vast:
    metrics: "skipped"
    logs: "skipped"
  ome:
    metrics: "deployed"
    logs: "deployed"

bridges:
  vector_ldms: "deployed"
  vector_ome: "deployed"

deploy_unreachable_nodes:
  ldms: []
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `domain` | string | Always `"telemetry"` |
| `type` | string | `"deploy"` for a deployment report |
| `project_name` | string | Active project name |
| `overall_status` | string | `"success"`, `"failed"`, or `"partial"` |
| `generated_at` | string | ISO 8601 timestamp |
| `namespace` | string | K8s namespace (always `"telemetry"`) |
| `kube_vip` | string | K8s control plane VIP used for deployment |
| `packages.install_mode` | string | `"offline"` or `"online"` |
| `packages.repo_url` | string | Pulp base URL (offline mode) |
| `sinks.<name>` | string | `"deployed"`, `"failed"`, or `"skipped"` |
| `sources.<name>.metrics` | string | Metrics outcome: `"deployed"`, `"failed"`, or `"skipped"` |
| `sources.<name>.logs` | string | Logs outcome when supported: `"deployed"`, `"failed"`, or `"skipped"` |
| `bridges.<name>` | string | `"deployed"`, `"failed"`, or `"skipped"` |
| `deploy_unreachable_nodes.ldms` | list | LDMS nodes skipped because Ansible could not reach them |

### Deployment reachability warnings

Deployment status reports LDMS nodes that could not be reached and were skipped:

```yaml
deploy_unreachable_nodes:
  ldms:
    - "compute-01"
    - "login-02"
```

An unreachable LDMS node is a non-fatal deployment warning when the remaining
LDMS components deploy successfully. Deployment continues on reachable nodes,
and the warning does not by itself change `overall_status` from `success`.
Failures returned by reachable nodes and an unreachable Kubernetes VIP remain
fatal.

---

## 2. Cleanup

`cleanup.yml` removes:

- Telemetry workloads, services, and component custom resources, except the
  Kafka identity resources retained in preservation mode
- Helm releases (Strimzi, VictoriaMetrics operator, cert-manager)
- PVCs only when `Delete_volume=true` or `delete_volume=true`; otherwise PVCs are preserved
- `telemetry_status.yml` is NOT removed (preserves last-known state)

When volume deletion is not requested, Kafka cleanup retains `Kafka/kafka` in
paused state, its managed `KafkaTopic` resources, the `controller` and `broker`
`KafkaNodePool` resources, and the `kafka-cluster-id` Secret. These objects hold
the cluster ID, node IDs, and topic metadata required to mount the preserved
Kafka PVCs safely on the next deployment. In this mode, `sinks.kafka: cleaned`
and `cleanup_components.kafka: cleaned` mean the Kafka runtime was removed;
`volumes.components.kafka: preserved` records that its data and identity were
retained.

Cleanup status adds a `volumes` block:

```yaml
volumes:
  delete_requested: false
  status: "preserved"
  components:
    idrac: "preserved"
    ldms: "preserved"
    ome: "skipped"
    powerscale: "preserved"
    ufm: "skipped"
    vast: "skipped"
    kafka: "preserved"
    victoria_metrics: "preserved"
    victoria_logs: "preserved"
```

Component volume values are `cleaned`, `preserved`, `failed`, or `skipped`.
PVC deletion does not directly delete a PV; backend data disposition follows the
PV and StorageClass reclaim policy.

Cleanup status also reports delegated nodes that were skipped because they were
unreachable:

```yaml
cleanup_unreachable_nodes:
  ldms:
    - "compute-01"
    - "login-02"
```

An unreachable LDMS sampler node is a non-fatal cleanup warning. Cleanup
continues on reachable sampler nodes and `overall_status` remains `success` when
there are no other failures. Errors returned by a reachable sampler node and an
unreachable Kubernetes VIP remain fatal.

LDMS sampler cleanup always closes the configured sampler firewall port and
removes the generated `{{ slurm_cluster_mount }}/telemetry/ldms/samplers`
configuration subtree from reachable Slurm nodes. These operations are not
controlled by `Delete_volume`; persistent Kafka, VictoriaMetrics, and legacy
LDMS PVC data continues to follow the volume setting.

Reusing the preserved iDRAC database claim requires the same MySQL credentials.
The existing claim also keeps its current requested size unless it is resized separately.

---

## 3. Downstream Consumers

| Consumer | Usage |
|----------|-------|
| `omnia-cli check` | Validates `overall_status == "success"` |
| Operators | Manual verification of deployment state |
