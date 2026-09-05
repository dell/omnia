# Set PXE Boot Utility

## Overview

The `set_pxe_boot` utility configures Dell iDRAC nodes to boot from PXE and optionally verifies successful provisioning via cloud-init node-registration callbacks.

## Features

- **CSV-based input**: Uses `pxe_mapping_file.csv` for node inventory (no manual inventory files)
- **Orchestrator credential integration**: Reuses BMC credentials from orchestrator credential store
- **Node-registration verification**: Waits for nodes to boot and send cloud-init callbacks
- **Conditional execution**: Can be enabled/disabled via configuration flag
- **Tag-based execution**: Run standalone or as part of orchestrator workflow

## Prerequisites

1. **Orchestrator credentials**: BMC credentials must be provisioned first
   ```bash
   ansible-playbook orchestrator.yml --tags prepare
   ```

2. **PXE mapping file**: `pxe_mapping_file.csv` must exist in orchestrator input directory
   - Location: `$OMNIA_DATA_PATH/orchestrator/input/$OMNIA_PROJECT_NAME/pxe_mapping_file.csv`
   - Required columns: `BMC_IP` (column 9), `ADMIN_IP` (column 7), `HOSTNAME` (column 5)

3. **Configuration file**: `set_pxe_boot_config.yml` (optional, uses defaults if missing)
   - Location: `$OMNIA_DATA_PATH/orchestrator/input/$OMNIA_PROJECT_NAME/set_pxe_boot_config.yml`

## Usage

### Standalone Execution

```bash
cd src/orchestrator/playbooks

# Basic PXE boot with node-registration verification (default)
ansible-playbook pxeboot/pxeboot.yml

# Disable node-registration verification (faster, no wait)
ansible-playbook pxeboot/pxeboot.yml -e enable_node_registration=false

# Override node-registration timing
ansible-playbook pxeboot/pxeboot.yml \
  -e node_registration_pause_minutes=5 \
  -e node_registration_retries=180 \
  -e node_registration_delay=10
```

### Via Orchestrator Workflow

```bash
cd src/orchestrator/playbooks

# Run orchestrator with pxeboot tag
ansible-playbook orchestrator.yml --tags pxeboot
```

## Configuration

### set_pxe_boot_config.yml

```yaml
# Node-registration verification
enable_node_registration: true
node_registration_pause_minutes: 3   # Initial wait before polling
node_registration_retries: 120       # Max retries (120 × 15s = 30 min)
node_registration_delay: 15          # Delay between retries (seconds)

# PXE boot options
restart_host: true
force_restart: true
boot_source_override_enabled: continuous  # or: once, disabled
boot_source_override_target: pxe         # or: uefi_http, hdd, etc.
```

**Note**: Legacy variable names (`enable_phone_home`, `phone_home_pause_minutes`, etc.) are supported for backward compatibility but deprecated.

## Input Files

### pxe_mapping_file.csv Format

```csv
FUNCTIONAL_GROUP_NAME,GROUP_NAME,SERVICE_TAG,PARENT_SERVICE_TAG,HOSTNAME,ADMIN_MAC,ADMIN_IP,BMC_MAC,BMC_IP,IB_NIC_NAME,IB_IP
slurm_control_node_x86_64,grp0,ABCD12,,node1,aa:bb:cc:dd:ee:ff,172.16.1.10,xx:yy:zz:aa:bb:cc,172.17.1.10,,
slurm_node_x86_64,grp1,ABCD34,,node2,aa:bb:cc:dd:ee:gg,172.16.1.11,xx:yy:zz:aa:bb:dd,172.17.1.11,,
```

**Required columns:**
- Column 5: `HOSTNAME` (node hostname)
- Column 7: `ADMIN_IP` (admin network IP for node-registration verification)
- Column 9: `BMC_IP` (iDRAC IP address)

## Output

### Success

- Exit code: `0`
- Output file: `$OMNIA_DATA_PATH/orchestrator/output/$OMNIA_PROJECT_NAME/failed_nodes.json`
  - Empty `failed_nodes` array if all nodes succeed

### Failure

- Exit code: `2`
- Output file: `failed_nodes.json` with details:

```json
{
  "timestamp": "2026-08-25T10:30:00Z",
  "total_nodes": 10,
  "failure_count": 2,
  "success_count": 8,
  "failed_nodes": [
    {
      "bmc_ip": "172.17.1.10",
      "admin_ip": "172.16.1.10",
      "hostname": "node1",
      "service_tag": "ABCD12",
      "failure_stage": "pxe_boot",
      "status": "failed",
      "error": "iDRAC timeout"
    }
  ]
}
```

## Node-Registration Verification

When `enable_node_registration: true`:

1. **Initial wait**: Waits `node_registration_pause_minutes` for nodes to boot
2. **Polling**: Checks SSH port reachability and metadata-service journal for node-registration callbacks
3. **Timeout**: Fails if nodes don't register within `node_registration_retries × node_registration_delay` seconds
4. **Exclusions**: Nodes that failed PXE boot are excluded from node-registration verification

**Boot freshness check**: The playbook verifies that nodes actually rebooted after PXE boot was triggered by checking `/proc/uptime` via SSH. This prevents false positives from nodes that have been up for days.

**Log pattern searched**: `"phone-home"` (cloud-init standard, not renamed)

## Troubleshooting

### BMC credentials not found

```
FAILED! => BMC credentials not found. Run orchestrator credentials first
```

**Solution**: Run `ansible-playbook orchestrator.yml --tags prepare` to provision credentials.

### pxe_mapping_file.csv not found

```
FAILED! => pxe_mapping_file.csv not found at $OMNIA_DATA_PATH/orchestrator/input/$OMNIA_PROJECT_NAME/pxe_mapping_file.csv
```

**Solution**: Copy `pxe_mapping_file.csv` to the orchestrator input directory.

### No BMC hosts found in CSV

```
FAILED! => No BMC hosts found in pxe_mapping_file.csv
```

**Solution**: Ensure column 9 (`BMC_IP`) is populated in the CSV file.

### Node-registration timeout

```
FAILED! => Node-registration failures: 172.16.1.10, 172.16.1.11
```

**Solution**:
- Check metadata-service is running on OIM
- Verify admin network connectivity
- Increase `node_registration_retries` or disable node-registration with `-e enable_node_registration=false`

## Examples

### Example 1: Quick PXE boot without verification

```bash
ansible-playbook pxeboot/pxeboot.yml -e enable_node_registration=false
```

### Example 2: Extended node-registration timeout (1 hour)

```bash
ansible-playbook pxeboot/pxeboot.yml \
  -e node_registration_pause_minutes=10 \
  -e node_registration_retries=240 \
  -e node_registration_delay=15
```

### Example 3: Run as part of orchestrator

```bash
ansible-playbook orchestrator.yml --tags pxeboot
```

## Architecture

### Workflow

1. **Setup**: Load orchestrator environment and configuration
2. **Credentials**: Load BMC credentials from orchestrator credential store
3. **Inventory**: Parse `pxe_mapping_file.csv` and build dynamic BMC inventory
4. **PXE Boot**: Set PXE boot on each iDRAC and restart nodes
5. **Report**: Collect PXE boot failures
6. **Node-Registration**: Wait for cloud-init callbacks (if enabled)
7. **Final Report**: Generate `failed_nodes.json` and exit

### Roles Used

- `orchestrator_setup`: Environment and path resolution
- `orchestrator_common`: Credential decryption and loading
- `idrac_pxe_boot`: iDRAC PXE boot configuration and restart
- `verify_node_registration`: Cloud-init node-registration verification

## Migration from utils Domain

This utility was moved from `src/utils` to `src/orchestrator` in Omnia 2.2+.

**Old path**: `src/utils/playbooks/set_pxe_boot.yml`
**New path**: `src/orchestrator/playbooks/pxeboot/pxeboot.yml`

**Key changes**:
- Uses `pxe_mapping_file.csv` instead of inventory files
- Uses orchestrator credentials (no separate credential collection)
- Conditional execution via `enable_pxe_boot` flag
- Tag-based execution: `--tags pxeboot`

## Related Documentation

- Orchestrator README: `src/orchestrator/README.md`
- PXE mapping file example: `examples/pxe_mapping_file.csv`
- Orchestrator configuration: `src/orchestrator/input/orchestrator_config.yml`
