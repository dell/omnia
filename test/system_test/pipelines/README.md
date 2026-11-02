# SVT pipeline (GitLab)

> **Not maintained for the current SVT flow.** `test/system_test` now runs
> locally: `./setup_env.sh` (configure, install, credentials) and
> `./run_validation.sh svt_<theme>` (initialization, system_verification,
> summary); see [`../README.md`](../README.md). These GitLab files still call
> the earlier stages (`cleanup`, `environment_setup`) and `--inputs`, and need
> an update before use.

This folder builds a separate GitLab project that runs the Omnia system
verification (SVT) on one or more clusters. The project holds only cluster
files and pipeline definitions; the Omnia code is cloned on each OIM at a
pinned commit. It is independent of `test/pipeline` and changes nothing there.

```text
 GitLab project (e.g. root/omnia-svt)                   OpenBao (KV v2)
 ├─ clusters/<cluster>/cluster.yml   OIM, clone, OpenBao   secret/omnia/<cluster>/
 ├─ clusters/<cluster>/user_inputs.yml  cluster values       oim, repo_manager,
 ├─ clusters/<cluster>/test_config.yml  BuildStream FVT      image_build_manager,
 └─ .gitlab-ci.yml + ci/                                     orchestrator, build_stream
        │ Run pipeline (THEME ▾ CLUSTERS ▾ START_STAGE ▾) or push      ▲ JWT (id_tokens)
        ▼                                                              │
 plan:  validate clusters -> generated/pipeline.yml                    │
 run:   child pipeline, per cluster (parallel, resource_group svt-<cluster>):
        initialization -> cleanup -> environment_setup -> svt:<case>... -> summary
                    │  each job: ci/scripts/remote_stage.sh  (runner) ──SSH──> OIM
                    ▼
        OIM: <clone_path>/test/system_test/run_validation.sh svt_<theme> <stage> (systemd-run unit)
```

## What each job does

| Job | Action | Default timeout |
|---|---|---|
| `plan` | Checks PyYAML, validates the selected clusters and the theme, writes the child pipeline | project |
| `validate_only` | Merge requests only: validates every cluster, runs nothing | project |
| `run` | Starts the child pipeline and mirrors its result | none (trigger) |
| `<c>:initialization` | Takes the cluster lock. Clones or fetches `clone_url` and checks out `clone_ref` (prints the resolved commit). Uploads `user_inputs.yml` and `test_config.yml`. Runs the `initialization` stage (generator, manifest) | 1h |
| `<c>:cleanup` | `cleanup` stage: removes the previous installation with each suite's own cleanup FVT: `fvt_build_stream cleanup` (when BuildStream is installed), `fvt_orchestrator`, `fvt_image_build_manager`, `fvt_repo_manager cleanup`, then `fvt_main cleanup` (`omnia.sh --cleanup`). Skipped on a fresh OIM | 4h |
| `<c>:environment_setup` | `environment_setup` stage: `fvt_main setup` and `fvt_main init` (`omnia.sh --setup-venv`, every `domain-init.sh`, with their checks), then the test dependencies in the Omnia venv. Then pipes each credential module from OpenBao to `setup_env.sh --domain-creds-stdin` | 4h |
| `<c>:svt:<case>` | `system_verification --case <case>`, one job per SVT case, streaming the full log | 12h |
| `<c>:summary` | `summary` stage, collects reports, releases the cluster lock; always runs | 30m |

Every stage job also does the following:

- **Detached unit:** it starts the stage as a transient systemd unit
  (`svt-<run_id>-<stage>`, `RuntimeMaxSec` = job timeout), so a dropped SSH
  session does not stop it.
- **Following:** it polls once a minute and prints one `[in progress Nm]` line
  when the step changes. SVT case jobs instead stream the complete stage log in
  a collapsible section.
- **On failure:** it prints the last 150 log lines and the log path on the OIM.
- **Reports:** it copies the run reports into `svt-reports/<cluster>/`. The
  artifacts are `reports.tgz` plus the JUnit XML, which appears in the
  pipeline's **Tests** tab; they are kept for 30 days.
- **`after_script`:** it stops the unit when the job fails or is cancelled, and
  a cancel also releases the lock.

**Re-run from a stage:** **Run pipeline** with `START_STAGE`. The new run
adopts the last initialized run on the OIM (`--resume`), keeps that commit and
inputs, and only accepts the same theme.

## One-time admin setup

### 1. Runner

Register a **shell** runner for the project. It needs:

- Python 3.9+ with PyYAML (`dnf install python3-pyyaml`), `ssh`, `tar`, and
  `sshpass` only if an OIM uses password login;
- network access to every OIM (SSH) and to OpenBao (HTTPS 8200).

Optional tags: `runner_tag` in `cluster.yml` pins all jobs to one runner, and
`full_log_runner_tag` sends the SVT case jobs to a runner with a large log
limit (see 3).

### 2. Timeouts (stages run longer than 3 hours)

- `setup_project.py` sets the project CI timeout to 24h.
- Each job sets its own `timeout:` from the theme file, or the cluster's
  `timeouts` overrides (`<number>m` or `<number>h`).
- A job timeout may exceed the project timeout but **not the runner's
  "Maximum job timeout"**. Leave that runner field empty, or set it at least to
  the longest stage (12h). `setup_project.py` warns when it is lower.

### 3. Log size (SVT cases print a lot)

| Limit | Default | Change |
|---|---|---|
| Runner `output_limit` | 4096 KB: the log is cut, the job continues | `[[runners]] output_limit = 1048576` (KB) in the runner's `config.toml` (use a dedicated runner and its tag in `full_log_runner_tag`) |
| GitLab `ci_jobs_trace_size_limit` | 100 MB: the job is **marked failed** | Rails console on the GitLab server: `Plan.default.actual_limits.update!(ci_jobs_trace_size_limit: 1024)` |
| Maximum artifacts size | 100 MB | Admin Area > Settings > CI/CD > Continuous Integration and Deployment |

Even when a log is cut, nothing is lost:

- each SVT case is its own job, so each has its own log limit;
- `reports.tgz` holds the complete logs;
- every log stays on the OIM under `<clone_path>/test/system_test/reports/<run_id>/`.

### 4. OpenBao

Print the one-time setup commands for an OpenBao admin. They create the KV v2
mount, the JWT auth bound to this GitLab, a read-only policy for
`secret/data/omnia/*`, and the `omnia-svt` role. The role accepts only jobs of
this project on a **protected branch**.

```bash
./openbao_secrets.py --print-setup --gitlab-url https://gitlab.example.com --project root/omnia-svt
```

Set `bound_audiences` to the `openbao_addr` (or `openbao_audience`) used in
`cluster.yml`.

## Create the project

```bash
cd test/system_test/pipelines
./setup_project.py --gitlab-url https://gitlab.example.com --project root/omnia-svt \
    --cluster cluster1 [--cluster cluster2] [--cacert /path/gitlab-ca.crt]
```

- **Token:** asked with a hidden prompt (`api` scope), or read from
  `--token-stdin`. It is never an argument or printed. TLS is always verified.
- **Pipeline files:** pushes `.gitlab-ci.yml`, `ci/` and the project
  `README.md` in one `[skip ci]` commit. Re-running it updates them.
- **Cluster files:**
  - `clusters/<cluster>/cluster.yml` comes from the template;
  - `user_inputs.yml` comes from `test/system_test/user_inputs/`;
  - `test_config.yml` comes from `test/build_stream/`;
  - existing cluster files are kept unless `--overwrite-clusters`.
- **Checks:** it creates the project when needed (private), protects the
  default branch, raises the CI timeout, reports the GitLab version (the
  drop-downs need 15.7+), and lists each runner with its tags and maximum
  timeout.

## Store the secrets of a cluster

```bash
./openbao_secrets.py --addr https://bao.example.com:8200 --cluster cluster1 [--module all]
```

It asks with hidden prompts for each value below and writes
`secret/omnia/<cluster>/<module>`:

| Module | Fields |
|---|---|
| `oim` | `ssh_private_key` (read from a key file, recommended) or `password` |
| `repo_manager` | `pulp_password`, optional `docker_username`, `docker_password` |
| `image_build_manager` | `s3_secret_key`, optional `s3_access_id`, `aarch64_ssh_password` |
| `orchestrator` | `provision_password`, `bmc_username`, `bmc_password`, optional Slurm, OpenLDAP and CSI fields |
| `build_stream` | `gitlab_root_password`, `gitlab_ssh_password`, `build_stream_auth_username`, `build_stream_auth_password`, `postgres_user`, `postgres_password` |

- **Field names** are those of the product credential files, so the pipeline
  pipes them unchanged to `setup_env.sh --domain-creds-stdin`.
- **Credential modules:** the `build_stream` theme uses all four
  (`credential_modules` in `ci/themes/build_stream.yml`).
- **Token:** asked with a hidden prompt, or read from a `--token-file` with
  mode 0600.
- **Automation:** `--values-stdin` reads one JSON object,
  `{"<module>": {"<field>": "<value>"}}`.

## Fill a cluster (in GitLab)

`clusters/<cluster>/cluster.yml`:

| Key | Required | Meaning |
|---|---|---|
| `oim_host` | yes | OIM IP or host name |
| `oim_user`, `oim_port` | no | SSH user (`root`) and port (`22`) |
| `oim_host_key` | recommended | One known_hosts line (`ssh-keyscan -t ed25519 <oim>`); with a port other than 22 use `[host]:port`. Empty = trust on first use, with a warning |
| `clone_url`, `clone_ref` | yes | Omnia repository and branch, tag or commit |
| `clone_path` | yes | Dedicated absolute directory on the OIM (not `/`, `/root`, `/opt`, `/opt/omnia`) |
| `openbao_addr`, `openbao_role` | yes | `https://` address and JWT role |
| `openbao_auth_mount`, `openbao_kv_mount`, `openbao_path`, `openbao_audience`, `openbao_cacert` | no | `jwt`, `secret`, `omnia/<cluster>`, `openbao_addr`, system trust |
| `runner_tag`, `full_log_runner_tag` | no | Runner tags for all jobs, and for the SVT case jobs |
| `timeouts` | no | Per-stage overrides, for example `system_verification: 16h` |

- **`user_inputs.yml`:** see `test/system_test/README.md`. MANDATORY values
  must be filled.
- **`test_config.yml`:** the BuildStream FVT settings (catalogs, pipelines,
  BuildStream cleanup flags); see `test/build_stream/docs/test_config.md`. The
  base domain cleanups use the `test_config.yml` of their own suite
  (`cleanup_credentials` in repo_manager and image_build_manager; orchestrator
  `cleanup_credentials`, `cleanup_slurm`, `cleanup_k8s`) as committed in
  `clone_ref`.

## Run

- **Run pipeline** (CI/CD > Pipelines): choose `THEME` (`build_stream`), `CLUSTERS` (`all` or names, comma separated) and `START_STAGE`.
- **Push:** a push to the default branch that changes `clusters/<name>/` runs
  only the changed clusters with the default theme (`build_stream`).
- **Merge request:** validates every cluster without touching any OIM.

## Security

- **OpenBao only:**
  - **Where secrets live:** in OpenBao only, read with the job's `id_token`
    through a role bound to this project and a protected branch.
  - **How a secret is fetched:** `bao_fetch.py` verifies TLS and writes each
    secret to a mode-0600 file in a private temp directory, which is deleted
    when the job ends.
  - **How it reaches the OIM:** module credentials travel over SSH **stdin**.
  - **What GitLab holds:** no secret variables.
- **No secret** in Git, arguments, environment values, logs, dotenv files or
  artifacts. Report archives exclude the uploaded inputs.
- **Host keys:** pin `oim_host_key`; then SSH runs with strict host key
  checking.
- **Values:** `svt_ci.py` validates every `cluster.yml` value against a fixed
  character set before any use, and remote commands quote each value
  (`printf %q`).
- **Concurrency:** the cluster lock (`/run/lock/svt-<cluster>`) and per-cluster
  resource groups keep two pipelines from interleaving on one OIM.

## Troubleshooting

| Message | Fix |
|---|---|
| `fill the mandatory value(s)` in `plan` | Complete `clusters/<c>/cluster.yml` |
| `the runner needs PyYAML` | `dnf install python3-pyyaml` on the runner |
| `OpenBao: POST auth/jwt/login: HTTP 403` | Role `bound_claims` or `bound_audiences`, protected branch, project path |
| `OpenBao <path>/oim has neither ssh_private_key nor password` | `./openbao_secrets.py --module oim` |
| `cluster <c> is busy with run '<id>'` | Wait for that pipeline, or remove the stale lock on the OIM: `rm -rf /run/lock/svt-<c>` |
| `run <id> was not initialized` | Run from `initialization`, or use `START_STAGE` (adds `--resume`) |
| Job killed at the runner timeout | Raise or clear the runner's maximum job timeout |
| Log ends with "Job's log exceeded limit" | Use `full_log_runner_tag` and the limits in section 3; the full log is in `reports.tgz` |

## Files

```text
pipelines/
├── README.md               this file
├── setup_project.py        create or update the GitLab project (verified TLS, hidden token)
├── openbao_secrets.py      store cluster secrets; --print-setup for the OpenBao admin
└── project_template/       pushed to the project
    ├── README.md           how to use the project (for its users)
    ├── .gitlab-ci.yml      parent: drop-downs, plan, validate_only, run
    ├── ci/themes/          build_stream.yml (timeouts, cases, credential modules)
    ├── ci/scripts/         render_pipeline.py, remote_stage.sh, bao_fetch.py,
    │                       cluster_config.py, svt_ci.py
    └── clusters/cluster1/cluster.yml   cluster template
```

Checked here: the planner, cluster validation, `bao_fetch.py` against a mock
HTTPS OpenBao (JWT login, field and JSON output, 0600 files, 403/404, an
untrusted certificate), and `remote_stage.sh` with a local SSH shim (unit
start, polling, run guard, cluster lock, report collection). Not run here: a
real GitLab pipeline and a real OpenBao.
