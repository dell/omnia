# BuildStream System Verification Test (SVT)

System verification suite for BuildStream on one Omnia OIM. It runs the real
product entry points in lifecycle order and checks each result on the live
system: containers and services, `build_stream_db`, GitLab, S3 and the
domain data paths.

```text
prepare_base -> installation -> auto_cleanup -> cleanup
                (install -> build -> deploy -> cadence -> cadence disable/re-enable)
```

Every test carries the `br_86010` marker: the suite is the automated
evidence for the system test plan TEST-BR-86010 (NERSC Backend Buildstream).
The shared `omnia_auto` package provides the OIM connection, streamed command
execution, structured logging and the JSON/HTML reports.

## Before you start

| Requirement | Expectation |
|---|---|
| Python | 3.12 or later, with `python3 -m venv` |
| Target | An Omnia OIM with `/etc/omnia/omnia.env` set up (`./omnia.sh --setup-venv`) |
| Remote mode | SSH access to the OIM (`oim_server_ip` in `test_config.yml`) |
| Credentials | The four domain credential stores ([docs/test_creds.md](docs/test_creds.md)) |
| Repository URLs | The repo_manager inputs list a URL for every repository the selected catalog uses |

## 1. Set up

```bash
cd test/system/build_stream
./setup_env.sh --venv                 # create .venv and install the dependencies
source .venv/bin/activate
./setup_env.sh --set-domain-creds     # repo_manager, image_build_manager, orchestrator, build_stream
./setup_env.sh --set-creds            # only for remote mode (oim_server_ip set)
./setup_env.sh                        # show the credential status
```

## 2. Configure

Edit `test_config.yml`. The most important settings are:

| Setting | Default | What it does |
|---|---|---|
| `installation.catalog` | `29` | Catalog to install and commit: a number from `./omnia.sh --list-catalogs` or the full path of your own catalog |
| `pipeline.<name>_job_id` | `""` | Empty triggers the pipeline; a job UUID only verifies that job |
| `cleanup.*.enabled` | `true` | Which domains the cleanup scenario removes |
| `continue_on_failure` | `false` | `false` stops at the first failure; `true` keeps running independent tests |
| `debug_mode` | `false` | `true` streams every pipeline stage and cadence log live |

All settings are described in [docs/test_config.md](docs/test_config.md).

## 3. Run

```bash
./run_validation.sh --help                                         # commands and options
./run_validation.sh svt_build_stream list                          # scenarios and test case IDs
./run_validation.sh svt_build_stream test                          # full flow, every test
./run_validation.sh svt_build_stream installation test             # one scenario
./run_validation.sh svt_build_stream installation verify --marker cadence   # cadence tests only
./run_validation.sh svt_build_stream installation verify --suite build      # one suite
./run_validation.sh --config                                       # batch from test_run_config.yml
```

| Command | What runs |
|---|---|
| `exec` | The scenario's precheck (`E001`) and entry point (`E002`): `omnia.sh`, a playbook or a cleanup pass |
| `verify` | The scenario's verification cases (`V…`) against the live system |
| `test` | `exec`, then `verify` |

The full flow ends with `cleanup`, which **removes every domain enabled under
`cleanup` in `test_config.yml`**. Run single scenarios when you want to keep
the deployment.

Batch runs are described in [docs/test_run_config.md](docs/test_run_config.md).

## Failure handling

| Case | Behaviour |
|---|---|
| A scenario precheck (`E001`) fails | The rest of that scenario is skipped; the long entry point never starts |
| A scenario entry point (`E002`) fails | That scenario's verification is skipped (it depends on the execution) |
| The build pipeline test fails | The deploy pipeline test is skipped (it deploys the image group the build makes) |
| `continue_on_failure: false` | Every remaining test is skipped after the first failure |
| `continue_on_failure: true` | Independent tests keep running (other scenarios, the cadence tests); dependent ones above are still skipped |

Every skip prints its full reason.

## Test cases

IDs are `BSM_SVT_<SCENARIO>_<E|V><NUMBER>`: `E` runs a product entry point,
`V` verifies the result. The full table, with pass criteria and the BR-86010
plan cases, is in [svt/README.md](svt/README.md).

## Reports

Each run writes `<report_path>/<report_name>.json` and `.html` (default
`/opt/omnia/reports/system_build_stream_report.*`) and prints a summary table
with the test case IDs. Runner logs go to `reports/logs/`.

## Layout

| Path | Contents |
|---|---|
| `svt/` | Scenarios and test cases — [svt/README.md](svt/README.md) |
| `library/` | Functions, constants, test case registry and messages — [library/README.md](library/README.md) |
| `docs/` | [test_config.md](docs/test_config.md), [test_run_config.md](docs/test_run_config.md), [test_creds.md](docs/test_creds.md) |
| `utility/svt_runner.py` | The SVT validation runner (help, list, full flow, batch) |
| `utility/domain_credentials.py` | Domain credential store helper used by `setup_env.sh` |
| `conftest.py` | omnia_auto setup, `--marker`, dependency gates, `continue_on_failure`, ordering, reports |
| `setup_env.sh` | Dependencies and credentials |
| `run_validation.sh`, `_run.py` | Runner entry points (category `svt_build_stream`) |
| `test_config.yml`, `test_run_config.yml` | Settings and batch selection |
| `reports/` | Reports, runner logs and exec state (git-ignored) |
