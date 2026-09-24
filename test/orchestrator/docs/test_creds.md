# test_creds.yml — Credentials Reference

`test_creds.yml` is the local encrypted test credential store. Its vault key
is `.test_creds.key`. Both files are mode `0600`, excluded from Git, and must
never be copied into datasets or reports.

## Fields

| Field | Required when | Purpose |
|---|---|---|
| `oim_password` | Password-based remote SSH is used | Authenticate to the execution OIM. |
| `ldap_username` | LDAP identity tests are selected | LDAP identity used by SSH, PAM, Slurm, and proxy verification. |
| `ldap_password` | LDAP identity tests are selected | Authenticate the LDAP test identity. |
| `external_ldap_bind_password` | External LDAP validation and reconciliation are enabled | Bind `omnia_auth` to the external directory. |

Product credentials such as BMC, provisioning, Slurm database, OpenLDAP
database, and CSI values belong in the separate project-domain store created
with `--set-domain-creds`.

## Interactive setup

```bash
./setup_env.sh --set-creds
./setup_env.sh --update-creds
```

When external LDAP is disabled, the prompt contains only `oim_password`.
When it is enabled, the same schema additionally requires all three LDAP
fields. Existing encrypted values can be retained during an update.

## Non-interactive setup

Send one bounded JSON object through standard input:

```bash
credential_provider | ./setup_env.sh --creds-stdin
```

External LDAP enabled:

```json
{
  "oim_password": "<SSH_SECRET>",
  "ldap_username": "<LDAP_TEST_IDENTITY>",
  "ldap_password": "<LDAP_TEST_SECRET>",
  "external_ldap_bind_password": "<LDAP_BIND_SECRET>"
}
```

External LDAP disabled:

```json
{
  "oim_password": "<SSH_SECRET>"
}
```

Unknown fields, missing required fields, invalid types, and oversized input
are rejected by the shared `omnia_auto` credential API. Do not place secrets
in command arguments, environment variables, source, logs, or shell history.
