# verify_phone_home

Verify cloud-init phone-home callbacks from PXE-booted nodes.

## Description

This role monitors the cloud-init-server journal on the OIM server to verify that
nodes have successfully booted and completed cloud-init after PXE boot. It polls
the journal for phone-home requests from each target node and reports success or
failure.

## Requirements

- `cloud-init-server` service running on OIM server
- Journal access (requires `become: true`)
- Target nodes configured with cloud-init phone-home module

## Role Variables

Available variables are listed below (see `vars/main.yml`):

```yaml
# Pause before polling (minutes)
phone_home_pause_minutes: 3

# Polling configuration
phone_home_retries: 120
phone_home_delay: 15

# Journal pattern to match
phone_home_log_pattern: "Phone home request from"

# Status indicators
phone_home_status_ok: "[OK]"
phone_home_status_wait: "[WAIT]"
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
- name: Verify phone-home from PXE-booted nodes
  hosts: oim_server
  become: true
  vars:
    pxe_start_epoch: "{{ lookup('pipe', 'date +%s') }}"
    target_node_admin_ips:
      - 192.168.1.50
      - 192.168.1.51
  roles:
    - role: verify_phone_home
```

## Workflow

1. **Assert facts** - Verify `pxe_start_epoch` and `target_node_admin_ips` are defined
2. **Initial pause** - Wait for nodes to begin cloud-init (configurable)
3. **Poll journal** - Check journalctl for phone-home requests from all target IPs
4. **Retry loop** - Retry until all nodes phone home or retries exhausted
5. **Parse results** - Extract list of failed IPs
6. **Cache results** - Store `phone_home_failed_ips` on localhost for reporting
7. **Report outcome** - Display success or warning message

## Output Facts

After execution, the following facts are available on `localhost`:

| Fact | Description |
|------|-------------|
| `phone_home_failed_ips` | List of IPs that did not phone home |
| `phone_home_completed` | Boolean indicating the role completed |

## Tasks

- `main.yml` - Poll journal, track per-node status, report results

## License

Apache 2.0

## Author Information

Dell Technologies Omnia Team
