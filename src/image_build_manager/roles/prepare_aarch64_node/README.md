# prepare_aarch64_node

Prepares ARM64 (aarch64) remote build hosts for cross-architecture image building via SSH.

## Requirements

- SSH access to the aarch64 build host
- Podman installed on the remote host
- Network connectivity between OIM and build host

## Role Variables

See `vars/main.yml` for the full list. Key variable: `aarch64_inventory_host_ip` in `image_build_config.yml`.

## Dependencies

- `image_build_setup` — environment and config loading
- `collect_build_credentials` — aarch64 SSH credentials

## Example

```yaml
- hosts: localhost
  roles:
    - prepare_aarch64_node
```
