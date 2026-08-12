# test_config.yml — Configuration Reference

Primary configuration file for the test automation framework.
Edit this file before running any tests.

---

## Execution Modes

### Local Mode

Run tests directly on the machine where `repo_manager` is deployed.

```yaml
oim_server_ip: ""    # Leave empty — tests run locally
```

No SSH, no sync, no clone settings needed. The playbook must already be
deployed on this machine.

### Remote Mode

Run tests against a remote OIM server over SSH.

```yaml
oim_server_ip: "10.20.0.100"   # MANDATORY — target server IP
oim_ssh_user: root              # SSH user (default: root)
oim_ssh_port: 22                # SSH port (default: 22)
```

---

## Fields

### Connection

| Field | Required | Description | Default |
|-------|----------|-------------|---------|
| `oim_server_ip` | Conditional | Target server IP. Leave empty for local mode. | `""` |
| `oim_ssh_user` | Remote only | SSH username | `root` |
| `oim_ssh_port` | Remote only | SSH port | `22` |

### Clone Settings (Remote only, Optional)

Only needed if the repo is **not already cloned** on the target server.
If the repo exists, just set `clone_path` to the existing location.

| Field | Required | Description | Default |
|-------|----------|-------------|---------|
| `clone_url` | No | Git URL to clone on target. Leave empty to skip. | `""` |
| `clone_path` | No | Absolute path on target where repo is/will be cloned | `/root/repo-manager` |
| `force_clone` | No | Delete existing clone and re-clone fresh | `false` |

### Dataset

| Field | Required | Description | Default |
|-------|----------|-------------|---------|
| `dataset` | No | Dataset folder name under `datasets/` | `data_set_01` |

The dataset folder contains `input/` (repo_manager_config, credentials,
endpoint config, software_config) that the playbook needs.

### Sync Options

| Field | Required | Description | Default |
|-------|----------|-------------|---------|
| `sync_repo_manager_input` | No | Push dataset input/ files to target before tests | `true` |

When `sync_repo_manager_input: true`, the framework syncs:
```
datasets/<dataset>/input/  →  <OMNIA_DATA_PATH>/repo_manager/input/<project_name>/
```

The framework reads `OMNIA_DATA_PATH` and `OMNIA_PROJECT_NAME` from the target
server's `/etc/omnia/omnia.env` to resolve the sync destination. Directories
are created automatically if they don't exist.

### Runtime Paths

| Field | Required | Description | Default |
|-------|----------|-------------|---------|
| `shared_path` | No | Where repo_manager stores runtime output on target | `/opt/omnia/repo_manager` |

### Report Settings

| Field | Required | Description | Default |
|-------|----------|-------------|---------|
| `report_path` | No | Directory for test reports (relative or absolute) | `reports` |
| `report_name` | No | Base name for report files (no extension) | `repo_manager_test_report` |
| `report_id` | No | Custom report ID. Empty = auto-generated timestamp. | `""` |

---

## Example — Minimal Remote Setup

```yaml
oim_server_ip: "10.20.0.100"
oim_ssh_user: root
clone_path: "/root/repo-manager"
dataset: "data_set_01"
sync_repo_manager_input: true
```

## Example — Local Mode

```yaml
oim_server_ip: ""
dataset: "data_set_01"
sync_repo_manager_input: false
```
