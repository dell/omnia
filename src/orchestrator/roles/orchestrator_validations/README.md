# orchestrator_validations

Performs environment and availability checks that require resolved runtime
facts or external services. Structural L1/L2 input validation belongs to
`validate_orchestrator_input`.

## What It Does

- Loads required Orchestrator inputs and catalog-derived software facts.
- Confirms that mapping-based orchestration has a readable PXE mapping.
- Normalizes the mapping and validates hostname rules.
- Validates storage references and NFS reachability for selected workloads.
- Resolves Image Build Manager artifacts per functional group and verifies
  kernel, initrd, and rootfs accessibility.
- Updates the managed cluster hosts file.
- Provides focused OIM timezone, OpenLDAP container, and BuildStream checks.

## Requirements

- `orchestrator_setup` and `orchestrator_functional_groups` completed.
- Required Image Build Manager, Repository Manager, catalog, mapping, and
  storage artifacts available for the selected tag.
- Network reachability to referenced NFS and object-storage endpoints.

## Role Variables

See `vars/main.yml`; key inputs include `orchestrator_inputs`, mapping and
temporary-file paths, generated functional groups, storage paths, and image
validation messages.

## Dependencies

No automatic dependency is declared in `meta/main.yml`.

## Example

```yaml
- hosts: localhost
  connection: local
  roles:
    - orchestrator_validations
```

The supported route is `orchestrator.yml --tags precheck`.

## License

Apache-2.0
