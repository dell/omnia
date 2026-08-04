# collect_build_credentials

Collects and prepares credentials for the image build process including S3 access keys, registry credentials, and aarch64 SSH keys. Writes `image_build_credentials.yml`.

## Requirements

- Ansible Vault for encrypted credential storage

## Role Variables

See `vars/main.yml` for the full list.

## Dependencies

- `image_build_setup` — environment and config loading

## Example

```yaml
- hosts: localhost
  roles:
    - collect_build_credentials
```
