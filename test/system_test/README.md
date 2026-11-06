# Omnia System Verification (SVT)

`test/system_test` is the integration test of Omnia on one OIM. You choose a
**theme** (today `build_stream`, the default): its settings are
`<theme>_test_config.yml` (`build_stream_test_config.yml`). You fill the
cluster values in `user_inputs.yml`. Then two commands do everything:

```bash
./setup_env.sh                            # configure (new run) -> install -> credentials
./run_validation.sh svt_build_stream all  # initialization -> the theme's stages -> summary
```

- **`./setup_env.sh`** ([SETUP.md](SETUP.md)): starts a run, loads your values into the Omnia inputs
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

## `build_stream_test_config.yml` (the theme's settings)

`./setup_env.sh --configure` writes the `build_stream` block and the cleanup
flags into the FVT suites' `test/<suite>/test_config.yml`, so they override
the suites' own values. A change here needs a new `--configure` (a new run).

| Key | Default | Effect |
|---|---|---|
| `build_stream.catalog` | `29` | Catalog the build_deploy stage commits as `catalog_rhel.json` (FVT `installation.catalog`): a number of `./omnia.sh --list-catalogs` or an absolute path |
| `build_stream.cadence_catalog` | `29` | Catalog the cadence stage uploads (FVT `installation.cadence_catalog`); `""` = the same as catalog |
| `build_stream.allow_pipeline_cancel` | `true` | Cancel GitLab pipelines still running before a commit or trigger (FVT `pipeline.allow_pipeline_cancel`); `false`: the test fails and lists them |
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
  for `yes` unless `--yes`. install rewrites a different `/etc/omnia/omnia.env`, and with `--yes`
  overwrites the runtime inputs.
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
  - a step or stage of the run failed or was interrupted, or a section of the
    run's SVT report failed. Results other processes write into the FVT report
    (a suite run by hand, the BuildStream validate stage) do not count;
  - another SVT step holds the lock (see below).
- **One step at a time (`reports/svt.lock`):** every `./setup_env.sh` action and
  `./run_validation.sh` stage holds the lock (pid, step, run, heartbeat every
  30 s). A second step is refused while the holder lives. A lock whose process
  is gone, or whose heartbeat is older than 10 minutes, is stale: its step is
  recorded as interrupted (the run is failed at `<step> (interrupted)`, history
  in `reports/interrupted.json`) and the lock is taken. Ctrl-C is recorded as
  a failed step. Other test processes on the OIM (an FVT run by hand, an
  ansible-playbook of another checkout) are listed as a warning when a step
  starts. `--status` shows the lock.
- **Settings drift:** before every step and stage the run's settings (cleanup
  flags, FVT settings, report path and run id) are written into the suites'
  `test_config.yml` again when they no longer match (a hand edit, a git
  checkout); the changed values are printed.
- **After a failure, two ways on:**
  - **Retry in the same run (`--retry`):** fix the cause, then run the failed
    step again. Never edit `current_run.json` or the report by hand.
    ```bash
    ./run_validation.sh svt_build_stream prepare_build_stream --retry   # that stage again
    ./run_validation.sh svt_build_stream all --retry     # resume at the first stage that did not pass
    ./setup_env.sh --retry                  # resume the setup at the step that failed
    ./setup_env.sh --install --retry        # one setup step again (also after Ctrl-C)
    ```
    `--retry` works when the run failed (or was interrupted) at one of the
    steps the command runs; another failed step is refused and named. The
    failure is cleared (kept in `retries` of `current_run.json`) and the new
    attempt takes the failed section's place in the report: **one section per
    stage**, with `(attempt 2)` in its title and the earlier attempts listed
    in it (status, steps, duration, failed steps). The stage log keeps every
    attempt (it is appended to). `setup_env.sh --retry` with no action skips
    configure and the steps this run already passed, so a clean reinstall is
    not repeated.
  - **A new run (`./setup_env.sh --configure`):** a new id and folder. The
    installation, the test requirements and the credential stores are kept, so
    `./run_validation.sh svt_<theme> all` can follow directly. The new run's
    report names the previous run and its state.
- **`summary` always runs** (also on a failed run): it re-renders the report
  and fails when anything in the run failed.
- **A fixed `report.run_id`** reuses its folder only for the same theme;
  configure fails when the folder belongs to another theme.

## The SVT report

One report per run: `<run folder>/<report_name>.json` and `.html`, in the SVT's
own format: the data in `library/functions/svt_report_func.py`, the page in
`library/functions/svt_report_html.py` (self-contained, the look of the
omnia_auto FVT report, light/dark). Top to bottom:

1. **Header:** the theme name (`THEMES[theme]["title"]`, build_stream:
   *BuildStream End-to-End Lifecycle*), the theme id and description, run id,
   OIM, commit.
2. **Overall banner:** PASSED, PASSED SO FAR, FAILED or RUNNING, with the
   stages run of those planned and the run state.
3. **Cards:** stages, SVT steps, and the SVT steps passed / failed / skipped
   (click to filter), pass rate, duration. The counts are SVT steps; FVT test
   counts are shown only inside the step that ran them, so a stage's numbers
   always agree with its status.
4. **Run Details** and **Stage Overview.** Run Details lists the theme, run,
   state, previous run, then the **Git Clone URL**, **Branch** and **Commit**
   of the tested checkout, each a link to the repository page (GitHub
   `/tree/<branch>` and `/commit/<sha>`, GitLab `/-/tree`, `/-/commit`). A
   credential embedded in the clone URL (the user and token before the host) is
   removed, and an address that is an IP is shown masked and not linked. Stage Overview has one row per
   stage: status, SVT steps, passed, failed, skipped, pass rate, duration;
   stages not run yet are listed.
5. **Stage Details:** one collapsible block per stage (open when it failed or
   runs). **Stage 1: Initialization** holds the phases *Cleanup* and *Install*
   (when `./setup_env.sh` ran them in this run; one entry per sub-step: each
   cleanup FVT, `omnia.sh -s`, each suite's requirements) and *Readiness* (the
   checks). The theme stages follow, one entry per SVT test. configure and the
   credentials are not reported.

Each SVT step opens (like an FVT report block) to:

- **Header chips:** the FVT suite, tag and action (`EXEC`, `VERIFY`, `TEST`)
  and its options; the counts of the FVT tests that step ran
  (`FVT tests: n passed ...`) and its duration;
- **Command** and its rc, the **Error** when it failed;
- **FVT results:** the same table as the FVT report: `[TC ID] test`, module,
  status, duration; a row opens to its details and error;
- **Screen Output:** everything the step printed (playbook output of `exec`,
  test output of `verify`), open when the step failed.

Search, status filter and expand/collapse all work on steps and FVT tests.

**Stage outputs and product state** (theme `state_probe`, build_stream: the
image groups and their jobs in `build_stream_db`, read-only): the rows a stage
created or changed are its *Stage outputs* (also in `run.json` and the stage
log), so a rerun can be traced to its image group and job. `summary` adds
*Product State at Summary*: the rows created in this run and those left in a
status a run should not leave (build_stream: BUILT/FAILED groups, jobs still
IN_PROGRESS). It is reported only and never fails the run.

**Large output:** the HTML shows the last 200,000 characters of a step's
output (the JSON keeps more; the stage and setup logs keep everything).

**Which FVT results a step shows:** each FVT step runs with its own
`OMNIA_RESULTS_FILE` (omnia_auto exports every session's results there), so
exactly the tests that step ran are shown; their details come from the suite's
FVT report. Results another process writes into the same FVT report (a suite
run by hand, the BuildStream validate stage) are never shown under a step.
`<tag> test` steps (cleanup) fall back to the results added to the FVT report.

- **Statuses:** Passed, Failed, Skipped everywhere; a stage still running is
  Running.
- **When it is rendered:** after every cleanup and install, after every SVT
  test, at the end of every stage and in `summary`.
- **Repeated sections:** a section that runs again in the same run (a
  `--retry`) replaces the earlier one: one section per stage, titled
  `(attempt N)`, with the earlier attempts listed in it.
- **Masking:** IPs and secrets are masked in the HTML with omnia_auto's own
  redaction; credential prompts are never logged.

## Reports (gitignored)

| Path | Content |
|---|---|
| `reports/setup/<step>.log` | Output of each setup step (`configure`, `cleanup`, `install`, `creds`), appended per run; credential prompts excluded |
| `reports/setup/setup.json` | Last outcome of each step: status, time, duration, error, checksums, venv, suites installed, stale inputs, stores written |
| `reports/current_run.json` | The current run: id, theme, folder, start time, failed step, previous run |
| `reports/svt.lock`, `reports/interrupted.json` | The step running now (pid, heartbeat); steps found interrupted |
| `<run folder>/svt_run.json` | The run id and theme the folder belongs to |
| `<run folder>/<report_name>.json`, `.html` | The SVT report of the run, see above |
| `<run folder>/fvt/` | The FVT suites' own omnia_auto reports of the run (the source of the FVT results) |
| `<run folder>/run.json` | Theme, commit, checksums, cleanup flags, setup outcomes, every stage outcome |
| `<run folder>/setup/` | Copy of `reports/setup/` taken by `initialization` |
| `<run folder>/<stage>.log`, `.progress`, `.status` | Stage output, current step, final status |
| `<run folder>/junit_<theme>_<stage>.xml`, `svt_results.json` | SVT test results |

The run folder is `<report_path>/<run_id>/` (default `reports/<run_id>/`).

## Directory structure

```text
test/system_test/
├── README.md                    this file
├── SETUP.md                     setup_env.sh, user_inputs.yml and the dataset generator
├── build_stream_test_config.yml the theme's settings: FVT overrides, cleanup flags, report
├── run_validation.sh, _run.py   SVT runner: svt_<theme> list | <stage> | all
├── requirements.txt             SVT .venv: pytest, pytest-order, PyYAML, ruamel.yaml, omnia_auto
├── conftest.py, pytest.ini      markers (theme and stage), results for summary
├── dataset_generator/           dataset_edit.py: the comment-preserving YAML edit of config_func
├── library/
│   ├── vars/                    common_vars (every path and file name), theme_vars (themes,
│   │                            stages, FVT settings, cleanup flags, credential stores),
│   │                            domain_vars, test_case_vars (each SVT test: stage, FVT step)
│   ├── messages/svt_msgs.py     stage, setup and config text with HOW TO FIX
│   └── functions/               readiness_func (setup record, readiness checks),
│                                svt_report_func (the SVT report data), svt_report_html (its
│                                page), config_func (<theme>_test_config.yml), run_func (the
│                                run), state_func and lock_func (run state, one step at a
│                                time), omnia_func (omnia.env checks), stage_func (stages,
│                                manifest), fvt_func (FVT bridge), test_func (one SVT test),
│                                process_func (no-shell runner)
├── svt/test_svt.py              every SVT test, generated from test_case_vars.py
└── reports/                     setup and run files (gitignored)
```

## Adding a theme, a stage or a test

1. **Theme data:** add the theme to `library/vars/theme_vars.py`: `title`
   (the theme name in the report and the email), description, profile,
   cleanup steps, suites to install (`fvt_domains`), credential domains, its
   stages, `stage_info` (title and description of each stage) and its
   `fvt_settings` (theme block -> FVT test_config keys), and
   `<theme>_test_config.yml` next to this README.
2. **Inputs:** add `dataset_generator/profiles/<theme>.yml`.
3. **Test:** add its ID, title, order, stage and FVT step to
   `library/vars/test_case_vars.py` (key `<theme>_<name>`). `svt/test_svt.py`
   generates the test (markers theme and stage, the order); no test function
   to write.
4. **Optional:** `creds_suite`, `cleanup_requires` (a cleanup step that runs
   only when a file exists) and `state_probe` (read-only product state: each
   stage's outputs and what the run left behind) in the theme entry.

## Local checks (same as the GitHub workflows)

```bash
cd <repository root>
find test/system_test -name '*.py' ! -name '__init__.py' ! -path '*/.venv/*' -print0 \
  | xargs -0 -n1 env PYTHONPATH=.:./src/build_stream pylint      # each file >= 8
bandit -r test/system_test -ll -ii -x '*/.venv/*'
find test/system_test -name '*.sh' ! -path '*/.venv/*' -print0 | xargs -0 shellcheck -f gcc
ansible-lint --config=.config/ansible-lint.yml test/system_test/build_stream_test_config.yml
```
