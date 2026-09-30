# validate_build_runtime

Validates build-specific configuration immediately before an architecture
build. Despite the historical role name, it does not check installed Python,
Podman, or Ansible versions.

## Structure

- `tasks/main.yml` validates storage, architecture, and repository status.
- `tasks/powerscale_check.yml` validates an external PowerScale endpoint.
- `tasks/validate_aarch64_host.yml` validates and registers the ARM build host.

## Requirements

- Configuration facts loaded by `image_build_setup`.
- Network access to an external PowerScale endpoint when that provider is selected.
- ICMP reachability to the aarch64 build host when ARM builds are enabled.

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

## Dependencies

No dependency is declared in `meta/main.yml`; callers must first run
`image_build_setup` so configuration and upstream status facts exist.

## Example Playbook

```yaml
- name: Validate Image Build Manager runtime inputs
  hosts: localhost
  connection: local
  gather_facts: false
  roles:
    - role: validate_build_runtime
```
