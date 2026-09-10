# Discovery — Output Contract

> **Last Updated**: Sep 9, 2026 | **Domain**: `discovery`

This document defines all output artifacts produced by the `discovery` domain.

---

## 1. bmc_pxe_mapping_file_\<timestamp\>.csv

**Purpose**: Maps discovered servers to PXE boot parameters for orchestrator consumption.

**Location**: `$OMNIA_DATA_PATH/discovery/output/<project_name>/bmc_pxe_mapping_file_<timestamp>.csv`

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

**Location**: `$OMNIA_DATA_PATH/discovery/output/<project_name>/bmc_discovery_report_<timestamp>.csv`

**Producer**: `ome_discovery` role → `generate_discovery_report` module

**Consumer**: Operator (informational only)

### Contents

- BMC, Ethernet, and InfiniBand NIC link status per server
- Used to verify network connectivity before provisioning

---

## 3. discovery_status.yml

**Purpose**: Records the latest Discovery execution outcome, mechanism, output
mapping path, discovered-server count, and failure details when applicable.

**Location**: `$OMNIA_DATA_PATH/discovery/output/<project_name>/discovery_status.yml`

**Producer**: `ome_discovery` role

**Consumer**: Operator and automation reporting

---

## 4. Data Flow to Orchestrator

```
Discovery Output                              Orchestrator Input
──────────────────                             ──────────────────
bmc_pxe_mapping_file_<ts>.csv ──(manual copy)──► pxe_mapping_file.csv
                                                 $OMNIA_DATA_PATH/orchestrator/input/<project>/
```

The mapping file must be **manually reviewed and copied** to the orchestrator
input directory. This deliberate handoff ensures operators can review/edit
node assignments (HOSTNAME, FUNCTIONAL_GROUP_NAME, GROUP_NAME) before
provisioning.

---

## 5. Cleanup

The supported cleanup does not remove or create the current-project output
directory. When the directory exists, cleanup removes every entry inside it,
including timestamped mappings, the latest symlink, reports, hidden
directories, and status files, and leaves the empty directory in place:

```bash
ansible-playbook playbooks/discovery.yml --tags cleanup
```

The same command removes `discovery_credentials.yml` and its vault key by
default. Preserve those two input artifacts while still removing all outputs:

```bash
ansible-playbook playbooks/discovery.yml --tags cleanup \
  -e cleanup_credentials=false
```

All other Discovery input files are preserved in both cases.
Use `--tags cleanup_credentials` to remove only the credential file and vault
key without changing the Discovery output contents.
An explicit `cleanup_credentials` tag takes precedence over
`cleanup_credentials=false`.

Cleanup affects only the project selected by `OMNIA_PROJECT_NAME`. Discovery
log files and all non-credential input files are preserved.

Copy any mapping required by Orchestrator to its input project directory before
running full Discovery cleanup. Cleanup removes both timestamped mappings and
the canonical latest-mapping symlink from the Discovery output directory.
