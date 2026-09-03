# collect_install_os_credentials

Collects and manages credentials for OS installation via iDRAC virtual media.

## Description

This role handles the complete credential lifecycle for OS installation operations, including:

- Validation of existing credential files
- Creation of credential files from templates
- Vault encryption/decryption of sensitive credentials
- Interactive prompting for mandatory credential fields
- Generation of password hashes for kickstart files
- SSH public key injection for kickstart

The role is idempotent and will skip credential collection if credentials are already loaded in the current Ansible run.

## Requirements

- Ansible Vault for credential encryption
- Sufficient permissions to create/manage credential files
- SSH public key for kickstart injection (optional but recommended)

## Role Variables

Available variables are listed below, along with default values (see `vars/main.yml`):

```yaml
# Credential file configuration
install_os_credential_file:
  file_path: "/path/to/install_os_credentials.yml"
  vault_path: "/path/to/install_os_vault_key"
  template: "templates/install_os_credentials.j2"
  file_mode: "0600"

# Mandatory credential fields to prompt for
install_os_cred_config:
  mandatory:
    - bmc_username
    - bmc_password
    - os_root_password

# SSH public key path for kickstart injection
ssh_public_key_path: "/root/.ssh/id_rsa.pub"
```

## Dependencies

None.

## Example Playbook

```yaml
- name: Collect OS installation credentials
  hosts: localhost
  connection: local
  gather_facts: false
  roles:
    - role: collect_install_os_credentials
```

## Credential Flow

1. **Validate**: Check if credential file and vault key exist
2. **Create**: Generate credential file from template if missing
3. **Encrypt**: Apply Ansible Vault encryption to credential file
4. **Load**: Decrypt and load credentials into Ansible variables
5. **Prompt**: Interactively prompt for any missing mandatory fields
6. **Process**: Generate password hashes and prepare SSH keys
7. **Secure**: Re-encrypt credential file and mark as loaded

## Security Notes

- All credentials are stored encrypted using Ansible Vault
- Vault keys are protected with restrictive file permissions (0600)
- Sensitive operations use `no_log: true` to prevent credential leakage
- The role automatically encrypts plaintext credential files

## License

Apache 2.0

## Author Information

Dell Technologies Omnia Team
