# test_creds.yml — Credentials Reference

SSH credentials for connecting to the remote OIM server.
**Only required for remote mode** (when `oim_server_ip` is set in `test_config.yml`).

---

## Fields

| Field | Description |
|-------|-------------|
| `oim_password` | SSH password for the remote OIM server |

---

## Setup

### 1. Edit the file

```yaml
# test_creds.yml
oim_password: "your_ssh_password"
```

### 2. Run tests

On first run, the framework **automatically encrypts** `test_creds.yml`
with Ansible Vault. A random vault key is generated and saved to
`.test_creds.key` (gitignored).

After encryption, `test_creds.yml` will contain Ansible Vault-encrypted
content instead of plain text. The framework handles decryption transparently.

---

## Passwordless SSH

If you use `ssh-copy-id` for key-based authentication, set `oim_password`
to any non-empty value (the password itself is not used):

```yaml
oim_password: "placeholder"
```

---

## Re-encrypting

If you need to change the password:

1. Delete the vault key: `rm .test_creds.key`
2. Replace `test_creds.yml` with plain text:
   ```yaml
   oim_password: "new_password"
   ```
3. Run tests — the framework will re-encrypt automatically.

---

## Security

- `.test_creds.key` — **Never committed** (in `.gitignore`)
- `test_creds.yml` — Safe to commit when encrypted (Ansible Vault)
- Before pushing to git, reset to: `oim_password: ""`
