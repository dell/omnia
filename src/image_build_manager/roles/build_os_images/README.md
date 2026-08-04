# build_os_images

Builds base and compute OS images for x86_64 and aarch64 architectures using
OpenCHAMI image-builder. Uploads artifacts to S3 and verifies pushed images
via `regctl`.

## Build Flow

1. **Common setup** — compute image tag suffix, configure registry host
2. **Base image** — single base OS image per architecture
3. **Compute images** — per-functional-group images with concurrency control
   via `image_build_orchestrator` module
   - `_orchestrator_cmds` is defensively initialized to `[]` before the build loop
     to prevent undefined variable errors even if the loop is somehow empty
   - Each compute group uses its own `os_version` from `compute_images_dict`
4. **Verification** — `regctl` manifest inspection for each pushed image
5. **Status** — record built images in `build_completed_images` for `build_status.yml`

Compute image builds are **skipped** when `compute_images_dict` is empty
(e.g. base-only builds or no functional groups resolved for the architecture).

## Requirements

- Podman 5.0+ for container image building
- S3-compatible storage (MinIO or PowerScale)
- OCI registry for storing built images (with `regctl` pre-installed by `deploy_registry`)
- Valid `repo_status.yml` from repo_manager

## Role Variables

See `defaults/main.yml` and `vars/main.yml` for the full list.

## Dependencies

- `image_build_setup` — environment and config loading
- `collect_build_credentials` — S3 and registry credentials
- `deploy_minio` — local MinIO deployment (when s3_provider is minio)
- `deploy_registry` — local OCI registry deployment (includes `regctl` install)
- `fetch_build_packages` — resolves `base_image_packages` and `compute_images_dict`

## Example

```yaml
- hosts: localhost
  roles:
    - build_os_images
```
