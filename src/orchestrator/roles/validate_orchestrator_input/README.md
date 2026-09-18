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

## Role Variables

See `vars/main.yml` and `defaults/main.yml` for available variables.

## License

Apache-2.0
