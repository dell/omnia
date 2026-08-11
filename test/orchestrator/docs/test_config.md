# Orchestrator — `test_config.yml` Reference

## Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `oim_server_ip` | string | No | `""` | Target server IP. Empty = local execution |
| `oim_ssh_user` | string | No | `root` | SSH username for remote mode |
| `oim_ssh_port` | int | No | `22` | SSH port for remote mode |
| `clone_path` | string | Yes | `/root/omnia` | Repo path on target |
| `dataset` | string | Yes | `data_set_01` | Dataset folder under `datasets/` |
| `project_name` | string | Yes | `project_default` | Omnia project name on target |
| `sync_orchestrator_input` | bool | No | `true` | Sync dataset input to target |
| `sync_repo_manager_output` | bool | No | `false` | Sync repo_status.yml to target |
| `shared_path` | string | No | `/opt/omnia/orchestrator` | Domain data path |
| `report_path` | string | No | `/opt/omnia/reports` | Report output directory |
| `report_name` | string | No | `orchestrator_test_report` | Report file name |
| `report_id` | string | No | `""` | Auto-generated if empty |

## Execution Modes

- **Local mode**: Leave `oim_server_ip` empty. Tests run on the local machine.
- **Remote mode**: Set `oim_server_ip` to the target OIM server. Tests connect via SSH/Testinfra.
