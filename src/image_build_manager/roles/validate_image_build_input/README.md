# validate_image_build_input

Validates Image Build Manager inputs with JSON Schema (L1) and cross-field
logic (L2).

## Files Validated

| File | Behavior |
|------|----------|
| `image_build_config.yml` | Required; schema and S3/build/ARM logic validation |
| `image_build_credentials.yml` | Optional on the first run; plaintext files are validated, Vault-encrypted files are recorded but cannot be schema-checked by the module |
| `package_groups.yml` | Required in config mode; also schema-validated when present in catalog mode |
| Catalog JSON | Required in catalog mode through `CATALOG_FILE_PATH`; schema and catalog-logic validation |

`repo_status.yml` is intentionally outside this role. `image_build_setup`
validates that upstream contract only for build/execute/default flow.

Validation details are written to
`<OMNIA_DATA_PATH>/image_build_manager/log/<project>/image_build_validation_<project>.log`
unless the domain data path is overridden.

## Requirements

- JSON schemas in `plugins/module_utils/input_validation/schema/`
- Python 3.12+

## Role Variables

See `vars/main.yml` for the schema directory and messages.

## Orchestration Prerequisite

No dependency is declared in `meta/main.yml`; callers must first run
`image_build_setup` to define runtime paths.

## Example

```yaml
- hosts: localhost
  roles:
    - validate_image_build_input
```
