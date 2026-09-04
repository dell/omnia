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
