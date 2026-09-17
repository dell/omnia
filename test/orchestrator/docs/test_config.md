# Orchestrator `test_config.yml` reference

| Field | Type | Default | Purpose |
|---|---|---|---|
| `oim_server_ip` | string | `""` | Empty runs on the local OIM; otherwise use SSH/Testinfra |
| `oim_ssh_user` | string | `root` | Remote SSH user |
| `oim_ssh_port` | integer | `22` | Remote SSH port |
| `clone_path` | absolute path | `/omnia` | Remote checkout used to execute playbooks |
| `dataset` | string | `""` | Generated folder below `datasets/`; empty uses source fallbacks |
| `sync_orchestrator_input` | boolean | `false` | Sync dataset `input/` |
| `sync_repo_manager_output` | boolean | `false` | Sync `repo_manager_output/repo_status.yml` |
| `sync_image_build_manager_output` | boolean | `false` | Sync `image_build_manager_output/build_status.yml` |
| `catalog_path` | path | `""` | Optional explicit catalog for feature detection |
| `report_path` | path | `/opt/omnia/reports` | Remote-mode report destination |
| `report_name` | string | `orchestrator_test_report` | Report basename |
| `report_id` | string | `""` | Optional stable report identifier |

Generate a dataset with the PR #5220 generator before selecting it:

```bash
cd test/orchestrator/datasets/generator
./generate_dataset.py slurm_only slurm_only
```

Synchronization is opt-in. With every sync flag false, verification reads the
state already present on the target and does not overwrite runtime inputs or
upstream handoffs.

## Runtime project and paths

Orchestrator follows the same environment-owned runtime contract as Repo
Manager, Image Build Manager, and Telemetry. The target file
`/etc/omnia/omnia.env` is authoritative.

The Orchestrator data root is resolved in this order:

1. `ORCHESTRATOR_DATA_PATH`, when set.
2. `$OMNIA_DATA_PATH/orchestrator`.

The project is selected by `OMNIA_PROJECT_NAME`. Installed Omnia environments
normally define all required values in `/etc/omnia/omnia.env`.

```bash
source /etc/omnia/omnia.env
echo "$ORCHESTRATOR_DATA_PATH"
echo "$OMNIA_PROJECT_NAME"
```

`test_config.yml` controls test connectivity, datasets, synchronization, and
reporting only. It does not override the installed runtime project or paths.

Dataset synchronization uses the same target environment. Repo Manager and
Image Build Manager handoffs also honor `REPO_MANAGER_DATA_PATH` and
`IMAGE_BUILD_MANAGER_DATA_PATH` before falling back below `OMNIA_DATA_PATH`.

Create or update the selected project's encrypted credential store with:

```bash
source /etc/omnia/omnia.env
./setup_env.sh --set-domain-creds
```

Missing, relative, root-level, or path-like project values fail with an
actionable error before verification or synchronization proceeds.
