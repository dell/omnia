# Test Credentials

The `test_creds.yml` file contains encrypted credentials for target servers.

## Encryption

Credentials are encrypted using Ansible Vault with the key in `.test_creds.key`.

## Format

```yaml
ssh_username: "encrypted_value"
ssh_password: "encrypted_value"
```

## Security

- Never commit `.test_creds.key` to version control
- Add `test_creds.yml` to `.gitignore`
