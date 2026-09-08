# deploy_minio

Deploys MinIO S3-compatible object storage as a Podman Quadlet systemd service
for image build artifact storage.

The role is skipped for the external PowerScale provider. For local MinIO it
also installs/configures `s3cmd`, creates `boot-images` and `efi`, and applies
the public-read policy to `boot-images`.

## Requirements

- Podman 5.0+
- systemd for Quadlet service management

## Role Variables

See `vars/main.yml`; this role has no `defaults/main.yml`.

Key variables:
- `health_check_retries` / `health_check_delay` — MinIO readiness polling
- `image_pull_retries` / `image_pull_delay` — MinIO container image pull retries
- `download_retries` / `download_delay` — `s3cmd` RPM download retries

## Orchestration Prerequisites

No role dependencies are declared in `meta/main.yml`. The playbook invokes
these roles first:

- `image_build_setup` — environment and config loading
- `collect_build_credentials` — S3 credentials

## Example

```yaml
- hosts: localhost
  roles:
    - deploy_minio
```
