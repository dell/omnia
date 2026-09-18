# utils_status_writer

Writes and validates the project-scoped status contract for Utils playbooks.

## Output

```text
$OMNIA_DATA_PATH/utils/output/$OMNIA_PROJECT_NAME/utils_status.yml
```

The file contains `utility`, `overall_status`, `playbook`, `version`, start/end
timestamps, and optional role results, errors, and warnings. After writing, the
role verifies that the file exists, is readable YAML, and includes required
fields.

## Variables

```yaml
utils_domain_status: "success"
utils_playbook_name: ""
utils_execution_start_time: ""
utils_execution_end_time: ""
utils_role_results: []
utils_execution_errors: []
utils_execution_warnings: []
omnia_data_path: "{{ lookup('env', 'OMNIA_DATA_PATH') | default('/opt/omnia', true) }}"
omnia_project_name: "{{ lookup('env', 'OMNIA_PROJECT_NAME') | default('project_default', true) }}"
utils_status_file_path: "{{ omnia_data_path }}/utils/output/{{ omnia_project_name }}/utils_status.yml"
```

## Usage

```yaml
- name: Write execution status
  ansible.builtin.include_role:
    name: utils_status_writer
  vars:
    utils_domain_status: "success"
    utils_playbook_name: "collect.yml"
```

The caller should set execution timestamps before invoking the role. The
`utils.yml`, collection, OS-install, cleanup, and OIM-backup flows already do
this.

## Dependencies

None.

## License

Apache License, Version 2.0
