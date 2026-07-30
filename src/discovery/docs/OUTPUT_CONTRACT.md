# Discovery — Output Contract

> **Last Updated**: Jul 22, 2026 | **Domain**: `discovery`

This document defines all output artifacts produced by the `discovery` domain.

---

## 1. bmc_pxe_mapping_file_\<timestamp\>.csv

**Purpose**: Maps discovered servers to PXE boot parameters for orchestrator consumption.

**Location**: `/opt/omnia/output/<project_name>/discovery/bmc_pxe_mapping_file_<timestamp>.csv`

**Producer**: `ome_discovery` role → `generate_pxe_mapping` module

**Consumer**: Operator (manual review) → Orchestrator domain (after copy)

### Schema

| Column | Type | Description |
|--------|------|-------------|
| `FUNCTIONAL_GROUP_NAME` | string | Node functional group (e.g., `slurm_node_aarch64`) |
| `GROUP_NAME` | string | Scalable Unit / group identifier (e.g., `grp0`) |
| `SERVICE_TAG` | string | Dell server service tag |
| `PARENT_SERVICE_TAG` | string | Parent node service tag (for child nodes) |
| `HOSTNAME` | string | Generated hostname (e.g., `nid00001`) |
| `ADMIN_MAC` | string | Admin NIC MAC address |
| `ADMIN_IP` | string | Admin IP (derived from admin_subnet + BMC IP) |
| `BMC_MAC` | string | BMC/iDRAC MAC address |
| `BMC_IP` | string | BMC/iDRAC IP address |
| `BMC_HOSTNAME` | string | BMC hostname |
| `IB_NIC_NAME` | string | InfiniBand NIC FQDD (if present) |
| `IB_IP` | string | InfiniBand IP (derived from ib_subnet + BMC IP) |

### Symlink

A symlink `bmc_pxe_mapping_file.csv` always points to the latest timestamped file.

---

## 2. bmc_discovery_report_\<timestamp\>.csv

**Purpose**: NIC link status report for operator review. Not consumed programmatically.

**Location**: `/opt/omnia/output/<project_name>/discovery/bmc_discovery_report_<timestamp>.csv`

**Producer**: `ome_discovery` role → `generate_discovery_report` module

**Consumer**: Operator (informational only)

### Contents

- BMC, Ethernet, and InfiniBand NIC link status per server
- Used to verify network connectivity before provisioning

---

## 3. Data Flow to Orchestrator

```
Discovery Output                              Orchestrator Input
──────────────────                             ──────────────────
bmc_pxe_mapping_file_<ts>.csv ──(manual copy)──► pxe_mapping_file.csv
                                                 /opt/omnia/input/<project>/orchestrator/
```

The mapping file must be **manually reviewed and copied** to the orchestrator
input directory. This deliberate handoff ensures operators can review/edit
node assignments (HOSTNAME, FUNCTIONAL_GROUP_NAME, GROUP_NAME) before
provisioning.

---

## 4. Cleanup

Discovery outputs are timestamped and accumulate. To clean up:

```bash
rm -f /opt/omnia/output/<project>/discovery/bmc_pxe_mapping_file*.csv
rm -f /opt/omnia/output/<project>/discovery/bmc_discovery_report*.csv
```
