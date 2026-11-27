# Omnia System Verification (SVT)

`test/system_test` is the integration test of Omnia on one OIM. You choose a
**theme** (`build_stream`, the default; `catalog_build`; `cluster_lifecycle`; `observability`:
iDRAC and LDMS telemetry, see [below](#theme-observability)): its settings are
`<theme>_test_config.yml` (`build_stream_test_config.yml`). The cleanup (the same for every theme)
and OpenBao are blocks of `user_inputs.yml`, where you also fill the cluster values. Then two
commands do everything:

```bash
./setup_env.sh                            # configure (new run) -> install -> credentials
./run_validation.sh svt_build_stream all  # initialization -> the theme's stages -> summary
```

**Several themes in one GitLab pipeline:** list them per cluster, for example
`themes: "catalog_build,build_stream"` in `pipeline/svt_pipeline_config.yml`. They run one after
another (the next theme runs whether the previous passed or failed) in one pipeline with a single
`preflight`, `initialization` and `summary`; each theme opens as its own nested pipeline, and the
report has an index and a page per theme with Previous / Next links. `build_stream` starts from
scratch (its own `clean_install` job) and must be the last theme. See
[docs/PIPELINE.md](docs/PIPELINE.md) for the diagram.

- **`./setup_env.sh`** ([docs/SETUP.md](docs/SETUP.md)): starts a run, loads your values into the Omnia inputs
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
| `test/orchestrator`, `test/discovery`, `test/image_build_manager`, `test/repo_manager`, `test/telemetry` | their `cleanup` tag (discovery and telemetry only when they hold deployed state); their test requirements in the Omnia venv |
| `test/build_stream` | `prepare_base`, `precheck`, `prepare`, `execute` (exec and verify), `cleanup`; its `setup_env.sh` writes every domain credential store |

## Quick start (on the OIM, as root)

```bash
cd test/system_test
${EDITOR:-vi} user_inputs.yml                # cluster values (MANDATORY ones marked), the cleanup and OpenBao blocks (shared by every theme)
${EDITOR:-vi} build_stream_test_config.yml   # catalog, cadence catalog, pipeline cancel

./setup_env.sh                       # configure (new run), install, prompt the missing credentials
./setup_env.sh --status              # the run, the steps and the readiness checks, in a box
./run_validation.sh svt_build_stream all
```

Optional inputs, all in `user_inputs.yml` (see [docs/SETUP.md](docs/SETUP.md)):

- **PowerVault:** `orchestrator.storage_config.powervault_config`: give `ip` (a list or comma
  separated), `iscsi_initiator` and `volume_id`; the other keys are defaults. Without an `ip`
  there is no PowerVault.
- **PowerScale CSI:** `enable_powerscale_csi: true` in `omnia_config`, with `secret.yaml` and
  `values.yaml` edited for your array next to `user_inputs.yml` (the pipeline seeds them from the
  product's reference examples). They are copied to the paths of `omnia_config.yml`
  (default: the orchestrator's project input folder, written from `$ORCHESTRATOR_DATA_PATH` and
  `$OMNIA_PROJECT_NAME`) by the last step of `./setup_env.sh`, or by `./setup_env.sh --stage-files`,
  only when it is true; then both files must exist.
- **Another inputs file:** in the GitLab pipeline each cluster picks its file with the variable
  `<CLUSTER>_SVT_USER_INPUTS` (default `user_inputs.yml`); by hand, `dataset_generator/generate_dataset.py
  --inputs <file>` fills the `src` inputs from any file with the same syntax.

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

## Stages and test cases

Every SVT test runs one FVT step of `test/build_stream`: `exec` runs the playbook,
`verify` runs its verification tests. Within a stage, once a test fails, the later
tests of the stage are skipped (they need what it set up).
`./run_validation.sh svt_build_stream list` prints them. IDs are
`SVT_BUILD_STREAM_<NNN>`; `001`-`003` were the former whole-case tests and are not reused.

| Stage | ID | What it verifies | FVT step it runs |
|---|---|---|---|
| `initialization` | | The OIM is ready: inputs configured and installed, test requirements in the Omnia venv, every credential store present (one report entry per check) | `./setup_env.sh --status` checks |
| `prepare_build_stream` | `004` | `./omnia.sh --prepare-base` for repo_manager, image_build_manager, orchestrator | `prepare_base exec` |
| | `005` | Base domains prepared | `prepare_base verify` |
| | `006` | `build_stream.yml --tags precheck` | `precheck exec` |
| | `007` | Precheck results | `precheck verify` |
| | `008` | `build_stream.yml --tags prepare` (Postgres, API, playbook watcher) | `prepare exec` |
| | `009` | BuildStream prepared | `prepare verify` |
| | `010` | `build_stream.yml --tags execute` (GitLab server, runner, project) | `execute exec` |
| | `011`-`013` | GitLab server, runner and project are up | `execute verify --suite gitlab_server`, `gitlab_runner`, `gitlab_project` |
| `build_deploy` | `014` | The automatic build pipeline builds an image, then the deploy pipeline deploys it | `execute verify --marker automatic_execution` |
| `cadence` | `015` | A new build, one cadence cycle and the cadence pipeline (sanity set; the disable / re-enable and artifact cases are not run) | `execute verify --suite cadence --marker sanity` |
| `automatic_cleanup` | `016` | The automatic cleanup of the cadence image: marked FAILED, one cleanup_cron pass, S3, registry and NFS checked | `execute verify --suite auto_cleanup` |
| `summary` | | Prints the run, renders the report, fails when anything in the run failed (runs on a failed run too) | |

The tests are data in [`library/vars/test_case_vars.py`](library/vars/test_case_vars.py);
`svt/test_svt.py` generates one pytest test per entry.

## Theme observability

Telemetry (observability) of a **deployed** cluster: the iDRAC and LDMS sources are
deployed with the product command `./omnia.sh -r telemetry`, then checked with the
telemetry FVT tests selected by suite and marker. Every source but iDRAC and LDMS is off
(`telemetry` block of `user_inputs.yml`).

```bash
./setup_env.sh --theme observability           # configure, install (no cleanup), credentials
./run_validation.sh svt_observability all       # initialization -> observability stages -> summary
./run_validation.sh svt_observability all --skip-stages none   # also build the cluster first
```

Two kinds of SVT test:

- **RUN**: `./omnia.sh --prepare-base` or `./omnia.sh -r <domain> [--tags <tag>]`, as a
  customer runs it (allowed commands: `OMNIA_RUN_TAGS` in `library/vars/theme_vars.py`).
- **VERIFY**: one FVT step, selected by suite and marker like build_stream (for example
  `--suite sources --marker idrac+sanity`). The step passes when its exit status is 0.

| Stage | Type | ID | Step | FVT test cases |
|---|---|---|---|---|
| `prepare_base` | hard, **skipped by default** | `001`-`004` | `./omnia.sh --prepare-base`; repo_manager, image_build_manager, orchestrator `prepare verify --marker sanity` | |
| `repo_sync` | hard, **skipped by default** | `005`-`006` | `./omnia.sh -r repo_manager --tags execute`; `execute verify` | |
| `image_build` | hard, **skipped by default** | `007`-`008` | `./omnia.sh -r image_build_manager --tags build`; `build verify` | |
| `cluster_deploy` | hard, **skipped by default** | `009`-`013` | `./omnia.sh -r orchestrator --tags provision`, `--tags pxeboot`; provision, Kubernetes and Slurm cluster checks | |
| `observability_cleanup` | soft, **off by default** (`stages:` in `observability_test_config.yml`) | `014`-`017` | `./omnia.sh -r telemetry --tags cleanup_ldms`, `cleanup_idrac` | `TEL_FVT_CLEANUP_V007`, `V006` |
| `observability_precheck` | hard | `018`-`021` | `./omnia.sh -r telemetry --tags precheck`, `--tags validate` | `TEL_FVT_PRECHECK_V001`-`V003`, `TEL_FVT_VALIDATE_V001` |
| `observability_deploy` | hard | `022`-`023` | `./omnia.sh -r telemetry` | `TEL_FVT_DEPLOY_V001`-`V008`, `V110` |
| `observability_idrac` | soft | `024`-`025` | readiness, then data flow | `V010`, `V011`, `V012`, `V016`, `V017`, `V112`, `V113`; `V013`, `V014`, `V015`, `V018` |
| `observability_ldms` | soft | `026`-`027` | readiness, then data flow | `V020`, `V021`, `V022`, `V026`; `V023`-`V025`, `V027`, `V028`, `V029` |

IDs are `SVT_OBSERVABILITY_<NNN>`; FVT IDs `V0xx`/`V1xx` are `TEL_FVT_DEPLOY_V0xx`.

**Defaults** (theme data): `./run_validation.sh svt_observability all` leaves out
`prepare_base`, `repo_sync`, `image_build` and `cluster_deploy` (recorded as skipped;
`--skip-stages none` runs them, a single stage runs with `./run_validation.sh
svt_observability <stage>`), and `./setup_env.sh` cleans nothing without `--force`. In the
pipeline, an empty `skip_stages` and `clean_reinstall` of the cluster block give the same
defaults (`skip_stages: "none"` runs every stage). The telemetry credential store
(`telemetry_credentials.yml`: BMC, MySQL and LDMS sampler) is written by
`test/telemetry/setup_env.sh`; the OpenBao secret is `<secret_path>/telemetry`
([OPENBAO.md](docs/OPENBAO.md)).

## Theme catalog_build

For every catalog, one at a time: `./omnia.sh --select-catalog <catalog>`, then the
repo_manager and image_build_manager FVT steps (no orchestrator deploy, no PXE boot).
User guide: [`docs/CATALOG_BUILD.md`](docs/CATALOG_BUILD.md). Settings:
[`catalog_build_test_config.yml`](catalog_build_test_config.yml); design:
[`docs/CATALOG_BUILD_DESIGN.md`](docs/CATALOG_BUILD_DESIGN.md).

```bash
./setup_env.sh --theme catalog_build            # configure (freezes the catalog plan) -> install -> creds
./setup_env.sh --theme catalog_build --force    # cleanup first (deletes OMNIA_DATA_PATH)
./run_validation.sh svt_catalog_build list      # the catalog stages and their tests
./run_validation.sh svt_catalog_build all       # every catalog stage, then summary
./run_validation.sh svt_catalog_build all --start-stage catalog_02
./run_validation.sh svt_catalog_build all --retry
```

`--configure` resolves `catalog_build.catalogs` (`all` = the `./omnia.sh
--list-catalogs` order) into the plan of the run, `reports/catalog_build_plan.json`.
The theme's stages (`catalog_01`, `catalog_02` ...) and tests are generated from it
([`library/vars/catalog_vars.py`](library/vars/catalog_vars.py)) and run like the
build_stream tests. IDs are `SVT_CATALOG_BUILD_<catalog NN><step NN>`.

| Test of a catalog stage | What it does | Step |
|---|---|---|
| `NN00` | Put back the shared runtime inputs, apply `catalog_overrides/<catalog>/<domain>/<file>`, write `repo_config`, `caching_policy`, `repo_policies`, `force_rebuild` and `functional_groups_source: catalog` into `<OMNIA_DATA_PATH>/<domain>/input/<project>/`, then `./omnia.sh --select-catalog` | `svt select <catalog>` |
| `NN01`... | Every `steps` entry `[domain, tag]` of the theme block, as two tests | `fvt_<domain> <tag> exec`, `fvt_<domain> <tag> verify` |
| last | `cleanup_between` (`images`, `repos`, `full`); runs even after a failure | `fvt_<domain> cleanup... test` |

A catalog with an aarch64 layer is one skipped test (`NN00`, with the reason) unless
`include_aarch64: true` (needs `aarch64_inventory_host_ip` in user_inputs.yml). With
`continue_on_failure: true` every catalog stage is a soft stage: a failed catalog does
not stop the next one; the summary still fails. After a failed `exec` the orphaned
`ansible-playbook <domain>.yml` workers (and a running `dnf download`) are stopped, so
a playbook killed at the FVT timeout cannot overlap the next test.

From GitLab (`catalog_build` in `clusters.<name>.themes` of `pipeline/svt_pipeline_config.yml`) every
catalog is its own pipeline job, `catalog_01` ...; see
[docs/PIPELINE_CONFIG.md](docs/PIPELINE_CONFIG.md#theme-catalog_build-one-job-per-catalog).
How the theme compares with build_stream: [docs/CATALOG_BUILD.md](docs/CATALOG_BUILD.md).

## Documentation

| Doc | Contents |
|---|---|
| [docs/SETUP.md](docs/SETUP.md) | `./setup_env.sh` (configure, cleanup incl. NFS shares, install, credentials, PowerScale files, status), `user_inputs.yml` (PowerVault, PowerScale CSI), the dataset generator |
| [docs/TEST_CONFIG.md](docs/TEST_CONFIG.md) | Every setting of `build_stream_test_config.yml` (catalogs, the report) and the shared `cleanup` block of `user_inputs.yml` (flags per suite: telemetry, discovery, NFS shares ...) |
| [docs/CATALOG_BUILD.md](docs/CATALOG_BUILD.md) | **User guide of the `catalog_build` theme**: prerequisites, the two files to edit, step by step, every setting, reading the report, failures, the GitLab pipeline (one job per catalog), how it compares with build_stream, troubleshooting |
| [docs/RUNNER.md](docs/RUNNER.md) | `./run_validation.sh`, the run and its guard, retry, the SVT report, adding a theme, stage or test |
| [docs/OPENBAO.md](docs/OPENBAO.md) | Passwords from OpenBao: one place for its settings, the pipeline and manual ways to read them |
| [docs/PIPELINE.md](docs/PIPELINE.md) | Run the SVT from GitLab: how it works, where each secret goes, setup, **updating an existing pipeline**, troubleshooting |
| [docs/PIPELINE_CONFIG.md](docs/PIPELINE_CONFIG.md) | Every setting of `pipeline/svt_pipeline_config.yml` and the CI/CD variable it becomes |

## Directory structure

```text
test/system_test/
├── README.md                    this file: the stages and test cases
├── docs/                        SETUP.md, TEST_CONFIG.md, RUNNER.md, OPENBAO.md, PIPELINE.md,
│                                PIPELINE_CONFIG.md
├── pipeline/                    setup_svt_project.py, cleanup_svt_project.py, svt_ci.py, svt_pipeline_config.yml (GitLab); README.md
├── build_stream_test_config.yml the theme's settings: FVT overrides, report
├── observability_test_config.yml the observability theme's settings
├── user_inputs.yml              the cluster values, the cleanup and the OpenBao block (shared by every theme)
├── (secret.yaml, values.yaml)   PowerScale CSI, optional: seeded from src/orchestrator/examples/ into
│                                the cluster's folder of the GitLab project and edited there (or by
│                                hand in this folder)
├── run_validation.sh, _run.py   SVT runner: svt_<theme> list | <stage> | all
├── requirements.txt             SVT .venv: pytest, pytest-order, PyYAML, ruamel.yaml, omnia_auto
├── conftest.py, pytest.ini      markers (theme and stage), results for summary
├── dataset_generator/           user_inputs.yml -> src inputs (dataset_merge.py: the merge, PowerVault,
│                                $NAME paths; dataset_edit.py: the comment-preserving YAML edit)
├── library/
│   ├── vars/                    every constant: common_vars (paths, file names, settings keys),
│   │                            nfs_vars (NFS cleanup), report_vars (the SVT report), theme_vars
│   │                            (themes, stages, FVT settings, cleanup flags, credential stores),
│   │                            domain_vars, test_case_vars (each SVT test: stage, FVT step)
│   ├── messages/svt_msgs.py     stage, setup and config text with HOW TO FIX
│   └── functions/               nfs_func (empty the NFS shares on cleanup), openbao_func (read
│                                OpenBao), readiness_func (setup record, readiness checks),
│                                svt_report_func (the SVT report data), svt_report_html (its
│                                page), config_func (<theme>_test_config.yml), run_func (the
│                                run), state_func and lock_func (run state, one step at a
│                                time), omnia_func (omnia.env checks), stage_func (stages,
│                                manifest), fvt_func (FVT bridge), test_func (one SVT test),
│                                process_func (no-shell runner)
├── svt/test_svt.py              every SVT test, generated from test_case_vars.py
└── reports/                     setup and run files (gitignored)
```
