# OpenBao credentials for the SVT

The SVT needs the passwords of four credential stores (domains): `repo_manager`,
`image_build_manager`, `orchestrator` and `build_stream`. Typing them is the default.
They can instead be read from OpenBao, the secret store the GitLab pipelines already use.
This page explains both ways, where the settings live, and what is (not) secret.

## 1. One place for the settings

OpenBao's address, secret path and TLS setting are kept **only** in the `openbao` block of
`user_inputs.yml`, the file of the lab's values. It is there, and not in the theme's
`build_stream_test_config.yml`, because OpenBao belongs to the lab and is shared by every
module and theme that needs passwords, now and later. The dataset generator does not write
it into any Omnia input file.

```yaml
openbao:
  server_url: "https://openbao.example.com:8200"   # "" = OpenBao is not used
  secret_path: "secret/data/omnia"                 # KV v2: secret/data/<path>; KV v1: secret/<path>
  tls_skip_verify: true                            # like test/pipeline (curl -k); false: use ca_cert / system CA
  ca_cert: ""                                      # absolute path of a CA file ("" = none)
```

Both users read it:

| User | How |
|---|---|
| `./setup_env.sh` on the OIM | reads the block directly |
| the GitLab project (`pipeline/setup_svt_project.py`) | turns `server_url`, `secret_path` and `tls_skip_verify` into the CI/CD variables `BAO_SERVER_URL`, `BAO_DATA_PATH` and `BAO_TLS_SKIP_VERIFY` |

`pipeline/svt_pipeline_config.yml` only has `openbao.auth_role` (the JWT role of the GitLab
login). A cluster can still use other credentials with `clusters.<name>.secret_path`.

## 2. How the secrets are laid out

One secret per domain, below the secret path: `<secret_path>/<domain>`, e.g.
`secret/data/omnia/repo_manager`. The fields are exactly those of the stores (an
unknown field is refused with "Unsupported fields"):

| Domain | Fields |
|---|---|
| `repo_manager` | `pulp_username`, `pulp_password`, `docker_username`, `docker_password` |
| `image_build_manager` | `s3_access_id`, `s3_secret_key`, `aarch64_ssh_password` |
| `orchestrator` | `provision_password`, `bmc_username`, `bmc_password`, `slurm_db_password`, `openldap_db_username`, `openldap_db_password`, `csi_username`, `csi_password` |
| `build_stream` | `gitlab_root_password`, `gitlab_ssh_password`, `build_stream_auth_username`, `build_stream_auth_password`, `postgres_user`, `postgres_password` |

Empty fields are ignored. This is the layout `test/pipeline` uses, so an OpenBao that
already serves it needs no change. To list the field **names** of a secret (never the
values): `bao kv get -format=json -mount=secret omnia/orchestrator | python3 -c
'import sys,json; print(sorted(json.load(sys.stdin)["data"]["data"]))'`.

## 3. Two ways to read them

### a. In the GitLab pipeline (automatic)

The `initialization` job has a GitLab ID token (`id_tokens: VAULT_ID_TOKEN`, audience
`$BAO_SERVER_URL`), logs in at `/v1/auth/jwt/login` with the role `BAO_AUTH_ROLE`, reads
the four secrets and pipes them as one JSON object to
`./setup_env.sh --domain-creds-stdin` on the OIM over SSH. This is the same login and read
`test/pipeline` does. Nothing is written to disk, logged or passed as an argument. No token
or password is stored in the project; the role's policy decides what may be read.

### b. By hand on the OIM (`./setup_env.sh`)

There is no GitLab on a manual run, so there is no ID token; you authenticate with an
OpenBao **token** that may read the secret path:

```bash
export BAO_TOKEN=<token>                        # or leave it unset: a hidden prompt asks
./setup_env.sh --domain-creds-from-openbao      # all four stores
./setup_env.sh --domain-creds-from-openbao --domain orchestrator   # one store
./setup_env.sh --openbao                        # every step; only the MISSING stores are read
./setup_env.sh --force --openbao                # clean reinstall first, then the same
```

What happens, step by step:

1. The `openbao` block of `user_inputs.yml` is read and checked (address, path, TLS).
2. The token comes from `BAO_TOKEN`, else from a hidden prompt. It is never a setting, a
   file or an argument. With no terminal and no `BAO_TOKEN` the step stops.
3. For each domain, `GET <server_url>/v1/<secret_path>/<domain>` with the token. KV v1 and
   v2 answers are both understood. A 403 ("the token may not read this path"), a 404
   ("check the path and the domain") or an unreachable server stops with that reason.
4. The field **names** are printed (to see what OpenBao holds); a value is never printed,
   logged or written to a file.
5. The fields go, in memory, as JSON on stdin to the suite's `--domain-creds-stdin`, which
   writes the encrypted stores (ansible-vault) exactly as when you type them.

`--openbao` with no action replaces the credential prompts of the every-step run: only the
stores still missing are read from OpenBao. Stores that exist are left alone.

## 4. How the pipeline gets access (no token is stored)

`test/pipeline` keeps no OpenBao token in GitLab, and neither does the SVT pipeline. GitLab
gives every job its own short-lived signed token (a JWT), OpenBao verifies it and answers with
a short-lived OpenBao token, and the job reads the secrets with that. Only three non-secret
variables are in GitLab: `BAO_SERVER_URL`, `BAO_AUTH_ROLE` and `BAO_DATA_PATH` (and optionally
`BAO_CACERT`).

```text
 initialization job (GitLab runner)                      OpenBao
 1. GitLab creates VAULT_ID_TOKEN for this job
    (id_tokens, audience = BAO_SERVER_URL, ~minutes)
 2. POST /v1/auth/jwt/login {jwt, role=BAO_AUTH_ROLE} --> checks the signature against GitLab's
                                                         keys (oidc_discovery_url), the audience
                                                         and the role's bound claims
 3.                                                  <-- short-lived OpenBao token, limited to
                                                         the role's policy (read secret path)
 4. GET /v1/<BAO_DATA_PATH>/<domain> x4, with that token (kept in the job's memory only)
 5. the four secrets -> one JSON on stdin of ssh -> ./setup_env.sh --domain-creds-stdin on the OIM
```

The token of step 3 is never written to a file, logged, stored as a variable or passed as an
argument, and expires by itself (`token_explicit_max_ttl` of the role, 3600 s in
`test/pipeline`'s setup). Nothing needs rotating in GitLab when the OpenBao token policy
changes: it is decided at login.

**What the OpenBao administrator does once** (the same as `test/pipeline`; an OpenBao already
set up for it only needs the policy to cover the SVT's path, see below). Full commands:
`test/pipeline/docs/OPENBAO_SETUP.md`, phase 3.

```bash
bao auth enable jwt
bao write auth/jwt/config oidc_discovery_url="https://<GITLAB>" bound_issuer="https://<GITLAB>" \
    oidc_discovery_ca_pem=@/tmp/gitlab.crt            # the CA of a self-signed GitLab
cat > gitlab-policy.hcl <<'HCL'
path "secret/data/<path>/*"     { capabilities = ["read", "list"] }
path "secret/metadata/<path>/*" { capabilities = ["read", "list"] }
path "auth/token/lookup-self"   { capabilities = ["read"] }
HCL
bao policy write gitlab-policy gitlab-policy.hcl
bao write auth/jwt/role/gitlab-role role_type=jwt policies=gitlab-policy \
    token_explicit_max_ttl=3600 user_claim=user_email \
    bound_audiences="https://<OPENBAO>:8200"
```

- **The policy path must be the SVT's `secret_path`** (without `/data`): the `openbao` block of
  `user_inputs.yml` says `secret_path: "secret/data/omnia"` → policy
  `secret/data/omnia/*`. A role whose policy covers another path gets "permission denied".
- **A new project must be allowed by the role.** `test/pipeline`'s role has no `bound_claims`,
  so any job of that GitLab can log in. To limit it to the SVT project, add
  `bound_claims='{"project_path":"root/omnia-system-test"}'` (or `project_id`) to the role; check
  with `bao read auth/jwt/role/gitlab-role`.
- **Audience:** `bound_audiences` is the OpenBao URL, and the job's token is requested for
  exactly `BAO_SERVER_URL`: both must be the same URL, port included.
- **GitLab 15.7 or later** (the `id_tokens` keyword).
- **Manual runs are different:** there is no GitLab job, so `./setup_env.sh
  --domain-creds-from-openbao` uses an OpenBao token you provide in `BAO_TOKEN` (section 3b).

## 5. TLS

`test/pipeline` has no CA setting: it calls OpenBao with `curl -k`. The SVT does the same by
default (`tls_skip_verify: true`, a warning is printed). To verify the certificate set
`tls_skip_verify: false` and either `ca_cert: /path/ca.pem` (manual runs), or in GitLab give
the optional File variable `BAO_CACERT` (or `BAO_TLS_SKIP_VERIFY=false` for the system CA
store).

## 6. Troubleshooting

| Message | Cause |
|---|---|
| `no OpenBao token` | export `BAO_TOKEN`, or run on a terminal |
| `permission denied (the token may not read this path)` | the token's policy does not cover `secret_path` |
| `not found (check openbao.secret_path and the domain name)` | wrong path (KV v2 needs `secret/data/...`) or the domain secret does not exist |
| `cannot reach OpenBao: ...` | server address/port, firewall; with a certificate error see section 4 |
| `Unsupported fields: x` | the secret holds a field the store does not have (section 2) |
| `the secret ... has no fields` | the secret exists but is empty |
| in GitLab: the login is rejected | the JWT role is bound to another project (`bound_claims`); `bao read auth/jwt/role/gitlab-role` |
