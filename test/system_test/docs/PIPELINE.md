# Run the SVT from GitLab

The pipeline runs the same `./setup_env.sh` and `./run_validation.sh` of the SVT
(`test/system_test`, see the [README](../README.md)) on the OIM over SSH; without the pipeline
the SVT runs unchanged on the OIM. One GitLab project can test one or many clusters (one OIM
each).

| File | Role |
|---|---|
| `pipeline/svt_pipeline_config.yml` | Your settings: GitLab project, theme, job timeouts, email, the clusters. Every key: [PIPELINE_CONFIG.md](PIPELINE_CONFIG.md) |
| `pipeline/setup_svt_project.py` | Creates or updates the project (GitLab client of `test/pipeline/setup_gitlab_project.py`) |
| `pipeline/cleanup_svt_project.py` | Checks, empties (pipelines, logs, artifacts) or deletes the project, then verifies it: see [pipeline/README.md](../pipeline/README.md) |
| `pipeline/svt_ci.py` | What every pipeline job runs on the GitLab runner (standard library only) |
| `build_stream_test_config.yml` (or `<theme>_test_config.yml`), `user_inputs.yml` | What is tested and the cluster values; each cluster gets a copy in the project. Every key: [TEST_CONFIG.md](TEST_CONFIG.md), [SETUP.md](SETUP.md); theme `catalog_build`: [CATALOG_BUILD.md](CATALOG_BUILD.md) |

Contents: [how it works](#how-it-works-and-where-each-secret-goes) · [what you need](#1-what-you-need) ·
[OpenBao](#2-openbao-the-domain-credentials) · [fill the configs](#3-fill-the-configs) ·
[create the project](#4-create-the-project) · [give the inputs](#5-give-the-inputs) ·
[run it](#6-run-it) · [results](#7-results) ·
[**update an existing pipeline**](#update-an-existing-pipeline) · [when it fails](#when-it-fails)

## How it works, and where each secret goes

```text
 your machine --setup_svt_project.py (GitLab API token)--> GitLab project
                                                            .gitlab-ci*.yml, svt_ci.py,
                                                            CI/CD variables, clusters/<name>/svt/
 pipeline run (you, a schedule or the API)
   GitLab runner: svt_ci.py <job> --ssh (OIM password or key)--> OIM: ./setup_env.sh, ./run_validation.sh
        |  initialization job only: job token --> OpenBao --> the four credential secrets
        +--------------------------------- as JSON on stdin of the SSH session ------------------>
```

| Secret | Kept where | Used by | Notes |
|---|---|---|---|
| GitLab API token | Your shell (`GITLAB_TOKEN`) or a prompt; never in a file | `setup_svt_project.py` only | Not stored in the project. Create it with scope `api`, revoke it when done |
| OIM SSH password | `<CLUSTER>_SVT_TARGET_PASS`, a masked, **protected** CI/CD variable | The runner, to SSH to the OIM (`SSHPASS` environment variable, never an argument) | Protected: only given to pipelines on a protected branch (the default branch is). Or use the File variable `<CLUSTER>_SVT_SSH_KEY` |
| OIM host key | `<CLUSTER>_SVT_SSH_KNOWN_HOSTS`, a protected File variable | The runner, to check it is talking to the OIM | Required (see step 4) |
| **OpenBao token** | **Not stored anywhere** | The `initialization` job | GitLab gives the job a short-lived token; OpenBao exchanges it for a short-lived OpenBao token that lives in the job's memory. [OPENBAO.md](OPENBAO.md#4-how-the-pipeline-gets-access-no-token-is-stored) |
| Domain credentials (Pulp, S3, BMC, DB ...) | OpenBao | The `initialization` job reads them and pipes them over SSH to `./setup_env.sh --domain-creds-stdin` | Never written to disk, logged or passed as an argument |
| SMTP login | `SMTP_USER`, `SMTP_PASSWORD`, masked variables | The `summary` job | Only when the relay needs a login |

## 1. What you need

| Where | What |
|---|---|
| GitLab server | 15.7 or later (`id_tokens`); a user with an API token (scope `api`) that may create projects in the namespace |
| GitLab runner | Registered for the project (shell executor), with `python3`, `ssh` and `sshpass` (`dnf install -y python3 openssh-clients sshpass`); reaches every OIM on port 22 and OpenBao |
| Each OIM | RHEL with `git` and Python 3.12+; root SSH login (password or key) from the runner; reaches the Omnia repository; the Omnia branch it tests must contain `test/system_test` |
| OpenBao (optional) | The one of test/pipeline; holds the domain credentials. Without it the credential stores must already be on each OIM |
| Your machine (setup only) | `python3` with `requests`, `pyyaml`, `urllib3`, and this checkout (the script reads the theme and `user_inputs.yml` from it) |

## 2. OpenBao: the domain credentials

Once per OpenBao: JWT login for GitLab, a policy that reads the SVT's secret path, and the role
`gitlab-role` (the commands and the reasons are in
[OPENBAO.md section 4](OPENBAO.md#4-how-the-pipeline-gets-access-no-token-is-stored); an
OpenBao already set up for `test/pipeline` only needs its policy to cover your `secret_path`).
Then store one secret per credential domain: the field names and a `bao kv put` example are in
[OPENBAO.md section 2](OPENBAO.md#2-how-the-secrets-are-laid-out). Then set where OpenBao is, in the
`openbao` block of `test/system_test/user_inputs.yml` (`server_url`, `secret_path`,
`tls_skip_verify`); it becomes the pipeline's `BAO_*` variables.

The certificate is not checked by default, like `test/pipeline` (`curl -k`): give the optional
File variable `BAO_CACERT` (`--bao-cacert FILE`) to check it, or `BAO_TLS_SKIP_VERIFY=false` to
use the system CA store.

## 3. Fill the configs

1. **`pipeline/svt_pipeline_config.yml`**: the GitLab project, the cluster(s) (OIM IP, Omnia repo,
   branch, install path), email, timeouts. Every key, its default and the variable it becomes:
   [PIPELINE_CONFIG.md](PIPELINE_CONFIG.md).
2. **`user_inputs.yml`**: the cluster values and the `openbao` block ([SETUP.md](SETUP.md)).
3. **`<theme>_test_config.yml`** of every theme in `clusters.<name>.themes`:
   `build_stream_test_config.yml` (catalogs, the report, [TEST_CONFIG.md](TEST_CONFIG.md)) and
   `catalog_build_test_config.yml` ([CATALOG_BUILD.md](CATALOG_BUILD.md); its catalog list decides
   the pipeline jobs, so render the files after changing it). The cleanup (NFS shares included)
   and OpenBao are one block each in `user_inputs.yml`, shared by every theme.


## The pipeline of a cluster with several themes

`clusters.<name>.themes` is a comma separated list (`"catalog_build,cluster_lifecycle,build_stream"`). They run one
after another in **one pipeline**; a theme runs whether the one before passed or failed.
`preflight`, `initialization` and `summary` exist **once**; each theme is its own nested pipeline
that opens when you click it in the GitLab graph.

```
 .gitlab-ci.yml (root)          select_clusters ──▶ svt_<cluster>   (one resource group per OIM)
                                                         │
 cluster pipeline  ──────────────────────────────────────▼──────────────────────────────────────
   ┌───────────┐   ┌────────────────┐   ┌─────────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────┐
   │ preflight │──▶│ initialization │──▶│ ▶ build_stream  │──▶│ ▶ theme2    │──▶│ ▶ theme3    │──▶│ summary │
   └───────────┘   └────────────────┘   └─────────────────┘   └─────────────┘   └─────────────┘   └─────────┘
     once              once              theme 1 (expand)      theme 2 (expand)  theme 3 (expand)    once
   SSH, OpenBao,     cleanup, omnia.sh    skipped if the        run even if the   run even if the    always runs;
   Omnia checkout    install, Omnia env,  initialization        themes before     themes before      red if anything
                     credentials, ready   failed                passed OR failed  passed OR failed   failed

 expand "build_stream"                              expand "theme2", "theme3" ...
   prepare_build_stream ─▶ build_deploy ─▶            the stages of that theme ─▶ theme_result
   cadence ─▶ automatic_cleanup ─▶ theme_result
```

- **preflight** (once): SSH to the OIM, OpenBao reachable, the Omnia checkout on the OIM, the
  `svt/` inputs copied.
- **initialization** (once): the complete start of the OIM, with the first theme: `--configure`,
  the clean reinstall (`--install --yes --force`: the shared `cleanup` block of `user_inputs.yml`,
  NFS shares included, then `omnia.sh -s` and the Omnia environment), the credentials from the
  one OpenBao block, the PowerScale CSI files and the readiness checks. `svt.clean_reinstall:
  "false"` skips the cleanup.
- **theme ▶** (one per theme, in list order): there is no setup job. The theme starts directly with
  its first stage (`prepare_build_stream`, `catalog_01` ...), then the others, then `theme_result`
  (the theme's SVT summary and verdict, kept on the OIM). The first theme uses the run the
  initialization started. A theme after the first one starts its own run inside its first stage
  job (`--configure`, `--install --yes`: no cleanup, the installation and the credential stores
  are kept). A retry of that job continues the same run.
- **build_stream is the last theme and starts from scratch.** `--update` refuses it anywhere
  else. Its nested pipeline begins with the job `clean_install` (once more the shared cleanup,
  `omnia.sh -s`, the credentials, the CSI files and the readiness checks, in one job), then
  `prepare_build_stream`, `build_deploy`, `cadence`, `automatic_cleanup` and `theme_result`. The
  other themes share the one `initialization`; any of them can run alone. With `build_stream`
  alone there is no `initialization`, `clean_install` does the work.
- **One cleanup for every theme.** It is the block at the bottom of `user_inputs.yml`; a
  `<theme>_test_config.yml` with its own `cleanup:` block fails the `preflight` job before
  anything is cleaned.
- **A failed theme does not stop the next one.** If `initialization` fails, no theme runs and only
  the summary runs.
- **summary** (once): reads every theme's result, builds **one report**,
  `svt_report/svt_report.html` (a single file: an overview that explains the run, then one page per
  theme with the theme's own SVT report; Previous / Next buttons, tabs, arrow keys, light and
  dark) and sends **one email** with that file attached. The pipeline is red when any theme failed.
- **The GitLab graph:** GitLab draws the downstream pipelines of a pipeline in one column to the
  right of its last stage, newest first, whatever the order of the trigger jobs. That is why the
  themes appear after `summary`. Each theme pipeline is therefore named
  `SVT <cluster>, theme <n> of <m>: <theme>`, and the report lists them in run order.
- A run can use fewer themes: set `<CLUSTER>_SVT_THEMES` (a subset of the rendered list, in the
  rendered order) in GitLab or in Run pipeline. A new theme or a new order needs `--update`.

## 4. Create the project

```bash
cd test/system_test/pipeline
./setup_svt_project.py --render            # look at the generated .gitlab-ci.yml, the cluster files and the theme files
export GITLAB_TOKEN='<your-gitlab-token>' # or type it at the prompt
./setup_svt_project.py --create --gitlab-url https://<gitlab-host> --scan-host-keys
./setup_svt_project.py --validate --gitlab-url https://<gitlab-host>   # GitLab CI lint
```

Add `--no-verify-ssl` for a GitLab with a self-signed certificate. `--create` asks for each
cluster's OIM SSH password (or reads `<CLUSTER>_SVT_TARGET_PASS` from the environment; press
Enter to skip a cluster) and stores it as a masked, protected variable. It commits:

| In the project | Content |
|---|---|
| `.gitlab-ci.yml` | One trigger job per cluster (`svt_<cluster>`), each holding the resource group `svt-<cluster>` |
| `.gitlab-ci-svt-cluster-<cluster>.yml` | The cluster pipeline: preflight, initialization, one trigger per theme, summary |
| `.gitlab-ci-svt-<theme>.yml` | The jobs of one theme (nested pipeline): its stages, then theme_result |
| `svt_ci.py`, `svt_report_page.py`, `svt_pipeline_config.yml` | The runner helper and the report page builder; a reference copy of your config |
| `clusters/<cluster>/svt/secret.yaml`, `values.yaml` | PowerScale CSI; `--create` adds them copied from the product's reference examples, you edit them (never replaced by `--update-inputs`). Copied next to `user_inputs.yml` on the OIM at every checkout; the initialization job then runs `./setup_env.sh --stage-files`, which moves them to the paths of `omnia_config.yml` (default: the orchestrator's project input folder) only when `enable_powerscale_csi` is true, and then both must exist (see SETUP.md, PowerScale CSI) |
| `clusters/<cluster>/svt/user_inputs.yml` | The cluster values (from `test/system_test`; edit them in GitLab). Other files with the same syntax can sit beside it; the CI/CD variable `<CLUSTER>_SVT_USER_INPUTS` (`svt.user_inputs` in the config) names the one the cluster's pipeline uses, default `user_inputs.yml` |
| `clusters/<cluster>/svt/<theme>_test_config.yml` | The theme settings of that cluster (catalogs, cleanup flags ...) |

It also sets the CI/CD variables (see [PIPELINE_CONFIG.md](PIPELINE_CONFIG.md#the-variables-the-script-creates))
and raises the project CI timeout to the longest job.

**OIM host key (required).** The jobs refuse to connect to an OIM whose host key they cannot
check, because an unchecked key lets someone in the middle read the OIM password and the
credentials the initialization job pipes over SSH. `--scan-host-keys` runs `ssh-keyscan` from your
machine for every cluster's `target.ip` and stores the result as the File variable
`<CLUSTER>_SVT_SSH_KNOWN_HOSTS`; it prints the fingerprint, so compare it with the OIM's
(`ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub`), because the scan trusts whatever answers at
that moment. Or add that variable by hand with the line `ssh-keyscan -t ed25519 <OIM>` prints. Only
if you accept the risk, set `clusters.<name>.target.ssh_skip_host_key: "true"` (the jobs warn).

Variables to add in GitLab (Settings > CI/CD > Variables) when needed:

| Variable | Type | When |
|---|---|---|
| `BAO_CACERT` | File | Optional: verify the OpenBao certificate with this CA (`--bao-cacert` sets it) |
| `<CLUSTER>_SVT_SSH_KEY` | File | An SSH key instead of the password |
| `SMTP_USER`, `SMTP_PASSWORD` | Variable, masked | The SMTP server needs a login |

## 5. Give the inputs

Edit, in the GitLab project (Repository > Files, or a clone of it):

- `clusters/<cluster>/svt/user_inputs.yml`: the cluster values (OIM identity, networks, PXE
  mapping, BuildStream and GitLab hosts ...), the same file as `test/system_test/user_inputs.yml`;
- `clusters/<cluster>/svt/<theme>_test_config.yml`: catalogs, cleanup flags.

The preflight job copies both into the OIM's `test/system_test/` before every run; configure then
writes them into the Omnia inputs. A commit does not start the pipeline. The files hold cluster
values (IPs, names) but never credentials.

## 6. Run it

CI/CD > Pipelines > **Run pipeline** (branch `main`). Variables for this run only:

| Variable | Example | Effect |
|---|---|---|
| `SVT_CLUSTERS` | `cluster1,cluster3` | Only these clusters, comma separated (default: every enabled cluster of the config) |
| `CLUSTER1_SVT_THEMES` | `build_stream` | Run only these themes on cluster1 (a subset of `clusters.cluster1.themes`, in its order; default: the project variable, set from the config) |
| `CLUSTER1_SVT_SKIP_STAGES` | `cadence,automatic_cleanup` | Leave theme stages out on cluster1 |
| `CLUSTER1_SVT_CLEAN_REINSTALL` | `false` | No cleanup, install only what changed |
| `CLUSTER1_SVT_OMNIA_BRANCH` | `my-fix` | Test another branch |

Also: CI/CD > Schedules (nightly; give each schedule its own `SVT_CLUSTERS`), or the API
(`POST /projects/:id/pipeline` with `variables`).

**Several clusters:** every selected cluster is its own child pipeline, so they start together
and run in parallel, each on its own OIM (one pipeline at a time per OIM: a second one for the same
cluster waits in its resource group). The first job, `select_clusters`, prints the clusters and
their themes, and **fails at once** when `SVT_CLUSTERS` names a cluster that is not in the config
(a typo) or selects none, so nothing half-starts. `enabled: false` in a cluster block keeps it out
of the default selection. **The runner must have `concurrent` at least the number of clusters**
(`/etc/gitlab-runner/config.toml`): a stage job holds a runner slot while it streams the OIM's log,
so with `concurrent = 1` the clusters run one after the other.

**Jobs of each cluster (child pipeline `svt_<cluster>`):**

1. `preflight`: SSH to the OIM, `git` and `python3` there, OpenBao reachable; then the Omnia
   checkout, a check that it has the SVT scripts, and the cluster's `svt/` inputs.
2. `initialization`: `./setup_env.sh --configure`, then `--install --yes --force` (cleanup first,
   including telemetry, discovery and the NFS shares), both detached on the OIM; then the credentials read
   from OpenBao go to `--domain-creds-stdin`; then `--stage-files` (the PowerScale CSI files, only when enabled); then `./run_validation.sh svt_<theme>
   initialization`.
3. The theme stages (build_stream: `prepare_build_stream`, `build_deploy`, `cadence`,
   `automatic_cleanup`): `./run_validation.sh svt_<theme> <stage>`. `prepare_build_stream` is a
   hard stage: when it fails, the stages after it do not run. `build_deploy`, `cadence` and
   `automatic_cleanup` are soft stages (`soft_stages` of the theme, `allow_failure: true` in the
   generated job): when one fails, the next one still runs. catalog_build: one job per catalog
   (`catalog_01` ...), resolved from `catalog_build_test_config.yml` when the files are rendered,
   all soft with `continue_on_failure: true`; the initialization job fails right after configure
   when the plan on the OIM differs from these jobs
   ([PIPELINE_CONFIG.md](PIPELINE_CONFIG.md#theme-catalog_build-one-job-per-catalog)).
4. `summary`: always, last. `./run_validation.sh svt_<theme> summary`, the report collected, the
   email sent, then it **fails when any job or stage failed**.

- **Long stages:** they run detached on the OIM (`setsid`; log, pid and rc under
  `test/system_test/reports/ci/<pipeline id>/`); the job streams the log, so a dropped SSH
  connection does not stop a stage. A timed-out or cancelled job stops its stage on the OIM.
- **Multi-cluster:** the clusters run at the same time, each on its own OIM; a second pipeline for
  the same OIM waits for the first (resource group). Each cluster's summary sends its own email.

## 7. Results

| Where | What |
|---|---|
| `summary` job > artifacts `svt_report/` | The SVT report (`.html`, `.json`), `logs/` (complete output of every step), `junit/` |
| Pipeline > Tests tab | Every SVT test (from `junit/`) |
| Email | Subject with the status and the failed stage(s). A coloured status banner, then a table with the run, OIM, theme, **repository, branch and commit as links** (the branch and the commit open the page of the tested code on GitHub or GitLab), and the pipeline link; the failed job(s) as links to their GitLab page, each with the error its job recorded (for example the checkout error), the failed SVT steps with their error line and the jobs that did not run; buttons to open the pipeline, browse the report and download the artifacts; the job table and the SVT sections. A plain-text version is included for clients that do not show HTML. When the pipeline failed before any SVT step ran, the mail says so: there is no run, no commit, no SVT sections table, no report button and no attachment. Otherwise the SVT HTML report is attached (gzip above 5 MB) |
| The OIM | `test/system_test/reports/<run_id>/` as for a run by hand |

**Retry and the summary:** GitLab does not run a job again that already ran, so after you retry
a failed stage the old `summary` (and its email) would stay failed. The last job to end after the
summary ran therefore asks GitLab to run `summary` again (it does nothing while another job of the
pipeline is unfinished, and never before the summary ran). It uses the job token; if this GitLab
refuses it (the log says `the summary job could not be started again (HTTP ...)`), give a project
access token with the `api` scope as the masked, protected CI/CD variable `SVT_API_TOKEN`, or
retry `summary` by hand once the stages have ended.

**When a stage fails:** if it is a hard stage (`preflight`, `initialization`,
`prepare_build_stream`) the pipeline stops at it (the later stages do not run); if it is a soft
stage (`build_deploy`, `cadence`, `automatic_cleanup`) the next stages still run. In both cases the
`summary` job runs and **fails**. Its log ends with a block that names the failed stage(s), the failed
SVT steps with the first line of their error, and the stages that did not run; the email carries
the same, so you know which stage to Retry. A **Retry** of the failed job continues the same run
(`--retry`), resumes the stage at the test that failed (the tests that passed are not run again;
the track file is `<run folder>/track/<stage>.json` on the OIM) and its new attempt replaces the
failed one in the report; then run the `summary` job
again (see [RUNNER.md](RUNNER.md)).

## Update an existing pipeline

Once the project exists, you do not create it again: change the local files, then run
`--update`. The project holds copies of the pipeline files, so **a pull of new SVT code does
not change the project until you run `--update`**.

```bash
cd test/system_test && git pull                        # new SVT code, if any
cd pipeline
./setup_svt_project.py --render                        # optional: look at what will be committed
export GITLAB_TOKEN='<your-gitlab-token>'
./setup_svt_project.py --update --gitlab-url https://<gitlab-host>          # add --no-verify-ssl if needed
./setup_svt_project.py --validate --gitlab-url https://<gitlab-host>        # GitLab CI lint
```

`--update` **always**: commits `.gitlab-ci.yml`, `.gitlab-ci-svt-cluster-<cluster>.yml` (one per cluster), `.gitlab-ci-svt-<theme>.yml` (one per theme), `svt_ci.py` and the
reference `svt_pipeline_config.yml` to the project's branch; rewrites every CI/CD variable of the
config (it prints each as `created`/`updated` with its value, secrets are never printed); and
raises the project CI timeout to the longest job.

`--update` **adds** a cluster's input file that is missing from `clusters/<name>/svt/` (for example the
test config of a new theme) and **never**, unless you ask, changes one that exists, an OIM
password, a host key, `BAO_CACERT`, or a variable you added yourself.

| What changed | What to run |
|---|---|
| New SVT code (`svt_ci.py`, the stages, the CI template), or a value of `svt_pipeline_config.yml` (timeouts, email, a cluster's branch or path, `clean_reinstall`, `skip_stages`) | `--update` |
| Only a value that is a CI/CD variable: the **email** (`email` block: recipients, SMTP), `poll_seconds`, `log_limit_kb`, a cluster's `skip_stages`, `clean_reinstall`, branch, path or `checkout_mode`, `enabled` | `--set-variables` (rewrites the variables only, commits nothing). Or edit the variable in Settings > CI/CD > Variables for one change; the next `--update` or `--set-variables` writes the config's value again |
| A cluster's **themes** (`clusters.<name>.themes` in the cluster block) | The themes are the cluster's CI/CD variable `<PREFIX>_SVT_THEMES` (for example `CLUSTER1_SVT_THEMES`): set a subset of the rendered list (in the rendered order) in Settings > CI/CD > Variables or in Run pipeline for one run; no `--update` is needed. A new theme or a new order needs `--update` (run `--set-variables` to make the CI/CD variable match the config). The themes are not an SVT input (`user_inputs.yml` is for the cluster's values) and not in the `svt` block. `--update` commits the cluster pipeline file and the child pipeline file of every theme and adds each cluster's missing `<theme>_test_config.yml` (an existing file is never replaced). A running pipeline keeps its themes; the first job of a new one fails on a theme that is not known |
| OpenBao's address, path or TLS (`openbao` block of `user_inputs.yml`) | `--update` (it becomes `BAO_SERVER_URL`, `BAO_DATA_PATH`, `BAO_TLS_SKIP_VERIFY`) |
| The JWT role (`openbao.auth_role`) | `--update` |
| A cluster's inputs (`user_inputs.yml`, `<theme>_test_config.yml`) | Edit them in the GitLab project (they are used at the next run). To replace them with your local files: `--update --update-inputs` (**replaces the inputs of every cluster**, discarding edits made in GitLab) |
| A new cluster | Add its block, then `--create --gitlab-url ...` on the existing project: it fills the project, adds the missing `clusters/<name>/svt/` inputs only, and asks the passwords (Enter keeps a cluster's as it is). Add `--scan-host-keys` for the new OIM |
| An OIM password changed | `--update --set-password` (asks every cluster, or reads `<CLUSTER>_SVT_TARGET_PASS`) |
| An OIM was reinstalled (new host key) | `--update --scan-host-keys` |
| A new OpenBao CA certificate | `--update --bao-cacert ca.pem` |
| A project created by an older version | `--update --scan-host-keys` (the host key variable is now required), then check the CI/CD variables against [PIPELINE_CONFIG.md](PIPELINE_CONFIG.md) |

- **Pipelines already running** keep the files of the commit they started from; start a new
  pipeline to use the update.
- **Check the result:** Settings > CI/CD > Variables shows the variable names (values of masked
  ones are hidden); Repository > Files shows the committed files; `--validate` lints the CI files.
- **Undo:** the old files are in the project's Git history (restore a file from a previous
  commit); put the old value in the config and `--update` for a variable.
- **Keep your config in Git, not the passwords:** `svt_pipeline_config.yml` has no secrets, so
  you can commit your copy; the OIM passwords and tokens are only in your environment and in
  GitLab variables.

## Clean or delete the project

`pipeline/cleanup_svt_project.py` resets the GitLab side (details and troubleshooting in
[pipeline/README.md](../pipeline/README.md)):

```bash
cd test/system_test/pipeline
./cleanup_svt_project.py --status      --gitlab-url https://<gitlab-host>   # what the project holds
./cleanup_svt_project.py --clean       --gitlab-url https://<gitlab-host>   # every pipeline, log and artifact
./cleanup_svt_project.py --delete      --gitlab-url https://<gitlab-host>   # the whole project
./cleanup_svt_project.py --verify-gone --gitlab-url https://<gitlab-host>   # exit 0 when it is gone
```

`--clean` keeps the project, its files and variables; `--delete` removes everything (create it
again with `setup_svt_project.py --create`). Both ask you to type the project path (`--yes` skips
it, `--dry-run` only lists) and verify the result. The OIM is cleaned there, with
`./setup_env.sh --cleanup`.

## When it fails

| Symptom | Check |
|---|---|
| `SVT_SSH_KNOWN_HOSTS ... is required` | `./setup_svt_project.py --update --scan-host-keys`, or add the File variable; `ssh_skip_host_key: "true"` accepts the risk |
| `the checkout has no usable SVT` | The branch has no `test/system_test/setup_env.sh` (with `--configure` and `--domain-creds-stdin`) and `run_validation.sh`: use a branch that has the system test |
| `Job's log exceeded limit of 4194304 bytes` | The job printed more than the runner keeps. The pipeline already hides base64 lines, cuts long lines and stops at `svt.log_limit_kb`; lower it, or raise `output_limit` (KB) in the runner's `config.toml` and restart it. The full logs are on the OIM under `reports/ci/<pipeline id>/` |
| `the summary email was NOT sent` | `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USER`/`SMTP_PASSWORD`; the report is still in the job artifacts. `email.required: "true"` makes it fail the job |
| `preflight`: SSH failed | `<CLUSTER>_SVT_TARGET_IP`, password/key, port 22 from the runner, `sshpass` on the runner |
| A protected variable is empty in the job | The pipeline ran on a branch that is not protected: run it on `main` (Settings > Repository > Protected branches) |
| `OpenBao: could not read ...` with a certificate error | `BAO_TLS_SKIP_VERIFY=false` verifies with the system CA store; give `BAO_CACERT` for a private CA, or leave both unset (not verified, with one warning) |
| `OpenBao: could not read the credentials` | `BAO_SERVER_URL`, `BAO_AUTH_ROLE`, the role's `bound_audiences` (= the OpenBao URL) and `bound_claims` (does it allow this project?), the policy's path = `secret_path`, GitLab 15.7+. [OPENBAO.md section 4](OPENBAO.md#4-how-the-pipeline-gets-access-no-token-is-stored) |
| `Unsupported fields` in initialization | A key in the OpenBao secret that the store does not have |
| `another SVT step is running on this OIM` | A run by hand or an old pipeline holds `reports/svt.lock`; wait, or stop it |
| A stage failed | Its job log; the report in `svt_report/`; the stage log in `svt_report/logs/`. Fix the cause, then **Retry** that job in GitLab: it runs `--retry`, so the same run continues |
| Start over completely | **Run pipeline** again: a new pipeline is a new run (initialization does a clean reinstall unless `SVT_CLEAN_REINSTALL=false`) |
| Retried the `initialization` job | It starts a new run (configure) and reinstalls; the later jobs follow that run |
| Job killed at the time limit | Raise `svt.timeouts_hours.<stage>`, `--update`; check the runner's maximum timeout |
