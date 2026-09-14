# Catalog role

## Description

Generates, updates, transforms, and validates Repo Manager catalog files.
The requested operation is selected through the catalog operation tags.

## Requirements

- Ansible Core 2.20 or later
- Python 3.12 or later
- A catalog input file for add, delete, generate, and transform operations

## Role variables

- `catalog_file`: catalog output or validation path
- `schema_file`: catalog schema path
- `input_file`: operation input supplied by the caller
- `catalog_name`: name used when generating a catalog
- `default_arch`: default package architecture
- `default_os`: default operating-system family
- `default_os_version`: default operating-system version
- `force`: permits replacement during catalog generation
- `validate_after`: validates a catalog after an update

Defaults are documented in `defaults/main.yml`. Error and success messages are
defined in `vars/main.yml`.

## Dependencies

None.

## Example usage

```yaml
- name: Validate a Repo Manager catalog
  ansible.builtin.include_role:
    name: omnia.repo_manager.catalog
  tags:
    - catalog_validate
```

## License

Apache-2.0

## Author information

Dell Technologies
