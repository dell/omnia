# verify_node_registration

Verify fresh boot and cloud-init completion on PXE-booted nodes.

## Description

This role verifies that nodes have successfully booted and completed cloud-init
after PXE boot. The role runs once per dynamically inventoried admin IP. Ansible
checks those hosts concurrently, and a node passes only when passwordless SSH
works, its boot timestamp is newer than the PXE trigger, and
`cloud-init status --long` reports `done`. OpenCHAMI metadata-service v0.2.1
returns a header-only user-data document, so the corresponding `empty cloud
config` recoverable warning is accepted only when it is the sole degraded
condition. Every other cloud-init error or recoverable warning fails the node.

## Requirements

- Passwordless root SSH from the OIM to target nodes
- Target nodes containing `cloud-init` and `/proc/uptime`

## Role Variables

Available variables are listed below (see `vars/main.yml`):

```yaml
# Pause before polling (minutes)
node_registration_pause_minutes: 3

# Polling configuration
node_registration_retries: 120
node_registration_delay: 15

# Status indicators
verify_node_registration_status_ok: "OK Node boot verified:"
verify_node_registration_status_failed: "FAILED Node boot verification:"
```

## Required Facts

These facts must be set by the calling playbook before invoking this role:

| Fact | Description |
|------|-------------|
| `hostvars['localhost']['pxe_start_epoch']` | Epoch timestamp when PXE boot started |
| `hostvars['localhost']['node_registration_retries']` | Maximum attempts per node |
| `hostvars['localhost']['node_registration_delay']` | Delay between attempts |
| `bmc_ip` | BMC address associated with the current admin-IP inventory host |

## Dependencies

None.

## Example Playbook

```yaml
- name: Verify node registration from PXE-booted nodes
  hosts: node_registration_targets
  connection: local
  roles:
    - role: verify_node_registration
```

## Workflow

1. **Assert context** - Verify the PXE epoch and BMC mapping
2. **Poll independently** - Open one SSH session per attempt and read uptime and cloud-init state
3. **Verify freshness** - Reject a boot that predates the PXE request
4. **Handle completion** - Pass on clean `done`, or on `done` with only the known
   OpenCHAMI empty user-data warning; fail every other degraded or terminal state
5. **Retry pending states** - Retry unreachable, stale, unknown, and running states
6. **Record result** - Store the exact state, detail, terminal flag, attempt
   count, verification method, and machine-readable cloud-init state on the
   inventory host

## Output Facts

After execution, the following fact is available on every host in
`node_registration_targets`:

| Fact | Description |
|------|-------------|
| `verify_node_registration_result` | Node identity, status, state, detail, terminal flag, attempts, verification method, and structured `cloud_init` data |

The nested `cloud_init` object preserves `status`, `extended_status`,
`boot_status_code`, `errors`, and `recoverable_errors` from `cloud-init status
--format json`. If the installed cloud-init version does not return valid JSON,
the object uses safe defaults while the `--long` output continues to drive the
verification result.

## Tasks

- `main.yml` - Poll and record one node's boot/cloud-init state

## License

Apache 2.0

## Author Information

Dell Technologies Omnia Team
