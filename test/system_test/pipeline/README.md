# Run the SVT from GitLab

The pipeline runs the same `./setup_env.sh` and `./run_validation.sh` of the SVT
(`test/system_test`, see its README) on the OIM over SSH; without the pipeline
the SVT runs unchanged on the OIM. One GitLab project can test one or many
clusters (one OIM each).

| File | Role |
|---|---|
| `pipeline/svt_pipeline_config.yml` | Your settings: GitLab project, theme, job timeouts, OpenBao, email, the clusters |
| `pipeline/setup_svt_project.py` | Creates or updates the project (GitLab client of `test/pipeline/setup_gitlab_project.py`) |
| `pipeline/svt_ci.py` | What every pipeline job runs on the GitLab runner (standard library only) |

## 1. What you need

| Where | What |
|---|---|
| GitLab server | 15.7 or later (`id_tokens`); a user with an API token (scope `api`) that may create projects in the namespace |
| GitLab runner | Registered for the project (shell executor), with `python3`, `ssh` and `sshpass` (`dnf install -y python3 openssh-clients sshpass`); reaches every OIM on port 22 and OpenBao |
| Each OIM | RHEL with `git` and Python 3.12+; root SSH login (password or key) from the runner; reaches the Omnia repository |
| OpenBao (optional) | The one of test/pipeline; holds the domain credentials. Without it the credential stores must already be on each OIM |
| Your machine (setup only) | `python3` with `requests`, `pyyaml`, `urllib3`, and this checkout (the script reads the theme from it) |

## 2. OpenBao: credentials for the domain stores

Follow `test/pipeline/docs/OPENBAO_SETUP.md` phases 1 to 3 (install, KV v2 at
`secret/`, JWT auth for GitLab, policy, role `gitlab-role` with
`bound_audiences` = the OpenBao URL). An OpenBao already set up for
test/pipeline is used as it is.

Store one secret per credential domain of the theme (build_stream:
`repo_manager`, `image_build_manager`, `orchestrator`, `build_stream`). The
keys are the fields of the stores, as `./setup_env.sh --set-domain-creds`
asks them; an unknown key is refused:

```bash
bao kv put secret/omnia/repo_manager pulp_username=admin pulp_password='...' \
    docker_username='' docker_password=''
bao kv put secret/omnia/image_build_manager s3_access_id='' s3_secret_key='...' \
    aarch64_ssh_password=''
bao kv put secret/omnia/orchestrator provision_password='...' bmc_username=root \
    bmc_password='...' slurm_db_password='...' openldap_db_username=admin \
    openldap_db_password='...' csi_username='' csi_password=''
bao kv put secret/omnia/build_stream gitlab_root_password='...' \
    gitlab_ssh_password='...' build_stream_auth_username=admin \
    build_stream_auth_password='...' postgres_user=postgres postgres_password='...'
bao kv get secret/omnia/build_stream          # check
```

- **Different credentials per cluster:** store them at another path, e.g.
  `secret/omnia/cluster2/<domain>`, and set `clusters.cluster2.secret_path:
  "secret/data/omnia/cluster2"`.
- **CA certificate (required):** after the project exists, add the CI/CD
  variable `BAO_CACERT`, type **File**, with the OpenBao CA certificate
  (e.g. `/opt/openbao/tls/tls.crt` of a self-signed OpenBao).
  `openbao.tls_skip_verify: "true"` skips the check instead (not
  recommended).
- The pipeline reads the four secrets in the initialization job and pipes
  them as one JSON object to `./setup_env.sh --domain-creds-stdin` on the OIM.
  They are never written to disk, logged or passed as an argument.

## 3. Fill `pipeline/svt_pipeline_config.yml`

```yaml
gitlab: {project_name: "omnia-svt", namespace: "root", branch: "main"}
svt:
  theme: "build_stream"
  timeouts_hours: {default_hours: 6, initialization: 4, build_deploy: 8, cadence: 8}
openbao: {server_url: "https://10.0.0.50:8200", auth_role: "gitlab-role",
          secret_path: "secret/data/omnia", tls_skip_verify: "false"}
email: {recipients: "you@example.com", sender: "svt@example.com",
        smtp_server: "smtp.example.com", smtp_port: "25"}
clusters:
  cluster1:
    target: {ip: "10.0.0.11", user: "root"}
    omnia: {repo: "https://github.com/dell/omnia.git", branch: "staging",
            install_path: "/root/omnia", checkout_mode: "update"}
    svt: {clean_reinstall: "true", skip_stages: ""}
```

- **timeouts_hours:** hours each job may run; rendered into the pipeline
  file (GitLab does not expand variables in `timeout:`). Change them, then
  `--update`. A runner's own maximum timeout still applies.
- **checkout_mode:** `update` (clone when missing, else fetch the branch and
  reset to it; dedicate `install_path` to the pipeline), `clone` (remove and
  clone again), `keep` (use the checkout as it is).
- **clean_reinstall:** `true` = the initialization stage removes the previous
  installation and installs everything again (`--install --force`).
- **skip_stages:** theme stages left out, e.g. `"cadence,automatic_cleanup"`.

## 4. Create the project

```bash
cd test/system_test/pipeline
./setup_svt_project.py --render            # check the generated .gitlab-ci.yml and .gitlab-ci-svt.yml
export GITLAB_TOKEN='<your-gitlab-token>' # or type it at the prompt
./setup_svt_project.py --create --gitlab-url https://<gitlab-host>
./setup_svt_project.py --validate --gitlab-url https://<gitlab-host>   # GitLab CI lint
```

`--create` asks for each cluster's OIM SSH password (or reads
`CLUSTER1_SVT_TARGET_PASS` from the environment) and stores it as a masked,
protected CI/CD variable. Add `--no-verify-ssl` for a GitLab with a
self-signed certificate. It commits:

| In the project | Content |
|---|---|
| `.gitlab-ci.yml` | One trigger job per cluster (`svt_<cluster>`), each holding the resource group `svt-<cluster>` |
| `.gitlab-ci-svt.yml` | The jobs of one cluster (child pipeline) |
| `svt_ci.py`, `svt_pipeline_config.yml` | The runner helper; a reference copy of your config |
| `clusters/<cluster>/svt/user_inputs.yml` | The cluster values (from test/system_test; edit them in GitLab) |
| `clusters/<cluster>/svt/<theme>_test_config.yml` | The theme settings of that cluster (catalog, cleanup flags ...) |

It also sets the CI/CD variables (cluster ones prefixed `CLUSTER1_...`, e.g.
`CLUSTER1_SVT_TARGET_IP`) and raises the project CI timeout to the longest
job.

Then, in GitLab (Settings > CI/CD > Variables), when needed:

| Variable | Type | When |
|---|---|---|
| `BAO_CACERT` | File | With OpenBao (required) |
| `<CLUSTER>_SVT_SSH_KEY` | File | SSH key instead of the password |
| `<CLUSTER>_SVT_SSH_KNOWN_HOSTS` | File | Check the OIM host key (its `known_hosts` line) |
| `SMTP_USER`, `SMTP_PASSWORD` | Variable, masked | SMTP server needs a login |

## 5. Give the inputs

Edit, in the GitLab project (Repository > Files, or a clone of it):

- `clusters/<cluster>/svt/user_inputs.yml`: the cluster values (OIM identity,
  networks, PXE mapping, BuildStream and GitLab hosts ...), the same file as
  `test/system_test/user_inputs.yml` (see below for its rules);
- `clusters/<cluster>/svt/<theme>_test_config.yml`: catalog, cadence catalog,
  pipeline cancel, cleanup flags.

The checkout job copies both into the OIM's `test/system_test/` before every
run; configure then writes them into the Omnia inputs. A commit does not
start the pipeline.

## 6. Run it

CI/CD > Pipelines > **Run pipeline** (branch `main`). Variables for this run
only:

| Variable | Example | Effect |
|---|---|---|
| `SVT_CLUSTERS` | `cluster1` | Only these clusters (default: all of the config) |
| `CLUSTER1_SVT_SKIP_STAGES` | `cadence,automatic_cleanup` | Leave theme stages out on cluster1 |
| `CLUSTER1_SVT_CLEAN_REINSTALL` | `false` | No cleanup, install only what changed |
| `CLUSTER1_SVT_OMNIA_BRANCH` | `my-fix` | Test another branch |

Also: CI/CD > Schedules (nightly), or the API
(`POST /projects/:id/pipeline` with `variables`).

**Jobs of each cluster (child pipeline `svt_<cluster>`):**

1. `preflight`: SSH to the OIM, `git` and `python3` there, OpenBao reachable.
2. `checkout`: the Omnia checkout, then the cluster's `svt/` inputs.
3. `initialization`: `./setup_env.sh --configure`, then `--install --yes
   --force` (cleanup first), both detached on the OIM; then
   `--domain-creds-stdin` (OpenBao); then `./run_validation.sh svt_<theme>
   initialization`.
4. The theme stages (build_stream: `prepare_build_stream`, `build_deploy`,
   `cadence`, `automatic_cleanup`): `./run_validation.sh svt_<theme>
   <stage>`. A failed stage skips the ones after it.
5. `summary`: always, last. `./run_validation.sh svt_<theme> summary`, the
   report collected, the email sent, then it **fails when any job or stage
   failed**.

- **Long stages:** they run detached on the OIM (`setsid`; log, pid and rc
  under `test/system_test/reports/ci/<pipeline id>/`); the job streams the
  log, so a dropped SSH connection does not stop a stage. A timed-out or
  cancelled job stops its stage on the OIM.
- **Multi-cluster:** the clusters run at the same time, each on its own OIM;
  a second pipeline for the same OIM waits for the first (resource group).
  Each cluster's summary sends its own email.

## 7. Results

| Where | What |
|---|---|
| `summary` job > artifacts `svt_report/` | The SVT report (`.html`, `.json`), `logs/` (complete output of every step), `junit/` |
| Pipeline > Tests tab | Every SVT test (from `junit/`) |
| Email | Status, OIM, branch, commit, the job table, the SVT sections; the HTML report attached (gzip above 5 MB) |
| The OIM | `test/system_test/reports/<run_id>/` as for a run by hand |

## 8. Add a cluster or change the config

1. Add a block under `clusters:` (or change a value).
2. `./setup_svt_project.py --update --gitlab-url ...` (pipeline files and
   variables). New clusters get their `clusters/<name>/svt/` inputs with
   `--update-inputs` (it also replaces existing ones with the files of
   test/system_test); `--set-password` asks the passwords again.

## 9. When it fails

| Symptom | Check |
|---|---|
| `preflight`: SSH failed | `<CLUSTER>_SVT_TARGET_IP`, password/key, port 22 from the runner, `sshpass` on the runner |
| `BAO_CACERT ... is required` | Add the File variable `BAO_CACERT`, or `BAO_TLS_SKIP_VERIFY=true` |
| `OpenBao: could not read the credentials` | `BAO_SERVER_URL`, `BAO_AUTH_ROLE`, the role's `bound_audiences` (= the OpenBao URL), the secret path |
| `Unsupported fields` in initialization | A key in the OpenBao secret that the store does not have |
| `another SVT step is running on this OIM` | A run by hand or an old pipeline holds `reports/svt.lock`; wait, or stop it |
| A stage failed | Its job log; the report in `svt_report/`; the stage log in `svt_report/logs/`. Fix the cause, then **Retry** that job in GitLab: it runs `--retry`, so the same run continues and its new attempt replaces the failed one in the report |
| Start over completely | **Run pipeline** again: a new pipeline is a new run (initialization does a clean reinstall unless `SVT_CLEAN_REINSTALL=false`) |
| Retried the `initialization` job | It starts a new run (configure) and reinstalls; the later jobs follow that run |
| Job killed at the time limit | Raise `svt.timeouts_hours.<stage>`, `--update`; check the runner's maximum timeout |
