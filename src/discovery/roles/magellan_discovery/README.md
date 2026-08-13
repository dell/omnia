# Magellan Discovery Role

## Overview

The `omnia.discovery.magellan_discovery` role implements the Magellan bare-metal
discovery mechanism for Omnia. It discovers server inventory directly from each
baseboard management controller (BMC) via Redfish, starting from a sparse
`admin_inventory.csv`, and produces the timestamped PXE mapping, xnames mapping,
and discovery-report files required for provisioning.

This role is invoked by `discovery.yml` when `discovery_mechanism=magellan`.

## Purpose

- Read the sparse admin inventory CSV (`admin_inventory.csv`).
- Validate and expand the CSV to a complete inventory with `BMC_IP` and `USLOT` values.
- Load BMC Redfish endpoint configuration from `bmc_redfish_config.csv`.
- Query each iDRAC over Redfish for:
  - Service tag and system model
  - BMC MAC address and link status
  - Admin (Ethernet) NIC MAC address and link status
  - InfiniBand NIC name and link status (when an IB network is configured)
- Generate the following timestamped output files:
  - `bmc_pxe_mapping_file_<timestamp>.csv`
  - `xnames_mapping_file_<timestamp>.csv` (when `ROW`, `RACK`, and `USLOT` data are present)
  - `bmc_discovery_report_<timestamp>.csv`

## Input Requirements

The role expects the following project input files in the active discovery input
directory (default `/opt/omnia/input/project_default/discovery`):

- `admin_inventory.csv` — Sparse admin inventory (see format below).
- `bmc_redfish_config.csv` — Vendor-specific Redfish endpoint configuration.
- `network_spec.yml` — Admin, BMC, and IB network definitions.
- `omnia_config_credentials.yml` (optional) — Vault-encrypted iDRAC credentials.

### Admin Inventory Format

The sparse `admin_inventory.csv` must contain at least these columns:

```csv
SERVICE_TAG,GROUP_NAME,FUNCTIONAL_GROUP_NAME,RANGE
```

Optional location columns may be added to enable xnames generation:

```csv
SERVICE_TAG,GROUP_NAME,FUNCTIONAL_GROUP_NAME,ROW,RACK,USLOT,RANGE
```

| Column | Required | Description |
|--------|----------|-------------|
| `SERVICE_TAG` | Yes | Server service tag. |
| `GROUP_NAME` | Yes | Group name, e.g. `SU1`. May be carried forward from a previous row. |
| `FUNCTIONAL_GROUP_NAME` | Yes | Omnia functional group, e.g. `slurm_node_x86_64`. |
| `ROW` | No | Physical row / aisle number. Required for xnames. |
| `RACK` | No | Physical rack number. Required for xnames. |
| `USLOT` | No | Physical u-slot. May be left empty to be auto-assigned per `(ROW, RACK)`. |
| `RANGE` | Yes | IPv4 BMC IP range in `start-end` format, e.g. `172.17.107.60-172.17.107.79`. |

Blank `GROUP_NAME`, `FUNCTIONAL_GROUP_NAME`, and `RANGE` values are carried
forward from the last populated row in the same group. Rows with blank `ROW` or
`RACK` still receive a `BMC_IP`, but xnames mapping is skipped for those rows.

### BMC Redfish Config Format

The `bmc_redfish_config.csv` file is a two-column key-value CSV that tells the
role how to address a given vendor's Redfish implementation. Example (Dell iDRAC):

```csv
vendor_profile,dell
system_endpoint,/redfish/v1/Systems/System.Embedded.1
managers_collection_endpoint,/redfish/v1/Managers
systems_collection_endpoint,/redfish/v1/Systems
manager_endpoint,/redfish/v1/Managers/iDRAC.Embedded.1
manager_attributes_endpoint,/redfish/v1/Managers/iDRAC.Embedded.1/Attributes
manager_ethernet_interfaces_endpoint,/redfish/v1/Managers/iDRAC.Embedded.1/EthernetInterfaces
system_network_adapters_endpoint,/redfish/v1/Systems/System.Embedded.1/NetworkAdapters
system_ethernet_interfaces_endpoint,/redfish/v1/Systems/System.Embedded.1/EthernetInterfaces
location_endpoint,/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/DellAttributes/System.Embedded.1
service_tag_field,SKU
static_ip_address_key,IPv4Static.1.Address
static_ip_netmask_key,IPv4Static.1.Netmask
static_ip_gateway_key,IPv4Static.1.Gateway
static_ip_dhcp_enable_key,IPv4.1.DHCPEnable
dhcp_disable_value,Disabled
location_aisle_field,ServerTopology.1.AisleName
location_rack_field,ServerTopology.1.RackName
location_slot_field,ServerTopology.1.RackSlot
idrac_name_key,NIC.1.DNSRacName
idrac_name_format,{GROUP_NAME}R{RACK}OU{USLOT}C1
```

Required keys are validated by the `omnia.discovery.validate_bmc_redfish_config`
module.

## Workflow

1. Configure inputs in the project discovery input directory:

   - Create or edit `admin_inventory.csv`.
   - Create or edit `bmc_redfish_config.csv`.
   - Ensure `network_spec.yml` defines `admin_network` and, if applicable,
     `ib_network`.

2. Run discovery from the `src/discovery` directory:

   ```bash
   ansible-playbook discovery.yml -e "discovery_mechanism=magellan"
   ```

3. Review the generated timestamped files in the discovery output directory
   (default `/opt/omnia/output/project_default/discovery`):

   - `bmc_pxe_mapping_file_YYYYMMDDTHHMMSS.csv`
   - `xnames_mapping_file_YYYYMMDDTHHMMSS.csv` (if location data is present)
   - `bmc_discovery_report_YYYYMMDDTHHMMSS.csv`

4. The role creates `bmc_pxe_mapping_file.csv` and `xnames_mapping_file.csv`
   symlinks in the same output directory pointing to the latest timestamped files.

5. Update `provision_config.yml`:

   ```yaml
   pxe_mapping_file_path: "/opt/omnia/output/project_default/discovery/bmc_pxe_mapping_file.csv"
   ```

6. Run provision:

   ```bash
   ansible-playbook orchestrator.yml
   ```

## Collected Information

For each server discovered from its BMC, the following fields are recorded:

| Field | Source | Description |
|-------|--------|-------------|
| `service_tag` | Redfish / CSV | Server service tag. |
| `idrac_ip` | Expanded inventory | BMC IP address from the `RANGE` allocation. |
| `idrac_mac` | Redfish manager Ethernet interface | BMC MAC address. |
| `idrac_link_status` | Redfish | BMC NIC link status. |
| `first_nic_name` | Redfish network adapter | First Ethernet NIC function ID. |
| `first_nic_mac` | Redfish network adapter | First Ethernet NIC MAC address. |
| `first_nic_link_status` | Redfish | First Ethernet NIC link status. |
| `ib_nic_name` | Redfish network adapter | InfiniBand NIC name, when detected. |
| `ib_nic_link_status` | Redfish | InfiniBand NIC link status. |
| `row`, `rack`, `uslot` | Expanded inventory | Physical location used for xnames. |
| `group_name` | CSV | Group name, e.g. `SU1`. |
| `functional_group` | CSV | Omnia functional group name. |

## Output

All generated files are timestamped so that successive discovery runs do not
overwrite previous results.

| File | Default Location | Description |
|------|------------------|-------------|
| `admin_complete_inventory.csv` | `<discovery_input_dir>/admin_complete_inventory.csv` | Validated and expanded inventory with `BMC_IP` and `USLOT`. |
| `bmc_pxe_mapping_file_<timestamp>.csv` | `<discovery_output_dir>/` | PXE mapping used for provisioning. |
| `xnames_mapping_file_<timestamp>.csv` | `<discovery_output_dir>/` | BMC-IP to xname mapping, generated when `ROW`, `RACK`, and `USLOT` are present. |
| `bmc_discovery_report_<timestamp>.csv` | `<discovery_output_dir>/` | Report of BMC, Ethernet, and IB NIC link statuses. |

## Credential Handling

iDRAC credentials are resolved from `omnia_config_credentials.yml` in the project
input directory (plain or Ansible-Vault encrypted).

If no credentials are supplied, the role falls back to the default iDRAC
username `root` and password `calvin`.

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `admin_inventory_path` | `{{ hostvars['localhost']['discovery_input_dir'] \| default('/opt/omnia/input/project_default/discovery') }}/admin_inventory.csv` | Path to the sparse admin inventory CSV. |
| `admin_complete_inventory_path` | `{{ hostvars['localhost']['discovery_input_dir'] \| default('/opt/omnia/input/project_default/discovery') }}/admin_complete_inventory.csv` | Path to the generated complete inventory CSV. |
| `default_functional_group` | `slurm_node_aarch64` | Default functional group when not specified in the CSV. |
| `default_group_name` | `grp0` | Default group name when not specified in the CSV. |
| `hostname_prefix` | `nid` | Prefix for generated hostnames. |
| `hostname_start_number` | `1` | Starting number for generated hostnames. |
| `hostname_padding` | `5` | Zero-padding width for generated hostnames, e.g. `nid00001`. |
| `pxe_mapping_output_file` | `<discovery_output_dir>/bmc_pxe_mapping_file_<timestamp>.csv` | Timestamped PXE mapping output file. |
| `xnames_mapping_file` | `<discovery_output_dir>/xnames_mapping_file_<timestamp>.csv` | Timestamped xnames mapping output file. |
| `discovery_report_output_file` | `<discovery_output_dir>/bmc_discovery_report_<timestamp>.csv` | Timestamped discovery report output file. |

## Role File Structure

```
roles/magellan_discovery/
├── README.md
├── defaults/main.yml
├── meta/main.yml
├── vars/main.yml
└── tasks/
    ├── main.yml
    ├── get_idrac_credentials.yml
    ├── validate_admin_inventory.yml
    ├── load_bmc_redfish_config.yml
    ├── collect_inventory.yml
    ├── generate_pxe_mapping.yml
    ├── generate_xnames_mapping.yml
    └── generate_discovery_report.yml
```

## Files Added

- `src/discovery/roles/magellan_discovery/` — Ansible collection role and supporting tasks.
- `src/discovery/plugins/modules/magellan_inventory.py` — Collects per-server inventory over Redfish.
- `src/discovery/plugins/modules/validate_admin_inventory.py` — Validates and expands the sparse admin inventory.
- `src/discovery/plugins/modules/validate_bmc_redfish_config.py` — Validates `bmc_redfish_config.csv`.
- `src/discovery/plugins/modules/generate_pxe_mapping.py` — Generates PXE mapping CSV.
- `src/discovery/plugins/modules/generate_xnames_mapping.py` — Generates xnames mapping CSV.
- `src/discovery/plugins/modules/generate_discovery_report.py` — Generates discovery report CSV.
- `src/discovery/utils/inventory_expander.py` — Utility to expand sparse admin inventory.
- `src/discovery/input/admin_inventory.csv` — Sample sparse admin inventory.
- `src/discovery/input/bmc_redfish_config.csv` — Sample BMC Redfish configuration.

## Files Modified

- `src/discovery/discovery.yml` — Now invokes `omnia.discovery.magellan_discovery` for `discovery_mechanism=magellan`.
- `src/discovery/input/discovery_config.yml` — Added `admin_inventory_path` field for Magellan.
- `src/discovery/input/network_spec.yml` — Added `bmc_network` and `additional_subnets` examples.
- `src/discovery/plugins/modules/generate_pxe_mapping.py` — Updated to support multiple admin subnets and Magellan data.
- `src/discovery/plugins/modules/ome_server_inventory.py` — Fetches additional location parameters for xnames.
- `src/discovery/roles/ome_discovery/tasks/generate_pxe_mapping.yml` — Uses `admin_subnets` list.
- `src/discovery/roles/ome_discovery/tasks/generate_discovery_report.yml` — Adds xnames mapping summary.
- `src/discovery/roles/ome_discovery/tasks/main.yml` — Includes `generate_xnames_mapping.yml`.
- `src/orchestrator/plugins/modules/generate_xname_in_mapping_file.py` — Supports optional `xnames_mapping_file_path`.
- `src/orchestrator/roles/orchestrator_validations/tasks/validate_mapping_file.yml` — Passes `xnames_mapping_file_path`.

## Notes

- The Magellan mechanism does not require Dell OpenManage Enterprise (OME). It
  queries each BMC directly, which is useful when OME is not available.
- Admin IP addresses are derived from the BMC IP using the `admin_network` and
  `additional_subnets` definitions in `network_spec.yml`. The longest matching
  CIDR wins.
- InfiniBand IP addresses are derived from the BMC IP and the `ib_network`
  subnet when an InfiniBand adapter is detected.
