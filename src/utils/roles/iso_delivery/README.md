# iso_delivery

Deploys an existing NFS-hosted custom ISO to a Dell server through iDRAC
virtual media and optionally verifies the installed system over SSH.

## Requirements

- Dell iDRAC reachable over HTTPS with virtual-media capability
- BMC credentials loaded by `collect_install_os_credentials`
- `custom_iso_path` resolved to both an NFS URI and an existing local mount path
- Target admin IP reachable after installation

## Behavior

1. Verify the custom ISO exists on the local NFS mount.
2. Abort when the target is already reachable unless `force_reinstall` is true.
3. Validate iDRAC Redfish access.
4. Eject existing media, attach the NFS ISO, set one-time UEFI CD boot, and
   force-restart the server.
5. Wait for SSH, verify key-only root access, and read installed OS details when
   `ssh_verify_enabled` is true.
6. Eject virtual media after installation.

## Key Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `target_bmc_ip` | Required | iDRAC address |
| `target_admin_ip` | Required | Installed-system address |
| `bmc_username` | Loaded host fact | iDRAC user |
| `bmc_password` | Loaded host fact | iDRAC password |
| `force_reinstall` | `false` | Permit deployment to an SSH-reachable target |
| `ssh_verify_enabled` | `true` | Wait for and validate SSH after installation |
| `ssh_verify_retries` | `60` | Verification attempt budget used to calculate timeout |
| `ssh_verify_delay` | `30` | Initial/retry delay in seconds |

The resolved `_nfs_server`, `_nfs_full_path`, and `_local_iso_path` facts come
from `validate_install_os_config` and the ISO build/mount flow.

## Usage

```bash
cd src/utils
ansible-playbook playbooks/install_os.yml --tags deploy
```

## Dependencies

Normally preceded by `validate_install_os_config` and
`collect_install_os_credentials`.

## License

Apache License, Version 2.0
