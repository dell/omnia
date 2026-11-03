# Omnia System Verification (SVT)

`test/system_test` is the integration test of Omnia on one OIM. You choose a
**theme** (today `build_stream`, the default): its settings are
`<theme>_test_config.yml` (`build_stream_test_config.yml`). You fill the
cluster values in `user_inputs.yml`. Then two commands do everything:

```bash
./setup_env.sh                            # configure (new run) -> install -> credentials
./run_validation.sh svt_build_stream all  # initialization -> the theme's stages -> summary
```

- **`./setup_env.sh`:** starts a run, loads your values into the Omnia inputs
  and the FVT suites' settings, installs Omnia (`omnia.sh -s`) and the test
  requirements, and stores the domain credentials.
- **`./run_validation.sh`:** runs the theme's stages in order. Each stage is a
  set of SVT tests; each test runs one FVT step (the playbook, or its
  verification). Everything goes into one SVT report per run.
- **No activation step:** you never source `activate-omnia.sh` yourself;
  every step that needs the Omnia venv activates it.

The SVT never copies FVT logic: every cleanup step and every SVT test is one
FVT runner call (`test/<domain>/_run.py fvt_<domain> ...`), defined as data in
[`library/vars/theme_vars.py`](library/vars/theme_vars.py) and
[`library/vars/test_case_vars.py`](library/vars/test_case_vars.py):

| Owner suite | Used by the SVT for |
|---|---|
| `test/main` | `cleanup` (`omnia.sh --cleanup`) |
| `test/orchestrator`, `test/image_build_manager`, `test/repo_manager` | their `cleanup` tag; their test requirements in the Omnia venv |
| `test/build_stream` | `prepare_base`, `precheck`, `prepare`, `execute` (exec and verify), `cleanup`; its `setup_env.sh` writes every domain credential store |

## Quick start (on the OIM, as root)

```bash
cd test/system_test
${EDITOR:-vi} user_inputs.yml                # cluster values (MANDATORY ones marked)
${EDITOR:-vi} build_stream_test_config.yml   # catalog, cadence catalog, pipeline cancel, cleanup flags

./setup_env.sh                       # configure (new run), install, prompt the missing credentials
./setup_env.sh --status              # the run, the steps and the readiness checks, in a box
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

Options: `--theme <theme>` (default `build_stream`; its settings are
`<theme>_test_config.yml`), `--yes` (answer every confirmation), `--force`
(with no action or `--install`), `--domain <d>`, `--recreate-venv` (the SVT
`.venv/`), `--debug` (pip output), `--help`.

### What each step does

**configure**
- The dataset generator writes `user_inputs.yml` into `src/<domain>/input` and
  `src/main/omnia.env`, with the profile `dataset_generator/profiles/<theme>.yml`.
- It starts a new SVT run, first of all: a new `run_id` (`svt-<UTC time>`,
  unless `report.run_id` is set), the theme and the run folder
  `<report_path>/<run_id>/`. Every later step (cleanup, install, creds,
  `./run_validation.sh`) adds to this run; see [The run](#the-run).
- The `cleanup` flags and the `build_stream` block (catalog,
  cadence_catalog, allow_pipeline_cancel) of `build_stream_test_config.yml`
  are written into each `test/<suite>/test_config.yml`.
- The FVT report settings of the run (`<run folder>/fvt`, `fvt_report`, the
  run id) are written into every suite's `test_config.yml` (main,
  repo_manager, image_build_manager, orchestrator, build_stream), so their
  results can be shown in the [SVT report](#the-svt-report).
- It checks `main.catalog` against `./omnia.sh --list-catalogs`.
- It stops on a YAML error, an unknown key, a credential-like key, an empty
  MANDATORY value or an unknown catalog.

**cleanup** (DESTRUCTIVE)
- It writes the cleanup flags again, lists the steps and asks for `yes`; `--yes`
  confirms without asking.
- It then runs, in order:
  1. `fvt_build_stream cleanup test` (only when BuildStream is installed);
  2. `fvt_orchestrator cleanup test`;
  3. `fvt_image_build_manager cleanup test`;
  4. `fvt_repo_manager cleanup test --marker destructive`;
  5. with `cleanup.main.cleanup_all: true` (default): every
     `src/<domain>/domain-init.sh --cleanup` (each domain's input and log
     artifacts). `omnia.sh --cleanup --all` runs the same helpers, but only
     after a preflight that refuses while `<data>/<domain>/log` holds a file;
     the validate playbooks write logs there and no domain cleanup tag removes
     them, so without this step `--all` stops and removes nothing;
  6. `fvt_main cleanup test` from `test/main/.venv`: `omnia.sh --cleanup --all
     --skip-approval` (the whole `OMNIA_DATA_PATH`, credential stores
     included), or `omnia.sh --cleanup` with `cleanup_all: false`; then the
     verify cases MAIN_FVT_CLEANUP_V001-V005 check what was removed.
- **Complete reset:** after `cleanup_all` nothing of the previous installation
  is left, so the next install asks no "overwrite existing files?" question.
  omnia.sh refuses, and deletes nothing, while a domain still holds deployed
  state; the cleanup block of the report shows which.
- **Report location:** with `cleanup_all` the cleanup refuses when the report
  directory is inside `OMNIA_DATA_PATH`, which it would delete.
- **test/main venv:** test/main skips `omnia.sh --cleanup` when the Omnia venv
  is the active virtualenv, so the SVT always runs it with `test/main/.venv`.
- It is skipped when there is no `/etc/omnia/omnia.env`. A suite with
  `enabled: false` is skipped.

**install**
- It runs `src/main/omnia.sh -s` with its full output, outside any active venv
  (`omnia.sh` creates the venv, every `domain-init.sh`, the catalog and
  `omnia-cli`).
- With `main.catalog` set in `user_inputs.yml` it then runs
  `./omnia.sh --select-catalog <name>` (answering its replace question).
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
│ [ OK ] Inputs configured (user_inputs.yml, build_stream_test_config.yml)    │
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

## `build_stream_test_config.yml` (the theme's settings)

`./setup_env.sh --configure` writes the `build_stream` block and the cleanup
flags into the FVT suites' `test/<suite>/test_config.yml`, so they override
the suites' own values. A change here needs a new `--configure` (a new run).

| Key | Default | Effect |
|---|---|---|
| `build_stream.catalog` | `29` | Catalog the build_deploy stage commits as `catalog_rhel.json` (FVT `installation.catalog`): a number of `./omnia.sh --list-catalogs` or an absolute path |
| `build_stream.cadence_catalog` | `29` | Catalog the cadence stage uploads (FVT `installation.cadence_catalog`); `""` = the same as catalog |
| `build_stream.allow_pipeline_cancel` | `true` | Cancel GitLab pipelines still running before a commit or trigger (FVT `pipeline.allow_pipeline_cancel`); `false`: the test fails and lists them |
| `omnia_force_env` | `true` | install replaces a different `/etc/omnia/omnia.env` with the configured `src/main/omnia.env` |
| `cleanup.<suite>.enabled` | `true` | `false` skips that suite's cleanup step |
| `cleanup.<suite>.<flag>` | as shipped | Written into `test/<suite>/test_config.yml` before its cleanup runs |
| `cleanup.main.cleanup_all` | `true` | Complete reset: every `domain-init.sh --cleanup`, then `omnia.sh --cleanup --all`; `false`: `omnia.sh --cleanup` (data kept) |
| `report.report_path` | `""` = `test/system_test/reports` | Parent of the run folders (`<report_path>/<run_id>/`); keep it outside `OMNIA_DATA_PATH` |
| `report.report_name` | `""` = `svt_build_stream_report` | SVT report file name (`.json`, `.html`) in the run folder |
| `report.run_id` | `""` = new `svt-<UTC time>` per configure | The run id; a fixed value reuses that run folder (same theme only) |

| Suite | Flags (booleans) |
|---|---|
| build_stream | `postgres_backup`, `cleanup_credentials` (its `cleanup:` section) |
| orchestrator | `cleanup_credentials`, `cleanup_slurm`, `cleanup_k8s`, `cleanup_benchmark_tools` |
| image_build_manager | `cleanup_credentials` |
| repo_manager | `cleanup_credentials` |
| main | `cleanup_all` |

- **Accepted keys:** only these keys are accepted.
- **What is rewritten:** only a value that differs is rewritten; the comments
  and layout of the suite's file stay as they were. This edits the tracked
  `test/<suite>/test_config.yml` files of the checkout.
- **Keeping credentials:** with `cleanup_credentials: false` the stores
  survive a cleanup, so the next `./setup_env.sh` has none to ask for. A
  `cleanup_all` reset deletes them anyway (the cleanup warns).

## Unattended runs

Every question the SVT asks can be answered on the command line:

| Question | Unattended answer |
|---|---|
| cleanup: "Type 'yes'" | `--yes` (without it and without a terminal, cleanup is refused) |
| domain-init: "Overwrite existing files?" | `--yes`: `omnia.sh -s` gets no stdin, then `domain-init.sh --force` for the stale domains |
| credential prompts | JSON keyed by domain on stdin (`provider \| ./setup_env.sh --yes`, or `--domain-creds-stdin`) |
| `./run_validation.sh` | asks nothing; FVT steps run with an empty stdin. `--quiet` writes to the stage logs only |

## The stages of `build_stream`

Every SVT test runs one FVT step of `test/build_stream`: `exec` runs the
playbook, `verify` runs its verification tests. Within a stage, once a test
fails, the later tests of the stage are skipped (they need what it set up).
`./run_validation.sh svt_build_stream list` prints the tests of each stage.

| Stage | SVT tests (ID: FVT step) | After the stage |
|---|---|---|
| `initialization` | the readiness checks of `--status` (one report entry each) | the run manifest is written |
| `prepare_build_stream` | `004` prepare_base exec, `005` prepare_base verify, `006` precheck exec, `007` precheck verify, `008` prepare exec, `009` prepare verify, `010` execute exec, `011`-`013` execute verify `gitlab_server`, `gitlab_runner`, `gitlab_project` | the base domains and BuildStream run; GitLab server, runner and project are up |
| `build_deploy` | `014` execute verify `--marker automatic_execution` (build_automatic and deploy_automatic in one process: the deploy uses the image the build made) | an image built and deployed |
| `cadence` | `015` execute verify `--suite cadence` (a new build, one cadence cycle, the cadence pipeline) | the cadence image is handed to the automatic cleanup |
| `automatic_cleanup` | `016` execute verify `--suite auto_cleanup` (marks the cadence image FAILED, one cleanup_cron pass, checks S3, registry, NFS) | |
| `summary` | prints the run and renders the report; fails when anything in the run failed | |

IDs are `SVT_BUILD_STREAM_<NNN>`; `001`-`003` were the former whole-case tests
and are not reused.

## `./run_validation.sh`

`run_validation.sh` activates the Omnia venv when it is not active. It reads
`OMNIA_DATA_PATH` and `OMNIA_VENV_PATH` from `/etc/omnia/omnia.env`, then
sources `<OMNIA_DATA_PATH>/activate-omnia.sh`. Both files must belong to root
(or you) and be writable by no one else. Before `omnia.sh -s` has run, it
reports what is missing.

```bash
./run_validation.sh svt_build_stream list                    # stages and their tests
./run_validation.sh svt_build_stream initialization
./run_validation.sh svt_build_stream prepare_build_stream
./run_validation.sh svt_build_stream build_deploy
./run_validation.sh svt_build_stream cadence
./run_validation.sh svt_build_stream automatic_cleanup
./run_validation.sh svt_build_stream summary
./run_validation.sh svt_build_stream all                     # every stage, then summary
./run_validation.sh svt_build_stream all --start-stage cadence
```

| Option | Default | Effect |
|---|---|---|
| `svt_<theme>` | required | Theme (`svt_build_stream`); `list` prints its stages and tests |
| `<stage>` / `all` | required | One stage, or every stage from `--start-stage`, then `summary` |
| `--run-id` | the current run | Must be the run started by `./setup_env.sh --configure`; another id is refused |
| `--start-stage` | `initialization` | With `all`: first stage |
| `--quiet` | off | Output to the stage log only |

Exit codes: `0` passed or skipped, `1` failed, `2` invalid arguments, the
Omnia venv cannot be activated, or the run guard refused.

## Safety model

- **Destructive steps:** cleanup (`--cleanup`, `--force`) deletes the previous
  installation: BuildStream and GitLab, orchestrator, image_build_manager,
  repo_manager, then the Omnia setup (venv, `/etc/omnia/omnia.env`) and, with
  `cleanup_all`, the whole `OMNIA_DATA_PATH`. It asks
  for `yes` unless `--yes`. install rewrites `/etc/omnia/omnia.env` (with
  `omnia_force_env: true`), and with `--yes` overwrites the runtime inputs.
  The stages deploy, commit to GitLab, PXE-boots nodes and delete image
  groups. Use them only on a lab OIM you own.
- **Run guard:** no step runs without a run, after a theme change, or after a
  step of the run failed; see [The run](#the-run).
- **Credentials:** never in `user_inputs.yml` or `<theme>_test_config.yml` (the
  generator rejects credential-like keys). They are never logged and never
  an argument; JSON from stdin is kept in memory only.

## The run

`./setup_env.sh --configure` (and `./setup_env.sh` with no action, which starts
with configure) starts a run. The run is recorded in
`reports/current_run.json`: run id, theme, run folder, start time, the failed
step (if any) and the previous run.

```text
./setup_env.sh --configure        -> run svt-20261103T094900Z (theme build_stream)
./setup_env.sh --install          -> same run
./setup_env.sh --set-domain-creds -> same run
./run_validation.sh svt_build_stream all  -> same run
```

- **One run, one folder, one theme:** the SVT report, the stage logs,
  `run.json`, `svt_run.json` (the folder's theme) and the FVT suites' own
  reports (`fvt/`) are all in `<report_path>/<run_id>/`. The HTML report is
  self-contained: that one file is what you send.
- **A step is refused (exit 2, with the reason and how to fix it) when:**
  - no run was started (`./setup_env.sh --configure` first);
  - the run is of another theme (`--theme`, `svt_<theme>`), or the theme's
    test_config changed `report_*`;
  - a step or stage of the run failed, or the run's report holds failed
    results (an FVT suite run by hand counts too).
- **After a failure:** fix the cause, then `./setup_env.sh --configure` starts
  a new run. The installation, the test requirements and the credential
  stores are kept, so `./run_validation.sh svt_<theme> all` can follow
  directly. The new run's report names the previous run and its state.
- **`summary` always runs** (also on a failed run): it re-renders the report
  and fails when anything in the run failed.
- **A fixed `report.run_id`** reuses its folder only for the same theme;
  configure fails when the folder belongs to another theme.

## The SVT report

One report per run: `<run folder>/<report_name>.json` and `.html`, in the SVT's
own format (`library/functions/svt_report_func.py`). Top to bottom:

1. **Run Details:** theme, description, run id, run state (Open, Failed at a
   step, or Failed: what failed), started, last updated, previous run,
   commit, OIM, test counts.
2. **Summary:** one row per section: status, tests, passed, failed, skipped,
   duration, start; each links to its section.
3. **Setup: Cleanup**, **Setup: Install** (when run in this run): one entry per
   sub-step (each cleanup FVT, each `domain-init.sh --cleanup`, `omnia.sh -s`,
   each suite's requirements ...). configure and the credentials are not
   reported.
4. **Stage 1: Initialization**, **Stage 2: Prepare BuildStream**, **Stage 3:
   Build and Deploy**, **Stage 4: Cadence**, **Stage 5: Automatic Cleanup**: one
   entry per SVT test.

Each entry opens to show:

- **Command:** the FVT step or command it ran, and its rc;
- **FVT Results:** every test result the FVT step added to its suite's report
  (`<run folder>/fvt/`), each with its details;
- **Screen Output:** everything the step printed on the screen: the playbook
  output of an `exec` step, the test output of a `verify` step (open by
  default when the entry failed);
- **Error:** why it failed.

- **Statuses:** Passed, Failed, Skipped everywhere; a stage still running is
  Running.
- **When it is rendered:** after every cleanup and install, after every SVT
  test, at the end of every stage and in `summary`.
- **Repeated sections:** a section that runs again in the same run gets its
  own section (`install (2)`).
- **Masking:** IPs and secrets are masked in the HTML with omnia_auto's own
  redaction; credential prompts are never logged.

## Reports (gitignored)

| Path | Content |
|---|---|
| `reports/setup/<step>.log` | Output of each setup step (`configure`, `cleanup`, `install`, `creds`), appended per run; credential prompts excluded |
| `reports/setup/setup.json` | Last outcome of each step: status, time, duration, error, checksums, venv, suites installed, stale inputs, stores written |
| `reports/current_run.json` | The current run: id, theme, folder, start time, failed step, previous run |
| `<run folder>/svt_run.json` | The run id and theme the folder belongs to |
| `<run folder>/<report_name>.json`, `.html` | The SVT report of the run, see above |
| `<run folder>/fvt/` | The FVT suites' own omnia_auto reports of the run (the source of the FVT results) |
| `<run folder>/run.json` | Theme, commit, checksums, cleanup flags, setup outcomes, every stage outcome |
| `<run folder>/setup/` | Copy of `reports/setup/` taken by `initialization` |
| `<run folder>/<stage>.log`, `.progress`, `.status` | Stage output, current step, final status |
| `<run folder>/junit_<theme>_<stage>.xml`, `svt_results.json` | SVT test results |

The run folder is `<report_path>/<run_id>/` (default `reports/<run_id>/`).

## `user_inputs.yml` and the dataset generator

`user_inputs.yml` holds the values of one cluster. It uses the same key names
and indentation as the real input files, so a value goes into the same place
in the matching file.

- **Order:** one block per module: main → repo_manager → image_build_manager →
  orchestrator → build_stream.
- **MANDATORY values:** OIM identity, admin network, BuildStream and GitLab
  IPs. configure stops and lists any left empty.
- **Optional values:** `""` (or `[]`) is written as empty, so clearing a value
  in `user_inputs.yml` clears it in the input file too. A blank never changes
  a boolean, a number, a block or a list of items.
- **Paths:** `OMNIA_DATA_PATH`, `OMNIA_PROJECT_NAME` and `OMNIA_VENV_PATH` are
  not asked; they keep the values of `src/main/omnia.env`.
- **Catalog:** `main.catalog` is a number or a name of
  `./omnia.sh --list-catalogs` (`""` = the default catalog). configure checks
  it and records the name; install then runs
  `./omnia.sh --select-catalog <name>`, which copies it to `CATALOG_FILE_PATH`
  of `omnia.env` (and keeps a backup of the previous one).
- **PXE mapping:** the CSV keeps its header line; all its rows are replaced by
  `row1`, `row2`, ...
- **VAST:** without a VAST `source`, the generator comments out the whole
  `vast_storage` mount and `vast_storage_name` (the product then skips VAST),
  and does not merge the `vast_storage` item of `user_inputs.yml`. Giving a
  source restores them.

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
├── build_stream_test_config.yml the theme's settings: FVT overrides, cleanup flags, report
├── setup_env.sh, _setup.py      prepare the OIM: configure, cleanup, install, credentials, status
├── run_validation.sh, _run.py   SVT runner: svt_<theme> list | <stage> | all
├── requirements.txt             SVT .venv: pytest, pytest-order, PyYAML, ruamel.yaml, omnia_auto
├── conftest.py, pytest.ini      markers (theme and stage), results for summary
├── dataset_generator/           user_inputs.yml -> src inputs (profiles/<theme>.yml)
├── library/
│   ├── vars/                    common_vars (every path and file name), theme_vars (themes,
│   │                            stages, FVT settings, cleanup flags, credential stores),
│   │                            domain_vars, test_case_vars (each SVT test: stage, FVT step)
│   ├── messages/svt_msgs.py     stage, setup and config text with HOW TO FIX
│   └── functions/               setup_func (setup steps, readiness), cleanup_func (cleanup),
│                                svt_report_func (the SVT report), status_func (status box),
│                                config_func (<theme>_test_config.yml), run_func (the run),
│                                omnia_func (omnia.env checks), stage_func (stages, manifest),
│                                fvt_func (FVT bridge), test_func (one SVT test),
│                                process_func (no-shell runner)
├── svt/build_stream/            one test file per stage
├── pipelines/                   GitLab project templates (not maintained for this flow)
└── reports/                     setup and run files (gitignored)
```

## Adding a theme, a stage or a test

1. **Theme data:** add the theme to `library/vars/theme_vars.py`: description,
   profile, cleanup steps, suites to install (`fvt_domains`), credential
   domains, its stages and its `fvt_settings` (theme block -> FVT
   test_config keys), and `<theme>_test_config.yml` next to this README.
2. **Inputs:** add `dataset_generator/profiles/<theme>.yml`.
3. **Test:** add its ID, title, order, stage and FVT step to
   `library/vars/test_case_vars.py`, and its test function in
   `svt/<theme>/test_<stage>.py` (`run_svt_test(theme, name)`).

## Local checks (same as the GitHub workflows)

```bash
cd <repository root>
find test/system_test -name '*.py' ! -name '__init__.py' ! -path '*/.venv/*' -print0 \
  | xargs -0 -n1 env PYTHONPATH=.:./src/build_stream pylint      # each file >= 8
bandit -r test/system_test -ll -ii -x '*/.venv/*'
find test/system_test -name '*.sh' ! -path '*/.venv/*' -print0 | xargs -0 shellcheck -f gcc
ansible-lint --config=.config/ansible-lint.yml test/system_test/user_inputs.yml \
  test/system_test/build_stream_test_config.yml
```
