# repo_manager_setup

## Description

Loads Repo Manager environment variables, derives runtime paths, validates
catalog prerequisites for catalog-consuming operations, and publishes catalog
execution-context facts.

## Requirements

- Ansible >= 2.14
- Python >= 3.9

## Role Variables

Required environment variables:

- `SYSTEM_ADMIN_NIC_IPV4`: IPv4 address assigned to an OIM interface.
- `CATALOG_FILE_PATH`: absolute path to the selected catalog JSON file.

Optional environment variables:

- `OMNIA_DATA_PATH`: Omnia data root; defaults to `/opt/omnia`.
- `REPO_MANAGER_DATA_PATH`: Repo Manager runtime root.
- `OMNIA_PROJECT_NAME`: project name; defaults to `project_default`.
- `REPO_MANAGER_INPUT_PROJECT_DIR`: explicit project input directory.

Catalog-consuming playbooks use `tasks_from: resolve_catalog_context.yml`.
That task validates `CATALOG_FILE_PATH` before calling the resolver and exports
`catalog_context`, `catalog_execution_contexts`, `cluster_os_type`,
`cluster_os_version`, and `selected_architectures`.

## Dependencies

None.

## Example Playbook

```yaml
- hosts: localhost
  roles:
    - role: repo_manager_setup
```

## License

Apache-2.0

## Author Information

Dell Technologies
