# utils_setup

Initializes and validates the utils domain environment before executing utility playbooks.

## Description

This role performs pre-execution validation and setup for the utils domain. It checks system prerequisites, validates configuration files, and prepares the runtime environment for all utility operations including OS installation, log collection, and Slurm management.

## Requirements

- Ansible 2.19+
- Python 3.12+ on control node
- Required configuration files in input directory
- Sufficient disk space for operations

## Role Variables

Available variables are listed below, along with default values (see `defaults/main.yml`):

```yaml
# Validation settings
validate_prerequisites: true
validate_config_files: true
validate_disk_space: true

# Minimum disk space requirements (GB)
min_disk_space_gb: 50

# Configuration file paths
config_files_to_validate:
  - iso_config.yml
  - telemetry_config.yml
  - omnia_config.yml

# Guard facts
utils_domain_ready: false
```

## Dependencies

None.

## Example Playbook

```yaml
- hosts: localhost
  connection: local
  gather_facts: true
  roles:
    - role: utils_setup
      vars:
        validate_prerequisites: true
        validate_config_files: true
        validate_disk_space: true
        min_disk_space_gb: 100
```

## Tasks

- `main.yml` - Main orchestration
- `validate_prerequisites.yml` - Check system prerequisites (Python, Ansible versions)
- `validate_config_files.yml` - Validate required configuration files exist and are readable
- `validate_disk_space.yml` - Ensure sufficient disk space for operations
- `set_guard_facts.yml` - Set guard facts for downstream playbooks

## License

Apache 2.0

## Author Information

Dell Technologies Omnia Team
