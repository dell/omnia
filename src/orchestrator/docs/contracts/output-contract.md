# Orchestrator — Output Contract

> **Last Updated**: Sep 8, 2026 | **Domain**: `orchestrator`

This document defines all output artifacts produced by the `orchestrator` domain.

---

## 1. functional_groups_config.yml

**Purpose**: Maps PXE mapping file entries into functional groups used by BSS, cloud-init, and service configuration roles.

**Location**:
`$OMNIA_DATA_PATH/orchestrator/output/$OMNIA_PROJECT_NAME/.data/functional_groups_config.yml`

**Producer**: `orchestrator_functional_groups` role during `precheck`, `prepare`,
`provision`, and `execute`.

**Consumers**:
- `configure_ochami` — BSS boot params per functional group
- `orchestrator_validations` — image validation per functional group
- `telemetry`, `slurm_config`, `k8s_config` — service deployment scoping

### Structure

```yaml
functional_groups:
  - name: "slurm_control_node_x86_64"
    nodes:
      - hostname: "node001"
        admin_ip: "10.5.0.101"
        admin_mac: "aa:bb:cc:dd:ee:01"
        bmc_ip: "10.3.0.101"
        service_tag: "ABC1234"
  - name: "slurm_node_x86_64"
    nodes:
      - hostname: "node002"
        admin_ip: "10.5.0.102"
        ...
```

---

## 2. OpenCHAMI Configuration Artifacts

Produced by `configure_ochami` role on the OIM host.

### 2.1 BSS Boot Parameters

**Location**: Configured via OpenCHAMI BSS API (not file-based)

| Parameter | Source | Description |
|-----------|--------|-------------|
| `kernel` | `s3_configurations.endpoint_url` + `build_status.kernel` | S3 URL to vmlinuz |
| `initrd` | `s3_configurations.endpoint_url` + `build_status.initrd` | S3 URL to initramfs |
| Root image in `params` | `s3_configurations.endpoint_url` + `build_status.image` | S3 URL to rootfs |
| `params` | BSS template (`boot-svc.yaml.j2`) | Boot parameters including root image, cloud-init, network |

### 2.2 Cloud-Init Configurations

| File | Scope | Description |
|------|-------|-------------|
| `cloud-init-default.yaml` | Global | Default cloud-init for all nodes |
| `cloud-init-group-*.yaml` | Per functional group | Group-specific packages, mounts, services |
| `cloud-init-node-*.yaml` | Per node | Node-specific hostname, network, SSH keys |

---

## 3. Node Orchestration Files

### 3.1 nodes.yaml

**Location**: Generated on OIM by `configure_ochami`

**Purpose**: Master node inventory for OpenCHAMI SMD registration

### 3.2 hostname.yaml

**Purpose**: Hostname assignments for xname-to-hostname mapping

### 3.3 groups.yaml

**Purpose**: Functional group definitions for OpenCHAMI

---

## 4. Lifecycle Status Reports

Provisioning and PXE boot publish versioned, phase-specific reports under:

`$OMNIA_DATA_PATH/orchestrator/output/$OMNIA_PROJECT_NAME/`

| File | Producer | Contract |
|------|----------|----------|
| `provisioning_report.yml` | Provision validation | SMD, BSS, Metadata Service, interface, and hostname registration results |
| `pxeboot_status.yml` | PXE boot | PXE initiation and optional fresh-boot/cloud-init verification for every selected node |
| `failed_nodes.json` | PXE boot | Compatibility failure-only view of the PXE report; written even when no node fails |
| `orchestrator_status.yml` | Provision and PXE boot | Stable aggregate view containing the latest provisioning and PXE phase states |

All four reports use `schema_version: "1.0"`. A later phase does not replace the
aggregate report with a different schema. Instead, it updates
`last_completed_phase`, retains the provisioning result when available, and
adds the PXE result.

### 4.1 Provisioning report

`provisioning_report.yml` reports whether the expected nodes, administrative
interfaces, BSS boot configurations, and Metadata Service configurations were
registered. Provisioning success does not mean that a node has booted or that
cloud-init completed; those conditions belong to the PXE phase.

Important fields include `overall_status`, `total_expected_nodes`,
`total_registered_nodes`, `success_count`, `failure_count`, `missing_nodes`,
`missing_admin_interfaces`, `inventory_source`, and `timestamp`.

### 4.2 PXE status and failed-node compatibility report

`pxeboot_status.yml` is always written. Its `nodes` list includes every node
selected for PXE boot. When node verification is enabled, each entry records
the verification method and structured cloud-init state:

```yaml
schema_version: "1.0"
phase: pxeboot
overall_status: failed
verification_enabled: true
nodes:
  - xname: x1000c0s1b0n0
    admin_ip: 192.168.1.54
    bmc_ip: 172.20.44.54
    status: failed
    failure_stage: node_registration
    verification_state: cloud_init_error
    verification_method: ssh_cloud_init
    cloud_init:
      status: done
      extended_status: degraded done
      boot_status_code: enabled-by-kernel-command-line
      errors: []
      recoverable_errors: {}
```

`failed_nodes.json` retains the existing failure-only interface and legacy
flat fields, while adding the same schema, run, inventory, verification, and
structured cloud-init data. Consumers that only inspect `failed_nodes` remain
compatible.

When verification is disabled, successful iDRAC requests are recorded as
`pxe_initiated_unverified`; they are not reported as verified operating-system
boots.

### 4.3 Aggregate Orchestrator status

`orchestrator_status.yml` has one stable schema across phases. Its top-level
node fields, including the provisioning `failure_reason`, remain available for
compatibility, and each node also contains phase-specific `provisioning` and
`pxeboot` objects. The `phases` map records the status, counts, timestamp, and
report filename for each lifecycle phase.

After provisioning, the PXE phase is `not_run`. After PXE boot, the aggregate
status is failed when either the retained provisioning phase or the current
PXE phase failed. A provisioning report is retained only when its
`inventory_source` matches the active PXE inventory. If PXE boot is run without
a matching provisioning report, the provisioning phase is `not_run` and
per-node provisioning state is `unknown` rather than being inferred.

For custom PXE inventories that do not contain XNAME values, PXE results are
still reported by BMC and administrative address, while provisioning
correlation remains `unknown`.

---

## 5. Ansible Inventory

**Location**: `$OMNIA_DATA_PATH/hosts`

**Producer**: `passwordless_ssh` role

**Purpose**: Dynamic Ansible inventory for service configuration plays

---

## 6. Deployed Services

The orchestrator deploys the following on OIM and compute nodes:

### 6.1 OpenCHAMI (on OIM)

| Service | Description |
|---------|-------------|
| `openchami.target` | Systemd target for all OpenCHAMI services |
| SMD | State Management Daemon — node inventory |
| BSS | Boot Script Service — PXE boot parameters |
| cloud-init-server | Cloud-init metadata service |
| CoreDHCP | DHCP server for PXE boot |
| CoreDNS | DNS server (when `dns_enabled`) |
| HAProxy | TLS termination proxy |
| Hydra | OAuth2 provider |
| PostgreSQL | Database backend |

### 6.2 Node Services (on compute nodes via cloud-init)

| Service | Condition | Description |
|---------|-----------|-------------|
| Kubernetes | `k8s_config` role | K8s cluster setup |
| Slurm | `slurm_config` role | Slurm scheduler |
| OpenLDAP | `openldap` role | Directory service |
| Telemetry | `telemetry` role | Monitoring stack |
| Storage mounts | `mount_config` role | NFS/CIFS/local mounts |

---

## 7. Cleanup

Running `cleanup_orchestrator.yml` removes:
- OpenCHAMI containers and systemd units
- BSS/cloud-init configurations
- Generated functional groups
- Ansible inventory
- Credentials (opt-in with `--tags credentials`)

---

## 8. Consumers Summary

| Consumer Domain | What It Reads | Purpose |
|----------------|---------------|---------|
| Compute nodes (PXE) | BSS boot params + cloud-init | Boot and configure nodes |
| `telemetry` role | `functional_groups_config.yml` | Deploy telemetry per group |
| `slurm_config` role | `functional_groups_config.yml`, `nodes.yaml` | Configure Slurm partitions |
| `k8s_config` role | `functional_groups_config.yml`, `nodes.yaml` | Configure K8s clusters |
