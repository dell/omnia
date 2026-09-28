# generate_inventories

Generates the Ansible and BMC inventory artifacts consumed after OpenCHAMI
node registration.

## What It Does

- Loads the generated functional-group configuration and classification rules.
- Reads mapping rows after their permanent SMD XNAMEs have been resolved.
- Adds Kubernetes virtual-IP data only when the mapped cluster and valid HA
  configuration require it.
- Renders `orchestrator_inventory.yml` and `bmc_group_data.csv`.
- Copies the generated artifacts to the project output directory on localhost.

## Requirements

- Nodes registered in SMD and the in-memory mapping populated with XNAMEs.
- `functional_groups_config.yml` generated for the active project.
- Orchestrator output paths and permission facts established by setup.
- Access to the shared inventory templates under `configure_ochami`.

## Role Variables

The role consumes `read_mapping_file`, `functional_groups_config_path`,
`input_project_dir`, `orchestrator_output_dir`, and permission facts from
`localhost`. It has no role-local defaults or variable file.

## Dependencies

No automatic dependency is declared in `meta/main.yml`. Provision validation
invokes this role after registration and identity resolution.

## Example

```yaml
- hosts: oim
  roles:
    - generate_inventories
```

## Outputs

| File | Purpose |
|------|---------|
| `orchestrator_inventory.yml` | Cluster inventory for downstream configuration and validation |
| `bmc_group_data.csv` | BMC-oriented node mapping for supported consumers |

## License

Apache-2.0
