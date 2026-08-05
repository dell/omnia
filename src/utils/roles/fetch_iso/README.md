# fetch_iso

Downloads and validates OS ISO images for bare-metal provisioning.

## Description

This role handles downloading OS ISO images from various sources (HTTP, FTP, local filesystem), validates checksums, and prepares ISO files for use in bare-metal provisioning workflows. It supports multiple architectures and OS distributions.

## Requirements

- Network access to ISO download sources (if downloading)
- Sufficient disk space for ISO storage
- Tools for checksum validation (`sha256sum`, etc.)

## Role Variables

Available variables are listed below, along with default values (see `vars/main.yml`):

```yaml
# ISO source configuration
iso_download_url: ""
iso_local_path: ""
iso_target_path: "/opt/isos/"

# Validation settings
validate_checksum: true
expected_checksum: ""
checksum_algorithm: "sha256"

# Download options
download_timeout: 3600
resume_download: true
```

## Dependencies

None.

## Example Playbook

```yaml
- hosts: localhost
  connection: local
  gather_facts: false
  roles:
    - role: fetch_iso
      vars:
        iso_download_url: "https://example.com/rhel-10.0-x86_64-dvd.iso"
        iso_target_path: "/opt/isos/rhel-10.0-x86_64-dvd.iso"
        expected_checksum: "abc123def456..."
        validate_checksum: true
```

## License

Apache 2.0

## Author Information

Dell Technologies Omnia Team
