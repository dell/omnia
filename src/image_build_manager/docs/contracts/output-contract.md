# image_build_manager — Output Contract

> **Last Updated**: Jul 21, 2026 | **Domain**: `image_build_manager`

This document defines all output artifacts produced by the `image_build_manager` domain.

---

## 1. build_status.yml

**Purpose**: Reports the result of the image build process, including S3 endpoints and per-architecture image paths. Consumed by the `provision` domain for BSS template rendering and image validation.

**Location**:
- **Latest**: `output/project_default/build_status.yml`
- **Versioned**: `output/project_default/image_build_manager/build_status_<version>_<timestamp>.yml`

**Producer**: `image_build_manager.yml` (Step 8 — Write build_status)

**Consumers**:
- `provision/roles/provision_validations/tasks/validate_image.yml`
- `provision/roles/configure_ochami/tasks/configure_bss_group.yml`

### Structure

```yaml
overall_status: "success"   # "success" or "failed"

s3_configurations:
  endpoint_url: "http://10.20.0.1:9000"   # MinIO: auto-detected; PowerScale: from config
  bucket: "boot-images"

functional_group_images:
  - x86_64:
    - functional_group: "slurm_control_node_x86_64"
      kernel: "boot-images/efi-images/slurm_control_node_x86_64/rhel-.../vmlinuz"
      initrd: "boot-images/efi-images/slurm_control_node_x86_64/rhel-.../initramfs.img"
      image: "boot-images/slurm_control_node_x86_64/rhel-..."
  - aarch64:
    - functional_group: "slurm_node_aarch64"
      kernel: "boot-images/efi-images/slurm_node_aarch64/rhel-.../vmlinuz"
      initrd: "boot-images/efi-images/slurm_node_aarch64/rhel-.../initramfs.img"
      image: "boot-images/slurm_node_aarch64/rhel-..."
```

### Field Definitions

| Field | Type | Description |
|-------|------|-------------|
| `overall_status` | string | `"success"` if all requested builds completed; `"failed"` otherwise |
| `s3_configurations.endpoint_url` | string | S3-compatible endpoint URL for boot image retrieval |
| `s3_configurations.bucket` | string | S3 bucket name (always `"boot-images"`) |
| `functional_group_images` | list | Architecture-grouped list of built image entries |
| `functional_group_images[].x86_64` | list | x86_64 image entries (omitted if no x86_64 builds) |
| `functional_group_images[].aarch64` | list | aarch64 image entries (omitted if no aarch64 builds) |
| `*.functional_group` | string | Functional group name (includes arch suffix, e.g., `slurm_node_x86_64`) |
| `*.kernel` | string | S3 key for the kernel (vmlinuz) |
| `*.initrd` | string | S3 key for the initramfs image |
| `*.image` | string | S3 key prefix for the rootfs image |

### S3 Endpoint Behavior

| Provider | Behavior |
|----------|----------|
| **MinIO** | Auto-detected as `http://<admin_nic_ip>:9000` when `endpoint_url` is empty in input config |
| **PowerScale** | Uses configured `endpoint_url` as-is from `image_build_config.yml` |

### Consumers Behavior

| Consumer | What It Reads | Purpose |
|----------|---------------|---------|
| `validate_image.yml` | `overall_status`, `s3_configurations`, `functional_group_images` | Validates images exist in S3 before provisioning |
| `configure_bss_group.yml` | `functional_group_images[].kernel`, `initrd`, `image` | Renders BSS boot templates per functional group |

---

## 2. Deployed Services

The `prepare_image_build_manager.yml` sub-playbook deploys the following services on the OIM host as side-effects:

### MinIO (when provider != powerscale)

| Item | Value |
|------|-------|
| Service name | `minio.service` |
| Quadlet file | `/etc/containers/systemd/minio.container` |
| S3 data directory | `{{ oim_shared_path }}/omnia/openchami/s3/data/s3` |
| Ports | `9000` (API), `9001` (Console) |
| Health check | `http://localhost:9000/minio/health/live` |
| S3 buckets created | `boot-images`, `efi-images` |

### Container Registry (always)

| Item | Value |
|------|-------|
| Service name | `registry.service` |
| Quadlet file | `/etc/containers/systemd/registry.container` |
| Storage directory | `/opt/omnia/registry/data` |
| OCI data | `{{ oim_shared_path }}/omnia/openchami/s3/data/oci` |
| Port | `5000` |
| Health check | `http://localhost:5000/v2/` |

### omnia.target Updates

Services are appended to the existing `omnia.target` `Requires=` line:
- `registry.service` — always appended
- `minio.service` — appended only when provider != `powerscale`

---

## 3. Built Container Images

The image-builder container is built by `src/image_build_manager/containers/build_images.sh` and pushed to the local registry:

| Image | Registry Path | Description |
|-------|---------------|-------------|
| `image-builder` | `localhost:5000/image-builder:latest` | Builds OS boot images (kernel, initramfs, rootfs) |

---

## 4. S3 Artifacts

Images built by `image_creation` role are uploaded to S3 with the following key structure:

```
boot-images/
├── efi-images/
│   ├── <functional_group>/
│   │   └── rhel-<functional_group>_omnia_<version>/
│   │       ├── vmlinuz
│   │       └── initramfs-<kernel_version>.img
│   └── ...
├── <functional_group>/
│   └── rhel-<functional_group>_omnia_<version>/
│       └── <rootfs files>
└── ...
```

| Bucket | Contents |
|--------|----------|
| `boot-images` | Full OS images (rootfs) and EFI boot artifacts (kernel, initramfs) |

---

## 5. Cleanup

Running `cleanup_image_build_manager.yml` removes all output artifacts:
- MinIO container, data, S3 buckets
- Registry container and storage
- `build_status.yml` (latest + versioned)
- `omnia.target` service entries
- s3cmd configuration
- Credentials (opt-in with `--tags credentials`)
