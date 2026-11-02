# Omnia System Verification (SVT)

`test/system_test` is the integration test of Omnia on one OIM. You choose a
**theme** (today `build_stream`) in `test_config.yml` and fill the cluster
values in `user_inputs.yml`. Then two commands do everything:

```bash
./setup_env.sh                            # configure -> install -> credentials
./run_validation.sh svt_build_stream all  # initialization -> system_verification -> summary
```

- **`./setup_env.sh`:** loads your values into the Omnia inputs, installs
  Omnia (`omnia.sh -s`) and the test requirements, and stores the domain
  credentials.
- **`./run_validation.sh`:** checks the setup and drives the existing FVT
  suites in order. It writes one report per run, with the exact commit,
  inputs and setup used.
- **No activation step:** you never source `activate-omnia.sh` yourself;
  every step that needs the Omnia venv activates it.

The SVT never copies FVT logic. Every cleanup step and every SVT test case is
a list of FVT runner calls (`test/<domain>/_run.py fvt_<domain> ...`) defined
as data in [`library/vars/theme_vars.py`](library/vars/theme_vars.py):

| Owner suite | Used by the SVT for |
|---|---|
| `test/main` | `cleanup` (`omnia.sh --cleanup`) |
| `test/orchestrator`, `test/image_build_manager`, `test/repo_manager` | their `cleanup` tag; their test requirements in the Omnia venv |
| `test/build_stream` | `prepare_base`, `precheck`, `prepare`, `execute`, `cleanup`; its `setup_env.sh` writes every domain credential store |

## Quick start (on the OIM, as root)

```bash
cd test/system_test
${EDITOR:-vi} user_inputs.yml                   # cluster values (MANDATORY ones marked)
${EDITOR:-vi} test_config.yml                   # theme, cleanup flags
${EDITOR:-vi} ../build_stream/test_config.yml   # BuildStream FVT settings: catalogs, pipelines ...

./setup_env.sh                       # configure, install, prompt the missing credentials
./setup_env.sh --status              # the steps and the readiness checks, in a box
./run_validation.sh svt_build_stream all
```

For a clean installation, remove the previous one first:

```bash
./setup_env.sh --force               # configure, cleanup (asks 'yes'), full install, credentials
```

Unattended, for example from a pipeline. `--yes` answers every confirmation,
and the missing credentials are read as one JSON object from stdin:

```bash
credential-json-provider | ./setup_env.sh --force --yes
./run_validation.sh svt_build_stream all --quiet
```

## `./setup_env.sh`

`setup_env.sh` creates (or reuses) the SVT's own `.venv/` and runs every step
with it through the Python wrapper `_setup.py`. That venv is never activated.
With no action it runs every step in order and stops at the first failure.
Running it again is quick: steps with nothing to do are skipped.

| Command | Steps |
|---|---|
| `./setup_env.sh` | configure → install → credentials |
| `./setup_env.sh --force` | configure → cleanup → full install → credentials |
| `./setup_env.sh --configure` | configure |
| `./setup_env.sh --install` | install |
| `./setup_env.sh --install --force` | cleanup → full install |
| `./setup_env.sh --cleanup` | cleanup |
| `./setup_env.sh --set-domain-creds` / `--update-domain-creds` [`--domain <d>`] | prompt every store (or one) |
| `provider \| ./setup_env.sh --domain-creds-stdin` | write the stores from JSON keyed by domain |
| `./setup_env.sh --status` | show the status box (read-only) |

Options: `--yes` (answer every confirmation), `--force` (with no action or
`--install`), `--domain <d>`, `--recreate-venv` (the SVT `.venv/`), `--debug`
(pip output), `--help`.

### What each step does

**configure**
- The dataset generator writes `user_inputs.yml` into `src/<domain>/input` and
  `src/main/omnia.env`, with the profile `dataset_generator/profiles/<theme>.yml`.
- The `cleanup` flags of `test_config.yml` are written into each
  `test/<suite>/test_config.yml`.
- It stops on a YAML error, an unknown key, a credential-like key or an empty
  MANDATORY value.

**cleanup** (DESTRUCTIVE)
- It writes the cleanup flags again, lists the steps and asks for `yes`; `--yes`
  confirms without asking.
- It then runs, in order:
  1. `fvt_build_stream cleanup test` (only when BuildStream is installed);
  2. `fvt_orchestrator cleanup test`;
  3. `fvt_image_build_manager cleanup test`;
  4. `fvt_repo_manager cleanup test --marker destructive`;
  5. `fvt_main cleanup exec` (`omnia.sh --cleanup`, from `test/main/.venv`).
- It is skipped when there is no `/etc/omnia/omnia.env`. A suite with
  `enabled: false` is skipped.

**install**
- It runs `src/main/omnia.sh -s` with its full output, outside any active venv
  (`omnia.sh` creates the venv, every `domain-init.sh`, the catalog and
  `omnia-cli`).
- It then installs the test requirements into the Omnia venv, in order:
  repo_manager, image_build_manager, orchestrator, build_stream. Each suite's
  `setup_env.sh` runs with the venv active and `omnia.env` exported.
- **Inputs must be current:** it needs the inputs configured and unchanged
  since.
- **omnia.env:** it adds `--force-env` when `src/main/omnia.env` differs from
  `/etc/omnia/omnia.env` (`omnia_force_env: true`).
- **Inputs already on the OIM:** domain-init asks on the terminal before
  overwriting them. With `--yes` (or without a terminal), each domain whose
  runtime inputs still differ from src is re-staged with
  `domain-init.sh --force`. Any file that still differs is reported.
- **Requirements are not reinstalled when nothing changed:** a suite is only
  installed again when its `requirements.txt`, its `setup_env.sh` or the
  omnia_auto wheel changed. The checksums are kept in
  `<venv>/.svt_test_requirements.json`.
- **`--force`:** cleanup first, then `omnia.sh -s --force-deps`, and every
  test requirement again.

**credentials**
- Only the missing stores are written: repo_manager, image_build_manager,
  orchestrator, build_stream.
- On a terminal you are prompted for each one. Unattended, the JSON on stdin
  is passed once to `--domain-creds-stdin`.
- It runs `test/build_stream/setup_env.sh` with the Omnia venv activated. It
  needs the installed Omnia.
- The prompts and the JSON are never logged.

**`--set-domain-creds` / `--update-domain-creds` / `--domain-creds-stdin`**
- These run the same `test/build_stream/setup_env.sh` flag for every store (or
  `--domain <d>`), with the Omnia venv activated.
- They need the installed Omnia; otherwise: "Omnia is not set up (omnia.sh -s
  has not run)".

Every value about the installation is read from `/etc/omnia/omnia.env`: the
venv, the data path, the project and the domain data paths
(`<DOMAIN>_DATA_PATH`, else `<OMNIA_DATA_PATH>/<domain>`).

**Why credentials are not placed in `src/<domain>/input`:** domain-init copies
every file of `src/<domain>/input` to `<data>/<domain>/input/<project>`, but
with `rsync --exclude='.*'`. Each store's vault key is a dot file
(`.<store>_key`), so it would not be copied, and the stores would sit in the
git checkout. They are therefore written directly to the runtime folders,
after `omnia.sh -s` has created them.

### `--status`

```text
┌─ SVT setup status - theme build_stream ─────────────────────────────────────┐
│        step       status   started (UTC)              duration              │
│ [ OK ] configure  passed   2026-11-03T09:00:01+00:00  3s                    │
│ [ -- ] cleanup    not run                                                   │
│ [ OK ] install    passed   2026-11-03T09:00:04+00:00  14m21s                │
│ [ OK ] creds      passed   2026-11-03T09:14:25+00:00  1m02s                 │
├─ ready for ./run_validation.sh svt_build_stream? ───────────────────────────┤
│ [ OK ] Inputs configured (user_inputs.yml, test_config.yml)                 │
│ [ OK ] Omnia installed (omnia.sh -s: omnia.env, data path, venv, ...)       │
│ [ OK ] Installed after the last configure                                   │
│ [ OK ] Test requirements in the Omnia venv (4 suites)                       │
│ [ OK ] Credentials: repo_manager                                            │
│ ...                                                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│ READY: ./run_validation.sh svt_build_stream all                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

A failed check shows its HOW TO FIX line under it. The same box is printed at
the end of `./setup_env.sh` and `--install`.

## `test_config.yml`

| Key | Default | Effect |
|---|---|---|
| `theme` | `build_stream` | Dataset profile, suites installed, credential stores and SVT cases. Must match `svt_<theme>` |
| `omnia_force_env` | `true` | install replaces a different `/etc/omnia/omnia.env` with the configured `src/main/omnia.env` |
| `cleanup.<suite>.enabled` | `true` | `false` skips that suite's cleanup step |
| `cleanup.<suite>.<flag>` | as shipped | Written into `test/<suite>/test_config.yml` before its cleanup runs |

| Suite | Flags (booleans) |
|---|---|
| build_stream | `postgres_backup`, `cleanup_credentials` (its `cleanup:` section) |
| orchestrator | `cleanup_credentials`, `cleanup_slurm`, `cleanup_k8s`, `cleanup_benchmark_tools` |
| image_build_manager | `cleanup_credentials` |
| repo_manager | `cleanup_credentials` |
| main | `enabled` only |

- **Accepted keys:** only these keys are accepted.
- **What is rewritten:** only a value that differs is rewritten; the comments
  and layout of the suite's file stay as they were. This edits the tracked
  `test/<suite>/test_config.yml` files of the checkout.
- **Keeping credentials:** with `cleanup_credentials: false` the stores
  survive a cleanup, so the next `./setup_env.sh` has none to ask for.

## Unattended runs

Every question the SVT asks can be answered on the command line:

| Question | Unattended answer |
|---|---|
| cleanup: "Type 'yes'" | `--yes` (without it and without a terminal, cleanup is refused) |
| domain-init: "Overwrite existing files?" | `--yes`: `omnia.sh -s` gets no stdin, then `domain-init.sh --force` for the stale domains |
| credential prompts | JSON keyed by domain on stdin (`provider \| ./setup_env.sh --yes`, or `--domain-creds-stdin`) |
| `./run_validation.sh` | asks nothing; FVT steps run with an empty stdin. `--quiet` writes to the stage logs only |

## Themes and SVT test cases

| Theme | Case | ID | FVT steps |
|---|---|---|---|
| `build_stream` | `build_deploy` | `SVT_BUILD_STREAM_001` | `fvt_build_stream`: `prepare_base test`, `precheck test`, `prepare test`, `execute exec`, `execute verify` for `gitlab_server`, `gitlab_runner`, `gitlab_project`, then `execute verify --marker automatic_execution` (build and deploy in one process) |
| `build_stream` | `cadence` | `SVT_BUILD_STREAM_002` | `fvt_build_stream execute verify --suite cadence` (builds its own image, records it for the cleanup) |
| `build_stream` | `automatic_cleanup` | `SVT_BUILD_STREAM_003` | `fvt_build_stream execute verify --suite auto_cleanup` (deletes the cadence image; skips when that build failed) |

- **Ordering:** a case stops at its first failed FVT step. Cases run in ID
  order.
- **Live output:** the full FVT output streams into the SVT output.
- **FVT reports:** the FVT HTML/JSON reports go to the FVT `report_path`; the
  SVT result names it.

## `./run_validation.sh`

`run_validation.sh` activates the Omnia venv when it is not active. It reads
`OMNIA_DATA_PATH` and `OMNIA_VENV_PATH` from `/etc/omnia/omnia.env`, then
sources `<OMNIA_DATA_PATH>/activate-omnia.sh`. Both files must belong to root
(or you) and be writable by no one else. Before `omnia.sh -s` has run, it
reports what is missing.

| Stage | What it does | Fails when |
|---|---|---|
| `initialization` | Checks `test_config.yml` (same theme) and every readiness item of `--status`. Places `--test-config` (optional) as `test/<suite>/test_config.yml`. Starts the run manifest (commit, checksums, cleanup flags, setup outcomes) and copies `reports/setup/` into the run | Any check fails (all are listed with HOW TO FIX) |
| `system_verification` | The SVT cases (pytest on `svt/<theme>/`, `--case` for one) | A case fails |
| `summary` | Prints the manifest: commit, checksums, setup steps, every stage outcome, every SVT case result, report directory | A recorded stage failed |

```bash
./run_validation.sh svt_build_stream list                 # stages and cases
./run_validation.sh svt_build_stream initialization
./run_validation.sh svt_build_stream system_verification  # or --case cadence
./run_validation.sh svt_build_stream summary
./run_validation.sh svt_build_stream all --start-stage system_verification  # re-run from a stage
```

| Option | Default | Effect |
|---|---|---|
| `svt_<theme>` | required | Theme (`svt_build_stream`); `list` prints its stages and cases |
| `<stage>` / `all` | required | One stage, or every stage from `--start-stage`, then `summary` |
| `--test-config` | the suite's own file | FVT `test_config.yml` of the theme suite (build_stream) |
| `--run-id` | new for `initialization` / `all`, else the latest run | Run identifier (`[A-Za-z0-9._-]`, 64 max) |
| `--start-stage` | `initialization` | With `all`: first stage |
| `--case` | all | `system_verification`: one SVT case |
| `--resume` | off | A new run id for `system_verification` adopts the last initialized run (same theme) |
| `--quiet` | off | Output to the stage log only |

Exit codes: `0` passed or skipped, `1` failed, `2` invalid arguments, the
Omnia venv cannot be activated, or the run guard refused.

## Safety model

- **Destructive steps:** cleanup (`--cleanup`, `--force`) deletes the previous
  installation: BuildStream and GitLab, orchestrator, image_build_manager,
  repo_manager, then the Omnia setup (venv, `/etc/omnia/omnia.env`). It asks
  for `yes` unless `--yes`. install rewrites `/etc/omnia/omnia.env` (with
  `omnia_force_env: true`), and with `--yes` overwrites the runtime inputs.
  `system_verification` deploys, commits to GitLab, PXE-boots nodes and
  deletes image groups. Use them only on a lab OIM you own.
- **Run guard:** `system_verification` refuses a run id that `initialization`
  did not create. `--resume` continues the last initialized run of the
  checkout, for the same theme only.
- **Credentials:** never in `user_inputs.yml` or `test_config.yml` (the
  generator rejects credential-like keys). They are never logged and never
  an argument; JSON from stdin is kept in memory only.

## Reports (gitignored)

| Path | Content |
|---|---|
| `reports/setup/<step>.log` | Output of each setup step (`configure`, `cleanup`, `install`, `creds`), appended per run; credential prompts excluded |
| `reports/setup/setup.json` | Last outcome of each step: status, time, duration, error, checksums, venv, suites installed, stale inputs, stores written |
| `reports/<run_id>/run.json` | Theme, commit, checksums, cleanup flags, setup outcomes, `resumed_from`, every stage outcome |
| `reports/<run_id>/setup/` | Copy of `reports/setup/` taken by `initialization` |
| `reports/<run_id>/<stage>.log`, `.progress`, `.status` | Stage output, current step, final status. The SVT cases use `system_verification-<case>.log` |
| `reports/<run_id>/junit_<theme>.xml`, `svt_results.json` | SVT case results |

`reports/latest` names the last initialized run.

## `user_inputs.yml` and the dataset generator

`user_inputs.yml` holds the values of one cluster. It uses the same key names
and indentation as the real input files, so a value goes into the same place
in the matching file.

- **Order:** one block per module: main → repo_manager → image_build_manager →
  orchestrator → build_stream.
- **MANDATORY values:** OIM identity, admin network, BuildStream and GitLab
  IPs. configure stops and lists any left empty.
- **Optional values:** `""` keeps the shipped default.
- **PXE mapping:** the CSV keeps its header line; all its rows are replaced by
  `row1`, `row2`, ...
- **VAST:** without a VAST `source`, the generator comments out the
  `vast_storage` mount and `vast_storage_name` (the product then skips VAST).
  Giving a source restores them.

The generator can also run alone:

```bash
cd dataset_generator
../.venv/bin/python generate_dataset.py --dry-run   # what would change
../.venv/bin/python generate_dataset.py             # fill src/<domain>/input
../.venv/bin/python generate_dataset.py /abc        # or: a full input tree in /abc
```

The output-folder mode creates the folder and copies every non-credential
input file into it; an existing file that would change is moved to
`/abc/.backup/<UTC time>/`. To fill another input file, add a block to
`user_inputs.yml` and a target to `dataset_generator/profiles/<theme>.yml`.

## Directory structure

```text
test/system_test/
├── README.md                    this file
├── user_inputs.yml              the cluster values
├── test_config.yml              theme, omnia_force_env, cleanup flags
├── setup_env.sh, _setup.py      prepare the OIM: configure, cleanup, install, credentials, status
├── run_validation.sh, _run.py   SVT runner: svt_<theme> list | <stage> | all
├── requirements.txt             SVT .venv: pytest, pytest-order, PyYAML, ruamel.yaml, omnia_auto
├── conftest.py, pytest.ini      markers (theme and case), results for summary
├── dataset_generator/           user_inputs.yml -> src inputs (profiles/<theme>.yml)
├── library/
│   ├── vars/                    common_vars (every path and file name), theme_vars (themes,
│   │                            FVT steps, cleanup flags, credential stores), domain_vars,
│   │                            test_case_vars
│   ├── messages/svt_msgs.py     stage, setup and config text with HOW TO FIX
│   └── functions/               setup_func (setup steps, readiness), status_func (status box),
│                                config_func (test_config.yml), omnia_func (omnia.env checks),
│                                stage_func (stages, manifest), fvt_func (FVT bridge),
│                                case_func, process_func (no-shell runner)
├── svt/build_stream/            one test file per SVT case
├── pipelines/                   GitLab project templates (not maintained for this flow)
└── reports/                     setup and run files (gitignored)
```

## Adding a theme or a case

1. **Theme data:** add the theme to `library/vars/theme_vars.py`: description,
   profile, cleanup steps, suites to install (`fvt_domains`), credential
   domains, and the FVT steps of each case.
2. **Inputs:** add `dataset_generator/profiles/<theme>.yml`.
3. **Test case:** add its ID, title and order to
   `library/vars/test_case_vars.py`, and its test file under `svt/<theme>/`.

## Local checks (same as the GitHub workflows)

```bash
cd <repository root>
find test/system_test -name '*.py' ! -name '__init__.py' ! -path '*/.venv/*' -print0 \
  | xargs -0 -n1 env PYTHONPATH=.:./src/build_stream pylint      # each file >= 8
bandit -r test/system_test -ll -ii -x '*/.venv/*'
find test/system_test -name '*.sh' ! -path '*/.venv/*' -print0 | xargs -0 shellcheck -f gcc
ansible-lint --config=.config/ansible-lint.yml test/system_test/user_inputs.yml \
  test/system_test/test_config.yml
```
