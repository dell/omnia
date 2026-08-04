# deploy_registry

Deploys a local OCI container registry as a Podman Quadlet systemd service for
storing built OS images. Also installs and configures `regctl` for registry
image verification.

## What It Does

1. Creates registry storage directories
2. Renders Quadlet `.container` and `.service` unit files
3. Pulls the registry image and starts the systemd service
4. Waits for registry health check (configurable retries/delay)
5. Installs `regctl` binary (skipped if already present — idempotent)
6. Configures `regctl` TLS for the registry endpoint (HTTP, no TLS verify)

## Requirements

- Podman 5.0+
- systemd for Quadlet service management
- Internet access (or local mirror) for `regctl` binary download

## Role Variables

See `defaults/main.yml` and `vars/main.yml` for the full list.

Key variables:
- `health_check_retries` / `health_check_delay` — registry readiness polling
- `download_retries` / `download_delay` — `regctl` binary download retries

## Dependencies

- `image_build_setup` — environment and config loading

## Example

```yaml
- hosts: localhost
  roles:
    - deploy_registry
```
