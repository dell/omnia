# Orchestrator -- Output Contract

**Domain**: `orchestrator` | **Collection**: `omnia.orchestrator` | **Last updated**: September 24, 2026

This document defines all output artifacts produced by the `orchestrator` domain.

---

## 1. functional_groups_config.yml

**Purpose**: Maps PXE mapping file entries into functional groups used by
OpenCHAMI Boot Service, Metadata Service, and node service configuration roles.

**Location**:
`$ORCHESTRATOR_DATA_PATH/output/$OMNIA_PROJECT_NAME/.data/functional_groups_config.yml`

When `ORCHESTRATOR_DATA_PATH` is unset, it resolves to
`$OMNIA_DATA_PATH/orchestrator`.

**Producer**: `orchestrator_functional_groups` role during `precheck`, `prepare`,
`provision`, and `execute`.

**Consumers**:
- `provision_common` and category provisioning plays — Boot Service and Metadata Service data per functional group
- `orchestrator_validations` — image validation per functional group
- Orchestrator provisioning plays — category and cluster deployment scoping
- `generate_inventories` — group-to-node metadata for published inventories

### Structure

```yaml
groups:
  rack01:
    parent: ""
  rack02:
    parent: "ABCD12"

functional_groups:
  - name: "slurm_control_node_rhel_10_0_x86_64"
    cluster_name: "slurm_cluster"
    group:
      - rack01
  - name: "slurm_node_rhel_10_0_x86_64"
    cluster_name: "slurm_cluster"
    group:
      - rack02
```

`groups` maps each PXE mapping `GROUP_NAME` to its optional
`PARENT_SERVICE_TAG` value.
Each `functional_groups[].group` list contains group names, not individual node
records. Node addresses and service tags remain in the PXE mapping and the
generated inventory artifacts.

---

## 2. OpenCHAMI Configuration Artifacts

Produced by `provision_common` and the category provisioning plays on the OIM
host. These flows reuse templates and task files housed under
`configure_ochami`.

### 2.1 Boot Service Parameters

**Location**: Configured through the OpenCHAMI Boot Service API (not file-based).
The `ochami` client exposes some of these operations under the `ochami bss`
command group; this does not represent a separately
deployed BSS service.

| Parameter | Source | Description |
|-----------|--------|-------------|
| `kernel` | `s3_configurations.endpoint_url` + `build_status.kernel` | S3 URL to vmlinuz |
| `initrd` | `s3_configurations.endpoint_url` + `build_status.initrd` | S3 URL to initramfs |
| Root image in `params` | `s3_configurations.endpoint_url` + `build_status.image` | S3 URL to rootfs |
| `params` | Boot Service template (`boot-svc.yaml.j2`) | Boot parameters including root image, cloud-init, network |

### 2.2 Metadata Service Configurations

The generated payloads below are published to Metadata Service, which renders
the cloud-init data requested by provisioned nodes.

| File | Scope | Description |
|------|-------|-------------|
| `ms-defaults.yaml` | Cluster | Cluster identity, SSH keys, and default metadata |
| `ms-group-common.yaml` | Shared groups | Metadata shared by all applicable nodes |
| `ms-group-<functional-group>.yaml` | Per functional group | Group-specific packages, mounts, and services |

These working files are generated under
`$OMNIA_DATA_PATH/openchami/workdir/metadata-service/`. Per-node hostnames are
published through the Metadata Service `instanceinfos` API from the generated
`hostname_<category>.yaml` artifacts.

---

## 3. Node Orchestration Files

**Location**: `$OMNIA_DATA_PATH/openchami/workdir/nodes/`

These are internal OpenCHAMI working artifacts rather than public
cross-domain contracts.

| Pattern | Purpose |
|---|---|
| `nodes_<category>.yaml` | Per-category node payload used for SMD registration and service configuration. |
| `hostname_<category>.yaml` | Per-category xname-to-hostname mapping. |
| `groups-<functional-group>.yml` | SMD membership payload for a functional group. |
| `groups-common-<group>.yml` | SMD payload for shared/common groups. |

---

## 4. Lifecycle Status Reports

Provisioning and PXE boot publish versioned, phase-specific reports under:

`$ORCHESTRATOR_DATA_PATH/output/$OMNIA_PROJECT_NAME/`

| File | Producer | Contract |
|------|----------|----------|
| `provisioning_report.yml` | Provision validation | SMD, Boot Service, Metadata Service, interface, and hostname registration results |
| `pxeboot_status.yml` | PXE boot | PXE initiation and optional fresh-boot/cloud-init verification for every selected node |
| `failed_nodes.json` | PXE boot | Failure-only view of the PXE report; written even when no node fails |
| `orchestrator_status.yml` | Provision and PXE boot | Stable aggregate view containing the latest provisioning and PXE phase states |

`provisioning_report.yml`, `pxeboot_status.yml`, and
`orchestrator_status.yml` use `schema_version: "1.1"` for metadata application
tracking. The failure-only report uses schema 1.0. A later
phase does not replace the aggregate report with a different shape. Instead, it updates
`last_completed_phase`, retains the provisioning result when available, and
adds the PXE result.

`failed_nodes.json` remains at schema 1.0 as a supported compatibility
contract for consumers that read the `failed_nodes` array. New integrations
should prefer `pxeboot_status.yml` or the aggregate `orchestrator_status.yml`.

### 4.1 Provisioning report

`provisioning_report.yml` reports whether the expected nodes, administrative
interfaces, Boot Service configurations, and Metadata Service configurations were
registered. Provisioning success does not mean that a node has booted or that
cloud-init completed; those conditions belong to the PXE phase.

Important fields include `overall_status`, `total_expected_nodes`,
`total_registered_nodes`, `success_count`, `failure_count`, `missing_nodes`,
`missing_admin_interfaces`, `identity_changed_nodes`,
`metadata_changed_nodes`, `reprovision_required_nodes`,
`stale_metadata_groups_deleted`, `inventory_source`, and `timestamp`.

### 4.2 PXE status and failed-node report

`pxeboot_status.yml` is always written. Its `nodes` list includes every node
selected for PXE boot. When node verification is enabled, each entry records
the verification method and structured cloud-init state:

```yaml
schema_version: "1.1"
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

`failed_nodes.json` provides the failure-only interface and flat node fields
alongside schema, run, inventory, verification, and structured cloud-init
data. Consumers may inspect only the `failed_nodes` array when summary fields
are not required.

When verification is disabled, successful iDRAC requests are recorded as
`pxe_initiated_unverified`; they are not reported as verified operating-system
boots.

### 4.3 Aggregate Orchestrator status

`orchestrator_status.yml` has one stable schema across phases. Its top-level
node fields include the provisioning `failure_reason`, and each node also
contains phase-specific `provisioning` and `pxeboot` objects. The `phases` map
records the status, counts, timestamp, and report filename for each lifecycle
phase.

After provisioning, the PXE phase is `not_run`. After PXE boot, the aggregate
status is failed when either the retained provisioning phase or the current
PXE phase failed. A provisioning report is retained only when its
`inventory_source` matches the active PXE inventory. If PXE boot is run without
a matching provisioning report, the provisioning phase is `not_run` and
per-node provisioning state is `unknown` rather than being inferred.

Each aggregate per-node record also exposes:

| Field | Meaning |
|---|---|
| `identity_changed` | Provisioning created the persistent Service Tag-to-XNAME Hardware Inventory binding during the current run. |
| `metadata_changed` | Desired node or group metadata differs from the last verified node application. |
| `running_state_updated` | PXE and node-registration/cloud-init verification confirmed the desired state was applied. |
| `reprovision_required` | Metadata is pending application; an ordinary provision run cannot clear this field. |

Provisioning preserves a previously pending `reprovision_required` value even
when a later reconciliation is idempotent. Only a successful PXE run with
node-registration/cloud-init verification clears `metadata_changed` and
`reprovision_required`. A PXE request without verification does not claim that
the running operating system was updated.

PXE inventories do not supply XNAME values. Before rebooting any server, the
PXE workflow resolves each Service Tag through SMD Hardware Inventory and uses
the resulting permanent XNAME for report correlation. If an identity is
missing, PXE fails before Redfish operations and directs the operator to run
the provision phase first.

---

## 5. Published Inventories

**Location**:
`$ORCHESTRATOR_DATA_PATH/output/$OMNIA_PROJECT_NAME/`

**Producer**: `generate_inventories` role after successful provisioning

| File | Purpose |
|---|---|
| `orchestrator_inventory.yml` | Ansible inventory grouped by functional group, including administrative addresses and optional Kubernetes VIP data. |
| `bmc_group_data.csv` | BMC inventory exported with BMC address, group name, and parent-group data. |

Telemetry may consume `orchestrator_inventory.yml` through its
`cluster_inventory` input. It does not consume the internal
`functional_groups_config.yml` file.

---

## 6. Deployed Services

The orchestrator deploys the following on OIM and compute nodes:

### 6.1 OpenCHAMI (on OIM)

OpenCHAMI 0.2.0 uses the Fabrica-managed units below. It does not deploy
standalone BSS, cloud-init-server, Hydra, or OPAAL services; Boot Service and
Metadata Service provide the corresponding boot and node-metadata functions.

| Service | Description |
|---------|-------------|
| `openchami.target` | Systemd target for all OpenCHAMI services |
| `openchami-internal-network.service`, `openchami-external-network.service`, `openchami-cert-internal-network.service`, and `openchami-jwt-internal-network.service` | Podman network units used by the Fabrica services |
| `smd.service` and `smd-init.service` | State Management Database API and initialization |
| `boot-service.service` | PXE boot configurations |
| `metadata-service.service` | Node metadata and cloud-init rendering |
| `tokensmith.service` | OpenCHAMI access-token service |
| `step-ca.service`, `acme-register.service`, `acme-deploy.service`, and `openchami-cert-trust.service` | Local CA and certificate lifecycle installed by the OpenCHAMI 0.2.0 package |
| `coresmd-coredhcp.service` | DHCP service backed by SMD data |
| `coresmd-coredns.service` | DNS service backed by SMD data |
| `haproxy.service` | TLS termination and API routing |
| `postgres.service` | Database backend for SMD |

### 6.2 Node Services (on compute nodes via cloud-init)

| Service | Condition | Description |
|---------|-----------|-------------|
| Kubernetes | `k8s_config` role | K8s cluster setup |
| Slurm | `slurm_config` role | Slurm scheduler |
| OpenLDAP client | OpenLDAP is enabled | Directory-service client configuration |
| Storage mounts | `mount_config` role | NFS/CIFS/local mounts |

---

## 7. Cleanup

Running full Orchestrator cleanup removes:

- OpenCHAMI containers and systemd units
- Boot Service and Metadata Service configurations
- Generated functional groups
- Ansible inventory
- Orchestrator credentials and their vault key by default

Pass `-e cleanup_credentials=false` to preserve credentials during full
cleanup. Use `--tags cleanup_credentials` for credential-only cleanup.

---

## 8. Consumers Summary

| Consumer Domain | What It Reads | Purpose |
|----------------|---------------|---------|
| Compute nodes (PXE) | Boot Service parameters and Metadata Service data | Boot and configure nodes |
| Orchestrator provisioning and validation roles | `functional_groups_config.yml`, category node files | Scope provisioning and validate registered nodes and images. |
| `generate_inventories` | `functional_groups_config.yml`, PXE mapping data, SMD data | Publish `orchestrator_inventory.yml` and `bmc_group_data.csv`. |
| Telemetry | `orchestrator_inventory.yml` when configured | Resolve the service Kubernetes VIP and source-node groups. |
