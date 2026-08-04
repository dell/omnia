# telemetry_setup

Initial setup for the telemetry domain. Creates log and output directories,
loads telemetry configuration, displays usage information, and sets the
`telemetry_setup_done` guard fact.

This role should run first (tag: `always`) before any other telemetry role.

## Requirements

- Ansible >= 2.20
- RHEL/Rocky Linux 9.x or 10.x

## Role Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `telemetry_log_dir` | `/var/log/omnia/telemetry` | Ansible log directory |
| `telemetry_output_dir` | `<omnia_data_path>/telemetry/output` | Output/status file directory |
| `telemetry_config_file` | `<input_project_dir>/telemetry/telemetry_config.yml` | Main config file |

## Dependencies

None.

## Example Playbook

```yaml
- hosts: localhost
  connection: local
  roles:
    - role: omnia.telemetry.telemetry_setup
      tags: always
```

## License

Apache-2.0

## Author Information

Dell Technologies (<omnia-support@dell.com>)
