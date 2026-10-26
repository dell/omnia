# Credentials Reference

The suite uses one local test store and the four product domain stores. All
are Ansible Vault encrypted, mode `0600`, and excluded from Git. Never put
secrets in command arguments, environment variables, logs or shell history.

## test_creds.yml (local)

`test_creds.yml` with its key `.test_creds.key` lives in this directory.

| Field | Required when | Purpose |
|---|---|---|
| `oim_password` | Password-based remote SSH (`oim_server_ip` set) | Authenticate to the OIM. |

```bash
./setup_env.sh --set-creds
./setup_env.sh --update-creds
credential_provider | ./setup_env.sh --creds-stdin     # {"oim_password": "<SECRET>"}
```

## Domain stores (project input paths)

Each store is at `<DOMAIN>_DATA_PATH` (default `OMNIA_DATA_PATH/<domain>`)
`/input/<OMNIA_PROJECT_NAME>/`, resolved from `/etc/omnia/omnia.env`. They
are the stores the product playbooks read; saving them first lets the whole
suite run unattended. `--set-domain-creds` prompts them in suite order:

| Domain | File | Fields (`*` required) |
|---|---|---|
| `repo_manager` | `repo_manager_config_credentials.yml` | `pulp_password*`, `docker_username`, `docker_password` (both or neither) |
| `image_build_manager` | `image_build_credentials.yml` | `s3_access_id`, `s3_secret_key*`, `aarch64_ssh_password` |
| `orchestrator` | `orchestrator_credentials.yml` | `provision_password*`, `bmc_username*`, `bmc_password*`, `slurm_db_password`, `openldap_db_username`, `openldap_db_password`, `csi_username`, `csi_password` |
| `build_stream` | `build_stream_credentials.yml` | `gitlab_root_password*`, `gitlab_ssh_password*`, `build_stream_auth_username*`, `build_stream_auth_password*`, `postgres_user*`, `postgres_password*` |

For `build_stream` the Argon2id `build_stream_auth_password_hash` is
regenerated after every write. If BuildStream is already deployed, apply a
change with `./omnia.sh -r build_stream`.

```bash
./setup_env.sh --set-domain-creds                          # all four, in order
./setup_env.sh --set-domain-creds --domain orchestrator    # one domain
./setup_env.sh --update-domain-creds [--domain <name>]     # existing stores only
credential_provider | ./setup_env.sh --domain-creds-stdin
./setup_env.sh                                             # status of every store
```

`--domain-creds-stdin` takes one JSON object keyed by domain; only the
listed domains are written:

```json
{
  "repo_manager": {"pulp_password": "<SECRET>"},
  "build_stream": {"gitlab_root_password": "<SECRET>", "postgres_user": "<USER>"}
}
```

Pressing Enter at a prompt keeps the stored value. Writes go through
`utility/domain_credentials.py`: only the listed top-level fields change, data
the playbooks store in the same file (for example `oauth_clients`,
`gitlab_root_token`, `registry_credentials`) is kept, and the file is
re-encrypted atomically. Unknown fields and missing required fields are
rejected.
