# `svt_pipeline_config.yml`: every setting

`pipeline/svt_pipeline_config.yml` describes the GitLab project that runs the SVT and the
clusters (OIMs) it tests. `./setup_svt_project.py` reads it and writes three things into
GitLab: the pipeline files (`.gitlab-ci.yml`, `.gitlab-ci-svt-<theme>.yml`), CI/CD variables, and
a reference copy of the config. **Passwords and tokens are never in this file.**

Change a value, then apply it to an existing project:

```bash
cd test/system_test/pipeline
./setup_svt_project.py --render                                   # look at the CI files first
GITLAB_TOKEN=<token> ./setup_svt_project.py --update --gitlab-url https://<gitlab-host>
```

How to set up the project the first time and how to update a running one is in
[PIPELINE.md](PIPELINE.md). OpenBao's address, path and TLS are not in this file: they are the
`openbao` block of `user_inputs.yml` ([OPENBAO.md](OPENBAO.md)); the catalog and cleanup
flags are in `build_stream_test_config.yml` ([TEST_CONFIG.md](TEST_CONFIG.md)).

## `gitlab`

| Key | Example | Meaning |
|---|---|---|
| `project_name` | `omnia-system-test` | Name of the GitLab project. `--create` makes it when it does not exist; `--update` needs it to exist |
| `namespace` | `root` | User or group that owns the project. Letters, digits, `_`, `-`, `.` and `/` for subgroups |
| `branch` | `main` | Branch the CI files are committed to and pipelines start from. Use the protected default branch: the OIM password is a *protected* variable and is only given to pipelines on protected branches |

## `svt`

| Key | Default | Meaning | Becomes |
|---|---|---|---|
| `theme` | `build_stream` | The SVT theme (`THEMES` in `library/vars/theme_vars.py`). Its stages become the pipeline jobs, so a new theme or stage needs no change here. `catalog_build`: one job per catalog (see below) | read at generation time |
| `poll_seconds` | `30` | Seconds between two reads of a running stage's log on the OIM (minimum 5) | `SVT_POLL_SECONDS` |
| `log_limit_kb` | `2500` (empty) | How much of the OIM logs one job prints into the GitLab job log, in KB. GitLab Runner stops collecting a job log at 4096 KB (`output_limit` in the runner's `config.toml`) and timestamps every line, so the job hides base64-only lines, cuts lines over 600 characters and stops printing at this budget (shared by all logs of the job). The full logs stay on the OIM under `reports/ci/<pipeline id>/`, and the last 40 lines are printed when the job ends | `SVT_LOG_LIMIT_KB` |
| `timeouts_hours` | see below | Time limit of each job, in hours | rendered into `.gitlab-ci-svt-<theme>.yml` (GitLab does not expand variables in `timeout:`); the project's CI timeout is raised to the longest |

`timeouts_hours` keys are the job names: `preflight` (the checks and the checkout), `initialization`, then the
theme's stages (`prepare_build_stream`, `build_deploy`, `cadence`, `automatic_cleanup`) and
`summary`. A job without its own entry uses `default_hours` (6 when that is missing too). The
shortest allowed limit is 10 minutes. The runner's own maximum timeout still applies, so raise
that too for long stages.

### Theme `catalog_build`: one job per catalog

With `theme: "catalog_build"` the pipeline has one job per catalog, in run order:
`preflight -> initialization -> catalog_01 -> catalog_02 -> ... -> summary`. The jobs are
resolved when the CI files are rendered (`--render`, `--create`, `--update`), from
`catalog_build_test_config.yml` and `./omnia.sh --list-catalogs` of this checkout, exactly as
`./setup_env.sh --configure` resolves them on the OIM:

- Each job is titled with its catalog (`# Catalog 2: rhel/10.2/...` in `.gitlab-ci-svt.yml`).
  A catalog skipped by `include_aarch64: false` still gets a short job that records the skip.
- With `continue_on_failure: true` every catalog job has `allow_failure`: a failed catalog does
  not stop the next one, and the summary still fails.
- A catalog job without its own `timeouts_hours` entry uses `catalog_stage` (then
  `default_hours`).
- `skip_stages` (or `SVT_SKIP_STAGES`) takes catalog stages too, e.g. `catalog_03,catalog_07`.
- The rendered catalog list is the CI/CD variable `SVT_CATALOG_PLAN`. After configure, the
  initialization job compares it with the plan written on the OIM and fails, before cleanup
  and install, when they differ (the catalog list was edited in the project, or the tested
  branch bundles other catalogs). Change the list in this checkout, then
  `./setup_svt_project.py --update --update-inputs`.

## `openbao`

| Key | Example | Meaning | Becomes |
|---|---|---|---|
| `auth_role` | `gitlab-role` | The OpenBao JWT role the jobs log in with (the role `test/pipeline` uses) | `BAO_AUTH_ROLE` |

`BAO_SERVER_URL`, `BAO_DATA_PATH` and `BAO_TLS_SKIP_VERIFY` come from the `openbao` block of
`../user_inputs.yml`; a cluster that needs other credentials sets `secret_path` (below).
**No OpenBao token is stored in GitLab**: each job logs in with its own short-lived GitLab
token, see [OPENBAO.md](OPENBAO.md#4-how-the-pipeline-gets-access-no-token-is-stored).

## `email`

The `summary` job mails the result. Leave `recipients`, `sender` or `smtp_server` empty to send
no email.

| Key | Default | Meaning | Becomes |
|---|---|---|---|
| `recipients` | empty | Comma separated addresses | `EMAIL_RECIPIENTS` |
| `sender` | empty | From address | `EMAIL_SENDER` |
| `smtp_server` | empty | SMTP relay reachable from the runner | `SMTP_SERVER` |
| `smtp_port` | `25` | `25` plain, `587` STARTTLS, `465` TLS | `SMTP_PORT` |
| `required` | `false` | `true`: the `summary` job fails when the email cannot be sent. `false`: a failed email is reported as an error block in the job log but does not change the result | `SVT_EMAIL_REQUIRED` |

If the relay needs a login, add the masked variables `SMTP_USER` and `SMTP_PASSWORD` in GitLab
by hand. The email has the status, the failed stage(s) and steps, a link to the `svt_report/`
artifacts directory and the SVT HTML report as its only attachment.

## `clusters`

One block per cluster (one OIM each). The block name becomes the variable prefix (`oim1` →
`OIM1_`, `cluster-2` → `CLUSTER_2_`; two names that give the same prefix are refused) and the
resource group `svt-<name>`: two pipelines for the same OIM never run together, the second
waits. All clusters of the file run at the same time, each on its own OIM.

### `clusters.<name>.theme`

| Key | Default | Meaning | Where it is used |
|-----|---------|---------|------------------|
| `theme` | required | The SVT theme of this cluster (`THEMES` in `library/vars/theme_vars.py`). It is the value of the cluster's CI/CD variable `<PREFIX>_SVT_THEME`, and the pipeline picks the theme from that variable: there is one trigger job per cluster and theme, and the one whose theme equals the variable runs (the child pipeline files `.gitlab-ci-svt-<theme>.yml` exist for every theme). So the theme can be changed with the variable (Settings > CI/CD > Variables, or for one run in Run pipeline) without regenerating anything; the first job fails on a theme that is not known. The cluster's inputs are `clusters/<name>/svt/user_inputs.yml` and `<theme>_test_config.yml`. There is no theme in the `svt` block | `<PREFIX>_SVT_THEME` |

### `clusters.<name>.enabled`

| Key | Default | Meaning | Where it is used |
|-----|---------|---------|------------------|
| `enabled` | `true` | `false` leaves the cluster out of the default run (`SVT_CLUSTERS` lists the enabled clusters only). Its trigger job stays in the pipeline, so a run can still select it by name | the `SVT_CLUSTERS` variable |

### `clusters.<name>.target`

| Key | Default | Meaning | Becomes |
|---|---|---|---|
| `ip` | none | IP or name of the OIM, reachable from the runner on port 22 | `<PREFIX>_SVT_TARGET_IP` |
| `user` | `root` | SSH user | `<PREFIX>_SVT_TARGET_USER` |
| `ssh_skip_host_key` | `false` | `true`: do not check the OIM's host key (the jobs warn: someone in the middle could read the password and the credentials). `false`: the File variable `<PREFIX>_SVT_SSH_KNOWN_HOSTS` is required | `<PREFIX>_SVT_SSH_SKIP_HOST_KEY` |

### `clusters.<name>.omnia`

| Key | Default | Meaning | Becomes |
|---|---|---|---|
| `repo` | none | Git URL of the Omnia repository the OIM clones | `<PREFIX>_SVT_OMNIA_REPO` |
| `branch` | none | Branch to test. It must contain `test/system_test` | `<PREFIX>_SVT_OMNIA_BRANCH` |
| `install_path` | none | Absolute folder on the OIM for the checkout. Dedicate it to the pipeline | `<PREFIX>_SVT_OMNIA_INSTALL_PATH` |
| `checkout_mode` | `update` | `update`: clone when missing, else fetch the branch and reset to it (local changes of tracked files are discarded); `recreate`: delete the folder and clone it again, a fresh checkout every run (anything still running from the folder is stopped first; system folders such as `/root`, `/opt` or `/opt/omnia` are refused); `keep`: use it as it is | `<PREFIX>_SVT_CHECKOUT_MODE` |

### `clusters.<name>.svt`

| Key | Default | Meaning | Becomes |
|---|---|---|---|
| `clean_reinstall` | `true` | `true`: the initialization job runs `./setup_env.sh --force`: cleanup (including the NFS shares), then a full install. `false`: no cleanup, install only what changed | `<PREFIX>_SVT_CLEAN_REINSTALL` |
| `skip_stages` | empty | Theme stages to leave out, comma separated, e.g. `cadence,automatic_cleanup` | `<PREFIX>_SVT_SKIP_STAGES` |

### `clusters.<name>.secret_path`

Optional. The OpenBao path of this cluster's credentials when it differs from the `secret_path`
of `user_inputs.yml`, for example `secret/data/omnia/oim1`. Becomes `<PREFIX>_BAO_DATA_PATH`.
An empty value keeps the global one.

## The variables the script creates

`--create` and `--update` set these CI/CD variables (the value of a variable is shown by the
script, secrets are never printed):

| Variable | From | Notes |
|---|---|---|
| `SVT_CLUSTERS` | the enabled cluster names | Which clusters a pipeline runs, comma separated. Override it per run (Run pipeline, a schedule, the API); a name that is not in the config fails the first job |
| `<PREFIX>_SVT_THEME` | `clusters.<name>.theme` | The theme the pipeline runs on that cluster; change it here or per run, no `--update` needed |
| `SVT_POLL_SECONDS`, `SVT_LOG_LIMIT_KB`, `SVT_EMAIL_REQUIRED` | `svt`, `email` | |
| `EMAIL_*`, `SMTP_SERVER`, `SMTP_PORT` | `email` | |
| `BAO_AUTH_ROLE` | `openbao.auth_role` | |
| `BAO_SERVER_URL`, `BAO_DATA_PATH`, `BAO_TLS_SKIP_VERIFY` | `user_inputs.yml` `openbao` block | |
| `<PREFIX>_SVT_*`, `<PREFIX>_BAO_DATA_PATH` | the cluster block | A cluster variable that is empty keeps the global value of the same name |

Variables the script never overwrites unless you ask:

| Variable | Type | Set by |
|---|---|---|
| `<PREFIX>_SVT_TARGET_PASS` | masked, protected | `--create` or `--update --set-password` (asks, or reads the same-named environment variable) |
| `<PREFIX>_SVT_SSH_KNOWN_HOSTS` | File, protected | `--scan-host-keys` (or by hand) |
| `<PREFIX>_SVT_SSH_KEY` | File | by hand: an SSH key instead of the password |
| `BAO_CACERT` | File, protected | `--bao-cacert FILE` (optional: verify the OpenBao certificate) |
| `SMTP_USER`, `SMTP_PASSWORD` | masked | by hand |

`--update` rewrites every variable of the first two tables from the config, so a value you
changed by hand in GitLab for one of them is put back. Change it in the config instead.

## Examples

Two OIMs, the second with its own credentials and no cadence:

```yaml
clusters:
  oim1:
    target: {ip: "10.0.0.11", user: "root"}
    omnia: {repo: "https://github.com/dell/omnia.git", branch: "staging",
            install_path: "/root/omnia", checkout_mode: "update"}
    svt: {clean_reinstall: "true", skip_stages: ""}
  oim2:
    target: {ip: "10.0.1.11", user: "root"}
    omnia: {repo: "https://github.com/dell/omnia.git", branch: "staging",
            install_path: "/root/omnia", checkout_mode: "update"}
    svt: {clean_reinstall: "true", skip_stages: "cadence"}
    secret_path: "secret/data/omnia/oim2"
```

Then `--update` (and `--update-inputs`, or `--create`, for the new cluster's inputs; see
[PIPELINE.md](PIPELINE.md#update-an-existing-pipeline)).
