# repository_access

## Description

Prepare host-level RHEL subscription access once and resolve repository URLs
for each catalog OS-version and architecture context.

## Requirements

- Ansible >= 2.14
- Python >= 3.9

## Role Variables

See `vars/main.yml` for the RHEL provider variables. Platform capability
defaults are defined in `../../vars/default.yml`.

The host subscription check runs once and publishes `subscription_status` for
both validation and repository resolution. For each catalog execution context,
the role processes only `catalog_context.referenced_repositories`:

- An explicit URL always takes precedence.
- With subscription access, only a referenced BaseOS, AppStream or CodeReady
  Builder repository with an empty or missing URL uses subscription discovery.
- Without subscription access, every referenced RPM repository, including
  BaseOS, AppStream and CodeReady Builder, requires an explicit URL.
- Missing repositories are reported together across selected architectures.
- In subscription mode, every resolved referenced repository is checked for
  `repodata/repomd.xml` before Pulp synchronization.

## Dependencies

None.

## Example Playbook

```yaml
- name: Prepare host subscription access once
  ansible.builtin.include_role:
    name: repository_access
    tasks_from: prepare_host_repository_access.yml

- name: Resolve the active catalog context
  ansible.builtin.include_role:
    name: repository_access
    tasks_from: resolve_context_repository_urls.yml
```

## License

Apache-2.0

## Author Information

Dell Technologies
