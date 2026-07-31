# validate_image_build_input

Validates input configuration files (image_build_config.yml, credentials) using L1 JSON schema validation and L2 cross-field logic checks.

## Requirements

- Valid JSON schema files in `plugins/module_utils/input_validation/schema/`
- Python 3.12+

## Role Variables

See `vars/main.yml` for the full list.

## Dependencies

- `image_build_setup` — environment and config loading

## Example

```yaml
- hosts: localhost
  roles:
    - validate_image_build_input
```
