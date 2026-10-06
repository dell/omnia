# orchestrator_setup

Bootstrap role executed under the `always` tag. It establishes the complete
project and lifecycle context required by later Orchestrator plays.

## What It Does

1. Validates public tags and rejects incompatible combinations.
2. Resolves system identity, data paths, project name, and domain paths from
   the installed environment.
3. Initializes missing project inputs from source templates without
   overwriting an existing project directory.
4. Validates project inputs before consuming their fields.
5. Loads Orchestrator and Omnia cluster configuration.
6. Selects the deployed Kubernetes and Slurm configurations and derives
   feature flags.
7. Loads and validates Repository Manager output when required by the flow.
8. Loads the catalog and derives OS/version and feature facts when required.
9. Creates the dynamic `oim` group when requested.
10. Refreshes `orchestrator_state.yml` only when a stateful lifecycle phase
    loads the catalog. Catalog-independent operational phases preserve the
    previously derived feature flags.

## Requirements

- A sourced Omnia environment or valid values in `/etc/omnia/omnia.env`.
- Source input templates available when the project has not been initialized.
- Repository Manager and catalog artifacts for tags that consume them.

## Role Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `openchami_vars_support` | false | Load shared OpenCHAMI variables |
| `oim_group` | false | Add the configured OIM to dynamic inventory |
| `orchestrator_initialize_state` | Derived from tags | Override state initialization decision |

Supported tags, dependency requirements, default paths, and invalid tag
combinations are defined in `vars/main.yml`.

## Outputs

The role publishes project paths, configuration, repository, catalog, feature,
and OIM facts. Catalog-backed stateful phases also write:

```text
<ORCHESTRATOR_DATA_PATH>/output/<project>/orchestrator_state.yml
```

PXE-only, external node-registration verification, cleanup, and other
catalog-independent operational flows do not refresh this file. They preserve
the feature decisions produced by the latest catalog-backed lifecycle phase,
preventing fallback values from disabling OpenLDAP or Kubernetes support.

## Dependencies

No automatic dependency is declared in `meta/main.yml`; this is the first role
in the top-level workflow. It invokes input validation when required.

## Example

```yaml
- hosts: localhost
  connection: local
  roles:
    - role: orchestrator_setup
      vars:
        openchami_vars_support: true
        oim_group: true
```

## License

Apache-2.0
