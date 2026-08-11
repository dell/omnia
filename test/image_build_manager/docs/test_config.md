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
oim_server_ip: "<target_ip>"   # MANDATORY — target server IP
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

### Project Sync (Remote only)

| Field | Required | Description | Default |
|-------|----------|-------------|---------|
| `clone_path` | Remote only | Absolute path on target where the omnia monorepo is synced (rsync). In local mode, the playbook path is resolved automatically from the source tree. | `/omnia` |
| `venv_path` | No | Python venv path on target. If set, activated before `ansible-playbook`. Leave empty to use system-wide ansible. | `""` |

### Dataset

| Field | Required | Description | Default |
|-------|----------|-------------|---------|
| `dataset` | No | Empty = use `src/` files directly. Set to a dataset folder name for custom inputs. | `""` |
| `project_name` | No | Omnia project name on the target. Must match `OMNIA_PROJECT_NAME` env var. Used for input/output path resolution. | `"project_default"` |

When `dataset` is empty (default), input files are read from `src/image_build_manager/input/`
and `src/image_build_manager/samples/repo_manager_output/`. For custom datasets,
generate one with `datasets/generator/generate_dataset.py`.

### Sync Options

| Field | Required | Description | Default |
|-------|----------|-------------|---------|
| `sync_image_build_input` | No | Push input files to target before tests | `false` |
| `sync_output` | No | Push repo_manager_output to target | `false` |

When `sync_image_build_input: true`, the framework syncs input files
(from `src/` or the configured dataset) to the target server at
`<OMNIA_DATA_PATH>/image_build_manager/input/<project_name>/`.

When `sync_output: true`, the framework syncs `repo_manager_output/`
to the target. The remote path is derived from `repo_manager_output_path`
in `image_build_config.yml`.

### Report Settings

| Field | Required | Description | Default |
|-------|----------|-------------|---------|
| `report_path` | No | Directory for test reports (relative or absolute) | `/opt/omnia/reports` |
| `report_name` | No | Base name for report files (no extension) | `image_test_report` |
| `report_id` | No | Custom report ID. Empty = auto-generated timestamp. | `""` |

---

## Example — Minimal Remote Setup

```yaml
oim_server_ip: "<target_ip>"
oim_ssh_user: root
clone_path: "/omnia"
dataset: ""
project_name: "project_default"
sync_image_build_input: true
sync_output: false
```

## Example — Local Mode

```yaml
oim_server_ip: ""
dataset: ""
sync_image_build_input: false
sync_output: false
```

## Example — Custom Dataset

```yaml
oim_server_ip: "<target_ip>"
oim_ssh_user: root
clone_path: "/omnia"
dataset: "my_custom_ds"
project_name: "project_default"
sync_image_build_input: true
sync_output: true
```
