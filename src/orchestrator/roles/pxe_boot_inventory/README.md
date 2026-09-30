# pxe_boot_inventory

Read a PXE mapping or custom retry inventory, resolve permanent XNAMEs through
SMD Hardware Inventory, select the requested node scope, and build dynamic BMC
and node-registration host groups.

## Requirements

- OpenCHAMI services and TokenSmith authentication must be available.
- Every Service Tag must already have a persistent SMD identity.
- Every mapped node in the standard Orchestrator flow must have
  `provisioning_status: success`; otherwise selection fails before Redfish.
- The inventory must contain the required named columns.

## Role variables

SSH and token retry defaults are defined in `defaults/main.yml`. Required CSV
columns, internal paths, and messages are defined in `vars/main.yml`.

## Dependencies

The role uses `openchami_reconcile` for read-only identity resolution.

## Example playbook

```yaml
- name: Build PXE inventory
  hosts: localhost
  connection: local
  roles:
    - role: pxe_boot_inventory
```

## License

Apache 2.0
