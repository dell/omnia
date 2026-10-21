# precheck_build_stream

## Description

Environment precheck for Build Stream (`--tags precheck`). Cross-validates the
OIM host environment with `validate_system_environment`, verifies the
prepare-base containers (`pulp`, `minio-server`, `registry`) are running, and
checks that the repo_manager and image_build_manager credential files exist.
All results are summarized before the role fails on any missing prerequisite.

Build Stream consumes no upstream domain output contract; the checks cover
runtime prerequisites only. The role runs before credential collection and
does not read credential contents.

## Requirements

- Ansible >= 2.14
- Python >= 3.9
- `build_stream_setup` has run (provides `omnia_data_path` and `project_name`)

## Role Variables

See `vars/main.yml` for `required_containers` and `required_credential_files`.

## Dependencies

None.

## Example Playbook

```yaml
- hosts: localhost
  connection: local
  gather_facts: false
  roles:
    - role: precheck_build_stream
```

## License

Apache-2.0

## Author Information

Dell Technologies
