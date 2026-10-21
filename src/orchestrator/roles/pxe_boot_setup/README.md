# pxe_boot_setup

Initialize Orchestrator context and load, default, validate, and normalize PXE
boot configuration.

## Requirements

The project input directory must be available, or `orchestrator_setup` must be
able to initialize it.

## Role variables

User configuration is read from `set_pxe_boot_config.yml`. Internal allowed
values, paths, and messages are defined in `vars/main.yml`.

## Dependencies

The role conditionally invokes `orchestrator_setup` when the caller has not
already initialized the project.

## Example playbook

```yaml
- name: Setup PXE boot
  hosts: localhost
  connection: local
  roles:
    - role: pxe_boot_setup
```

## License

Apache 2.0
