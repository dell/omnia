# hosted_gitlab

## Description

Deploys GitLab CE Omnibus with TLS, CI/CD pipelines, runner, and project configuration

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
    - role: hosted_gitlab
```

## License

Apache-2.0

## Author Information

Dell Technologies
