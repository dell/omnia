# orchestrator_functional_groups

Generates the normalized functional-group configuration consumed by
validation and category-specific provisioning.

## What It Does

- Loads `orchestrator_config.yml` for the selected project.
- Reads the resolved PXE mapping without requiring an XNAME column.
- Classifies functional groups using
  `vars/functional_group_classification.yml`.
- Writes `.data/functional_groups_config.yml` under the project output path.
- Supports check mode without requiring the output file to be written.

## Requirements

- Valid project input directory and `orchestrator_config.yml`.
- A readable PXE mapping file with the required 11-column contract.
- `omnia_config.yml` available for cluster-level group context.

## Role Variables

| Variable | Purpose |
|----------|---------|
| `input_project_dir` | Active project input directory |
| `pxe_mapping_file_path` | Resolved mapping CSV |
| `functional_groups_config_path` | Generated output path |
| `omnia_config_dir` | Directory containing `omnia_config.yml` |

Internal filenames are defined in `vars/main.yml`.

## Dependencies

No automatic dependency is declared in `meta/main.yml`. The caller normally
runs `orchestrator_setup` first.

## Example

```yaml
- hosts: localhost
  connection: local
  roles:
    - orchestrator_functional_groups
```

## License

Apache-2.0
