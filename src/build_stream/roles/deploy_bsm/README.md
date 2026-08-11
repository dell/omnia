# deploy_bsm

## Description

Deploys the Build Stream Manager container and playbook watcher service

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
    - role: deploy_bsm
```

## License

Apache-2.0

## Author Information

Dell Technologies
