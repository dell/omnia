# validate_install_os_config

Loads `install_os_config.yml`, applies requirements for the active direct
playbook mode, and publishes facts consumed by ISO creation and delivery.

## Modes

| Mode | Required values |
|------|-----------------|
| `credentials` only | Config validation is skipped |
| `build_iso` | `source_iso_path`, `custom_iso_path`, SSH public key |
| `deploy` | `custom_iso_path`, `target_bmc_ip`, `target_admin_ip` |
| `generate_ks` | `source_iso_path`, SSH public key |
| No direct tag | Build and deploy requirements |

`custom_iso_path` must contain NFS URI syntax (`server:/path/file.iso`).
`kickstart_delivery_method` must be `embedded` or `nfs`, and
`target_architecture` must be `x86_64` or `aarch64` when supplied.

## Input Fields

The role consumes all fields documented in
`docs/contracts/input-contract.md`, including ISO paths, Kickstart selection,
target addresses, network settings, disk/timezone settings, rebuild controls,
and SSH verification controls.

## Published Facts

| Fact | Purpose |
|------|---------|
| `_nfs_server`, `_nfs_full_path`, `_nfs_dir`, `_nfs_iso_filename` | Parsed custom ISO URI |
| `_local_iso_dir`, `_local_iso_path` | Existing local NFS mount resolution for deploy mode |
| `os_arch` | Explicit or ISO-filename-derived architecture |
| `ks_hostname`, `ks_static_ip`, `ks_netmask`, `ks_gateway`, `ks_dns` | Kickstart network settings |
| `ks_network_device`, `ks_timezone`, `ks_install_disk` | Additional Kickstart settings |

When no architecture is supplied or identified in the source filename, the
implementation falls back to `x86_64`.

## Usage

```bash
cd src/utils
ansible-playbook playbooks/install_os.yml --tags build_iso
ansible-playbook playbooks/install_os.yml --tags deploy
ansible-playbook playbooks/install_os.yml --tags generate_ks
```

The role validates values and resolves mounted paths. Source ISO existence and
checksum are handled by `fetch_iso`; iDRAC and target reachability are handled
by `iso_delivery`.

## Dependencies

None.

## License

Apache License, Version 2.0
