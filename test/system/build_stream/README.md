# BuildStream System Test — Test Automation

End-to-end integration suite for BuildStream on one Omnia OIM. It drives the
real product entry points in lifecycle order and verifies each result against
the live system: containers and services, `build_stream_db`, GitLab, S3 and
the domain data paths.

```text
prepare_base -> installation (build -> deploy -> cadence) -> auto_cleanup -> cleanup
```

Every test carries the `br_86010` marker: the suite is the automated
evidence for the SysQA system test plan TEST-BR-86010 (NERSC Backend
Buildstream). The registry maps each case to its plan case.

The suite uses the shared `omnia_auto` package for the OIM connection,
streamed command execution, structured logging and JSON/HTML reports.

## Safety model

Each scenario follows the module FVT shape: a precheck, the entry point,
then verification suites. The runner separates execution from verification:

| Command | Behavior |
|---|---|
| `exec` | The scenario's `deploy`-marked tests: its precheck, then its entry point (omnia.sh, a playbook or a cleanup pass) |
| `verify` | The scenario's verification suites against the live system; no entry point runs |
| `test` | `exec`, then `verify` only if execution succeeded |

The precheck changes nothing. When it does not pass, the rest of the
scenario is skipped, so a long entry point never starts on a host that
cannot finish it. The installation pipeline suites are verification of the
installed BuildStream: with an empty `pipeline.<name>_job_id` they commit to
GitLab and trigger the pipeline (deploy reboots nodes); set the job ID to
verify an existing run only.

An untagged run covers `prepare_base` and `installation`. `auto_cleanup`
(deletes eligible image groups) and `cleanup` (removes every domain) run only
when selected by name. Without the runner, `deploy` tests are skipped unless
`OMNIA_COMMAND_TYPE=exec` is set or `--marker` selects them.

Playbooks, `omnia.sh` and pipeline stages run without a timeout.

## Prerequisites

| Requirement | Expectation |
|---|---|
| Python | 3.12 or later (`python3 -m venv` available) |
| Target | An Omnia OIM with `/etc/omnia/omnia.env` configured |
| Remote mode | SSH access to the OIM (`oim_server_ip` in `test_config.yml`) |
| Credentials | The four domain stores (see [docs/test_creds.md](docs/test_creds.md)) |

Runtime locations are read from `omnia.env` on the target: `OMNIA_DATA_PATH`,
`OMNIA_PROJECT_NAME`, `CATALOG_FILE_PATH` and the optional
`<DOMAIN>_DATA_PATH` overrides.

## Quick start

```bash
cd test/system/build_stream

# Environment and credentials
./setup_env.sh --venv
source .venv/bin/activate
./setup_env.sh --set-domain-creds          # repo_manager, image_build_manager,
                                           # orchestrator, build_stream
./setup_env.sh --set-creds                 # only for remote mode (oim_server_ip)
./setup_env.sh                             # credential status

# Review test_config.yml (catalog, job IDs, cleanup flags), then:
./run_validation.sh e2e_build_stream list
./run_validation.sh e2e_build_stream test                       # prepare_base + installation
./run_validation.sh e2e_build_stream installation test --suite cadence
./run_validation.sh e2e_build_stream installation verify --suite build
./run_validation.sh e2e_build_stream auto_cleanup test
./run_validation.sh e2e_build_stream cleanup test               # destructive
./run_validation.sh --config                                    # test_run_config.yml batch
```

`--marker` filters tests (`+` AND, `,` OR), for example `--marker sanity`,
`--marker br_86010` or `--marker pipeline+cadence`.

## Layout

| Path | Contents |
|---|---|
| `e2e/` | Scenarios and test cases — see [e2e/README.md](e2e/README.md) |
| `library/functions/` | Reusable behavior (prechecks, execution, monitoring, verification) |
| `library/vars/` | Constants, command and SQL templates, test-case registry, runner config |
| `library/messages/` | Log and assertion messages |
| `utility/domain_credentials.py` | Domain credential store helper used by `setup_env.sh` |
| `conftest.py` | omnia_auto setup, `--marker`, deploy gating, global order, reports |
| `test_config.yml` | Non-secret settings — [docs/test_config.md](docs/test_config.md) |
| `test_run_config.yml` | Batch runs — [docs/test_run_config.md](docs/test_run_config.md) |
| `setup_env.sh` | Dependencies and credentials — [docs/test_creds.md](docs/test_creds.md) |
| `run_validation.sh`, `_run.py` | Validation runner (`e2e_build_stream` category) |
| `reports/state/` | Exec facts read by the auto_cleanup and cleanup verification (git-ignored) |

## Ordering

Tests are sorted by `@pytest.mark.order(n)` across the whole suite, one band
per scenario: `prepare_base` 1000, `installation` 2000, `auto_cleanup` 3000,
`cleanup` 4000. Inside a band: +1 precheck, +2 entry point, +100 per
verification suite (installation: health 2101, repository 2201, build 2301,
deploy 2401, cadence 2501).

## Reports

Each run writes `<report_path>/<report_name>.json` and `.html` (default
`/opt/omnia/reports/system_build_stream_report.*`) and prints a summary
table with the test-case IDs. Runner logs go to `reports/logs/`.
