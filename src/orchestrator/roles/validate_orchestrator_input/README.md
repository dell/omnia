# validate_orchestrator_input

Canonical L1 schema and L2 logic validation role for Orchestrator inputs.

The role validates `orchestrator_config.yml`, `omnia_config.yml`,
`network_spec.yml`, the resolved PXE mapping CSV, and `storage_config.yml`
when present. It also validates `high_availability_config.yml` when
Kubernetes functional groups are selected and validates the additional
cloud-init file when one is configured.

Workload-specific checks follow the functional groups selected in the PXE
mapping. Storage configuration and referenced `nfs_storage_name` or
`vast_storage_name` entries are therefore required only for selected Slurm or
Kubernetes workloads. High-availability cluster, virtual-IP, subnet, DHCP,
and external-pool relationships are checked before provisioning.

System availability checks such as NFS reachability, S3 image access, and OIM
connectivity belong to `orchestrator_validations`, not this role.

## Requirements

- Active project input directory containing `orchestrator_config.yml`.
- Python dependencies required by the validation module installed in the Omnia
  virtual environment.
- Schema files under `plugins/module_utils/orchestrator_validation/schema/`.

## Role Variables

See `vars/main.yml` and `defaults/main.yml` for available variables.

## Dependencies

No automatic dependency is declared in `meta/main.yml`. This role invokes the
`validate_orchestrator_config` module.

## Example

```yaml
- hosts: localhost
  connection: local
  roles:
    - validate_orchestrator_input
```

The normal route is `orchestrator.yml --tags validate`.

## License

Apache-2.0
