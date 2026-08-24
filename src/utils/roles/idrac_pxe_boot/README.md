# idrac_pxe_boot

Configures Dell iDRAC systems for PXE boot and triggers node restart via Redfish API.

## Description

This role sets the boot source to PXE on Dell iDRAC systems and restarts the server.
It communicates with iDRAC via Redfish, verifying Lifecycle Controller readiness before
issuing boot configuration and power commands.

## Requirements

- Dell servers with iDRAC support
- Network access to iDRAC management interfaces
- BMC credentials loaded as `hostvars['localhost']` facts (`bmc_username`, `bmc_password`)
- `dellemc.openmanage` Ansible Galaxy collection

## Inventory Format

Inventory must include BMC IPs in the `[bmc]` group. For phone-home verification,
also include `admin_ip` and `hostname` as host variables:

```ini
[bmc]
172.16.0.73 admin_ip=172.16.1.50 hostname=node01
172.16.0.74 admin_ip=172.16.1.51 hostname=node02
```

Or in YAML:
```yaml
bmc:
  hosts:
    172.16.0.73:
      admin_ip: 172.16.1.50
      hostname: node01
    172.16.0.74:
      admin_ip: 172.16.1.51
      hostname: node02
```

## Role Variables

Available variables are listed below, along with default values (see `vars/main.yml`):

```yaml
# Restart the host after setting PXE boot (default: true)
restart_host: true

# Use ForceRestart instead of GracefulRestart (default: true)
force_restart: true

# Boot source override mode: once, continuous, or disabled
boot_source_override_enabled: continuous

# Boot source override target: pxe, uefi_http, hdd, cd, etc.
boot_source_override_target: pxe
```

## Dependencies

None.

## Example Playbook

```yaml
- hosts: bmc
  connection: local
  strategy: host_pinned
  gather_facts: false
  roles:
    - role: idrac_pxe_boot
```

Credentials are expected to be loaded on `localhost` before this role runs
(e.g., via the `collect_pxe_credentials` role).

## Tasks

- `main.yml` — Verify iDRAC LC status, set PXE boot, restart server, report results

## License

Apache 2.0

## Author Information

Dell Technologies Omnia Team
