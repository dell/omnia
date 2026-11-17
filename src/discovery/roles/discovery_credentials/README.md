# discovery_credentials

Collects, validates, encrypts, and stores the OME credentials that Discovery needs.

## What it does

Runs three task files in order:

1. `validate_credentials.yml`: validates the existing credential file.
2. `create_credentials.yml`: creates the credential file when it is missing, prompting for the mandatory values.
3. `update_credentials.yml`: updates stored credentials.

## Credentials

| Item | Value |
|------|-------|
| Mandatory fields | `ome_username`, `ome_password` |
| Credential file | `<input_project_dir>/discovery_credentials.yml` (mode `0600`, Ansible Vault encrypted) |
| Vault key | `<input_project_dir>/.discovery_credentials_key` |

The role runs for the default flow, `credentials`, and `execute`; the `validate`, `precheck`, `cleanup`, and `cleanup_credentials` routes skip credential prompting. Removal of the file and key is handled by `discovery_cleanup`.

## Variables

See `vars/main.yml` for the credential file definition, mandatory-field rules, and messages.

## License

Apache-2.0
