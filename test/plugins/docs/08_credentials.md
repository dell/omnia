# Credential management

**Source file:** `omnia_auto/functions/credential_func.py`

The credential API creates protected Ansible Vault keys, encrypts and decrypts
YAML credential mappings, and updates individual fields without putting secret
values in process arguments.

## Command-line interface

Installing the package provides `omnia-auto`. The equivalent module form is
`python -m omnia_auto`.

```bash
omnia-auto --help
omnia-auto write-fields --help
```

Available commands:

| Command | Purpose |
|---------|---------|
| `ensure-key` | Create a Vault key if it does not exist |
| `encrypt` | Encrypt a plaintext YAML credential file |
| `is-encrypted` | Test whether a file has an Ansible Vault header |
| `read-field` | Write one decrypted value to stdout |
| `read-all` | Write the decrypted mapping as JSON to stdout |
| `write-field` | Read one value from stdin, merge it, and encrypt |
| `write-fields` | Read a JSON mapping from stdin, merge it, and encrypt |
| `prompt` | Prompt for one secret without echo |
| `prompt-and-confirm` | Prompt twice and return the confirmed secret |
| `prompt-fields` | Interactively collect fields described by a JSON specification |

### Safely update multiple fields

Use an approved secret provider or CI secret-injection step that writes one
JSON object to stdout:

```bash
credential-json-provider | \
  omnia-auto write-fields \
    --fields-stdin \
    --creds-path credentials.yml \
    --key-path credentials.key
```

The input is limited to 64 KiB. It must be a non-empty JSON object whose keys
are safe field identifiers and whose values are strings.

Setup scripts SHOULD also pass their non-secret field specification through
`--spec`. This makes the specification an allowlist, enforces each configured
minimum length, and rejects misspelled or unexpected fields. Domains with a
fixed mandatory credential set can add `--require-complete`; component-driven
domains should omit that flag so disabled-component fields may remain absent.

```bash
credential-json-provider | \
  omnia-auto write-fields \
    --fields-stdin \
    --spec '[{"field":"api_user","secret":false},{"field":"api_password","secret":true,"min_length":8}]' \
    --require-complete \
    --creds-path credentials.yml \
    --key-path credentials.key
```

### Safely update one field

```bash
single-secret-provider | \
  omnia-auto write-field \
    --value-stdin \
    --field oim_password \
    --creds-path credentials.yml \
    --key-path credentials.key
```

Do not place secret values in command-line arguments, environment variables,
shell history, or logs. The `read-field`, `read-all`, `prompt`, and
`prompt-and-confirm` commands intentionally write secret material to stdout;
pipe that output only to an approved consumer and disable shell tracing.

## Python API

```python
from omnia_auto import (
    ensure_vault_key,
    is_vault_encrypted,
    prompt_and_confirm,
    prompt_credential,
    prompt_fields_interactive,
    read_all_fields,
    read_credential_field,
    vault_decrypt_to_dict,
    vault_encrypt,
    write_credential_fields,
)

ensure_vault_key("credentials.key")

result = write_credential_fields(
    "credentials.yml",
    "credentials.key",
    {"username": "admin", "password": supplied_secret},
)
if not result["success"]:
    raise RuntimeError(result["error"])

field = read_credential_field(
    "credentials.yml", "credentials.key", "username",
)
```

The write operation preserves fields not present in the supplied mapping,
serializes concurrent writers, and atomically replaces the encrypted
destination with private file permissions. `ansible-vault`, supplied by
`ansible-core`, must be available.

## Environment path helpers

The top-level package also exports `get_data_path()`, `get_project_name()`,
and `get_domain_input_path(domain)`. They read `OMNIA_DATA_PATH` and
`OMNIA_PROJECT_NAME`, using the Omnia defaults when those variables are absent.
They are process-local convenience helpers; automation that resolves paths on a
remote execution OIM should use `resolve_domain_data_path()` or
`resolve_domain_input_path()` from the host API instead.
