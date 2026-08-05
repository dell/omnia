# fetch_arm_params

Fetches ARM-specific parameters for ARM64/aarch64 node provisioning.

## Description

This role retrieves and validates ARM-specific parameters required for ARM64/aarch64 compute node provisioning. It handles architecture-specific configuration, boot parameters, and hardware compatibility checks.

## Requirements

- ARM64/aarch64 target hardware
- ARM-specific OS images and boot files
- Network access to ARM repositories

## Role Variables

Available variables are listed below, along with default values (see `vars/main.yml`):

```yaml
# ARM architecture settings
target_architecture: "aarch64"
arm_boot_params: {}
arm_kernel_params: ""

# Hardware compatibility
validate_arm_hardware: true
arm_cpu_vendor: ""
```

## Dependencies

None.

## Example Playbook

```yaml
- hosts: localhost
  connection: local
  gather_facts: true
  roles:
    - role: fetch_arm_params
      vars:
        target_architecture: "aarch64"
        validate_arm_hardware: true
```

## License

Apache 2.0

## Author Information

Dell Technologies Omnia Team
