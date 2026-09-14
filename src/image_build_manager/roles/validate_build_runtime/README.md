# validate_build_runtime

Validates build-specific configuration immediately before an architecture
build. Despite the historical role name, it does not check installed Python,
Podman, or Ansible versions.

## Checks

- `s3_configurations.provider` exists and is `minio` or `powerscale`.
- Fixed S3 facts are set to `boot-images` and `efi-images`.
- For PowerScale, `endpoint_url` is present and its endpoint is reachable.
- An aarch64 build has a configured `aarch64_inventory_host_ip`.
- `overall_status` is `success` when repository precheck validation is enabled.

The separate `validate_aarch64_host.yml` task file determines whether ARM
building is enabled, pings the configured host, and dynamically adds the host
to the `admin_aarch64` inventory group. SSH setup is performed later by
`prepare_aarch64_node`.

The `efi-images` value set here is a build-time object-prefix convention. The
local MinIO deployment separately creates an `efi` bucket; current artifacts
remain in `boot-images`.

## Role Variables

See `vars/main.yml` for fixed bucket names and validation messages.

## Orchestration Prerequisite

No dependency is declared in `meta/main.yml`; callers must first run
`image_build_setup` so configuration and upstream status facts exist.

## Example

```yaml
- hosts: localhost
  roles:
    - validate_build_runtime
```
