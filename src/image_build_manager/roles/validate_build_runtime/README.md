# validate_build_runtime

Validates that the build environment has all required runtime dependencies (Python, Podman, Ansible) at the correct versions.

## Requirements

- Python 3.12+
- Podman 5.0+
- Ansible Core 2.20+

## Role Variables

See `vars/main.yml` for the full list.

## Dependencies

- `image_build_setup` — environment and config loading

## Example

```yaml
- hosts: localhost
  roles:
    - validate_build_runtime
```
