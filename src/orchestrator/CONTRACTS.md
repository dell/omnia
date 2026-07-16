# Orchestrator Domain – Input/Output Contracts

## Overview

The Orchestrator domain (formerly "provision") owns all post-discovery
lifecycle orchestration: OpenCHAMI deployment, PXE boot configuration,
image resolution, node provisioning, and service deployment (K8s, Slurm,
telemetry, storage, LDAP).

## Inputs

All inputs are read from:

```
/opt/omnia/input/<project_name>/orchestrator/
```

### orchestrator_config.yml

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `pxe_mapping_file_path` | string | Yes | Path to PXE mapping CSV (from discovery) |
| `language` | string | No | Language for provisioned nodes |
| `default_lease_time` | int | No | DHCP lease time (seconds) |
| `dns_enabled` | bool | No | Enable CoreDNS configuration |
| `kernel_version_override` | string | No | Specific kernel version for boot images |
| `additional_cloud_init_config_file` | string | No | Extra cloud-init config path |
| `s3_storage_provider` | string | No | Storage backend: `minio` (default), `powerscale`, or `external` |
| `s3_endpoint` | string | Conditional | S3 endpoint URL (required for powerscale/external; empty for minio) |
| `s3_access_key` | string | No | S3 access key / MinIO username (default: `admin` for minio) |
| `s3_secret_key` | string | Conditional | S3 secret key (required for powerscale/external) |
| `s3_boot_images_bucket` | string | No | S3 bucket name (default: `boot-images`) |
| `s3_verify_ssl` | bool | No | Whether to verify SSL certificates (default: false) |

### pxe_mapping_file.csv (External Contract from Discovery)

This is the **primary input** — the data contract between Discovery and Orchestrator.

| Column | Type | Description |
|--------|------|-------------|
| `FUNCTIONAL_GROUP_NAME` | string | Node role (e.g., `slurm_node_aarch64`) |
| `GROUP_NAME` | string | Scalable Unit / logical group |
| `SERVICE_TAG` | string | Dell server service tag |
| `PARENT_SERVICE_TAG` | string | Parent node service tag |
| `HOSTNAME` | string | Assigned hostname |
| `ADMIN_MAC` | string | Admin NIC MAC address |
| `ADMIN_IP` | string | Admin network IP |
| `BMC_MAC` | string | BMC/iDRAC MAC address |
| `BMC_IP` | string | BMC/iDRAC IP address |
| `IB_NIC_NAME` | string | InfiniBand NIC FQDD |
| `IB_IP` | string | InfiniBand IP |

### network_spec.yml

Full network specification for DHCP/PXE/DNS configuration.

### Shared Inputs (from project root: `/opt/omnia/input/<project_name>/`)

- `omnia_config.yml` — K8s/Slurm cluster definitions
- `software_config.json` — Software stack selection
- `security_config.yml` — Security settings
- `telemetry_config.yml` — Telemetry configuration
- `storage_config.yml` — Storage mount configuration
- `build_stream_config.yml` — Build Stream/CI pipeline settings

## Outputs

```
/opt/omnia/output/<project_name>/orchestrator/
```

- `functional_groups_config.yml` — Generated functional groups
- OpenCHAMI nodes.yaml, hostname.yaml, groups.yaml
- BSS boot parameter configurations
- Cloud-init default/group/node configurations
- `/opt/omnia/hosts` — Ansible inventory

## OpenCHAMI Ownership

The Orchestrator domain **fully owns** OpenCHAMI lifecycle:

1. **Deployment** (`roles/deploy_openchami/`) — formerly in prepare_oim
   - Container deployment (smd, bss, cloud-init-server, coresmd, acme-deploy)
   - Systemd unit management
   - Certificate management

2. **Configuration** (`roles/configure_ochami/`)
   - Node registration in SMD
   - BSS boot parameter configuration
   - Cloud-init defaults, group, and per-node configuration
   - Image-to-functional-group resolution

## Image Resolution Flow

```
pxe_mapping_file.csv
    → FUNCTIONAL_GROUP_NAME
    → S3 pattern: rhel-{fg_name}{omnia_ver}{k8s_ver}{bs_suffix}
    → s3://boot-images/{fg_name}/
    → kernel (vmlinuz), initrd (initramfs), rootfs
    → BSS boot params per functional group
    → PXE boot
```

## Data Flow

```
Discovery Output          Orchestrator Input           Orchestrator Output
────────────────          ──────────────────           ───────────────────
bmc_pxe_mapping.csv ─copy─► pxe_mapping_file.csv
                            orchestrator_config.yml ──► functional_groups_config.yml
                            network_spec.yml        ──► BSS/cloud-init configs
                            omnia_config.yml        ──► nodes.yaml, hostname.yaml
                            software_config.json    ──► K8s/Slurm/telemetry setup
```
