# postgres

## Description

Deploys the PostgreSQL container for the Build Stream database

## Requirements

- Ansible >= 2.14
- Python >= 3.9

## Role Variables

See `vars/main.yml` for available variables.

## Dependencies

None.

## Example Playbook

```yaml
- hosts: oim_group
  roles:
    - role: postgres
```

## License

Apache-2.0

## Author Information

Dell Technologies
