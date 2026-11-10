# SVT runner: settings, stages, the run and the report

Details behind the [README](../README.md): `./run_validation.sh`, the safety
model, the run, the SVT report, and how to add a theme, a stage or a test. Setup is in
[SETUP.md](SETUP.md), the theme settings in [TEST_CONFIG.md](TEST_CONFIG.md), passwords in
[OPENBAO.md](OPENBAO.md), the GitLab pipeline in [PIPELINE.md](PIPELINE.md) and
[PIPELINE_CONFIG.md](PIPELINE_CONFIG.md).

## `build_stream_test_config.yml` (the theme's settings)

Every key (catalogs, the cleanup flags per suite, the NFS shares, the report) is described in
[TEST_CONFIG.md](TEST_CONFIG.md). A change needs `./setup_env.sh --configure` (a new run).

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
  installation: BuildStream and GitLab, telemetry (when deployed), orchestrator, image_build_manager,
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
    run's SVT report failed. A failed **soft stage** (`soft_stages` of the theme:
    `build_deploy`, `cadence`, `automatic_cleanup`) does not count: the next stage
    still runs, `all` goes on after it, and the summary still fails. Results other
    processes write into the FVT report (a suite run by hand, the BuildStream
    validate stage) do not count;
  - another SVT step holds the lock (see below).
- **One step at a time (`reports/svt.flock`, `reports/svt.lock`):** every
  `./setup_env.sh` action and `./run_validation.sh` stage takes a kernel lock
  (`flock`, non-blocking) on `reports/svt.flock`, so two steps starting at the
  same instant cannot both run: one gets it, the others are refused. The owner
  describes itself in `reports/svt.lock` (pid, step, run, heartbeat every
  30 s). The kernel frees the lock when its process ends however it ends (kill,
  lost SSH session, reboot); the description it leaves behind means the step was
  interrupted, so the next step records it (the run is failed at
  `<step> (interrupted)`, history in `reports/interrupted.json`) and takes the
  lock. A clean exit removes the description first. A frozen owner
  (`kill -STOP`) keeps the lock: stop it by the pid in the message. Ctrl-C is
  recorded as a failed step. Other test processes on the OIM (an FVT run by hand, an
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
| `reports/svt.flock`, `reports/svt.lock`, `reports/interrupted.json` | The kernel lock; the step running now (pid, heartbeat); steps found interrupted |
| `<run folder>/svt_run.json` | The run id and theme the folder belongs to |
| `<run folder>/<report_name>.json`, `.html` | The SVT report of the run, see above |
| `<run folder>/fvt/` | The FVT suites' own omnia_auto reports of the run (the source of the FVT results) |
| `<run folder>/run.json` | Theme, commit, checksums, cleanup flags, setup outcomes, every stage outcome |
| `<run folder>/setup/` | Copy of `reports/setup/` taken by `initialization` |
| `<run folder>/<stage>.log`, `.progress`, `.status` | Stage output, current step, final status |
| `<run folder>/junit_<theme>_<stage>.xml`, `svt_results.json` | SVT test results (merged by test id across stages and retries) |

The run folder is `<report_path>/<run_id>/` (default `reports/<run_id>/`).

## Adding a theme, a stage or a test

1. **Theme data:** add the theme to `library/vars/theme_vars.py`: `title`
   (the theme name in the report and the email), description, profile,
   cleanup steps, suites to install (`fvt_domains`), credential domains, its
   stages, `stage_info` (title and description of each stage) and its
   `fvt_settings` (theme block -> FVT test_config keys), and
   `<theme>_test_config.yml` next to the README.
2. **Inputs:** add `dataset_generator/profiles/<theme>.yml`.
3. **Test:** add its ID, title, order, stage and FVT step to
   `library/vars/test_case_vars.py` (key `<theme>_<name>`). `svt/test_svt.py`
   generates the test (markers theme and stage, the order); no test function
   to write.
4. **Optional:** `creds_suite`, `cleanup_requires` (a cleanup step that runs
   only when any of its files or folders exists, so a half installed product is still cleaned) and `state_probe` (read-only product state: each
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
