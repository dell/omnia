# Image Build Manager -- Output Contract

**Domain**: `image_build_manager` | **Collection**: `omnia.image_build`

---

## 1. build_status.yml

**Purpose**: Reports image build results with S3 artifact paths per functional group.

**Location**: `<IMAGE_BUILD_MANAGER_DATA_PATH>/output/<project>/build_status.yml`.
When `IMAGE_BUILD_MANAGER_DATA_PATH` is unset, the root defaults to
`<OMNIA_DATA_PATH>/image_build_manager`; with standard defaults the file is
`/opt/omnia/image_build_manager/output/project_default/build_status.yml`.

**Producer**: `build_os_images` role (write_build_status task)

**Consumer**: Provisioning workflow (image validation and BSS template rendering)

### Structure

The manifest stores exact endpoint-relative S3 object paths. Each path includes
the bucket name, omits the endpoint and `s3://` scheme, and ends with the object
filename rather than a directory.

```yaml
overall_status: "success"

s3_configurations:
  endpoint_url: "http://10.20.0.1:9000"
  bucket: "boot-images"

functional_group_images:
  - x86_64:
    - functional_group: "slurm_node_x86_64"
      kernel: "boot-images/slurm_node_x86_64/rhel-slurm_node_x86_64_omnia_2.3-imgth/10.0/vmlinuz"
      initrd: "boot-images/slurm_node_x86_64/rhel-slurm_node_x86_64_omnia_2.3-imgth/10.0/initramfs.img"
      image: "boot-images/slurm_node_x86_64/rhel-slurm_node_x86_64_omnia_2.3-imgth/10.0/rootfs.squashfs"
```

The object layout depends on `image_build_type`:

- `image-builder` publishes versioned kernel and initrd objects beneath the
  `efi-images/` prefix inside `boot-images`, and a versioned rootfs object under
  the functional-group prefix:

  ```text
  boot-images/efi-images/<functional_group>/<image_name>-imgbld/vmlinuz-<kernel-version>
  boot-images/efi-images/<functional_group>/<image_name>-imgbld/initramfs-<kernel-version>.img
  boot-images/<functional_group>/<image_name>-imgbld/<rootfs-filename>
  ```

- `image-thrillhouse` publishes fixed filenames together beneath the release
  directory:

  ```text
  boot-images/<functional_group>/<image_name>-imgth/<release>/vmlinuz
  boot-images/<functional_group>/<image_name>-imgth/<release>/initramfs.img
  boot-images/<functional_group>/<image_name>-imgth/<release>/rootfs.squashfs
  ```

Consumers construct download URLs as
`<s3_configurations.endpoint_url>/<artifact-path>` and must not prepend another
bucket or S3 scheme.

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `overall_status` | string | `"success"` or `"failed"` |
| `s3_configurations.endpoint_url` | string | S3 HTTP(S) endpoint URL, without the artifact path |
| `s3_configurations.bucket` | string | Artifact bucket; currently `"boot-images"` |
| `functional_group_images[].functional_group` | string | Group name with arch suffix |
| `functional_group_images[].kernel` | string | Exact endpoint-relative kernel object path (`vmlinuz*`) |
| `functional_group_images[].initrd` | string | Exact endpoint-relative initrd object path (`initramfs*`) |
| `functional_group_images[].image` | string | Exact endpoint-relative rootfs object path (`rhel*` or `rootfs.squashfs`) |

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
| Buckets | `boot-images`, `efi` |

### Container Registry (always)

| Item | Value |
|------|-------|
| Service | `registry.service` (Podman Quadlet) |
| Port | `5000` (HTTP) |

Both services are added to `omnia.target`.

---

## 3. S3 Artifacts

### image-builder

```text
boot-images/
+-- efi-images/
|   +-- <functional_group>/
|       +-- <image_name>-imgbld/
|           +-- vmlinuz-<kernel-version>
|           +-- initramfs-<kernel-version>.img
+-- <functional_group>/
    +-- <image_name>-imgbld/
        +-- <rootfs-filename>
```

### image-thrillhouse

```text
boot-images/
+-- <functional_group>/
    +-- <image_name>-imgth/
        +-- <release>/
            +-- vmlinuz
            +-- initramfs.img
            +-- rootfs.squashfs
```

`efi-images` above is an object-key prefix inside the `boot-images` bucket, not
a separate bucket.

---

## 4. Cleanup

`cleanup_image_build_manager.yml` removes:
- MinIO + Registry containers and data
- `build_status.yml`
- S3 buckets and artifacts
- `omnia.target` service entries
- Credentials and s3cmd config
