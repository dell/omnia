# test_creds.yml — Credentials Reference

SSH credentials for connecting to the remote OIM server. They are needed only
for password-based remote mode; omit them when key-based SSH already works.

---

## Fields

| Field | Description |
|-------|-------------|
| `oim_password` | SSH password for the remote OIM server |

---

## Setup

Use the setup command so the credential file and vault key are created with
the correct permissions and encrypted immediately:

```bash
./setup_env.sh --set-creds
```

The command prompts twice for the SSH password. If credentials already exist,
it asks before updating them. To update without the existence prompt, run:

```bash
./setup_env.sh --update-creds
```

For automation, a value can be supplied non-interactively:

```bash
./setup_env.sh --creds '<SSH_PASSWORD>'
```

Prefer the interactive command because a command-line password can remain in
shell history. The framework decrypts the vault transparently during tests.

---

## Passwordless SSH

If SSH key authentication is already configured, `test_creds.yml` is not
required. Leave it absent and verify the configured user can connect first:

```bash
ssh <oim_ssh_user>@<oim_server_ip>
```

The setup summary may report that SSH credentials are not set; this is
expected when key-based authentication is used.

---

## Updating Credentials

Run `./setup_env.sh --update-creds`. Do not delete the vault key or edit the
encrypted YAML manually.

---

## Security

- `test_creds.yml` and `.test_creds.key` are both gitignored.
- Never commit either credential file, even when the YAML is vault-encrypted.
- Prefer `./setup_env.sh --set-creds` over writing plaintext YAML manually.
