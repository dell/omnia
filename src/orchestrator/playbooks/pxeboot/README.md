# Set PXE Boot Utility

## Overview

The PXE boot utility configures Dell iDRAC nodes to boot from PXE and can
verify that every node performed a fresh boot and completed cloud-init.

## Features

- **CSV-based input**: Parses the named fields in `pxe_mapping_file.csv` and validates unique BMC and admin addresses
- **Orchestrator credential integration**: Reuses BMC credentials from orchestrator credential store
- **Parallel node verification**: Checks SSH, boot freshness, and cloud-init independently across nodes
- **Structured failures**: Records unreachable, stale-boot, pending, terminal cloud-init, and timeout states
- **Conditional execution**: Can be enabled/disabled via configuration flag
- **Tag-based execution**: Run standalone or as part of orchestrator workflow

## Prerequisites

1. **Orchestrator credentials**: BMC credentials must be provisioned first
   ```bash
   ansible-playbook orchestrator.yml --tags prepare
   ```

2. **PXE mapping file**: `pxe_mapping_file.csv` must exist in orchestrator input directory
   - Location: `$OMNIA_DATA_PATH/orchestrator/input/$OMNIA_PROJECT_NAME/pxe_mapping_file.csv`
   - Required columns: `BMC_IP`, `ADMIN_IP`, `HOSTNAME`, and `SERVICE_TAG`
   - Column order is not significant

3. **Configuration file**: `set_pxe_boot_config.yml` (optional, uses defaults if missing)
   - Location: `$OMNIA_DATA_PATH/orchestrator/input/$OMNIA_PROJECT_NAME/set_pxe_boot_config.yml`

## Usage

### Standalone Execution

```bash
cd src/orchestrator/playbooks

# Basic PXE boot with node-registration verification (default)
ansible-playbook pxeboot/pxeboot.yml

# Disable node-registration verification (PXE initiation is reported as unverified)
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
node_registration_retries: 120       # Retry count per node
node_registration_delay: 15          # Delay between retries (seconds)

# PXE boot options
restart_host: true
force_restart: true
boot_source_override_enabled: continuous  # or: once, disabled
boot_source_override_target: pxe         # or: uefi_http, hdd, etc.
```

**Note**: Legacy variable names (`enable_phone_home`, `phone_home_pause_minutes`, etc.) are supported for backward compatibility but deprecated.

`continuous` preserves the established Omnia behavior, but it also makes later
restarts select PXE until the iDRAC override is changed. Use `once` when only
the current provisioning boot should use PXE.

## Input Files

### pxe_mapping_file.csv Format

```csv
FUNCTIONAL_GROUP_NAME,GROUP_NAME,SERVICE_TAG,PARENT_SERVICE_TAG,HOSTNAME,ADMIN_MAC,ADMIN_IP,BMC_MAC,BMC_IP,IB_NIC_NAME,IB_IP
slurm_control_node_x86_64,grp0,ABCD12,,node1,aa:bb:cc:dd:ee:ff,172.16.1.10,xx:yy:zz:aa:bb:cc,172.17.1.10,,
slurm_node_x86_64,grp1,ABCD34,,node2,aa:bb:cc:dd:ee:gg,172.16.1.11,xx:yy:zz:aa:bb:dd,172.17.1.11,,
```

**Required columns:**

- `HOSTNAME`: node hostname
- `SERVICE_TAG`: node service tag
- `ADMIN_IP`: unique admin-network address used for SSH verification
- `BMC_IP`: unique iDRAC address used for Redfish operations

The parser follows CSV quoting rules. Invalid or duplicate BMC/admin addresses
fail before any Redfish operation is attempted.

## Output

The play writes all lifecycle reports under
`$OMNIA_DATA_PATH/orchestrator/output/$OMNIA_PROJECT_NAME/`, including on a
successful run:

- `pxeboot_status.yml`: complete PXE and verification result for every node.
- `failed_nodes.json`: failure-only compatibility report; `failed_nodes` is an
  empty array when all nodes succeed.
- `orchestrator_status.yml`: stable aggregate of provisioning and PXE phase
  status. An existing `provisioning_report.yml` is retained and correlated by
  XNAME only when its `inventory_source` matches the active PXE inventory.

The aggregate schema is not replaced by a phase-specific schema. Its
`last_completed_phase` changes to `pxeboot`, and its `phases` map retains the
provisioning status and adds the PXE status.

### Success

- Exit code: `0`
- `pxeboot_status.yml` reports `overall_status: success`.
- `failed_nodes.json` contains an empty `failed_nodes` array.

### Failure

- Exit code: `2`
- Output file: `failed_nodes.json` with details:

```json
{
  "schema_version": "1.0",
  "phase": "pxeboot",
  "run_id": "1788863400",
  "timestamp": "2026-08-25T10:30:00Z",
  "total_nodes": 10,
  "failure_count": 2,
  "success_count": 8,
  "verification_enabled": true,
  "unverified_count": 0,
  "failed_nodes": [
    {
      "bmc_ip": "172.17.1.10",
      "admin_ip": "172.16.1.10",
      "xname": "x1000c0s1b0n0",
      "hostname": "node1",
      "service_tag": "ABCD12",
      "failure_stage": "pxe_boot",
      "status": "failed",
      "verification_method": "not_started",
      "verification_state": "not_started",
      "cloud_init": {},
      "error": "iDRAC timeout"
    },
    {
      "bmc_ip": "172.17.1.11",
      "admin_ip": "172.16.1.11",
      "xname": "x1000c0s2b0n0",
      "hostname": "node2",
      "service_tag": "EFGH34",
      "failure_stage": "node_registration",
      "status": "failed",
      "verification_method": "ssh_cloud_init",
      "verification_state": "cloud_init_error",
      "cloud_init": {
        "status": "done",
        "extended_status": "degraded done",
        "errors": [],
        "recoverable_errors": {}
      },
      "error": "status: error;errors: scripts_user failed"
    }
  ]
}
```

Per-node status values in `orchestrator_status.yml` and `pxeboot_status.yml`
are:

- `success`: PXE initiation, fresh boot, and cloud-init completion verified.
- `failed`: iDRAC PXE or node-registration verification failed.
- `pxe_initiated_unverified`: iDRAC accepted the operation while verification
  was intentionally disabled.

## Node-Registration Verification

When `enable_node_registration: true`:

1. **Initial wait**: Waits `node_registration_pause_minutes` for nodes to boot
2. **Parallel polling**: Uses one SSH session per node attempt to read uptime and `cloud-init status --long`
3. **Freshness**: Rejects nodes whose calculated boot time predates the current PXE request
4. **Completion**: Passes only when cloud-init reports `done`
5. **Terminal failure**: Stops retrying a node when cloud-init reports `error`, `degraded`, or `disabled`
6. **Timeout**: Records the final state after the configured attempts are exhausted
7. **Concurrency**: Checks nodes concurrently, bounded by Ansible's `forks` setting
8. **Exclusions**: Does not verify nodes whose iDRAC PXE operation failed

**Boot freshness check**: The playbook verifies that nodes actually rebooted after PXE boot was triggered by checking `/proc/uptime` via SSH. This prevents false positives from nodes that have been up for days.

The OIM verifies each node directly. OpenCHAMI Metadata Service's
`/phone-home` route belongs to optional WireGuard bootstrap teardown and is
not used as a generic cloud-init completion callback.

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

**Solution**: Ensure all required named columns are present and every row has
unique, valid `BMC_IP` and `ADMIN_IP` values.

### Node-registration timeout

```
FAILED! => Node-registration failures: 172.16.1.10, 172.16.1.11
```

**Solution**:

- Verify passwordless root SSH from the OIM to the node admin address.
- Run `cloud-init status --long` and inspect the recorded detail in `failed_nodes.json`.
- Confirm that the node boot time is newer than the PXE request.
- Increase retries only when cloud-init is legitimately still running.

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
6. **Node Registration**: Verify fresh boot and cloud-init concurrently (if enabled)
7. **Final Report**: Generate `pxeboot_status.yml`, `failed_nodes.json`, and
   the aggregate `orchestrator_status.yml`, then exit

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

## Node completion signal

Omnia does not publish a generic cloud-init `phone_home` fragment. The
Metadata Service `/phone-home` route removes a temporary WireGuard peer when
WireGuard bootstrap is configured; the deployed Omnia service does not enable
that controller. Per-node completion is determined directly through SSH,
fresh-boot validation, and cloud-init state.

## Verification-disabled status

With `enable_node_registration: false`, a successful iDRAC operation is stored
as `pxe_initiated_unverified`. The overall play can complete successfully, but
the report does not claim that the operating system booted or cloud-init
completed.

## Related Documentation

- Orchestrator README: `src/orchestrator/README.md`
- PXE mapping file example: `examples/pxe_mapping_file.csv`
- Orchestrator configuration: `src/orchestrator/input/orchestrator_config.yml`
