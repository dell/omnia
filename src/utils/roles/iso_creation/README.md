# iso_creation

Builds a custom x86_64 or aarch64 installation ISO using a generated or
user-provided Kickstart file and writes the artifacts to an NFS export.

## Requirements

- Validated `install_os_config.yml` facts
- Existing local source ISO
- Reachable NFS export from `custom_iso_path`
- `xorriso` and `implantisomd5` (prepared by `fetch_iso`)

## Behavior

1. Validate NFS server/path values.
2. Reuse a matching NFS mount or mount the export at `/tmp/install_os_nfs`.
3. Resolve the custom ISO, `kickstart.ks`, and `install_os_manifest.yml` paths.
4. Skip an existing ISO unless `rebuild_iso: true`.
5. Render the built-in `rhel10` Kickstart or process `kickstart_file`.
6. Build either an embedded-Kickstart ISO or an ISO whose GRUB config points to
   the NFS-hosted Kickstart.
7. Unmount only the NFS mount created by this role.

## Key Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `source_iso_path` | Required upstream fact | Local source ISO |
| `custom_iso_path` | Required upstream fact | `server:/path/file.iso` destination |
| `kickstart_delivery_method` | `embedded` | `embedded` or `nfs` |
| `kickstart_file` | `""` | Optional user-provided Kickstart |
| `kickstart_template` | `rhel10` | Built-in template name |
| `rebuild_iso` | `false` | Rebuild an existing destination ISO |
| `nfs_kickstart_filename` | `kickstart.ks` | Generated Kickstart name |
| `manifest_filename` | `install_os_manifest.yml` | Build manifest name |

Network, hostname, disk, timezone, root-password hash, and SSH-key Kickstart
facts are supplied by the validation and credential roles.

## Usage

```bash
cd src/utils
ansible-playbook playbooks/install_os.yml --tags build_iso
```

## Dependencies

Normally preceded by `validate_install_os_config`,
`collect_install_os_credentials`, and `fetch_iso`.

## License

Apache License, Version 2.0
