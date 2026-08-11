# Orchestrator — `test_creds.yml` Reference

## Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `oim_password` | string | No | SSH password for remote target. Leave empty for key-based auth. |

## Auto-Encryption

On first test run, `test_creds.yml` is automatically encrypted with Ansible Vault.
The vault key is stored in `.test_creds.key` (gitignored).

## Setup

1. Fill in `oim_password` in `test_creds.yml` (if using password-based SSH)
2. Run any test — file will be encrypted automatically
3. To re-edit: `ansible-vault decrypt test_creds.yml --vault-password-file .test_creds.key`
