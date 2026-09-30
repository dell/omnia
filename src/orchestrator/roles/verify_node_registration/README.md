# verify_node_registration

Verify fresh boot and cloud-init completion on Orchestrator- or externally
booted nodes.

## Description

This role verifies that nodes have successfully booted and completed cloud-init
after PXE boot. The role runs a node-local Python module once per dynamically
inventoried admin IP. Ansible checks those hosts concurrently, and a node passes
only when passwordless SSH works, its boot timestamp is newer than the PXE
trigger, and `cloud-init status --long` reports `done`. OpenCHAMI
metadata-service v0.2.1
returns a header-only user-data document, so the corresponding `empty cloud
config` recoverable warning is accepted only when it is the sole degraded
condition. Every other cloud-init error or recoverable warning fails the node.

## Requirements

- Passwordless root SSH from the OIM to target nodes
- Target nodes containing `/usr/bin/python3`, `/usr/bin/cloud-init`, and
  `/proc/uptime`

## Role Variables

Polling defaults are listed below (see `defaults/main.yml`):

```yaml
verify_node_registration_retries: 120
verify_node_registration_delay: 15
verify_node_registration_connect_timeout: 5
```

## Required Facts

These facts must be set by the calling playbook before invoking this role:

| Fact | Description |
|------|-------------|
| `hostvars['localhost']['verification_start_epoch']` or `pxe_start_epoch` | Epoch timestamp before the expected fresh boot |
| `hostvars['localhost']['node_registration_retries']` | Optional maximum attempts per node; the role default is used when absent |
| `hostvars['localhost']['node_registration_delay']` | Optional delay between attempts; the role default is used when absent |
| `verification_trigger_method` | `orchestrator` (default) or `external` |
| `bmc_ip` | BMC address; required only for the `orchestrator` trigger method |

For `external` verification after a failed PXE attempt, the caller derives
`verification_start_epoch` from the completed aggregate lifecycle status. The
operator must therefore wait for the PXE workflow to finish writing that
status, and then boot the node. A boot older than this epoch is intentionally
treated as stale.

## Dependencies

None.

## Example Playbook

```yaml
- name: Verify node registration from PXE-booted nodes
  hosts: node_registration_targets
  connection: ssh
  roles:
    - role: verify_node_registration
```

## Workflow

1. **Assert context** - Verify the boot epoch and trigger-specific identity
2. **Poll independently** - Run `node_boot_status` over Ansible SSH to read
   uptime and cloud-init state
3. **Verify freshness** - Reject a boot that predates the PXE request
4. **Handle completion** - Pass on clean `done`, or on `done` with only the known
   OpenCHAMI empty user-data warning; fail every other degraded or terminal state
5. **Retry pending states** - Retry unreachable, stale, unknown, and running states
6. **Record result** - Store the module's state, detail, terminal flag, attempt
   count, verification method, and machine-readable cloud-init state on the
   inventory host

## Output Facts

After execution, the following fact is available on every host in
`node_registration_targets`:

| Fact | Description |
|------|-------------|
| `verify_node_registration_result` | Node identity, status, state, trigger method, detail, terminal flag, attempts, verification method, and structured `cloud_init` data |

The nested `cloud_init` object publishes only the normalized `status` required
by automation. The node-local module evaluates the complete `cloud-init status
--format json` response internally, but raw errors, warnings, Python paths, and
command output are not returned or persisted. Operators can inspect detailed
diagnostics directly in the node's cloud-init logs.

## Tasks

- `main.yml` - Poll and record one node's boot/cloud-init state

## License

Apache 2.0

## Author Information

Dell Technologies Omnia Team
