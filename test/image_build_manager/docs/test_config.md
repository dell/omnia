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

No SSH or clone setting is used, and project sync does not run. Optional input
and repo-manager-output sync still run locally when their flags are enabled.
Tests and playbooks use the current Omnia checkout.

### Remote Mode

Run tests against a remote OIM server over SSH.

```yaml
oim_server_ip: "<target_ip>"   # MANDATORY — target server IP
oim_ssh_user: root              # SSH user (default: root)
oim_ssh_port: 22                # SSH port (default: 22)
clone_path: "/omnia"            # MANDATORY — absolute path on target
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
| `dataset` | No | Empty selects canonical `src/` files as optional sync sources. A name selects only that generated dataset's `input/` and `repo_manager_output/`. | `""` |

**Empty dataset (`dataset: ""`)**: With sync disabled, the playbook reads the
files already present under the target's
`$OMNIA_DATA_PATH/image_build_manager/input/<project>/`. With a sync option
enabled, the corresponding canonical `src/image_build_manager` example is the
local source.

**Generated dataset (`dataset: "<name>"`)**: Create using the
[dataset generator](../datasets/generator/README.md), then set the name here:

```bash
cd datasets/generator/
./generate_dataset.py profiles
./generate_dataset.py create my_dataset --profile internet-config
```

Setting the name does not itself copy files to the target. Enable the relevant
sync option below for the scenario being executed.

### Sync Options

| Field | Required | Description | Default |
|-------|----------|-------------|---------|
| `sync_image_build_input` | No | Push input files to target before tests | `false` |
| `sync_output` | No | Push repo_manager_output to target | `false` |

When `sync_image_build_input: true`, a non-empty dataset name syncs only
`datasets/<name>/input/`; an empty name syncs canonical
`src/image_build_manager/input/`. The destination is
`<OMNIA_DATA_PATH>/image_build_manager/input/<project_name>/` on the execution
OIM. Credential files, keys, and backups are excluded.

When `sync_output: true`, a non-empty dataset name syncs only
`datasets/<name>/repo_manager_output/`; an empty name syncs the canonical
`src/image_build_manager/samples/repo_manager_output/` directory. The remote
path is derived from `repo_manager_output_path` in `image_build_config.yml`.

### Credentials

`./setup_env.sh --set-creds` configures only the SSH password used to reach a
remote OIM. S3/MinIO and optional ARM values use the separate encrypted domain
credential store:

```bash
./setup_env.sh --set-domain-creds
```

Run that command from `test/image_build_manager` directly on the execution OIM
with its `OMNIA_DATA_PATH` and `OMNIA_PROJECT_NAME` set for the runtime project.
For remote execution, SSH to the target OIM and run it there. The framework
never syncs the encrypted credential file, vault key, or backups. Domain values
are never read from `test_creds.yml` or copied from a dataset. Full cleanup
removes the runtime credential pair, so configure it again before the next
credential-dependent run.

### Report Settings

| Field | Required | Description | Default |
|-------|----------|-------------|---------|
| `report_path` | No | Directory for test reports (relative or absolute) | `/opt/omnia/reports` |
| `report_name` | No | Base name for report files (no extension) | `image_test_report` |
| `report_id` | No | Custom report ID. Empty = auto-generated timestamp. | `""` |

---

## Example — Remote Setup (empty dataset, target has input files)

```yaml
oim_server_ip: "<target_ip>"
oim_ssh_user: root
clone_path: "/omnia"
dataset: ""
sync_image_build_input: false
sync_output: false
```

## Example — Remote Setup (generated dataset)

```yaml
oim_server_ip: "<target_ip>"
oim_ssh_user: root
clone_path: "/omnia"
dataset: "my_dataset"
sync_image_build_input: true
sync_output: true
```

## Example — Local Mode

```yaml
oim_server_ip: ""
dataset: ""
sync_image_build_input: false
sync_output: false
```

---

## Environment Prerequisites

Before running tests, the target server must have the following environment
variables set (installed by `omnia.sh --setup-venv`):

| Variable | Required | Validation | Description |
|----------|----------|------------|-------------|
| `SYSTEM_ADMIN_NIC_IPV4` | Yes | `hostname -I` | Admin NIC IPv4 — must be assigned to a local interface |
| `SYSTEM_HOSTNAME` | Yes | `hostname -s` | Short hostname — must match system short hostname |
| `SYSTEM_DOMAIN_NAME` | Yes | `hostname -d` | Domain name — validated against system domain |
| `OMNIA_DATA_PATH` | Yes | `stat` | Root data directory (default: `/opt/omnia`) |
| `OMNIA_PROJECT_NAME` | Yes | — | Project name (default: `project_default`) |
| `OMNIA_VERSION` | Yes | — | Omnia release version |

### Verifying Environment

Use the precheck scenario to validate the full environment:

```bash
# Via test automation
./run_validation.sh fvt_image_build_manager precheck verify --marker sanity

# Via playbook
cd src/image_build_manager/playbooks
ansible-playbook image_build_manager.yml --tags precheck
```

The precheck validates (same checks as `omnia.sh validate_env()`):
1. SSH connectivity to the target
2. All required env vars are set
3. Short hostname (`hostname -s`) matches `SYSTEM_HOSTNAME`
4. Domain (`hostname -d`) matches `SYSTEM_DOMAIN_NAME`
5. Admin IP is one of the IPs on the server (`hostname -I`)
6. `omnia.sh --setup-venv` has been run (`/etc/omnia/omnia.env` exists)
