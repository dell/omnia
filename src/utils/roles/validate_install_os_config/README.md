# validate_install_os_config

Validates configuration parameters for OS installation operations based on execution mode.

## Description

This role performs comprehensive validation of `install_os_config.yml` parameters, ensuring that all required fields are present and correctly formatted based on the active execution mode. It supports multiple execution modes with different validation requirements:

- **build_iso**: Validates ISO building parameters (source ISO, custom ISO path)
- **deploy**: Validates deployment parameters (custom ISO, target BMC, target admin IP)
- **generate_ks**: Validates kickstart generation parameters (source ISO for arch detection)
- **credentials_only**: Skips config validation (credential collection only)
- **default**: Validates all parameters for end-to-end execution

## Requirements

- Valid `install_os_config.yml` file in the project input directory
- SSH public key for kickstart injection (required for build/generate modes)
- NFS server access for custom ISO storage

## Role Variables

The role loads configuration from `install_os_config.yml` and sets the following variables:

### Input Configuration (from install_os_config.yml)

```yaml
# ISO paths
source_iso_path: "/path/to/source.iso"
source_iso_checksum: "sha256:checksum"
custom_iso_path: "nfs-server:/path/to/custom.iso"

# Kickstart configuration
kickstart_delivery_method: "embedded"  # or "nfs"
kickstart_file: "/path/to/kickstart.ks"
kickstart_template: "rhel10"

# Target node configuration
target_bmc_ip: "192.168.1.100"
target_hostname: "node01"
target_admin_ip: "192.168.1.101"
target_architecture: "x86_64"  # or "aarch64"

# Network configuration
network_device: "eth0"
netmask: "255.255.255.0"
gateway: "192.168.1.1"
dns_server: "192.168.1.1"

# Installation parameters
install_disk: "sda"
timezone: "UTC"

# Build options
rebuild_iso: false
force_reinstall: false

# SSH verification
ssh_verify_enabled: true
ssh_verify_retries: 60
ssh_verify_delay: 30

# SSH key path
ssh_public_key_path: "/root/.ssh/id_rsa.pub"
```

### Output Variables (set by this role)

```yaml
# Resolved paths and components
_nfs_server: "nfs-server"
_nfs_dir: "/path/to"
_nfs_iso_filename: "custom.iso"
_local_iso_path: "/local/mount/path/custom.iso"

# Architecture detection
os_arch: "x86_64"  # auto-detected from ISO filename

# Kickstart variables
ks_hostname: "node01"
ks_static_ip: "192.168.1.101"
ks_netmask: "255.255.255.0"
ks_gateway: "192.168.1.1"
ks_dns: "192.168.1.1"
ks_network_device: "eth0"
ks_timezone: "UTC"
ks_install_disk: "sda"
```

## Dependencies

None.

## Example Playbook

```yaml
- name: Validate OS installation configuration
  hosts: localhost
  connection: local
  gather_facts: true
  tags: [build_iso, deploy, generate_ks]
  roles:
    - role: validate_install_os_config
```

## Validation Logic

The role determines execution mode from Ansible tags and validates accordingly:

### Build ISO Mode
- Requires: `source_iso_path`, `custom_iso_path`
- Validates: ISO file accessibility, SSH public key
- Auto-detects: Architecture from ISO filename

### Deploy Mode
- Requires: `custom_iso_path`, `target_bmc_ip`, `target_admin_ip`
- Validates: NFS URI format, BMC IP connectivity
- Resolves: Local mount path from NFS mounts

### Generate Kickstart Mode
- Requires: `source_iso_path`
- Validates: SSH public key availability
- Auto-detects: Architecture for kickstart template

### Credentials Only Mode
- Skips: All configuration validation
- Purpose: Credential collection without config validation

## Error Messages

The role provides descriptive error messages for common validation failures:

- Missing configuration file
- Invalid kickstart delivery method
- Malformed NFS URI in custom_iso_path
- Missing source ISO for build operations
- Missing target BMC/admin IP for deploy operations
- Invalid architecture (must be x86_64 or aarch64)
- Missing SSH public key

## NFS Path Handling

The role automatically resolves NFS paths to local mount points:

1. Parses `custom_iso_path` into server and path components
2. Queries system mount table for existing NFS mounts
3. Maps remote NFS export to local mount directory
4. Resolves full local path for ISO access

## Architecture Detection

If `target_architecture` is not specified, the role auto-detects architecture from the source ISO filename using pattern matching for `x86_64` or `aarch64`.

## License

Apache 2.0

## Author Information

Dell Technologies Omnia Team
