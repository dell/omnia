# validate_arm_config

Validates ARM64/aarch64 configuration for compute node provisioning.

## Description

This role validates ARM-specific configuration parameters, hardware compatibility, and boot settings for ARM64/aarch64 compute nodes. It ensures proper configuration before proceeding with ARM node provisioning workflows.

## Requirements

- ARM configuration files
- Hardware information for target ARM64 systems
- Access to ARM-specific repositories and images

## Role Variables

Available variables are listed below, along with default values (see `vars/main.yml`):

```yaml
# Validation settings
validate_arm_config: true
arm_config_file: "arm_config.yml"
strict_validation: false

# Hardware requirements
min_arm_cores: 4
min_arm_memory_gb: 8
supported_arm_vendors: []
```

## Dependencies

- Requires `fetch_arm_params` role for parameter validation

## Example Playbook

```yaml
- hosts: localhost
  connection: local
  gather_facts: false
  roles:
    - role: validate_arm_config
      vars:
        arm_config_file: "/opt/omnia/input/project_default/arm_config.yml"
        strict_validation: true
        min_arm_cores: 8
        min_arm_memory_gb: 16
```

## License

Apache 2.0

## Author Information

Dell Technologies Omnia Team
