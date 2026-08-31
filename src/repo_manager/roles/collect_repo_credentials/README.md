# collect_repo_credentials Role

## Description

Collects and manages repository manager credentials with support for multiple authentication types. This role handles credential creation, validation, encryption, and updates for various registry types including Pulp, Docker Hub, and custom container registries.

## Features

- **Flexible Authentication**: Supports basic auth and no-authentication modes
- **Interactive Prompting**: Prompts users for credentials when values are missing or empty
- **Credential Encryption**: Encrypts credential files using Ansible Vault
- **Multiple Registry Support**: Handles Pulp, Docker Hub, and custom container registries
- **Atomic Persistence**: Never decrypts the canonical credential file in place
- **Credential Persistence**: Preserves credentials across deployments unless explicitly deleted

## Requirements

- Ansible 2.9 or higher
- Ansible Vault for credential encryption
- `repo_manager_config.yml` must be configured with registry definitions

## Role Variables

### Main Variables

- `repo_manager_credential_file` - Path to credential file (auto-detected)
- `pulp_username` - Pulp server username (default: admin)
- `pulp_password` - Pulp server password (prompted if not provided)
- `docker_username` - Docker Hub username (optional)
- `docker_password` - Docker Hub password (optional)

### Registry Configuration

Registry authentication is configured using lowercase keys in `repo_manager_config.yml`:

```yaml
registries:
  harbor.example.com:
    base_url: "https://harbor.example.com"
    port: 443
    auth:
      type: basic
      credentials:
        vault_path: "registries/harbor-production"
    tls:
      ca_path: ""
      client_cert_path: ""
      client_key_path: ""
      insecure: false
```

## Dependencies

- `repo_manager_setup` role for configuration loading

## Example Usage

### Basic Usage

```yaml
- hosts: localhost
  roles:
    - role: collect_repo_credentials
```

### With Pre-provided Password

```bash
ansible-playbook playbook.yml -e pulp_password='your_password'
```

### Standalone Credential Collection

```yaml
- hosts: localhost
  roles:
    - role: collect_repo_credentials
```

## Credential File Structure

The role creates `repo_manager_config_credentials.yml` with the following structure:

```yaml
# Pulp Credentials
pulp_username: "admin"
pulp_password: "encrypted_password"

# Docker Hub Credentials (optional)
docker_username: "docker_user"
docker_password: "encrypted_password"

# Configured registry credentials (optional)
registry_credentials:
  registries/harbor-production:
    registry: "harbor.example.com"
    username: "registry_user"
    password: "encrypted_password"
```

## Authentication Types

### Basic Authentication
- Requires both username and password
- Username and password are mandatory for `type: basic`
- Encrypted using Ansible Vault

### TLS Authentication
- CA certificates, client certificates, and client keys are configured in
  `repo_manager_config.yml`; they are not credentials and are not prompted

### No Authentication
- Used for public registries
- Skips credential collection entirely

## Security Features

- **Encryption**: All credentials are encrypted using Ansible Vault
- **No Logging**: Sensitive data is not logged during execution
- **Interactive Prompts**: Passwords are prompted with echo disabled
- **Vault Key Management**: Automatic vault key generation
- **File Permissions**: Credential files have restricted permissions (0600)

## Tags

- `credentials` - Credential collection operations
- `prepare` - Part of preparation phase

## Notes

- Credentials are preserved across deployments unless explicitly deleted
- The role automatically detects if credentials are already loaded
- Missing mandatory credentials trigger interactive prompts
- Optional credentials can be skipped by pressing Enter
- The vault key is stored in `.repo_manager_config_credentials_key`

## Troubleshooting

### Credentials Not Being Prompted
- Check if `repo_manager_credential_file` already exists
- Verify that mandatory fields are actually empty
- Ensure the role is not being skipped by conditional logic

### Encryption Failures
- Verify vault key file exists and is accessible
- Check file permissions on credential and vault key files
- Ensure Ansible Vault is properly configured

### Registry Configuration Issues
- Validate `repo_manager_config.yml` syntax
- Check that registry names are unique
- Verify field names match between config and credential file
