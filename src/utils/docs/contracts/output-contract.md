# Utils Domain -- Output Contract

**Domain**: `utils` | **Collection**: `omnia.utils`

---

## 1. failed_nodes.json

**Purpose**: Machine-readable report of nodes that failed PXE boot or phone-home verification.

**Location**: `<OMNIA_DATA_PATH>/utils/output/<project>/failed_nodes.json`

**Producer**: `set_pxe_boot.yml` playbook

**Consumer**: BuildStream Manager, retry workflows

### Schema

```json
{
  "generated_at": "2026-08-21T10:30:00Z",
  "total_nodes": 10,
  "failed_count": 2,
  "success_count": 8,
  "failed_nodes": [
    {
      "bmc_ip": "100.10.0.73",
      "admin_ip": "192.168.1.50",
      "hostname": "node01",
      "service_tag": "ABC1234",
      "failure_stage": "pxe_boot",
      "error_message": "iDRAC unreachable"
    },
    {
      "bmc_ip": "100.10.0.74",
      "admin_ip": "192.168.1.51",
      "hostname": "node02",
      "service_tag": "XYZ5678",
      "failure_stage": "phone_home",
      "error_message": "Phone-home timeout after 30 minutes"
    }
  ]
}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `generated_at` | string (ISO 8601) | Report generation timestamp |
| `total_nodes` | int | Total nodes in inventory |
| `failed_count` | int | Count of failed nodes |
| `success_count` | int | Count of successful nodes |
| `failed_nodes` | array | List of failed node details |
| `failed_nodes[].bmc_ip` | string | BMC/iDRAC IP address |
| `failed_nodes[].admin_ip` | string | Node's admin network IP |
| `failed_nodes[].hostname` | string | Node hostname |
| `failed_nodes[].service_tag` | string | Dell service tag (if available) |
| `failed_nodes[].failure_stage` | string | Stage where failure occurred |
| `failed_nodes[].error_message` | string | Human-readable error description |

### Failure Stages

| Stage | Description |
|-------|-------------|
| `pxe_boot` | Failed to set PXE boot or restart via iDRAC |
| `phone_home` | Node did not phone home within timeout |
| `idrac_unreachable` | iDRAC not reachable during precheck |
| `lc_not_ready` | Lifecycle Controller not ready |

---

## 2. utils_status.yml

**Purpose**: Domain execution status for `omnia-cli status` integration.

**Location**: `<OMNIA_DATA_PATH>/utils/utils_status.yml`

**Producer**: `utils_status_writer` role

**Consumer**: `omnia-cli status` command

### Schema

```yaml
domain: utils
status: success
playbook: set_pxe_boot.yml
execution_start_time: "2026-08-21T10:00:00Z"
execution_end_time: "2026-08-21T10:30:00Z"
role_results:
  - role: collect_pxe_credentials
    status: success
  - role: idrac_pxe_boot
    status: success
    nodes_processed: 10
    nodes_failed: 2
  - role: verify_phone_home
    status: partial
    nodes_verified: 8
    nodes_timeout: 2
errors: []
warnings:
  - "2 nodes did not complete phone-home verification"
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `domain` | string | Domain name (`utils`) |
| `status` | string | Overall status: `success`, `partial`, `failed` |
| `playbook` | string | Name of executed playbook |
| `execution_start_time` | string (ISO 8601) | Execution start timestamp |
| `execution_end_time` | string (ISO 8601) | Execution end timestamp |
| `role_results` | array | Per-role execution results |
| `errors` | array | List of error messages |
| `warnings` | array | List of warning messages |

---

## 3. Collector Logs Archive

**Purpose**: Bundled logs from cluster nodes for support analysis.

**Location**: `<OMNIA_DATA_PATH>/collector_logs/<timestamp>.tar.gz`

**Producer**: `collect.yml` playbook

**Contents**:
- K8s master/worker logs
- Slurm controller/node logs
- Login node logs
- Cloud-init logs

---

## 4. Output Directory Structure

```
<OMNIA_DATA_PATH>/
├── utils/
│   ├── utils_status.yml           # Domain status (omnia-cli)
│   └── output/
│       └── <project>/
│           └── failed_nodes.json  # Failed nodes report
└── collector_logs/
    └── <timestamp>.tar.gz         # Log collection archive
```

---

## 5. Consumers

| Consumer | File | Purpose |
|----------|------|---------|
| `omnia-cli status` | `utils_status.yml` | Display domain execution status |
| BuildStream Manager | `failed_nodes.json` | Retry failed nodes |
| GitLab automation | `failed_nodes.json` | Track node failures |
| Support analysis | `collector_logs/*.tar.gz` | Debug cluster issues |
