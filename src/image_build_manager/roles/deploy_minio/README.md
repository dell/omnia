# deploy_minio

Deploys MinIO S3-compatible object storage as a Podman Quadlet systemd service for image build artifact storage.

## Requirements

- Podman 5.0+
- systemd for Quadlet service management

## Role Variables

See `defaults/main.yml` and `vars/main.yml` for the full list.

## Dependencies

- `image_build_setup` — environment and config loading
- `collect_build_credentials` — S3 credentials

## Example

```yaml
- hosts: localhost
  roles:
    - deploy_minio
```
