# deploy_registry

Deploys a local OCI container registry as a Podman Quadlet systemd service for storing built OS images.

## Requirements

- Podman 5.0+
- systemd for Quadlet service management

## Role Variables

See `defaults/main.yml` and `vars/main.yml` for the full list.

## Dependencies

- `image_build_setup` — environment and config loading

## Example

```yaml
- hosts: localhost
  roles:
    - deploy_registry
```
