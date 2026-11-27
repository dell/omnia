# Developing the Pipeline

How the pipeline sources fit together, how to change them and how they are tested.

---

## Layout

| File | Role | Runs on |
|---|---|---|
| `pipeline_render.py` | Tables of stages, order, rules; writes the parent, cluster, build stream and utils pipelines | your machine |
| `.gitlab-ci*.yml` | The generated pipelines (committed) | GitLab |
| `pipeline_ci.py` | The command of every cluster job | the GitLab runner, taken from the Omnia clone |
| `library/functions/email_func.py`, `library/vars/email_vars.py` | The summary email | the GitLab runner, taken from the clone |
| `setup_gitlab_project.py` | Creates the project, uploads files, sets variables, `--scan-host-keys` | your machine |
| `pipeline_triggers.py` | Reads `pipeline_config.yml`, writes the trigger jobs of the parent pipeline | the GitLab runner, uploaded to the project |
| `ut/` | Unit tests of the helpers | your machine |

Only the YAML files, `pipeline_triggers.py` and `pipeline_config.yml` are uploaded to the GitLab project
(`collect_pipeline_files()` in `setup_gitlab_project.py`). The helpers are not: the `initialization`
job clones Omnia on the OIM and copies `pipeline_ci.py` and `library/` out of the clone into
`ci_tools/` (the `BOOTSTRAP` script in `pipeline_render.py`), so a change to them only needs a push
to the Omnia branch the cluster clones. The bootstrap is the one piece that must stay inline.

`library/` follows the other test libraries: constants in `vars/`, text in `messages/`, logic in
`functions/`.

---

## Changing the stages

Everything about the shape of the cluster pipeline is in `pipeline_render.py`:

| Table | Meaning |
|---|---|
| `CLEANUP_ORDER` | The order of the cleanup stages |
| `DEPLOY_ORDER` | The domains with a deploy and a test stage, in order |
| `VARIABLES`, `RETRY_WHEN`, rule strings | Defaults, retry policy, `PIPELINE_MODE` and `DOMAINS` conditions |

After a change:

```bash
python3 pipeline_render.py --write
```

`pipeline_render.py --check` fails when the committed file is not the rendering, so the YAML is
never edited by hand.

**Add a domain.**
1. Add it to `DOMAINS` in `pipeline_ci.py`; for a deploy stage add its tags to `DOMAIN_STEPS`
   and, if it has credentials, to `CREDENTIAL_FILES`.
2. Add it to `CLEANUP_ORDER` and `DEPLOY_ORDER` in `pipeline_render.py`.
3. Add its `<DOMAIN>_TAGS` and `TEST_<DOMAIN>_CMD` variables to the trigger job generator in
   `setup_gitlab_project.py` and to the loader maps, then update the docs.

**Change a job.** Change the function in `pipeline_ci.py`; a job is only
`python3 pipeline_ci.py <command> [domain]`. Remote scripts are plain bash sent on stdin of
`bash -s`; quote every value with `shlex.quote` and validate names with the `SAFE_*` patterns.

---

## Checks

```bash
cd test/pipeline
python3 pipeline_render.py --check     # the committed YAML is the rendering
DRY_RUN=true ...                       # a pipeline run that prints what it would do on the OIM
```

`pipeline_render.py --check` fails when `.gitlab-ci-cluster.yml` was edited by hand or a table in
`pipeline_render.py` changed without `--write`. Try a change on a pipeline with
`DRY_RUN=true` (every job prints what it would run on the OIM and changes nothing) before a real
run, and check the YAML with the CI lint of your GitLab (`POST /projects/:id/ci/lint`). Do not run
the cleanup, the install or the NFS clearing against a live OIM to "test" them.

### Lint

CI runs pylint on every changed Python file and each file must score at least 8. Run it with the
repository settings:

```bash
PYTHONPATH=.:./src/build_stream pylint test/pipeline/pipeline_ci.py
```

---

## Running a helper command by hand

With a scratch folder, the cluster variables and a fake or real `sshpass`:

```bash
export CLUSTER=lab LAB_TARGET_IP=10.0.0.1 LAB_TARGET_USER=root LAB_TARGET_PASS=...
export PIPELINE_SSH_KNOWN_HOSTS=/path/to/known_hosts OMNIA_INSTALL_PATH=/root/omnia
DRY_RUN=true python3 pipeline_ci.py install
python3 pipeline_ci.py --help
```
