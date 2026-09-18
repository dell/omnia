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

The producer overwrites the latest file and also writes a timestamped snapshot
named `build_status_<OMNIA_VERSION>_<YYYYMMDD_HHMM>.yml` in the same directory.

### Structure

The manifest stores exact endpoint-relative S3 object paths. Each path includes
the bucket name, omits the endpoint and `s3://` scheme, and ends with the object
filename rather than a directory.

```yaml
overall_status: "success"
image_build_type: "image-thrillhouse"

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

`image_build_type` records the engine that produced this manifest. It is build
provenance, so consumers must use this value when interpreting artifact paths
rather than reading the potentially newer value from `image_build_config.yml`.
The object layout depends on this recorded value:

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
| `overall_status` | string | Currently always `"success"`; a failed build does not produce a failed-status manifest |
| `image_build_type` | string | Producing engine: `"image-builder"` or `"image-thrillhouse"` |
| `s3_configurations.endpoint_url` | string | S3 HTTP(S) endpoint URL, without the artifact path |
| `s3_configurations.bucket` | string | Artifact bucket; currently `"boot-images"` |
| `functional_group_images[].<architecture>[].functional_group` | string | Group name with architecture suffix |
| `functional_group_images[].<architecture>[].kernel` | string | Exact endpoint-relative kernel object path (`vmlinuz*`) |
| `functional_group_images[].<architecture>[].initrd` | string | Exact endpoint-relative initrd object path (`initramfs*`) |
| `functional_group_images[].<architecture>[].image` | string | Exact endpoint-relative rootfs object path (`rhel*` or `rootfs.squashfs`) |

### Compatibility and engine changes

Current manifests always include `image_build_type`. Validation of a legacy
manifest that does not contain the field may infer the engine only when all
artifact directories consistently contain one recognized suffix: `-imgbld`
or `-imgth`. Ambiguous or suffix-free legacy manifests must be regenerated.

Changing `image_build_config.yml` does not alter an existing manifest. Tests
use the manifest engine for path-layout checks and the current input for the
expected functional-group set. When those engine values differ, test output
reports the difference while validating the artifacts produced by the recorded
build. A new build overwrites the latest manifest with the newly selected
engine.

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

Both Quadlets declare `WantedBy=multi-user.target` and are enabled as systemd
services. The deployment roles do not add them to `omnia.target`.

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
a separate bucket. Local MinIO preparation also creates a bucket named `efi`,
but the current artifact layouts and manifest paths do not use it.

---

## 4. Cleanup

`cleanup_image_build_manager.yml` removes:

- the local MinIO and Registry services, Quadlets, and storage data;
- the project output directory, including latest and versioned status files;
- local work/data directories and logs;
- image-build credentials and the generated `s3cmd` configuration.

The domain data cleanup empties the shared `output/` and `log/` roots, not only
the selected project's subdirectories, and preserves both roots as empty
directories. Treat full cleanup as domain-wide in a multi-project installation.
It does not edit `omnia.target`.

For a PowerScale provider, full cleanup skips MinIO cleanup and does not erase
objects from external S3. `cleanup_images` can remove matching objects from the
`boot-images` bucket when `s3cmd` and `/root/.s3cfg` are already available; it
also removes matching registry tags while retaining the infrastructure.
