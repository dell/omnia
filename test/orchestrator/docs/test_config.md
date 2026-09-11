# Orchestrator `test_config.yml` reference

| Field | Type | Default | Purpose |
|---|---|---|---|
| `oim_server_ip` | string | `""` | Empty runs on the local OIM; otherwise use SSH/Testinfra |
| `oim_ssh_user` | string | `root` | Remote SSH user |
| `oim_ssh_port` | integer | `22` | Remote SSH port |
| `clone_path` | absolute path | `/omnia` | Remote checkout used to execute playbooks |
| `dataset` | string | `""` | Generated folder below `datasets/`; empty uses source fallbacks |
| `project_name` | string | `project_default` | Target Omnia project |
| `sync_orchestrator_input` | boolean | `false` | Sync dataset `input/` |
| `sync_repo_manager_output` | boolean | `false` | Sync `repo_manager_output/repo_status.yml` |
| `sync_image_build_manager_output` | boolean | `false` | Sync `image_build_manager_output/build_status.yml` |
| `shared_path` | absolute path | `/opt/omnia/orchestrator` | Target Orchestrator data root |
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
