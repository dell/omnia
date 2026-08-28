# Utils Domain -- Output Contract

**Domain**: `utils` | **Collection**: `omnia.utils`

---

> **Note**: PXE boot output contracts (`failed_nodes.json`, PXE-related `utils_status.yml`)
> have been moved to the orchestrator domain. See `src/orchestrator/playbooks/setpxe/`.

## 1. Collector Logs Archive

**Purpose**: Bundled logs from cluster nodes for support analysis.

**Location**: `<OMNIA_DATA_PATH>/collector_logs/<timestamp>.tar.gz`

**Producer**: `collect.yml` playbook

**Contents**:
- K8s master/worker logs
- Slurm controller/node logs
- Login node logs
- Cloud-init logs

---

## 2. Output Directory Structure

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

## 3. Consumers

| Consumer | File | Purpose |
|----------|------|---------|
| `omnia-cli status` | `utils_status.yml` | Display domain execution status |
| BuildStream Manager | `failed_nodes.json` | Retry failed nodes |
| GitLab automation | `failed_nodes.json` | Track node failures |
| Support analysis | `collector_logs/*.tar.gz` | Debug cluster issues |
