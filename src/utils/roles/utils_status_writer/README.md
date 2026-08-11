# utils_status_writer

Writes domain execution status and results to the status file contract.

## Description

This role records the execution status, results, and any errors/warnings from utils domain playbooks. It implements the status file contract required for integration with `omnia.sh` orchestration framework.

## Requirements

- Write access to `${OMNIA_DATA_PATH}/utils/` directory
- Execution context from parent playbook

## Role Variables

Available variables are listed below, along with default values (see `defaults/main.yml`):

```yaml
# Status information
utils_domain_status: "success"  # success, failure, in_progress
utils_playbook_name: ""
utils_execution_start_time: ""
utils_execution_end_time: ""

# Results tracking
utils_role_results: []
utils_execution_errors: []
utils_execution_warnings: []

# Status file location
utils_status_file_path: "{{ omnia_data_path }}/utils/utils_status.yml"
```

## Dependencies

None.

## Example Playbook

```yaml
- hosts: localhost
  connection: local
  gather_facts: true
  pre_tasks:
    - name: Record playbook start time
      ansible.builtin.set_fact:
        utils_execution_start_time: "{{ ansible_date_time.iso8601 }}"

  roles:
    - role: some_utility_role

  post_tasks:
    - name: Record playbook end time
      ansible.builtin.set_fact:
        utils_execution_end_time: "{{ ansible_date_time.iso8601 }}"

    - name: Write execution status
      ansible.builtin.include_role:
        name: utils_status_writer
      vars:
        utils_domain_status: "{{ 'success' if not ansible_failed_result else 'failure' }}"
        utils_playbook_name: "collect.yml"
```

## Tasks

- `main.yml` - Main orchestration
- `write_status_file.yml` - Write status file in YAML format
- `validate_status_file.yml` - Validate status file structure

## License

Apache 2.0

## Author Information

Dell Technologies Omnia Team
