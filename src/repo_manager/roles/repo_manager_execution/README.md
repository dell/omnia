# Repo Manager execution role

## Description

Executes resolved Repo Manager catalog contexts sequentially. The role prepares
repository access, validates each context, downloads its artifacts, records the
result, and stops before later OS versions when a context fails.

## Requirements

- Ansible Core 2.20 or later
- Python 3.12 or later
- A catalog context produced by `omnia.repo_manager.resolve_catalog_context`
- A reachable Pulp service for download operations

## Role variables

- `catalog_execution_contexts`: ordered contexts to execute
- `resync_repos`: optional repository resynchronization selection
- `run_subscription_check`: enables host repository-access preparation
- `repo_manager_log_dir`: root directory for context logs

The role publishes `catalog_execution_results` and `final_status` for status
generation and calling playbooks.

## Dependencies

The role invokes the `repository_access`, `validation`, and
`parse_and_download` roles as part of the existing execution flow.

## Example usage

```yaml
- name: Execute Repo Manager catalog contexts
  ansible.builtin.include_role:
    name: omnia.repo_manager.repo_manager_execution
```

## License

Apache-2.0

## Author information

Dell Technologies
