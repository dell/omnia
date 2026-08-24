# iso_delivery

Delivers custom ISO images to target systems via iDRAC virtual media for OS installation.

## Description

This role handles the delivery and deployment of custom ISO images to Dell servers through iDRAC virtual media mounting. It performs preflight checks, mounts ISO files remotely, and manages the OS installation process for bare-metal provisioning.

## Requirements

- Dell servers with iDRAC virtual media support
- Custom ISO image (created by iso_creation role)
- iDRAC credentials and network access
- Virtual media licensing (if required)

## Role Variables

Available variables are listed below, along with default values (see `vars/main.yml`):

```yaml
# ISO and deployment configuration
iso_custom_path: "/path/to/custom.iso"
virtual_media_mount: true
auto_boot_after_mount: true

# iDRAC connection settings
idrac_timeout: 600
deployment_timeout: 3600
```

## Dependencies

- Requires custom ISO created by `iso_creation` role

## Example Playbook

```yaml
- hosts: localhost
  connection: local
  gather_facts: false
  roles:
    - role: iso_delivery
      vars:
        iso_custom_path: "/opt/isos/rhel-10.0-custom.iso"
        target_node_bmc_ip: "172.16.0.100"
        bmc_username: "{{ vault_bmc_username }}"
        bmc_password: "{{ vault_bmc_password }}"
```

## Tasks

- `main.yml` - Main orchestration
- `deploy_os.yml` - Mount ISO and trigger OS installation
- `preflight_checks.yml` - Validate iDRAC capabilities and ISO availability

## License

Apache 2.0

## Author Information

Dell Technologies Omnia Team
