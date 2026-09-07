# verify_node_registration

Verify cloud-init node-registration callbacks from PXE-booted nodes.

## Description

This role verifies that nodes have successfully booted and completed cloud-init
after PXE boot. It uses SSH port reachability (TCP/22) as the primary check
and monitors the metadata-service journal for node-registration POST requests as
secondary confirmation.

## Requirements

- `metadata-service` (OpenCHAMI) running on OIM server
- Journal access (requires `become: true`)
- Target nodes configured with cloud-init phone-home module

## Role Variables

Available variables are listed below (see `vars/main.yml`):

```yaml
# Pause before polling (minutes)
node_registration_pause_minutes: 3

# Polling configuration
node_registration_retries: 120
node_registration_delay: 15

# Journal pattern to match (cloud-init standard, not renamed)
node_registration_log_pattern: "phone-home"

# Status indicators
node_registration_status_ok: "[OK]"
node_registration_status_wait: "[WAIT]"
```

## Required Facts

These facts must be set by the calling playbook before invoking this role:

| Fact | Description |
|------|-------------|
| `pxe_start_epoch` | Epoch timestamp when PXE boot started |
| `target_node_admin_ips` | List of admin IPs to wait for |

## Dependencies

None.

## Example Playbook

```yaml
- name: Verify node-registration from PXE-booted nodes
  hosts: oim_server
  become: true
  vars:
    pxe_start_epoch: "{{ lookup('pipe', 'date +%s') }}"
    target_node_admin_ips:
      - 172.16.1.50
      - 172.16.1.51
  roles:
    - role: verify_node_registration
```

## Workflow

1. **Assert facts** - Verify `pxe_start_epoch` and `target_node_admin_ips` are defined
2. **Initial pause** - Wait for nodes to begin cloud-init (configurable)
3. **Poll reachability** - Check SSH port (TCP/22) on each node and metadata-service journal
4. **Retry loop** - Retry until all nodes are reachable or retries exhausted
5. **Parse results** - Extract list of failed IPs
6. **Cache results** - Store `node_registration_failed_ips` on localhost for reporting
7. **Report outcome** - Display success or warning message

## Output Facts

After execution, the following facts are available on `localhost`:

| Fact | Description |
|------|-------------|
| `node_registration_failed_ips` | List of IPs that did not register |
| `node_registration_completed` | Boolean indicating the role completed |

## Tasks

- `main.yml` - Poll journal, track per-node status, report results

## License

Apache 2.0

## Author Information

Dell Technologies Omnia Team
