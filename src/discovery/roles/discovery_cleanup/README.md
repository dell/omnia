# discovery_cleanup

Does not remove or create the current Discovery project output directory. When
the directory exists, this role removes every generated entry inside it and
leaves the empty directory in place. It resets the current project's runtime
log directory to an empty directory and removes
`/var/log/omnia/discovery` by default. It also removes
`discovery_credentials.yml` and `.discovery_credentials_key` by default.

Set `cleanup_credentials=false` to preserve those two credential artifacts.
Set `cleanup_logs=false` to preserve the current project's runtime and Ansible
execution logs.
All other files in the Discovery input directory are always preserved.

## Requirements

- Ansible 2.14 or later
- `OMNIA_DATA_PATH`, optional `DISCOVERY_DATA_PATH`, and
  `OMNIA_PROJECT_NAME` exported when their defaults are not used

## Role Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `cleanup_credentials` | `true` | Remove the Discovery credential file and vault key |
| `cleanup_logs` | `true` | Reset project runtime logs and remove Discovery Ansible execution logs |

## Dependencies

The `discovery_setup` role must resolve the project input and output paths
before this role runs. The supported cleanup playbook handles that dependency.

## Usage

```bash
ansible-playbook playbooks/discovery.yml --tags cleanup
ansible-playbook playbooks/discovery.yml --tags cleanup \
  -e cleanup_credentials=false
ansible-playbook playbooks/discovery.yml --tags cleanup \
  -e cleanup_logs=false
ansible-playbook playbooks/discovery.yml --tags cleanup_credentials
```

The explicit `cleanup_credentials` tag takes precedence over
`cleanup_credentials=false`. Cleanup is limited to the current project and
removes its runtime logs by default. Preserving logs can block guarded global
cleanup until they are removed.

The cleanup playbook can also be run directly:

```bash
cd playbooks/cleanup
ansible-playbook cleanup_discovery.yml
```

## License

Apache-2.0
