# Orchestrator Test Utilities

## Standalone OpenLDAP server

The utility creates or reconciles an isolated OpenLDAP directory used by the
Orchestrator external-LDAP, Slurm identity, SSH, and PAM tests. It is separate
from the product-managed `omnia_auth` container.

`openldap_server_config.yml` contains only non-sensitive deployment settings.
Administrator, remote-SSH, and LDAP-user secrets are stored in the encrypted,
git-ignored `openldap_server_credentials.yml` file.

## Prerequisites

- Python 3.12 or later with the Orchestrator test requirements installed.
- Podman on the selected LDAP server.
- Network reachability from the OIM and provisioned nodes to the configured
  LDAP port.
- For a remote LDAP host, key-based SSH or the encrypted SSH credential.

## Configure the server

Edit `utility/openldap_server_config.yml`:

| Setting | Purpose |
|---|---|
| `openldap_server_ip` | Empty for the current host; otherwise a reachable remote host |
| `openldap_server_ssh_user` / `openldap_server_ssh_port` | Remote management identity and port |
| `openldap_server_ssh_private_key` | Optional key used for remote management |
| `openldap_server_ssh_strict_host_key_checking` | Keep `true` outside an isolated lab |
| `openldap_domain` | DNS-style domain converted to the LDAP base DN |
| `openldap_image` | OpenLDAP container image |
| `openldap_container_name` / `openldap_data_volume` | Persistent runtime names |
| `openldap_port` / `openldap_secure_port` | Published LDAP and LDAPS ports |
| `openldap_reset_existing` | Data-reset request; safe default is `false` |
| `openldap_default_uid_start` | First generated POSIX UID/GID |
| `openldap_default_login_shell` | Default shell for generated users |

Create or replace the encrypted credential store interactively:

```bash
cd test/orchestrator
./utility/setup_ldap_server.sh
```

The setup prompts for:

- directory administrator username and secret;
- optional remote-host SSH secret;
- number of LDAP test users; and
- username and secret for every test user.

The setup performs a non-mutating configuration check after encryption. It
does not deploy the LDAP server unless `--deploy` is supplied.

## Validate and deploy

```bash
# Validate YAML, encrypted credentials, identifiers, ports, and reset policy.
python3 utility/create_ldap_server.py --check

# Create or reconcile the container, directory, groups, and users.
python3 utility/create_ldap_server.py

# Configure credentials and reconcile in one interactive operation.
./utility/setup_ldap_server.sh --deploy
```

Use `python3 utility/create_ldap_server.py --help` for custom configuration or
credential paths.

## Idempotency

Normal execution preserves the named data volume, reuses or starts the
existing container, reconciles users and POSIX groups, updates supplied
authentication values, and verifies authenticated searches. Repeating the
same desired configuration does not reset directory data.

## Data reset

Deletion requires both controls:

1. Set `openldap_reset_existing: true` in
   `utility/openldap_server_config.yml`.
2. Run:

   ```bash
   python3 utility/create_ldap_server.py --allow-data-reset
   ```

This removes the named container and volume before rebuilding the directory.
Do not enable it against a directory whose data must be retained.

## Connect Orchestrator tests

After the standalone directory is ready:

1. Set `validate_external_ldap: true` in `test_config.yml`.
2. Set `configure_external_ldap: true` when the test may reconcile the local
   `omnia_auth` proxy configuration.
3. Set `external_ldap_server_ip`, `external_ldap_server_port`,
   `external_ldap_domain`, and `external_ldap_bind_username` to match it.
4. Store the OIM SSH credential and, because external LDAP is enabled, the
   LDAP test identity and bind secret with `./setup_env.sh --set-creds`.
5. Run `prepare verify --suite openldap` before the PXE Slurm identity cases.

```bash
./run_validation.sh fvt_orchestrator prepare verify --suite openldap
./run_validation.sh fvt_orchestrator pxeboot verify \
  --suite slurm_ldap --marker openldap
```

## Credential handling

Sensitive values are never stored in the committed configuration or passed as
command-line values. The encrypted credential file and its vault key are both
excluded by `.gitignore`. Keep the key mode at `0600`, and do not distribute
the encrypted file together with its key.
