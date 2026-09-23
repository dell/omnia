# deploy_registry

Deploys a local OCI container registry as a Podman Quadlet systemd service for
storing built OS images. Also installs and configures `regctl` for registry
image verification.

## What It Does

1. Creates registry storage and root-only authentication directories
2. Generates a protected client password and bcrypt `htpasswd` database
3. Renders `/etc/containers/systemd/registry.container` with TLS and basic authentication
4. Pulls the registry image, restarts the service, and performs an authenticated HTTPS health check
5. Authenticates Podman and regctl for every supported registry endpoint and requires verified TLS

The `configure_service_pki` role must run first so the registry certificate and
Omnia image-build CA are present. Existing installations are reconciled and
restarted instead of retaining an earlier unauthenticated HTTP configuration.

## Requirements

- Podman 5.0+
- systemd for Quadlet service management
- `httpd-tools` for bcrypt `htpasswd` generation (installed by the role)
- Access to GitHub releases for `regctl`, unless the binary is preinstalled
- Access to the configured registry container image

## Role Variables

See `vars/main.yml`; this role has no `defaults/main.yml`.

Key variables:
- `health_check_retries` / `health_check_delay` — registry readiness polling
- `download_retries` / `download_delay` — `regctl` binary download retries

## Orchestration Prerequisite

No dependency is declared in `meta/main.yml`; the caller must first provide
the paths and host facts set by `image_build_setup`, and must run
`configure_service_pki` before this role.

## Example

```yaml
- hosts: localhost
  roles:
    - deploy_registry
```
