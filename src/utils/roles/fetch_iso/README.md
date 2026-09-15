# fetch_iso

Validates a local source ISO and prepares the tooling and destination directory
required by the OS-install image-build flow.

This role does not download ISOs. `source_iso_path` must reference an existing
local file.

## Behavior

1. Verify that `source_iso_path` exists.
2. Compute and compare SHA256 when `source_iso_checksum` is set.
3. Install `xorriso` and `isomd5sum` when their commands are missing.
4. Create `iso_target_directory`.

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `iso_source_path` | Value of `source_iso_path` | Local source ISO |
| `iso_source_checksum` | Value of `source_iso_checksum` | Optional SHA256 checksum |
| `iso_target_directory` | Resolved local NFS directory or `/tmp/install_os` | Build destination |
| `required_iso_tools` | `xorriso`, `implantisomd5` | Commands and packages required for repacking |

These values are normally set by `validate_install_os_config` before this role
runs.

## Usage

```bash
cd src/utils
ansible-playbook playbooks/install_os.yml --tags build_iso
```

## Dependencies

None. Package installation requires suitable configured repositories and
privilege escalation.

## License

Apache License, Version 2.0
