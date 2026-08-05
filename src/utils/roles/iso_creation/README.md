# iso_creation

Creates custom OS installation ISO images with Kickstart automation for bare-metal provisioning.

## Description

This role modifies standard OS ISO images by injecting custom Kickstart files, creating NFS-bootable ISOs, and repacking ISO files for automated bare-metal installations. It supports both x86_64 and aarch64 architectures.

## Requirements

- Standard OS ISO image (RHEL, Rocky Linux, etc.)
- Kickstart configuration file
- `xorriso` and `isoinfo` tools for ISO manipulation
- Sufficient disk space for ISO extraction and rebuilding

## Role Variables

Available variables are listed below, along with default values (see `vars/main.yml`):

```yaml
# ISO source and target paths
iso_source_path: "/path/to/source.iso"
iso_custom_path: "/path/to/custom.iso"

# Kickstart configuration
kickstart_file: "ks.cfg"
user_kickstart_content: ""

# Build options
build_nfs_iso: false
inject_kickstart: true
```

## Dependencies

None.

## Example Playbook

```yaml
- hosts: localhost
  connection: local
  gather_facts: false
  roles:
    - role: iso_creation
      vars:
        iso_source_path: "/opt/isos/rhel-10.0-x86_64-dvd.iso"
        iso_custom_path: "/opt/isos/rhel-10.0-custom.iso"
        kickstart_file: "node-ks.cfg"
        inject_kickstart: true
```

## Tasks

- `main.yml` - Main orchestration
- `inject_user_kickstart.yml` - Inject custom Kickstart files
- `build_nfs_iso.yml` - Create NFS-bootable ISO variants
- `repack_iso.yml` - Repackage ISO with modifications

## License

Apache 2.0

## Author Information

Dell Technologies Omnia Team
