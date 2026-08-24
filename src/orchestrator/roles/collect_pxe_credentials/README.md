# collect_pxe_credentials

Self-contained credential flow for PXE boot operations.

## Description

This role handles the complete credential lifecycle for PXE boot:
- Validates existing credential files
- Creates credential files from templates if missing
- Prompts for mandatory credentials interactively
- Encrypts credentials using Ansible Vault
- Exposes credentials as facts for downstream roles

The flow is idempotent and skips if credentials are already loaded in the current run.

## Requirements

- Ansible Vault support
- Write access to the credential storage directory

## Role Variables

Available variables are listed below (see `vars/main.yml`):

```yaml
# Credential file configuration
pxe_credential_file:
  file_path: "{{ input_config_dir }}/set_pxe_boot_credentials.yml"
  vault_path: "{{ input_config_dir }}/.pxe_vault_key"
  template: "pxe_credentials.j2"
  file_mode: "0600"

# Credential fields configuration
pxe_cred_config:
  mandatory:
    - name: bmc_username
      prompt: "BMC Username"
      validate: "^[a-zA-Z][a-zA-Z0-9_-]{2,15}$"
    - name: bmc_password
      prompt: "BMC Password"
      secret: true
      validate: "^.{8,}$"
```

## Dependencies

None.

## Example Playbook

```yaml
- name: Collect PXE boot credentials
  hosts: localhost
  connection: local
  gather_facts: false
  roles:
    - role: collect_pxe_credentials
```

## Workflow

1. **Check existing files** - Verify if credential file and vault key exist
2. **Create if missing** - Generate credential file from template, create vault key
3. **Load credentials** - Decrypt, load into memory, re-encrypt
4. **Prompt for missing** - Interactively prompt for any missing mandatory credentials
5. **Expose facts** - Make `bmc_username` and `bmc_password` available as facts
6. **Set guard** - Mark `pxe_credentials_loaded: true` to prevent re-prompting

## Tasks

- `main.yml` - Full credential flow: validate, create, prompt, encrypt
- `prompt_credential_field.yml` - Interactive prompting for individual fields

## Security

- Credentials are stored encrypted with Ansible Vault
- Vault key is stored with mode 0600 (owner read/write only)
- Credentials are decrypted only temporarily during load
- No credentials are logged (`no_log: true` on sensitive tasks)

## License

Apache 2.0

## Author Information

Dell Technologies Omnia Team
