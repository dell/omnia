# idrac_pxe_boot

Configures iDRAC systems for PXE boot operations and BMC inventory management.

## Description

This role manages Dell iDRAC (Integrated Dell Remote Access Controller) systems for PXE network booting. It handles BMC inventory generation, pre-flight checks, and boot configuration for automated OS provisioning workflows.

## Requirements

- Dell servers with iDRAC support
- Network access to iDRAC interfaces
- BMC credentials (username/password)
- PXE-enabled network infrastructure

## Role Variables

Available variables are listed below, along with default values (see `vars/main.yml`):

```yaml
# BMC inventory and credentials
bmc_csv_file: "bmc_inventory.csv"
bmc_username: ""
bmc_password: ""

# Boot configuration
pxe_boot_enabled: true
boot_order_validation: true
```

## Dependencies

None.

## Example Playbook

```yaml
- hosts: bmc
  connection: local
  gather_facts: false
  roles:
    - role: idrac_pxe_boot
      vars:
        bmc_username: "{{ vault_bmc_username }}"
        bmc_password: "{{ vault_bmc_password }}"
```

## Tasks

- `main.yml` - Main orchestration
- `generate_bmc_inventory.yml` - Create BMC inventory from CSV
- `pre_checks.yml` - Validate iDRAC connectivity and configuration

## License

Apache 2.0

## Author Information

Dell Technologies Omnia Team
