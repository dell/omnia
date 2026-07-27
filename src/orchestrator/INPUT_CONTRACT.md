# Orchestrator — Input Contract

> **Last Updated**: Jul 22, 2026 | **Domain**: `orchestrator`

This document defines all input files consumed by the `orchestrator` domain.

---

## 1. orchestrator_config.yml

**Purpose**: Per-domain input configuration for orchestrator.

**Location**: `input/project_default/orchestrator/orchestrator_config.yml`

**Owner**: User (manually configured)

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `pxe_mapping_file_path` | string | Yes | — | Path to PXE mapping CSV (from discovery output) |
| `image_build_manager_output_path` | string | No | `output/project_default/image_build_manager/build_status.yml` | Path to `build_status.yml` |
| `language` | string | No | `"en-US"` | Language for provisioned nodes |
| `default_lease_time` | int | No | `86400` | DHCP lease time (seconds) |
| `dns_enabled` | bool | No | `false` | Enable CoreDNS configuration |
| `kernel_version_override` | string | No | `""` | Specific kernel version for boot images |
| `additional_cloud_init_config_file` | string | No | `""` | Extra cloud-init config path |

---

## 2. pxe_mapping_file.csv (External Contract from Discovery)

**Purpose**: Primary data contract between Discovery and Orchestrator domains.

**Location**: `input/project_default/orchestrator/pxe_mapping_file.csv`

**Producer**: `discovery` domain (output: `bmc_pxe_mapping_file.csv`)

**Consumer**: `orchestrator_functional_groups` role, `orchestrator_validations` role

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| `FUNCTIONAL_GROUP_NAME` | string | Yes | Node role (e.g., `slurm_node_aarch64`) |
| `GROUP_NAME` | string | Yes | Scalable Unit / logical group |
| `SERVICE_TAG` | string | Yes | Dell server service tag |
| `PARENT_SERVICE_TAG` | string | No | Parent node service tag |
| `HOSTNAME` | string | Yes | Assigned hostname |
| `ADMIN_MAC` | string | Yes | Admin NIC MAC address |
| `ADMIN_IP` | string | Yes | Admin network IP |
| `BMC_MAC` | string | No | BMC/iDRAC MAC address |
| `BMC_IP` | string | No | BMC/iDRAC IP address |
| `IB_NIC_NAME` | string | No | InfiniBand NIC FQDD |
| `IB_IP` | string | No | InfiniBand IP |

---

## 3. network_spec.yml

**Purpose**: Full network specification for DHCP/PXE/DNS configuration.

**Location**: `input/project_default/orchestrator/network_spec.yml`

**Owner**: User (manually configured)

**Key Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `Networks.admin_network.primary_oim_admin_ip` | string | Yes | OIM admin IP |
| `Networks.admin_network.oim_nic_name` | string | Yes | OIM NIC name |
| `Networks.admin_network.netmask_bits` | string | Yes | Netmask bits |
| `Networks.admin_network.dynamic_range` | string | Yes | DHCP dynamic range (e.g., `10.5.0.100-10.5.0.200`) |
| `Networks.admin_network.router` | string | Yes | Default gateway |
| `Networks.admin_network.dns` | list | No | DNS forwarders |
| `Networks.admin_network.additional_subnets` | list | No | Multi-subnet support |

---

## 4. build_status.yml (Upstream Dependency)

**Purpose**: Output from `image_build_manager` domain consumed as input by orchestrator.

**Location**: `output/project_default/image_build_manager/build_status.yml`
(or custom path via `image_build_manager_output_path` in `orchestrator_config.yml`)

**Producer**: `image_build_manager` domain

**Consumer**: `configure_s3_access.yml` (Step 4a)

### Structure

```yaml
overall_status: "success"

s3_configurations:
  endpoint_url: "http://10.20.0.1:9000"
  bucket: "boot-images"

functional_group_images:
  - x86_64:
    - functional_group: "slurm_control_node_x86_64"
      kernel: "boot-images/efi-images/slurm_control_node_x86_64/rhel-.../vmlinuz"
      initrd: "boot-images/efi-images/slurm_control_node_x86_64/rhel-.../initramfs.img"
      image: "boot-images/slurm_control_node_x86_64/rhel-..."
```

### Validation Rules

| Rule | Error Behavior |
|------|---------------|
| File must exist | Fail with "image_build_manager output not found" |
| `overall_status` must be `"success"` | Fail with "Fix image builds before running orchestrator" |
| `s3_configurations.endpoint_url` must be defined | Fail with assertion error |

### Facts Set from build_status.yml

| Fact | Source | Description |
|------|--------|-------------|
| `s3_configurations.endpoint_url` | `s3_configurations.endpoint_url` | S3 endpoint URL for BSS template |
| `s3_configurations.bucket` | `s3_configurations.bucket` | S3 bucket name (default: `boot-images`) |
| `build_status` | Full `_build_status` dict | Complete build status for image validation |

---

## 5. omnia_config_credentials.yml

**Purpose**: Vault-encrypted credentials for provisioning and services.

**Location**: `input/project_default/omnia_config_credentials.yml`

**Owner**: `orchestrator_credentials` role (auto-generated on first run via interactive prompts)

**Vault Key**: `input/project_default/.omnia_config_credentials_key`

| Field | Type | When Required | Description |
|-------|------|---------------|-------------|
| `provision_password` | string | Always | Root password for provisioned nodes |
| `bmc_username` | string | Always | BMC/iDRAC username |
| `bmc_password` | string | Always | BMC/iDRAC password |
| `slurm_db_password` | string | Slurm enabled | Slurm database password |
| `openldap_db_username` | string | OpenLDAP enabled | OpenLDAP admin username |
| `openldap_db_password` | string | OpenLDAP enabled | OpenLDAP admin password |

---

## 6. Shared Inputs (from project root)

These files are read from `input/project_default/` (project root, not orchestrator subdir):

| File | Description |
|------|-------------|
| `software_config.json` | Cluster OS type, version, and software stack |
| `omnia_config.yml` | K8s/Slurm cluster definitions |
| `storage_config.yml` | Storage mount configuration |
| `security_config.yml` | Security settings |
| `telemetry_config.yml` | Telemetry configuration |

---

## 7. Dependency Summary

```
                    ┌─────────────────────────┐
                    │  orchestrator_credentials│
                    │  (vault prompt/encrypt)  │
                    └────────┬────────────────┘
                             │ produces
                             ▼
                    ┌─────────────────────────┐
                    │ omnia_config_credentials │
                    │        .yml              │
                    └────────┬────────────────┘
                             │
  ┌──────────────┐           │           ┌──────────────────┐
  │ orchestrator │           │           │ build_status.yml │
  │  _config.yml │───────────┼──────────▶│ (from img_bld)   │
  └──────────────┘           │           └──────────────────┘
                             │
  ┌──────────────┐           │           ┌──────────────────┐
  │pxe_mapping   │           │           │ network_spec.yml │
  │  _file.csv   │───────────┼──────────▶│                  │
  └──────────────┘           │           └──────────────────┘
                             │
                    ┌────────▼────────────────┐
                    │    orchestrator.yml      │
                    └─────────────────────────┘
```
