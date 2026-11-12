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

## Task files

| File | Purpose |
|------|---------|
| `pin_host_key.yml` | Records the GitLab host key in `~/.ssh/known_hosts` on first contact (optionally checked against `gitlab_host_key_fingerprint`). |
| `bootstrap_key.yml` | Run on the control node before the first connection of a play (after `pin_host_key.yml`): creates `ssh_key_path` if missing and, only when key login does not work yet, installs it with `ssh-copy-id` using `gitlab_ssh_password`. The password goes through the environment (`sshpass -e`), never on a command line; the host key is checked against the pinned `known_hosts`. Without this, the first run from a new OIM fails at the first connection, and the failed logins make an OpenSSH 9.8+ GitLab host reset further connections (`kex_exchange_identification: Connection reset by peer`) for a short time. |
| `validate_ssh.yml` | Fails when key login with the pinned host key does not work. |

## License

Apache-2.0

## Author Information

Dell Technologies
