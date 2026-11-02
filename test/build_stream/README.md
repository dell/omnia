# Build Stream test automation

Functional (FVT) and non-functional (NFT) automation for the Omnia
`build_stream` domain.
It uses the shared `omnia_auto` package for runner dispatch, target access,
synchronization, logging, and HTML/JSON reporting.

The Omnia setup (`./omnia.sh --setup-venv`, `--cleanup`) is tested in
`test/main`, and each base domain's cleanup in its own suite (`test/repo_manager`,
`test/image_build_manager`, `test/orchestrator`). The end-to-end system
verification (SVT) chains those suites with these FVT tags, and its
`./setup_env.sh` writes every domain credential store through this suite's
`setup_env.sh`; see [`../system_test/README.md`](../system_test/README.md).

## Purpose and safety model

Each FVT tag follows a `build_stream.yml` tag (or `./omnia.sh --prepare-base`) and
verifies what that step creates. The three actions:

- `exec` runs the playbook or command;
- `verify` only reads state;
- `test` runs `exec`, then `verify` only when `exec` succeeded.

| Tag | Effect | Selection |
|---|---|---|
| `prepare_base` | Runs `./omnia.sh --prepare-base` (repo_manager, image_build_manager, orchestrator) | Explicit only |
| `precheck` | Read-only `--tags precheck` | Default lifecycle |
| `prepare` | Deploys BuildStream, Postgres and playbook-watcher | Default lifecycle |
| `execute` | Deploys GitLab and runs real pipelines (detail below) | Default lifecycle |
| `cleanup` | **Destructive**: removes GitLab and BuildStream. Postgres data and credentials follow `cleanup.postgres_backup` / `cleanup.cleanup_credentials` | Explicit only |

`execute` runs real pipelines: it builds and deploys images, runs a cadence
cycle, an image cleanup pipeline and an automated cleanup pass. It changes live
state:

- it commits catalogs and PXE mapping changes to GitLab;
- it deploys images to nodes;
- it deletes one image group (`pipeline_cleanup`);
- it runs the automated cleanup (`auto_cleanup`), which marks the image the
  cadence test built FAILED in the database, then deletes every FAILED image
  group;
- with `pipeline.allow_pipeline_cancel: true` (default) it cancels running
  GitLab pipelines before each commit or trigger.

### Security model

- **No secret on a command line.** Tokens, client secrets and passwords are
  sent from the test process with in-memory HTTPS requests (`http_func.py`).
  They are never a command argument, in a process listing, logged, or included
  in a returned error.
- **TLS is always verified:**
  - the BuildStream API against `<OMNIA_DATA_PATH>/build_stream/ssl/bs_cert.pem`;
  - GitLab against the CA `hosted_gitlab` creates (`/root/gitlab-certs/ca.crt`
    on the GitLab host, read over SSH).
- **SSH to the GitLab host** uses the key and pinned host key that
  `build_stream.yml --tags execute` installs (`/root/.ssh/omnia_gitlab`,
  `gitlab_passwordless_ssh`). It uses BatchMode and strict host key checking;
  no password is involved.
- **Credentials** live only in the encrypted stores described below.

## Prerequisites

- **Development host:** Python 3.12, `bash`, and this repository.
- **Execution OIM:**
  - an Omnia checkout;
  - an Omnia setup (`/etc/omnia/omnia.env` and the Omnia venv; create it with
    `./omnia.sh --setup-venv` or `test/main`: `./run_validation.sh fvt_main setup test`);
  - for `execute`, PXE nodes listed in `input/orchestrator/pxe_mapping_file.csv`.
- **Product credentials** saved with `./setup_env.sh --set-domain-creds` on the
  execution OIM, so no playbook stops to prompt.

## Quick start

```bash
cd test/build_stream
./setup_env.sh --venv
source .venv/bin/activate
```

For password-based SSH to a remote execution OIM:

```bash
./setup_env.sh --set-creds
```

On the execution OIM, save the product credentials:

```bash
./setup_env.sh --set-domain-creds
```

Review the settings and the registered surface, check the prerequisites, then run:

```bash
${EDITOR:-vi} test_config.yml
${EDITOR:-vi} test_run_config.yml
./run_validation.sh --help
./run_validation.sh fvt_build_stream list
./run_validation.sh fvt_build_stream precheck verify
./run_validation.sh fvt_build_stream test        # precheck -> prepare -> execute
```

### First run on a bare OIM (no Omnia venv yet)

```bash
(cd ../main && ./setup_env.sh --venv && .venv/bin/python _run.py fvt_main setup test \
   && .venv/bin/python _run.py fvt_main init test)        # omnia.sh setup + domain init
source "$(sed -n 's/^OMNIA_VENV_PATH=//p' /etc/omnia/omnia.env)/bin/activate"
./setup_env.sh                                            # test deps in the Omnia venv
./setup_env.sh --set-domain-creds
./run_validation.sh fvt_build_stream prepare_base test
./run_validation.sh fvt_build_stream test
```

## Environment setup

`./setup_env.sh` installs `requirements.txt` (including the `omnia_auto` wheel).
It never runs a playbook or a test.

| Install mode | Selected by |
|---|---|
| `.venv/` | `--venv` (`--force` recreates it) |
| Active virtualenv | `VIRTUAL_ENV` is set, for example the Omnia venv |
| User site (`pip --user`) | Otherwise |

Test (transport) credentials and product (domain) credentials are separate:

| Option | Writes | Read by |
|---|---|---|
| `--set-creds`, `--update-creds`, `--creds-stdin` | `test_creds.yml` + `.test_creds.key` (0600, gitignored) | The test framework (OIM SSH password) |
| `--set-domain-creds [--domain X]`, `--update-domain-creds`, `--domain-creds-stdin [--domain X]` | The domain stores below | The product playbooks |

| Domain | Store under `<DOMAIN>_DATA_PATH/input/$OMNIA_PROJECT_NAME/` |
|---|---|
| `repo_manager` | `repo_manager_config_credentials.yml` |
| `image_build_manager` | `image_build_credentials.yml` |
| `orchestrator` | `orchestrator_credentials.yml` |
| `build_stream` | `build_stream_credentials.yml` |

- **Encryption:** each store is Ansible Vault encrypted (0600) with its own key
  file.
- **Updating:** press Enter to keep a stored value. Only the listed top-level
  fields change; other data, such as BuildStream `oauth_clients`, is kept.
- **BuildStream:** the helper also generates the Argon2 registrar hash required
  by `/api/v1/auth/register`. Run `./omnia.sh -r build_stream` after changing
  BuildStream credentials.
- **Automation:** `--domain-creds-stdin` reads one JSON object, as
  `test/system_test/setup_env.sh --yes` does when no terminal is attached.

Fields and the standard-input format: [`docs/test_creds.md`](docs/test_creds.md).

## Local and remote execution, input and output

Run on the execution OIM, or set `oim_server_ip` in `test_config.yml` to run
from a development host over SSH.

- **Input sync:**
  - with `dataset: ""` and `sync_build_stream_input: false`, the target input is
    untouched;
  - with input sync enabled, an empty dataset uses `src/build_stream/input/` and
    a named dataset uses `datasets/<dataset>/input/`.
- **Destinations** come from `OMNIA_DATA_PATH` and `OMNIA_PROJECT_NAME` on the
  execution OIM.
- **Never synchronized:** credential files, vault keys, backups and symlinks.
- **`verify`** never writes input.

```bash
cd datasets/generator
./generate_dataset.py create my_dataset --profile defaults
```

## Tags and suites

| Tag | Suites | Contract |
|---|---|---|
| `prepare_base` | `readiness` | Prerequisite domains ready for BuildStream |
| `precheck` | `environment`, `containers`, `credentials` | Environment, prerequisite containers and credential stores |
| `prepare` | `build_stream` | BuildStream service, API, database, venv, TLS, queue |
| `execute` | `gitlab_server`, `gitlab_runner`, `gitlab_project`, `build_automatic`, `build_manual`, `deploy_automatic`, `deploy_manual`, `cadence`, `pipeline_cleanup`, `auto_cleanup` | GitLab, then each pipeline as one test case per step |
| `cleanup` | `gitlab`, `build_stream` | Removed and intentionally preserved resources |

Every test case, with its order, ID, markers and check, is listed in
[`fvt/README.md`](fvt/README.md).

### State shared between suites

- **Build and deploy:** a deploy suite deploys the image the build suite created
  *in the same pytest process*. Run them together, for example with
  `--marker automatic_execution`.
- **Cadence and automatic cleanup:** the cadence test records the outcome of its
  own build (image group, job, success) in `reports/state/cadence_build.json`.
  `auto_cleanup` uses it even when it runs in a later process, as the SVT does:
  it deletes that image, or skips with "nothing to clean" when the cadence build
  failed.
- **Exec and verify:** `cleanup` hands its exec facts to
  the verify phase through the same `reports/state/` directory (0600, no
  secrets).

## Options and markers

| Option | Effect |
|---|---|
| `--suite <suite>` | Run one suite of the tag |
| `--marker <expr>` | Marker filter; `+` = AND, `,` = OR. Without it every collected test runs |

| Marker | Selects |
|---|---|
| `sanity` | Baseline positive checks that must pass on a healthy system; not on the manual pipeline suites |
| `deploy` | The `test_playbook.py` entry test of each tag (runs `build_stream.yml --tags <tag>` or `omnia.sh`) |
| `pipeline` | Every execute suite that triggers or verifies a real pipeline |
| `build_pipeline` | Build pipeline: `build_automatic`, `build_manual` |
| `deploy_pipeline` | Deploy pipeline: `deploy_automatic`, `deploy_manual` |
| `automatic_execution` | Commit-triggered build and deploy: `build_automatic`, `deploy_automatic` |
| `manual_execution` | API-triggered (`PIPELINE_TYPE=build` / `deploy`) build and deploy: `build_manual`, `deploy_manual` |
| `cadence` | Cadence pipeline and the cadence disable / re-enable tests |
| `cleanup_pipeline` | `PIPELINE_TYPE=cleanup` pipeline: `pipeline_cleanup` |
| `automatic_cleanup` | Automated cleanup pass on the cadence build image: `auto_cleanup` |
| `nft`, `resilience`, `security`, `disruptive` | NFT selection; `disruptive` also needs its `nft_allow_*` key |

Combine markers with `+` (AND) and `,` (OR), for example
`--marker build_pipeline,cadence` or `--marker deploy_pipeline+manual_execution`.

## Lifecycle examples

```bash
# Default lifecycle, every test
./run_validation.sh fvt_build_stream test
# Baseline checks only
./run_validation.sh fvt_build_stream test --marker sanity

# prepare_base (explicit; base domain credential stores must be saved)
./run_validation.sh fvt_build_stream prepare_base test

# One tag, read-only
./run_validation.sh fvt_build_stream prepare verify

# execute suites one at a time
./run_validation.sh fvt_build_stream execute verify --suite build_automatic
./run_validation.sh fvt_build_stream execute verify --suite build_manual
./run_validation.sh fvt_build_stream execute verify --suite deploy_automatic
./run_validation.sh fvt_build_stream execute verify --suite cadence
./run_validation.sh fvt_build_stream execute verify --suite auto_cleanup      # after cadence
./run_validation.sh fvt_build_stream execute verify --suite pipeline_cleanup

# execute suites by marker
./run_validation.sh fvt_build_stream execute verify --marker automatic_execution  # build + deploy (commit)
./run_validation.sh fvt_build_stream execute verify --marker manual_execution     # build + deploy (API)
./run_validation.sh fvt_build_stream execute verify --marker build_pipeline
./run_validation.sh fvt_build_stream execute verify --marker deploy_pipeline      # needs pipeline.deploy_image_group_id
./run_validation.sh fvt_build_stream execute verify --marker cadence
./run_validation.sh fvt_build_stream execute verify --marker cleanup_pipeline
./run_validation.sh fvt_build_stream execute verify --marker automatic_cleanup

# cleanup (destructive)
./run_validation.sh fvt_build_stream cleanup test
```

`test_config.yml` keys per tag (all keys: [`docs/test_config.md`](docs/test_config.md)):

| Tag | Keys |
|---|---|
| all | `oim_server_ip`, `oim_ssh_user`, `oim_ssh_port`, `clone_path`, `dataset`, `sync_build_stream_input`, `report_*`, `run_id` |
| `execute` (build) | `installation.catalog` (number from `./omnia.sh --list-catalogs` or full path), `pipeline.build_job_id` (verify-only mode) |
| `execute` (deploy) | `pipeline.deploy_image_group_id` (deploy-only runs), `pipeline.deploy_job_id` (verify-only mode) |
| `execute` (cadence) | `installation.cadence_catalog` (empty = `installation.catalog`), `pipeline.cadence_job_id` (verify-only mode) |
| `execute` (all pipelines) | `pipeline.allow_pipeline_cancel`, `pipeline.poll_interval`, `debug_mode` |
| `execute` (`pipeline_cleanup`) | `pipeline.cleanup_image_group_id`. Empty = the newest BUILT/PASSED/FAILED group; when there is none the test fails with "No images to clean" |
| `execute` (`auto_cleanup`) | `pipeline.auto_cleanup_image_group_id`. Empty = the image the cadence test built (this session or `reports/state/cadence_build.json`), else the first BUILT/PASSED/FAILED group. The group is set to FAILED in the database first |
| `cleanup` | `cleanup.postgres_backup`, `cleanup.cleanup_credentials` |

**Build:** the build suites commit `installation.catalog` with the next unused
version.

**Deploy:** the deploy suites deploy the image group the build suite created in
the same run.
- When that build failed, every deploy test is skipped.
- A deploy-only run deploys `pipeline.deploy_image_group_id`. It fails with
  "image name is not present" when that is empty, and with "requested image not
  found" when the image group doesn't exist (or the deploy pipeline doesn't
  offer it).

**Cadence:**
- The suite builds its own image first, then uploads
  `installation.cadence_catalog`.
- It fails with the command to run when no build pipeline has run yet.
- Its disable / re-enable tests change `cadence.enabled` without restarting any
  service, and restore it afterwards.

## NFT, batch execution, reports

```bash
./run_validation.sh nft_build_stream list
./run_validation.sh nft_build_stream test --marker security
```

- **Disruptive NFTs:** each requires its `nft_allow_*` key in `test_config.yml`;
  see [`nft/README.md`](nft/README.md).
- **Batch runs:** follow `test_run_config.yml` (`./run_validation.sh --config`;
  see [`docs/test_run_config.md`](docs/test_run_config.md)).
- **Reports:** every run writes `<report_name>.json` and `<report_name>.html` to
  `report_path`, and one `run_id` groups the steps of a lifecycle.
- **UT:** there is no UT category for this domain.

Pipeline logs and stage artifacts on the OIM:

```text
$OMNIA_DATA_PATH/build_stream/log/<job_id>/
$OMNIA_DATA_PATH/build_stream/build_stream_root/artifacts/<job_id>/<stage>/attempt_<n>/
```

`nft/demo/test_restart_api.sh` is a manual demo of the restart API. It asks for
the BuildStream auth credentials with hidden prompts, verifies TLS against
`bs_cert.pem` and keeps every secret off the command line.

## Directory structure

```text
test/build_stream/
├── README.md        this overview
├── conftest.py      the only FVT conftest: markers, --marker filter, order,
│                    host fixture, reports, prepare_base precheck gate
├── _run.py, run_validation.sh, setup_env.sh, requirements.txt, pytest.ini
├── test_config.yml, test_run_config.yml
├── docs/            test_config.md, test_run_config.md, test_creds.md
├── library/
│   ├── functions/   domain helpers, one module per capability; http_func.py is
│   │                the shared in-process HTTPS client (verified TLS)
│   ├── vars/        common_vars, execute_vars, domain_vars, test_case_vars
│   ├── messages/    build_stream_msgs, execute_msgs
│   ├── cleanup_inspection.py, domain_credentials.py
├── fvt/             prepare_base, precheck, prepare, execute, cleanup
│                    (README.md: every test case, what it checks, pass criteria)
├── nft/             test_resilience.py, test_security.py (own conftest.py),
│                    unit/ (BuildStream app unit tests), demo/
├── reports/         run state between processes (gitignored)
└── datasets/        generator/
```

## Local checks (same as the GitHub workflows)

Run from the repository root:

```bash
# pylint (.github/workflows/pylint.yml): every file must score >= 8
find test/build_stream -name '*.py' ! -name '__init__.py' ! -path '*/.venv/*' -print0 \
  | xargs -0 -n1 env PYTHONPATH=.:./src/build_stream pylint
# bandit (.github/workflows/bandit.yml)
bandit -r test/build_stream -ll -ii -x '*/.venv/*'
# shellcheck (.github/workflows/shellcheck.yml): no error or warning
find test/build_stream -name '*.sh' ! -path '*/.venv/*' -print0 | xargs -0 shellcheck -f gcc
# ansible-lint on changed YAML (.github/workflows/ansible-lint.yml)
ansible-lint --config=.config/ansible-lint.yml test/build_stream/test_config.yml
git diff --check
```

The hpc-compliance workflow also rejects `shell=True`, `os.system`, `eval`,
`exec`, unsafe YAML loaders and pickle. Live FVT requires a suitable, authorized
environment; a missing lab is reported as not run and never counted as a
success.
