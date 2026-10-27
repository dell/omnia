# external_boot_verification

Prepare and report SSH/cloud-init verification for nodes booted outside the
Orchestrator PXE trigger, including virtual machines and manually rebooted
physical nodes.

## Responsibilities

- Load and validate the project `orchestrator_status.yml`.
- Select nodes with `reprovision_required: true` and verify only nodes whose
  `provisioning_status` is `success`.
- Fail before SSH when a mapped node has failed, unknown, or missing
  provisioning state.
- Build the dynamic `external_node_registration_targets` inventory.
- Use the lifecycle status modification time as the fresh-boot boundary.
- Reconcile verification results and persist compact lifecycle reports.

Node polling is delegated to `verify_node_registration`. Artifact writing is
delegated to `orchestrator_lifecycle_status`.

## Requirements

- A completed provision or PXE run that produced `orchestrator_status.yml`.
- Passwordless SSH access to each externally booted node selected for verification.
- Cloud-init available on each selected node.

## Role Variables

Overridable defaults are defined in `defaults/main.yml`:

- `external_boot_verification_ssh_user`
- `external_boot_verification_python`
- `external_boot_verification_ssh_timeout`
- `external_boot_verification_ssh_retries`
- `external_boot_verification_retries`
- `external_boot_verification_delay`

Internal paths and messages are defined in `vars/main.yml`.

## Task entry points

- `main.yml` prepares the dynamic inventory.
- `report.yml` reconciles and persists verification results.

## Dependencies

- `verify_node_registration` performs SSH/cloud-init polling in the remote play.
- `orchestrator_lifecycle_status` persists the reconciled reports.

## Example playbook

```yaml
- name: Prepare external verification
  hosts: localhost
  connection: local
  roles:
    - role: external_boot_verification
```

## License

Apache 2.0
