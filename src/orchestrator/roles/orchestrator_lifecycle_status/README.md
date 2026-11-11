# orchestrator_lifecycle_status

Persist canonical Orchestrator lifecycle reports returned by the
`orchestrator_status_reconcile` module.

## Required input

`orchestrator_lifecycle_status_result` must contain:

- `orchestrator_status`
- `failed_nodes_report`

## Requirements

`orchestrator_output_dir` must identify the current project output directory.

## Role variables

Artifact names and permissions are internal constants in `vars/main.yml`.

## Output

The role writes these project-scoped artifacts under
`orchestrator_output_dir`:

- `orchestrator_status.yml`
- `failed_nodes.json`

File names and permissions are internal constants in `vars/main.yml`. The
role performs no lifecycle calculation; it only validates and persists the
module result.

## Dependencies

None.

## Example playbook

```yaml
- name: Persist lifecycle status
  hosts: localhost
  connection: local
  roles:
    - role: orchestrator_lifecycle_status
      orchestrator_lifecycle_status_result: "{{ lifecycle_status }}"
```

## License

Apache 2.0
