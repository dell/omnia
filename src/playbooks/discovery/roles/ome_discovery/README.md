# OME Discovery Role

## Overview
Collects server inventory from Dell OpenManage Enterprise (OME) and generates a BMC PXE mapping file (`bmc_pxe_mapping_file.csv`) in the `input/` directory.

## Purpose
- Authenticate with OME and store credentials securely in Ansible Vault
- Collect server inventory including service tags, iDRAC details, and NIC information
- Generate `bmc_pxe_mapping_file.csv` in the `input/` directory for review

## Workflow
1. Run discovery: `ansible-playbook discovery/discovery.yml -e "discovery_mechanism=ome"`
2. Review and edit `input/bmc_pxe_mapping_file.csv` (update hostnames, groups, etc.)
3. Rename or copy it to `input/pxe_mapping_file.csv`
4. Run provision: `ansible-playbook provision/provision.yml`

## Collected Information
For each server discovered in OME:
- **SERVICE_TAG** - Dell service tag identifier
- **BMC_IP** - iDRAC management IP address
- **BMC_MAC** - iDRAC MAC address
- **BMC_HOSTNAME** - iDRAC hostname
- **ADMIN_MAC** - First Ethernet NIC MAC address
- **ADMIN_IP** - Calculated from iDRAC IP (second octet + 1)

## Generated File: `input/bmc_pxe_mapping_file.csv`
```csv
FUNCTIONAL_GROUP_NAME,GROUP_NAME,SERVICE_TAG,PARENT_SERVICE_TAG,HOSTNAME,ADMIN_MAC,ADMIN_IP,BMC_MAC,BMC_IP,BMC_HOSTNAME
compute_node,grp0,ABC1234,,nid00001,AA:BB:CC:DD:EE:10,10.102.1.10,AA:BB:CC:DD:EE:01,10.101.1.10,idrac-server01
```

> **Note:** Review and edit this file, then copy/rename to `input/pxe_mapping_file.csv` before running `provision.yml`.

## Usage
```bash
ansible-playbook discovery/discovery.yml -e "discovery_mechanism=ome"
```

## Credential Handling
- On first run, prompts for OME IP, username, and password
- Credentials are stored encrypted in `.vault/ome_credentials.yml`
- Subsequent runs use stored credentials automatically

## Variables
| Variable | Default | Description |
|----------|---------|-------------|
| `default_functional_group` | `compute_node` | Functional group for all discovered nodes |
| `default_group_name` | `grp0` | Group name for all discovered nodes |
| `hostname_prefix` | `nid` | Prefix for generated hostnames |
| `hostname_start_number` | `1` | Starting number for hostnames |
| `hostname_padding` | `5` | Zero-padding for hostname numbers |

## Output
BMC PXE mapping file is generated at: `input/bmc_pxe_mapping_file.csv`

After reviewing and editing, copy or rename to `input/pxe_mapping_file.csv` before running `provision/provision.yml`.
