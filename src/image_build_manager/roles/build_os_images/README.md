# build_os_images

Builds base and compute OS images for x86_64 and aarch64 architectures using
the selected OpenCHAMI `image-builder` or `image-thrillhouse` engine. Uploads
artifacts to S3 and verifies pushed OCI images via `regctl`.

## Structure

- `tasks/main.yml` coordinates common setup, base builds, compute builds, and status output.
- Architecture-specific build files contain x86_64 and aarch64 execution paths.
- `tasks/verify_compute_image_*.yml` verifies registry and S3 artifacts.
- `plugins/modules/image_build_orchestrator.py` runs independent builds concurrently.
- `templates/images/` contains the supported engine configuration templates.

## Build Flow

1. **Common setup** — compute image tag suffix, configure registry host
2. **Base image** — single base OS image per architecture
3. **Compute images** — per-functional-group images with concurrency control
   via `image_build_orchestrator` module
   - `_orchestrator_cmds` is defensively initialized to `[]` before the build loop
     to prevent undefined variable errors even if the loop is somehow empty
   - Each compute group uses its own `os_version` from `compute_images_dict`
4. **Verification** — `regctl` manifest inspection for each pushed image
5. **Status** — record completed functional-group images in
   `build_completed_images` for `build_status.yml`

Compute image builds are **skipped** when `compute_images_dict` is empty
(e.g. base-only builds or no functional groups resolved for the architecture).

## Requirements

- Podman 5.0+ for container image building
- S3-compatible storage (MinIO or PowerScale)
- OCI registry for storing built images (with `regctl` pre-installed by `deploy_registry`)
- Valid `repo_status.yml` from repo_manager

## Role Variables

See `vars/main.yml` for internal build constants and messages. The role does
not currently expose user-overridable defaults.

## Dependencies

The role declares no automatic dependencies in `meta/main.yml`. The top-level
playbooks prepare these facts and services before invoking it:

- `image_build_setup` — environment and config loading
- `collect_build_credentials` — S3 and optional aarch64 SSH credentials
- `deploy_minio` — local MinIO deployment (when s3_provider is minio)
- `deploy_registry` — local OCI registry deployment (includes `regctl` install)
- `fetch_build_packages` — resolves `base_image_packages` and `compute_images_dict`

## Example Playbook

```yaml
- name: Build operating-system images
  hosts: localhost
  connection: local
  gather_facts: false
  roles:
    - role: build_os_images
```
