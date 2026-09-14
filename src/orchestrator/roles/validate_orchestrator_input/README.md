# validate_orchestrator_input

Canonical L1 schema and L2 logic validation role for Orchestrator inputs.

The role validates `orchestrator_config.yml`, `network_spec.yml`, the resolved
PXE mapping CSV, and `storage_config.yml` when present. Storage configuration
is required when `omnia_config.yml` references an `nfs_storage_name` or
`vast_storage_name`.

System availability checks such as NFS reachability, S3 image access, and OIM
connectivity belong to `orchestrator_validations`, not this role.

## Role Variables

See `vars/main.yml` and `defaults/main.yml` for available variables.

## License

Apache-2.0
