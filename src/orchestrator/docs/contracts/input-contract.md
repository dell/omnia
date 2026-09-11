# Orchestrator — Input Contract

> **Last Updated**: Sep 9, 2026 | **Domain**: `orchestrator`

This document defines all input files consumed by the `orchestrator` domain.

---

## 1. orchestrator_config.yml

**Purpose**: Per-domain input configuration for orchestrator.

**Location**: `$OMNIA_DATA_PATH/orchestrator/input/$OMNIA_PROJECT_NAME/orchestrator_config.yml`

**Owner**: User (manually configured)

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `pxe_mapping_file_path` | string | Yes (may be empty) | Current project input directory | Optional override for the PXE mapping CSV path |
| `image_build_manager_output_path` | string | No | `$OMNIA_DATA_PATH/image_build_manager/output/$OMNIA_PROJECT_NAME/build_status.yml` | Path to `build_status.yml` |
| `language` | string | No | `"en-US"` | Language for provisioned nodes |
| `default_lease_time` | int | No | `86400` | DHCP lease time (seconds) |
| `dns_enabled` | bool | No | `false` | Enable CoreDNS configuration |
| `kernel_version_override` | string | No | `""` | Specific kernel version for boot images |
| `additional_cloud_init_config_file` | string | No | `""` | Extra cloud-init config path |
| `repo_manager_output_path` | string | No | `$OMNIA_DATA_PATH/repo_manager/output/$OMNIA_PROJECT_NAME/repo_status.yml` | Path to `repo_status.yml` from repo_manager |
| `catalog_file_path` | string | No | `$CATALOG_FILE_PATH`, then `$OMNIA_DATA_PATH/catalog/catalog_rhel.json` | Optional override for the catalog JSON path |

### Catalog availability

The `catalog_file_path` field is optional, but its resolved file is required
for flows that derive OS metadata or catalog-backed feature enablement: full
execution, `precheck`, `credentials`, `prepare`, `deploy`, `provision`,
`execute`, and `validate-deployment`.

PowerScale CSI enablement is not derived from the catalog. It is controlled by
`service_k8s_cluster[].enable_powerscale_csi` in `omnia_config.yml`.

Input-only `validate`, PXE-only, cleanup, upgrade, and rollback flows do not
consume the catalog contract and can run without the file. Standalone
credential collection requires it because Slurm and OpenLDAP feature flags
determine which credentials are mandatory.

---

## 2. pxe_mapping_file.csv (External Contract from Discovery)

**Purpose**: Primary data contract between Discovery and Orchestrator domains.

**Location**: `$OMNIA_DATA_PATH/orchestrator/input/$OMNIA_PROJECT_NAME/pxe_mapping_file.csv`

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

**Location**: `$OMNIA_DATA_PATH/orchestrator/input/$OMNIA_PROJECT_NAME/network_spec.yml`

**Owner**: User (manually configured)

**Key Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `Networks.admin_network.primary_oim_admin_ip` | string | Yes | OIM admin IP |
| `Networks.admin_network.primary_oim_bmc_ip` | string | Yes | OIM BMC/iDRAC IP added to generated BMC group data for iDRAC telemetry; use an empty value to exclude the OIM |
| `Networks.admin_network.oim_nic_name` | string | Yes | OIM NIC name |
| `Networks.admin_network.subnet` | string | Yes | Admin network address |
| `Networks.admin_network.netmask_bits` | string | Yes | Netmask bits |
| `Networks.admin_network.dynamic_range` | string | Yes | DHCP dynamic range (e.g., `10.5.0.100-10.5.0.200`) |
| `Networks.admin_network.router` | string | Yes | Default gateway |
| `Networks.admin_network.dns` | list | No | DNS forwarders |
| `Networks.admin_network.ntp_servers` | list | No | NTP server or pool entries |
| `Networks.admin_network.additional_subnets` | list | No | Subnets served through DHCP relay for multi-RAC or multi-subnet PXE |
| `Networks.admin_network.additional_subnets[].subnet` | string | Yes, per entry | Additional network address |
| `Networks.admin_network.additional_subnets[].netmask_bits` | string | Yes, per entry | Additional network CIDR prefix length |
| `Networks.admin_network.additional_subnets[].router` | string | Yes, per entry | Gateway supplied as DHCP option 3 |
| `Networks.admin_network.additional_subnets[].dynamic_range` | string | Yes, per entry | DHCP pool contained by the additional subnet |
| `Networks.ib_network.subnet` | string | Yes, when configured | InfiniBand network address |
| `Networks.ib_network.netmask_bits` | string | Yes, when configured | InfiniBand CIDR prefix length |
| `Networks.ib_network.dns` | list | No | InfiniBand DNS server addresses |

---

## 4. build_status.yml (Upstream Dependency)

**Purpose**: Output from `image_build_manager` domain consumed as input by orchestrator.

**Location**: `<IMAGE_BUILD_MANAGER_DATA_PATH>/output/<project>/build_status.yml`.
`IMAGE_BUILD_MANAGER_DATA_PATH` defaults to
`<OMNIA_DATA_PATH>/image_build_manager` (or use the custom path configured by
`image_build_manager_output_path` in `orchestrator_config.yml`).

**Producer**: `image_build_manager` domain

**Consumer**: `configure_s3_access.yml` (Step 4a)

**Reference sample**:
`src/orchestrator/samples/image_build_manager_output/build_status.yml`.
Image Build Manager's generated file remains authoritative.

### Structure

```yaml
overall_status: "success"
image_build_type: "image-builder"

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
| `image_build_type` identifies the producing engine | Interpret artifact paths using `image-builder` or `image-thrillhouse` provenance |
| `s3_configurations.endpoint_url` must be defined | Fail with assertion error |
| Every functional group must define kernel, initrd, and image paths | Fail before provisioning |
| Every rendered artifact URL must answer HTTP `HEAD` with status 200 | Report URL, status, and request error |

### Facts Set from build_status.yml

| Fact | Source | Description |
|------|--------|-------------|
| `s3_configurations.endpoint_url` | `s3_configurations.endpoint_url` | S3 endpoint URL for BSS template |
| `s3_configurations.bucket` | `s3_configurations.bucket` | S3 bucket name (default: `boot-images`) |
| `build_status` | Full `_build_status` dict | Complete build status for image validation |

During OpenCHAMI precheck and provisioning, Orchestrator validates every
functional group's `kernel`, `initrd`, and `image` entry. It sends an HTTP
`HEAD` request from the OIM to the same endpoint-relative URL rendered into
Boot Service configuration. This behavior is identical for manifests produced
by `image-builder` and `image-thrillhouse`; inaccessible or missing artifacts
fail before provisioning begins.

---

## 5. repo_status.yml (Upstream Dependency from repo_manager)

**Purpose**: Repository URLs and Pulp certificate paths generated by `repo_manager`.

**Location**: `$REPO_MANAGER_DATA_PATH/output/$OMNIA_PROJECT_NAME/repo_status.yml`;
`REPO_MANAGER_DATA_PATH` defaults to `$OMNIA_DATA_PATH/repo_manager`
(or custom path via `repo_manager_output_path` in `orchestrator_config.yml`)

**Producer**: `repo_manager` domain (`generate_local_repo_access` module)

**Consumer**: `orchestrator_setup` (loads as Step 7), then consumed by `k8s_config`, `slurm_config`, `configure_ochami` cloud-init templates

**Reference sample**:
`src/orchestrator/samples/repo_manager_output/repo_status.yml`.
Repo Manager's generated file remains authoritative.

### Structure

```yaml
overall_status: "success"
cluster_os_type: "rhel"
repo_config: "partial"

repo_manager:
  port: 2225
  certificates:
    server_crt: "<OMNIA_DATA_PATH>/repo_manager/pulp_config/settings/certs/pulp_webserver.crt"
    server_key: "<OMNIA_DATA_PATH>/repo_manager/pulp_config/settings/certs/pulp_webserver.key"
    certs_dir: "<OMNIA_DATA_PATH>/repo_manager/pulp_config/settings/certs"

repositories:
  "10.0":
    x86_64:
      baseos:
        url: "https://<admin_ip>:2225/pulp/content/.../rpms/baseos/"
      appstream:
        url: "https://<admin_ip>:2225/pulp/content/.../rpms/appstream/"
    aarch64:
      baseos: {}

registries:
  user_registry1:
    port: 443
    tls:
      capath: "/etc/omnia/certs/.../ca.crt"
      insecure: false

file_repos:
  x86_64:
    git:
      helm_charts: "https://<admin_ip>:2225/pulp/content/.../git/helm-charts/"
    tarball:
      helm_v3_20_1_amd64: "https://<admin_ip>:2225/pulp/content/.../tarball/helm-v3.20.1-amd64/"
    manifest:
      calico_v3_31_4: "https://<admin_ip>:2225/pulp/content/.../manifest/calico-v3.31.4/"
    pip_module:
      kubernetes_33_1_0: "https://<admin_ip>:2225/pypi/.../pip_module/kubernetes==33.1.0/"
  aarch64: {}

offline_tarball_path: "https://<admin_ip>:2225/pulp/content/.../tarball/"
offline_manifest_path: "https://<admin_ip>:2225/pulp/content/.../manifest/"
offline_git_path: "https://<admin_ip>:2225/pulp/content/.../git/"
offline_pip_module_path: "https://<admin_ip>:2225/pypi/.../pip_module/"
offline_shell_path: "https://<admin_ip>:2225/pulp/content/.../shell/"
offline_iso_path: "https://<admin_ip>:2225/pulp/content/.../iso/"
```

### Validation Rules

For flows that consume repository content (`precheck`, `prepare`, `deploy`,
`provision`, `execute`, `pxeboot`, and `upgrade`), Orchestrator requires the
file to exist, requires `overall_status: success`, validates its core mapping
and certificate fields, and verifies that the public certificate exists.
Cleanup, credential-only, input-validation, rollback, and deployment-health
flows remain runnable without `repo_status.yml`.

### Facts Set from repo_status.yml

| Fact | Source | Consumer |
|------|--------|----------|
| `cluster_os_type` | `cluster_os_type` | `k8s_config`, `slurm_config`, cloud-init templates |
| `pulp_port` | `repo_manager.port` | All Pulp URL references (replaces hardcoded `2225`) |
| `pulp_cert_path` | `repo_manager.certificates.server_crt` | `k8s_config`, `slurm_config` (cert copy to nodes) |
| `repositories` | `repositories.<version>.<arch>.<repo>.url` | RPM repo URLs keyed by OS version and arch |
| `registries` | `registries` | Container registry mirror configuration |
| `file_repos` | `file_repos.<arch>.<type>.<name>` | Git, tarball, manifest, pip URLs |
| `offline_tarball_path` | `offline_tarball_path` | `k8s_config` (helm, CUDA downloads) |
| `offline_manifest_path` | `offline_manifest_path` | `k8s_config` (Calico, MetalLB manifests) |
| `offline_git_path` | `offline_git_path` | `k8s_config` (whereabouts, helm-charts) |

---

## 6. orchestrator_credentials.yml

**Purpose**: Vault-encrypted credentials for provisioning and services.

**Location**: `$OMNIA_DATA_PATH/orchestrator/input/$OMNIA_PROJECT_NAME/orchestrator_credentials.yml`

**Owner**: `orchestrator_credentials` role (auto-generated on first run via interactive prompts)

**Vault Key**: `$OMNIA_DATA_PATH/orchestrator/input/$OMNIA_PROJECT_NAME/.orchestrator_credentials_key`

A full Orchestrator cleanup removes both the encrypted credential file and its
vault key by default. Pass `-e cleanup_credentials=false` with the `cleanup`
tag to preserve them. The `cleanup_credentials` tag remains available for
credential-only cleanup.

| Field | Type | When Required | Description |
|-------|------|---------------|-------------|
| `provision_password` | string | Always | Root password for provisioned nodes |
| `bmc_username` | string | Always | BMC/iDRAC username |
| `bmc_password` | string | Always | BMC/iDRAC password |
| `slurm_db_password` | string | Slurm enabled | Slurm database password |
| `openldap_db_username` | string | OpenLDAP enabled | OpenLDAP admin username |
| `openldap_db_password` | string | OpenLDAP enabled | OpenLDAP admin password |
| `csi_username` | string | `enable_powerscale_csi: true` | PowerScale API username used by the CSI driver |
| `csi_password` | string | `enable_powerscale_csi: true` | PowerScale API password used by the CSI driver |

---

## 7. Shared Inputs (from project root)

These files are read from `input/project_default/` (project root, not orchestrator subdir):

| File | Description |
|------|-------------|
| `software_config.json` | Cluster OS type, version, and software stack |
| `omnia_config.yml` | K8s/Slurm cluster definitions |
| `storage_config.yml` | Storage mount configuration |
| `security_config.yml` | Security settings |
| `telemetry_config.yml` | Telemetry configuration |

`storage_config.yml` is conditionally required. When `omnia_config.yml`
contains a non-empty `nfs_storage_name` or `vast_storage_name` in a Slurm or
service Kubernetes cluster definition, the file must exist and define a mount
with every referenced name. When no storage name is referenced, the file may
be absent. If present, it is always schema validated. Network reachability of
referenced NFS servers is checked later during precheck.

A dedicated optional Slurm VAST mount uses `storage_role: slurm_vast`. It is
included only when the active `slurm_cluster` entry has a non-empty
`vast_storage_name` referencing that mount. Other VAST-backed NFS mounts are
independent and must not use this role marker.

### PowerScale CSI selection

PowerScale CSI is an explicit option on the Kubernetes cluster selected for
deployment:

```yaml
service_k8s_cluster:
  - cluster_name: service_cluster
    deployment: true
    enable_powerscale_csi: true
    csi_powerscale_driver_secret_file_path: "/path/to/secret.yaml"
    csi_powerscale_driver_values_file_path: "/path/to/values.yaml"
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `enable_powerscale_csi` | bool | No | `false` | Enable dependency staging and PowerScale CSI deployment for the active Kubernetes cluster |
| `csi_powerscale_driver_secret_file_path` | string | When CSI is enabled | — | Absolute path to the PowerScale CSI `secret.yaml` |
| `csi_powerscale_driver_values_file_path` | string | When CSI is enabled | — | Absolute path to the PowerScale CSI `values.yaml` |

When the flag is omitted or `false`, Orchestrator does not request PowerScale
CSI credentials, stage CSI dependencies, add the CSI deployment script to
cloud-init, or execute that script. When it is `true`, both input files and the
CSI credentials are mandatory. Orchestrator resolves the versioned
`csi-powerscale`, `helm-charts`, and `external-snapshotter` artifacts from
`repo_status.yml` rather than using a catalog group as the runtime feature
switch.

---

## 8. Dependency Summary

```
                    ┌─────────────────────────┐
                    │  orchestrator_credentials│
                    │  (vault prompt/encrypt)  │
                    └────────┬────────────────┘
                             │ produces
                             ▼
                    ┌─────────────────────────┐
                    │ orchestrator_credentials │
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
  ┌──────────────┐           │           ┌──────────────────┐
  │ repo_status  │           │           │ repo_manager     │
  │  .yml        │◀──────────┼───────────│ (Pulp URLs/certs)│
  └──────────────┘           │           └──────────────────┘
                             │
                    ┌────────▼────────────────┐
                    │    orchestrator.yml      │
                    └─────────────────────────┘
```
