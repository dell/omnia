# cleanup_gitlab

## Description

Removes GitLab CE, runner, TLS certificates, CI/CD configuration, and credentials.
Supply `-e cleanup_credentials=false` to keep the GitLab root password in
`build_stream_credentials.yml`. The registered OAuth client is always removed:
its secret lives only in the GitLab project's CI variables, which this cleanup
deletes, and a client kept in the file would block the next registration
(`409 max_clients_reached`, the API allows one client).

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
