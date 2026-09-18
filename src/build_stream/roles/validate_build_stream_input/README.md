# validate_build_stream_input

Validates BuildStream inputs using the domain's 2.3 JSON Schemas (L1) and
cross-field business rules (L2).

## Files validated

| File | Behavior |
|------|----------|
| `build_stream_config.yml` | Required; schema and cross-field validation |
| `build_stream_credentials.yml` | Optional; schema-validated when present and not Vault-encrypted |

The schema engine uses the JSON Schema draft declared by each schema. This
enforces all declared types, patterns, string lengths, numeric bounds,
conditionals, nested constraints, and unexpected-property rules.

Callers must run `build_stream_setup` first so `input_project_dir` is defined.
The standalone validation playbook performs that setup automatically.
