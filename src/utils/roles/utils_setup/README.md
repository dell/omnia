# utils_setup

Initializes shared facts for every public Utils flow and optionally runs common
prerequisite, configuration-file, and disk-space checks.

## Defaults

```yaml
validate_prerequisites: false
validate_config_files: false
validate_disk_space: false
min_disk_space_gb: 50
config_files_to_validate: []
utils_domain_ready: false
```

The validations default to disabled because `collect`, `install_os`, and
`backup_oim_logs` own different input contracts and validate their required
files in their respective flows.

## Tasks

| Task file | Purpose |
|-----------|---------|
| `validate_prerequisites.yml` | Check supported Python and Ansible versions when enabled |
| `validate_config_files.yml` | Check caller-supplied `config_files_to_validate` when enabled |
| `validate_disk_space.yml` | Check free space below `OMNIA_DATA_PATH` when enabled |
| `set_guard_facts.yml` | Load environment-derived domain paths and set guard facts |

## Usage

The role is always executed by `playbooks/utils.yml`:

```bash
cd src/utils
ansible-playbook playbooks/utils.yml --tags setup
```

It may also be used with explicit optional checks:

```yaml
- name: Initialize Utils
  hosts: localhost
  connection: local
  gather_facts: true
  roles:
    - role: utils_setup
      vars:
        validate_prerequisites: true
        validate_disk_space: true
        min_disk_space_gb: 50
```

## Dependencies

None.

## License

Apache License, Version 2.0
