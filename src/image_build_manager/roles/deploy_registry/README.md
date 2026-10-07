# deploy_registry

Deploys a local OCI container registry as a Podman Quadlet systemd service for
storing built OS images. Also installs and configures `regctl` for registry
image verification.

## Structure

- `tasks/main.yml` installs `regctl`, renders the Quadlet, and validates health.
- `templates/registry.container.j2` defines the managed registry service.
- `vars/main.yml` owns the pinned image, retry settings, paths, and messages.

## What It Does

1. Creates registry storage directories
2. Renders `/etc/containers/systemd/registry.container`; systemd generates the service
3. Pulls `docker.io/library/registry:3.1.2` and starts the systemd service
4. Waits for registry health check (configurable retries/delay)
5. If `regctl` is absent, downloads it and configures the local registry for HTTP

The role always reconciles the Quadlet and pinned image. A changed service file
or image restarts an existing registry; an unchanged deployment remains
idempotent.

Current behavior skips both installation and registry configuration when the
`regctl` binary already exists. Ensure an existing installation already has
the local registry configured with TLS disabled.

## Requirements

- Podman 5.0+
- systemd for Quadlet service management
- Access to GitHub releases for `regctl`, unless the binary is preinstalled
- Access to the configured registry container image

## Role Variables

See `vars/main.yml` for internal deployment constants and messages. The role
does not currently expose user-overridable defaults.

Key variables:
- `registry_image` / `registry_tag` — pinned registry container image
- `health_check_retries` / `health_check_delay` — registry readiness polling
- `download_retries` / `download_delay` — `regctl` binary download retries

## Dependencies

No dependency is declared in `meta/main.yml`; the caller must first provide
the paths and host facts set by `image_build_setup`.

## Example Playbook

```yaml
- name: Deploy the Image Build Manager registry
  hosts: localhost
  connection: local
  gather_facts: false
  roles:
    - role: deploy_registry
```
