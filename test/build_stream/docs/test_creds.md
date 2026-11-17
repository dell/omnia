# Credential stores

Build Stream automation keeps transport and product credentials separate.

## OIM transport credential

`test_creds.yml` and `.test_creds.key` are local, gitignored files used only
for password-based SSH to a remote execution OIM. Create them with:

```bash
./setup_env.sh --set-creds
```

For automation, pipe the password through standard input:

```bash
approved-secret-provider | ./setup_env.sh --creds-stdin
```

## Domain credentials

Run the following on the execution OIM. `OMNIA_DATA_PATH`,
`OMNIA_PROJECT_NAME`, and any `<DOMAIN>_DATA_PATH` overrides are read from
`/etc/omnia/omnia.env`; variables that are already exported take precedence.

```bash
./setup_env.sh --set-domain-creds                          # every domain, in order
./setup_env.sh --set-domain-creds --domain orchestrator    # one domain
./setup_env.sh --update-domain-creds [--domain <name>]     # existing stores only
credential-json-provider | ./setup_env.sh --domain-creds-stdin
```

Each domain store and its Vault key are written (0600) to
`<DOMAIN>_DATA_PATH/input/$OMNIA_PROJECT_NAME/` (default
`$OMNIA_DATA_PATH/<domain>/input/$OMNIA_PROJECT_NAME/`):

| Domain | Store / key | Fields |
|--------|-------------|--------|
| `repo_manager` | `repo_manager_config_credentials.yml` / `.repo_manager_config_credentials_key` | `pulp_password`; optional `docker_username`, `docker_password` |
| `image_build_manager` | `image_build_credentials.yml` / `.image_build_credentials_key` | `s3_secret_key`; optional `s3_access_id`, `aarch64_ssh_password` |
| `orchestrator` | `orchestrator_credentials.yml` / `.orchestrator_credentials_key` | `provision_password`, `bmc_username`, `bmc_password`; optional Slurm, OpenLDAP, CSI fields |
| `build_stream` | `build_stream_credentials.yml` / `.build_stream_credentials_key` | `gitlab_root_password`, `gitlab_ssh_password`, `build_stream_auth_username`, `build_stream_auth_password` (8+ characters), `postgres_user`, `postgres_password` |

Behaviour:

- A store counts as configured only when it is Vault-encrypted and every
  required field is a non-empty value. The file existing is not enough.
- `--set-domain-creds` asks before changing a store that is already
  configured. While prompting, pressing Enter keeps the stored value.
- `--update-domain-creds` works only on stores that are already configured.
- `--domain-creds-stdin` takes a JSON object keyed by domain, for example
  `{"repo_manager": {"pulp_password": "..."}, "build_stream": {...}}`. Only
  the domains you list are written, and unknown fields are rejected.
- Only the top-level spec fields are changed. Other data, such as
  BuildStream `oauth_clients` or repo_manager `registry_credentials`, is
  kept.
- For `build_stream`, the Argon2id `build_stream_auth_password_hash` is
  regenerated after every write. The plaintext password is never printed.

The stores are handled by `library/domain_credentials.py`, which
`setup_env.sh` calls. It uses the Ansible Vault API directly because the flat
credential CLI cannot load stores that contain nested data.

BuildStream credentials are shared with the deployed service, and PostgreSQL
keeps its first password in its data volume. After you change BuildStream
credentials, redeploy:

```bash
./omnia.sh -r build_stream
```

If you change the Postgres or GitLab values of a deployment that is already
running, do a full BuildStream cleanup first:

```bash
./omnia.sh -r build_stream --tags cleanup
./setup_env.sh --set-domain-creds --domain build_stream
./omnia.sh -r build_stream
```

Credentials are never generated in datasets or synchronized by the framework.
