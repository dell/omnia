# test_config.yml — Configuration Reference

Primary configuration file for the test automation framework.
Edit this file before running any tests.

---

## Execution Modes

### Local Mode

Run tests directly on the machine where `image_build_manager` is deployed.

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
| `clone_path` | No | Absolute path on target where repo is/will be cloned | `/root/image-build-manager` |
| `force_clone` | No | Delete existing clone and re-clone fresh | `false` |

### Dataset

| Field | Required | Description | Default |
|-------|----------|-------------|---------|
| `dataset` | No | Dataset folder name under `datasets/` | `data_set_01` |

The dataset folder contains `input/` (config, build config, credentials) and
`repo_manager_output/` (upstream dependency files) that the playbook needs.

### Sync Options

| Field | Required | Description | Default |
|-------|----------|-------------|---------|
| `sync_image_build_input` | No | Push dataset input/ files to target before tests | `true` |
| `sync_output` | No | Push dataset repo_manager_output/ to target | `false` |

When `sync_image_build_input: true`, the framework syncs:
```
datasets/<dataset>/input/  →  <clone_path>/src/input/<project_name>/
datasets/<dataset>/input/config.yml  →  <clone_path>/config.yml
```

When `sync_output: true`, the framework syncs:
```
datasets/<dataset>/repo_manager_output/  →  <repo_manager_output_dir>/
```
The target path is read from `repo_manager_output_dir` in `image_build_config.yml`.
Default: `/opt/omnia/repo_manager/output/<project_name>/`.

### Runtime Paths

| Field | Required | Description | Default |
|-------|----------|-------------|---------|
| `shared_path` | No | Where image_build_manager stores runtime output on target | `/opt/omnia/image_build_manager` |

### Report Settings

| Field | Required | Description | Default |
|-------|----------|-------------|---------|
| `report_path` | No | Directory for test reports (relative or absolute) | `reports` |
| `report_name` | No | Base name for report files (no extension) | `image_build_test_report` |
| `report_id` | No | Custom report ID. Empty = auto-generated timestamp. | `""` |

---

## Example — Minimal Remote Setup

```yaml
oim_server_ip: "10.20.0.100"
oim_ssh_user: root
clone_path: "/root/image-build-manager"
dataset: "data_set_01"
sync_image_build_input: true
sync_output: false
```

## Example — Local Mode

```yaml
oim_server_ip: ""
dataset: "data_set_01"
sync_image_build_input: false
sync_output: false
```
