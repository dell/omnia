# precheck_environment Role

## Description

Validates the system environment before repo_manager operations. This role ensures that all required environment variables are set and system requirements are met before proceeding with repo_manager operations.

## Requirements

- Ansible 2.9 or higher
- `validate_system_environment` module must be available

## Role Variables

None. This role uses environment variables:

- `SYSTEM_ADMIN_NIC_IPV4` - Admin NIC IP address (required)
- `CATALOG_FILE_PATH` - Path to catalog JSON file (required)
- `OMNIA_DATA_PATH` - Base data directory (default: /opt/omnia)
- `OMNIA_PROJECT_NAME` - Project name (default: project_default)

## Dependencies

None.

## Example Usage

```yaml
- hosts: localhost
  roles:
    - role: precheck_environment
```

## Tags

- `precheck` - Run environment precheck
- `always` - Always run during playbook execution

## Validation Checks

1. **Environment Variables**: Validates required environment variables are set
2. **System Requirements**: Checks system IP configuration and path accessibility
3. **Upstream Contracts**: Validates upstream dependencies (if any exist)

## Notes

- This role runs BEFORE credential collection
- Does not require credentials to execute
- Should be called with `precheck` tag
- Integrated into main repo_manager.yml playbook