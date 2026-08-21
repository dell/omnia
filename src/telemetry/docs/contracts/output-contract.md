# Telemetry — Output Contract

**Domain**: `telemetry` | **Collection**: `omnia.telemetry`

---

## 1. telemetry_status.yml

**Purpose**: Reports telemetry deployment results with per-component status,
versions, and pod health.

**Location**: `<OMNIA_DATA_PATH>/telemetry/output/<project>/telemetry_status.yml`

**Producer**: `common` role — `write_telemetry_status` task (Phase 5 of deploy)

**Consumer**: `omnia-cli check`, operators

### Structure

```yaml
domain: "telemetry"
project_name: "project_default"
overall_status: "success"
generated_at: "2026-08-04T12:00:00Z"
namespace: "telemetry"
kube_vip: "192.168.13.150"

packages:
  install_mode: "offline"
  repo_url: "https://192.168.13.111:2225/pulp/content/.../rhel/10.0"
  container_registry: ""

sinks:
  kafka:
    deployed: true
    version: "quay.io/strimzi/kafka:1.1.0-kafka-4.3.0"
    topics_created:
      - "idrac"
      - "ldms"
  victoria_metrics:
    deployed: true
    version: "docker.io/victoriametrics/vmstorage:v1.149.0-cluster"
    deployment_mode: "cluster"
    operator: "docker.io/victoriametrics/operator:v0.68.3"
  victoria_logs:
    deployed: true
    version: "docker.io/victoriametrics/victoria-logs:v1.50.0"

sources:
  idrac:
    deployed: true
    version: "docker.io/dellhpcomniaaisolution/idrac_telemetry_receiver:1.3"
    bmc_servers_configured: 4
  ldms:
    deployed: true
    version: "docker.io/dellhpcomniaaisolution/ubuntu-ldms:1.1"
    sampler_nodes: 3
  ome:
    deployed: true
  powerscale:
    deployed: false
  dcgm:
    deployed: false
  ufm:
    deployed: false
  vast:
    deployed: false
  sfm:
    deployed: false
  skyway:
    deployed: false
  powervault:
    deployed: false

bridges:
  vector_ome:
    deployed: true
    version: "docker.io/timberio/vector:0.54.0-debian"
    metrics_enabled: true
    logs_enabled: true
  vector_ldms:
    deployed: true
    version: "docker.io/timberio/vector:0.54.0-debian"

pods:
  total: 40
  ready: 40
  failed: 0
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `domain` | string | Always `"telemetry"` |
| `project_name` | string | Active project name |
| `overall_status` | string | `"success"`, `"failed"`, or `"partial"` |
| `generated_at` | string | ISO 8601 timestamp |
| `namespace` | string | K8s namespace (always `"telemetry"`) |
| `kube_vip` | string | K8s control plane VIP used for deployment |
| `packages.install_mode` | string | `"offline"` or `"online"` |
| `packages.repo_url` | string | Pulp base URL (offline mode) |
| `packages.container_registry` | string | Registry override (empty = upstream) |
| `sinks.<name>.deployed` | bool | Whether the sink is deployed |
| `sinks.<name>.version` | string | Container image version (when deployed) |
| `sinks.kafka.topics_created` | list | Kafka topics created for enabled sources |
| `sinks.victoria_metrics.deployment_mode` | string | Always `"cluster"` |
| `sinks.victoria_metrics.operator` | string | VM operator image |
| `sources.<name>.deployed` | bool | Whether the source is enabled/deployed |
| `sources.<name>.version` | string | Primary container image (when deployed) |
| `sources.idrac.bmc_servers_configured` | int | Number of BMC IPs configured |
| `sources.ldms.sampler_nodes` | int | Number of sampler plugins configured |
| `bridges.<name>.deployed` | bool | Whether the bridge is deployed |
| `bridges.<name>.version` | string | Vector image (when deployed) |
| `pods.total` | int | Total pods in telemetry namespace |
| `pods.ready` | int | Pods in Running state |
| `pods.failed` | int | Pods in error state |
| `pods.failed_pods` | list | Names of failed pods (only when `failed > 0`) |

---

## 2. Cleanup

`cleanup.yml` removes:
- All telemetry K8s resources (pods, services, PVCs, CRDs)
- Helm releases (Strimzi, VictoriaMetrics operator, cert-manager)
- Namespace (when full cleanup is requested)
- `telemetry_status.yml` is NOT removed (preserves last-known state)

---

## 3. Downstream Consumers

| Consumer | Usage |
|----------|-------|
| `omnia-cli check` | Validates `overall_status == "success"` |
| Operators | Manual verification of deployment state |
