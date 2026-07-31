# build_os_images

Builds base and compute OS images for x86_64 and aarch64 architectures using OpenCHAMI image-builder. Uploads artifacts to S3 and writes `build_status.yml`.

## Requirements

- Podman 5.0+ for container image building
- S3-compatible storage (MinIO or PowerScale)
- OCI registry for storing built images
- Valid `repo_status.yml` from repo_manager

## Role Variables

See `defaults/main.yml` and `vars/main.yml` for the full list.

## Dependencies

- `image_build_setup` — environment and config loading
- `collect_build_credentials` — S3 and registry credentials
- `deploy_minio` — local MinIO deployment (when s3_provider is minio)
- `deploy_registry` — local OCI registry deployment

## Example

```yaml
- hosts: localhost
  roles:
    - build_os_images
```
