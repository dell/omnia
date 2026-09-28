# Orchestrator — `test_creds.yml` Reference

## Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `oim_password` | string | No | SSH password for remote target. Leave empty for key-based auth. |
| `ldap_username` | string | No | POSIX directory account used by LDAP/Slurm verification. |
| `ldap_password` | string | No | Password for the LDAP test account. |
| `external_ldap_admin_password` | string | No | Required only by the explicit external LDAP setup utility. |

## Auto-Encryption

On first test run, `test_creds.yml` is automatically encrypted with Ansible Vault.
The vault key is stored in `.test_creds.key` (gitignored).

## Setup

Use `setup_env.sh`; do not edit or decrypt the file manually:

```bash
./setup_env.sh --set-creds
./setup_env.sh --set-ldap-test-creds
```

The LDAP password entered here must be the password reconciled on the
directory. Running `.venv/bin/python3 utility/create_ldap_user.py` creates a
new configured user or updates an existing user's password accordingly. When
changing to a new username, also select unused `external_ldap.uid_number` and
`external_ldap.gid_number` values in `test_config.yml`.
