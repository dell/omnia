# collect_build_credentials

Collects S3 credentials and, when an ARM host is configured, its initial SSH
password. It writes a Vault-encrypted `image_build_credentials.yml` and a
separate `.image_build_credentials_key` in the runtime project input directory.

`s3_secret_key` is always prompted when empty. `s3_access_id` is required only
for PowerScale; local MinIO defaults an empty access ID to `admin`. The ARM
password is currently required whenever `aarch64_inventory_host_ip` is set;
`prepare_aarch64_node` uses it to install a passwordless SSH key.

## Requirements

- Ansible Vault for encrypted credential storage

## Role Variables

See `vars/main.yml` for the full list.

## Orchestration Prerequisite

The role has no metadata dependency, but callers must first provide the paths
and configuration facts set by `image_build_setup`.

## Example

```yaml
- hosts: localhost
  roles:
    - collect_build_credentials
```
