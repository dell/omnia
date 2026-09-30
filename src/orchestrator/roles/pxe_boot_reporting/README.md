# pxe_boot_reporting

Collect PXE trigger and node-registration results, reconcile compact lifecycle
state, persist project reports, and run optional BuildStream post-processing.

## Requirements

The caller must provide the dynamic `bmc` group and the per-run PXE facts
created by the inventory and verification stages.

## Role variables

Internal report paths, modes, and failure messages are defined in
`vars/main.yml`. This role has no user-overridable defaults.

## Dependencies

- `orchestrator_lifecycle_status` persists reconciled reports.
- `pxe_buildstream_manager` is invoked only when BuildStream is enabled.

## Example playbook

```yaml
- name: Report PXE boot results
  hosts: localhost
  connection: local
  roles:
    - role: pxe_boot_reporting
```

## License

Apache 2.0
