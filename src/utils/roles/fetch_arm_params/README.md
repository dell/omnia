# fetch_arm_params

Legacy reusable role that derives aarch64 OS-install facts from a PXE mapping,
ISO configuration, OIM SSH key, and provisioning password.

This role is not imported by the current `playbooks/utils.yml` or
`playbooks/install_os.yml` flows. Current OS installation obtains equivalent
values from `install_os_config.yml` through `validate_install_os_config`.

## Behavior

- Read `pxe_mapping_file_path` and select the first `os_aarch64` entry.
- Read the OIM SSH public key.
- Require `provision_password`.
- Validate or auto-detect an NFS share.
- Publish ISO, Kickstart, network, iDRAC, and execution-control facts.

## Required Caller Variables

| Variable | Description |
|----------|-------------|
| `pxe_mapping_file_path` | CSV containing `FUNCTIONAL_GROUP_NAME`, `HOSTNAME`, `BMC_IP`, and `ADMIN_IP` fields |
| `oim_ssh_key_path` | OIM public-key path |
| `provision_password` | Password used by the legacy installation flow |
| `iso_config` | Mapping containing ISO, Kickstart, network, and execution settings |

`iso_config.nfs_share_path`, when set, must use `server:/path` syntax. Otherwise
the role checks whether `OMNIA_DATA_PATH` is itself backed by NFS.

## Dependencies

None, but callers must provide the variables above and gathered mount facts.

## License

Apache License, Version 2.0
