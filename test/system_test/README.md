# Omnia System Verification (SVT)

`test/system_test` is the integration test of Omnia on one OIM. You choose a
**theme** (today `build_stream`) and fill **one input file per cluster**; the
SVT then removes the previous installation, sets the OIM up again and drives
the existing FVT suites in order. It produces one report per run, with the
exact commit and inputs used.

It works in two modes that share every script:

| Mode | Started by | What runs |
|---|---|---|
| Local | `./run_validation.sh svt_build_stream <stage>` on the OIM | The stages below, in this checkout |
| GitLab | Push, or **Run pipeline** in the SVT project | One job per stage; the runner drives the same stages on the cluster's OIM over SSH ([`pipelines/README.md`](pipelines/README.md)) |

The SVT never copies FVT logic. Every stage step and every SVT test case is a
list of FVT runner calls (`test/<domain>/_run.py fvt_<domain> ...`) defined as
data in [`library/vars/theme_vars.py`](library/vars/theme_vars.py):

| Owner suite | Used by the SVT for |
|---|---|
| `test/main` | `setup`, `init` (`omnia.sh --setup-venv`, every `domain-init.sh`) and `cleanup` (`omnia.sh --cleanup`) |
| `test/orchestrator`, `test/image_build_manager`, `test/repo_manager` | their `cleanup` tag (flags in their own `test_config.yml`) |
| `test/build_stream` | `prepare_base`, `precheck`, `prepare`, `execute` and `cleanup` |

## Safety model

- **Destructive stages:** `cleanup` deletes the previous installation: BuildStream
  and GitLab, orchestrator, image_build_manager, repo_manager, then the Omnia
  setup itself (venv, `/etc/omnia/omnia.env`). `system_verification` deploys,
  commits to GitLab, PXE-boots nodes and deletes image groups. Run them only on
  a lab OIM you own.
- **Run guard:** `cleanup`, `environment_setup` and `system_verification` refuse
  to run on a run id that `initialization` did not create. `--resume` continues
  the last initialized run of the checkout, and only for the same theme.
- **One run at a time:** in the pipeline, `/run/lock/svt-<cluster>` on the OIM
  holds the run id from the first stage to `summary`, and a second pipeline
  stops with "cluster busy".
- **No credentials here:** the SVT holds none. The pipeline reads them from
  OpenBao and pipes them over SSH stdin to `test/build_stream/setup_env.sh
  --domain-creds-stdin`. Locally you save them with
  `test/build_stream/setup_env.sh --set-domain-creds`. `user_inputs.yml` rejects
  credential-like keys.

## Prerequisites

- **OIM:** RHEL with Python 3.12+ and pip access to the package index (each
  `setup_env.sh` installs requirements), an Omnia checkout, root, and
  `systemd-run` (pipeline mode).
- **Lab:** the nodes in the PXE mapping, plus the NFS shares and repositories
  named in `user_inputs.yml`.
- **Pipeline mode:** see [`pipelines/README.md`](pipelines/README.md) (GitLab
  15.7+, a shell runner, OpenBao).

## Quick start (local, on the OIM)

```bash
cd test/system_test
${EDITOR:-vi} user_inputs/user_inputs.yml          # cluster values (MANDATORY ones marked)
${EDITOR:-vi} ../build_stream/test_config.yml      # BuildStream FVT settings: catalogs, pipelines ...
./setup_env.sh --venv                              # optional: run_validation.sh does it when needed

./run_validation.sh svt_build_stream all           # every stage, then summary
```

When `environment_setup` finishes, before `system_verification`, save the
domain credentials once:

```bash
cd test/build_stream && source "$(sed -n 's/^OMNIA_VENV_PATH=//p' /etc/omnia/omnia.env)/bin/activate"
./setup_env.sh --set-domain-creds
```

Or run the stages one at a time:

```bash
./run_validation.sh svt_build_stream list                 # stages and cases
./run_validation.sh svt_build_stream initialization
./run_validation.sh svt_build_stream cleanup
./run_validation.sh svt_build_stream environment_setup
./run_validation.sh svt_build_stream system_verification  # or --case cadence
./run_validation.sh svt_build_stream summary
./run_validation.sh svt_build_stream all --start-stage system_verification  # re-run from a stage
```

## Themes and SVT test cases

| Theme | Case | ID | FVT steps |
|---|---|---|---|
| `build_stream` | `build_deploy` | `SVT_BUILD_STREAM_001` | `fvt_build_stream`: `prepare_base test`, `precheck test`, `prepare test`, `execute exec`, `execute verify` for `gitlab_server`, `gitlab_runner`, `gitlab_project`, then `execute verify --marker automatic_execution` (build and deploy in one process) |
| `build_stream` | `cadence` | `SVT_BUILD_STREAM_002` | `fvt_build_stream execute verify --suite cadence` (builds its own image, records it for the cleanup) |
| `build_stream` | `automatic_cleanup` | `SVT_BUILD_STREAM_003` | `fvt_build_stream execute verify --suite auto_cleanup` (deletes the cadence image; skips when that build failed) |

- **Ordering:** a case stops at its first failed FVT step. Cases run in ID
  order.
- **Live output:** the full FVT output (stage logs, check marks) streams into
  the SVT output.
- **FVT reports:** the FVT HTML/JSON reports go to the FVT `report_path`; the
  SVT result names it.

## Stages

| Stage | What it does on the OIM | Skips / fails when |
|---|---|---|
| `initialization` | Validates `--inputs` / `--test-config` as YAML mappings *before* copying anything. Places them in `user_inputs/user_inputs.yml` and `test/<domain>/test_config.yml`. Runs the dataset generator (fills `src/<domain>/input` and `src/main/omnia.env`). Starts the run manifest (commit, theme, input checksums) | Fails on invalid inputs, a mandatory value left empty, or a generator error |
| `cleanup` | Installs the test requirements of the cleaning suites into the Omnia venv, then runs, in order: `fvt_build_stream cleanup test` (only when BuildStream is installed), `fvt_orchestrator cleanup test`, `fvt_image_build_manager cleanup test`, `fvt_repo_manager cleanup test --marker destructive`, and last `fvt_main cleanup exec` (`omnia.sh --cleanup`) from `test/main/.venv` | Skipped when there is no previous setup (no `/etc/omnia/omnia.env`). Without the Omnia venv only the `test/main` cleanup runs. Fails at the first failed cleanup |
| `environment_setup` | `test/main/setup_env.sh --venv`, then `fvt_main setup test` (`omnia.sh --setup-venv --deps-only`) and `fvt_main init test` (every `domain-init.sh`), then `setup_env.sh` of build_stream, orchestrator, image_build_manager and repo_manager in the new Omnia venv | Fails when a step fails or the Omnia venv is missing |
| `system_verification` | The SVT cases (pytest on `svt/<theme>/`, `--case` for one) | Fails when a case fails |
| `summary` | Prints the manifest: commit, checksums, every stage outcome and duration, every SVT case result, report directory | Fails when a recorded stage failed |

Because `cleanup` ends with `omnia.sh --cleanup`, `environment_setup` always
starts from an OIM without the Omnia setup, so `src/main/omnia.env` (filled by
the generator) becomes `/etc/omnia/omnia.env`.

**Cleanup flags** come from each suite's own `test_config.yml`:

| Suite | Keys |
|---|---|
| build_stream | `cleanup.postgres_backup`, `cleanup.cleanup_credentials` |
| orchestrator | `cleanup_credentials`, `cleanup_slurm`, `cleanup_k8s` |
| image_build_manager | `cleanup_credentials` (`false` runs `-e cleanup_credentials=false`) |
| repo_manager | `cleanup_credentials` (`false` runs `-e cleanup_credentials=false`) |

With `cleanup_credentials: false` the credential stores survive, so a local
re-run needs no `--set-domain-creds`; the pipeline pipes them from OpenBao
after `environment_setup` anyway.

### Options (`./run_validation.sh svt_<theme> <stage>|all ...`)

| Option | Default | Effect |
|---|---|---|
| `svt_<theme>` | required | Theme (`svt_build_stream`); `list` prints its stages and cases |
| `<stage>` / `all` | required | One stage, or every stage from `--start-stage`, then `summary` |
| `--inputs` | `user_inputs/user_inputs.yml` | Cluster input file placed before the generator |
| `--test-config` | the suite's own file | FVT `test_config.yml` of the theme suite (build_stream) |
| `--run-id` | new for `initialization` / `all`, else the latest run | Run identifier (`[A-Za-z0-9._-]`, 64 max) |
| `--start-stage` | `initialization` | With `all`: first stage (re-run from a failed stage) |
| `--case` | all | `system_verification`: one SVT case |
| `--resume` | off | A new run id for a later stage adopts the last initialized run (same theme) |
| `--quiet` | off | Output to the stage log only (the pipeline follows the files) |

Exit codes: `0` passed or skipped, `1` failed, `2` invalid arguments or the run
guard refused.

### Run files (`reports/<run_id>/`, gitignored)

| File | Content |
|---|---|
| `run.json` | Theme, commit, input checksums, `resumed_from`, every stage outcome and duration |
| `<stage>.log` | Complete stage output, including all FVT output. The SVT cases use `system_verification-<case>.log` |
| `<stage>.progress` | The current step, one line, refreshed as it changes |
| `<stage>.status` | `passed`, `skipped` or `failed <rc>` when the stage ends |
| `junit_<theme>.xml`, `svt_results.json` | SVT case results (GitLab test report, summary) |
| `inputs/` | Cluster files uploaded by the pipeline |

`reports/latest` names the last initialized run.

## `user_inputs.yml` and the dataset generator

`user_inputs/user_inputs.yml` holds the values of one cluster. It uses the same
key names and indentation as the real input files, so a value goes into the
same place in the matching file.

- **Order:** one block per module: main → repo_manager → image_build_manager →
  orchestrator → build_stream.
- **MANDATORY values:** OIM identity, admin network, BuildStream and GitLab
  IPs. The run stops and lists any left empty.
- **Optional values:** `""` keeps the shipped default.
- **PXE mapping:** the CSV keeps its header line; all its rows are replaced by
  `row1`, `row2`, ...
- **VAST:** without a VAST `source`, the generator comments out the
  `vast_storage` mount and `vast_storage_name` (the product then skips VAST).
  Giving a source restores them.
- **What stops a run:** a YAML or indentation error, an unknown key (typo), or
  a credential-like key or vault value.

```bash
cd dataset_generator
../.venv/bin/python generate_dataset.py --dry-run   # what would change
../.venv/bin/python generate_dataset.py             # fill src/<domain>/input
../.venv/bin/python generate_dataset.py /abc        # or: a full input tree in /abc
```

The output-folder mode creates the folder and copies every non-credential
input file into it. An existing file that would change is moved to
`/abc/.backup/<UTC time>/`. System roots and folders inside `src/` are
rejected. The generator never writes `/opt/omnia`; `./omnia.sh --init` stages
the inputs there. To fill another input file, add a block to `user_inputs.yml`
and a target to `dataset_generator/profiles/build_stream.yml`; the merge is
generic.

## Directory structure

```text
test/system_test/
├── README.md                    this file
├── setup_env.sh                 SVT requirements (.venv, active venv or --user); no credentials
├── requirements.txt             pytest, pytest-order, PyYAML, ruamel.yaml, omnia_auto wheel
├── run_validation.sh, _run.py   SVT runner: svt_<theme> list | <stage> | all (local and pipeline)
├── conftest.py, pytest.ini      markers (theme and case), results for summary
├── user_inputs/user_inputs.yml  the cluster values (template)
├── dataset_generator/           fills src inputs from user_inputs.yml (profiles/build_stream.yml)
├── library/
│   ├── vars/                    common_vars (paths), theme_vars (themes and FVT steps),
│   │                            domain_vars (runner catalog), test_case_vars (IDs)
│   ├── messages/svt_msgs.py     log, assertion and stage text with HOW TO FIX
│   └── functions/               fvt_func (FVT bridge), stage_func (stages, manifest,
│                                run guard), case_func, process_func (no-shell runner)
├── svt/build_stream/            one test file per SVT case
├── pipelines/                   GitLab project: setup, OpenBao, CI templates
└── reports/                     run files (gitignored)
```

## Adding a theme or a case

1. **Theme data:** add the theme or case to `library/vars/theme_vars.py`:
   description, cleanup and setup steps, FVT suites to install, and the FVT
   steps of each case.
2. **Test case:** add its ID, title and order to
   `library/vars/test_case_vars.py`, and its test file under `svt/<theme>/`.
3. **Pipeline:** add `pipelines/project_template/ci/themes/<theme>.yml`
   (timeouts, cases, credential modules) and its option in the
   `THEME` drop-down of `.gitlab-ci.yml`.

## Local checks (same as the GitHub workflows)

```bash
cd <repository root>
find test/system_test -name '*.py' ! -name '__init__.py' ! -path '*/.venv/*' -print0 \
  | xargs -0 -n1 env PYTHONPATH=.:./src/build_stream pylint      # each file >= 8
bandit -r test/system_test -ll -ii -x '*/.venv/*'
find test/system_test -name '*.sh' ! -path '*/.venv/*' -print0 | xargs -0 shellcheck -f gcc
ansible-lint --config=.config/ansible-lint.yml test/system_test/user_inputs/user_inputs.yml \
  test/system_test/pipelines/project_template/.gitlab-ci.yml
```
