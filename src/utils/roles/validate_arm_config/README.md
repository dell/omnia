# validate_arm_config

Legacy reusable role that verifies prerequisites for the former PXE-mapping
based aarch64 installation path.

This role is not imported by the current `playbooks/utils.yml` or
`playbooks/install_os.yml` flows. Current aarch64 OS installation is configured
through `install_os_config.yml` and `validate_install_os_config`.

## Checks

- `pxe_mapping_file_path` exists.
- `network_spec_file` exists and loads as YAML.
- `oim_ssh_key_path` exists.
- `provision_password` is non-empty.

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `pxe_mapping_file_path` | Derived from `input_project_dir` | Legacy PXE mapping CSV |
| `network_spec_file` | Derived from `input_project_dir` | Legacy network specification |
| `oim_ssh_key_path` | `/root/.ssh/id_rsa.pub` | OIM public key |
| `provision_password` | Required caller value | Legacy provisioning password |

The role metadata declares `fetch_arm_params` as a dependency. Callers must
supply that role's required `iso_config` and inventory inputs as well.

## Dependencies

- `fetch_arm_params`

## License

Apache License, Version 2.0
