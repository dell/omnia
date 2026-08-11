# gitlab_passwordless_ssh

## Description

Configures passwordless SSH access from the control node to the GitLab server

## Requirements

- Ansible >= 2.14
- Python >= 3.9

## Role Variables

See `vars/main.yml` for available variables.

## Dependencies

None.

## Example Playbook

```yaml
- hosts: localhost
  roles:
    - role: gitlab_passwordless_ssh
```

## License

Apache-2.0

## Author Information

Dell Technologies
