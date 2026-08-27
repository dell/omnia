# Image Build Manager -- Output Contract

**Domain**: `image_build_manager` | **Collection**: `omnia.image_build`

---

## 1. build_status.yml

**Purpose**: Reports image build results with S3 artifact paths per functional group.

**Location**: `output/<project>/build_status.yml`

**Producer**: `build_os_images` role (write_build_status task)

**Consumer**: Provisioning workflow (image validation and BSS template rendering)

### Structure

```yaml
overall_status: "success"

s3_configurations:
  endpoint_url: "http://10.20.0.1:9000"
  bucket: "boot-images"

functional_group_images:
  - x86_64:
    - functional_group: "slurm_control_node_x86_64"
      kernel: "boot-images/efi-images/slurm_control_node_x86_64/rhel-.../vmlinuz-<kernel-version>"
      initrd: "boot-images/efi-images/slurm_control_node_x86_64/rhel-.../initramfs-<kernel-version>.img"
      image: "boot-images/slurm_control_node_x86_64/rhel-.../<rootfs-filename>"
  - aarch64:
    - functional_group: "slurm_node_aarch64"
      kernel: "boot-images/efi-images/slurm_node_aarch64/rhel-.../vmlinuz-<kernel-version>"
      initrd: "boot-images/efi-images/slurm_node_aarch64/rhel-.../initramfs-<kernel-version>.img"
      image: "boot-images/slurm_node_aarch64/rhel-.../<rootfs-filename>"
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `overall_status` | string | `"success"` or `"failed"` |
| `s3_configurations.endpoint_url` | string | S3 endpoint URL |
| `s3_configurations.bucket` | string | Always `"boot-images"` |
| `functional_group_images[].functional_group` | string | Group name with arch suffix |
| `functional_group_images[].kernel` | string | S3 key for vmlinuz (includes kernel-version suffix) |
| `functional_group_images[].initrd` | string | S3 key for initramfs (includes kernel-version suffix) |
| `functional_group_images[].image` | string | Full S3 object key for rootfs file (not just the directory prefix) |

### S3 Endpoint

| Provider | Behavior |
|----------|----------|
| MinIO | Auto-detected: `http://<admin_nic_ip>:9000` |
| PowerScale | Uses `endpoint_url` from config |

---

## 2. Deployed Services

Services deployed on OIM host by the `prepare` tag:

### MinIO (when provider != powerscale)

| Item | Value |
|------|-------|
| Service | `minio.service` (Podman Quadlet) |
| Ports | `9000` (API), `9001` (Console) |
| Buckets | `boot-images`, `efi-images` |

### Container Registry (always)

| Item | Value |
|------|-------|
| Service | `registry.service` (Podman Quadlet) |
| Port | `5000` (HTTP) |

Both services are added to `omnia.target`.

---

## 3. S3 Artifacts

```
boot-images/
+-- efi-images/
|   +-- <functional_group>/
|       +-- rhel-<group>_omnia_<version>/
|           +-- vmlinuz-<kernel-version>
|           +-- initramfs-<kernel-version>.img
+-- <functional_group>/
    +-- rhel-<group>_omnia_<version>/
        +-- rhel<os_ver>-rhel-<group>_omnia_<version>-<os_ver>
```

---

## 4. Cleanup

`cleanup_image_build_manager.yml` removes:
- MinIO + Registry containers and data
- `build_status.yml`
- S3 buckets and artifacts
- `omnia.target` service entries
- Credentials and s3cmd config
