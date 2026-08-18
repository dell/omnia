# provision_common

Common provisioning role shared by all category-specific provisioning playbooks (`provision_kubernetes.yml`, `provision_slurm.yml`, `provision_os.yml`, `provision_custom.yml`). Handles SMD node registration, BSS boot parameters, cloud-init configuration, DNS setup, and SELinux context management.

## Requirements

- OpenCHAMI services must be deployed and healthy.
- `functional_groups_config.yml` must be generated.

## Role Variables

See `vars/main.yml` for configurable paths, retry settings, and defaults.

## License

Apache-2.0
