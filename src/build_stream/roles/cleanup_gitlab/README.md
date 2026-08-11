# cleanup_gitlab

## Description

Removes GitLab CE, runner, TLS certificates, CI/CD configuration, and credentials

## Requirements

- Ansible >= 2.14
- Python >= 3.9

## Role Variables

See `vars/main.yml` for available variables.

## Dependencies

None.

## Example Playbook

```yaml
- hosts: gitlab_host
  roles:
    - role: cleanup_gitlab
```

## License

Apache-2.0

## Author Information

Dell Technologies
