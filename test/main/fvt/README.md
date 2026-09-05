# Test Cases — Omnia Main FVT

All test case IDs follow `MAIN_FVT_<PHASE>_<TYPE><SEQ>`, where `E` identifies
an execution test and `V` identifies a verification test. IDs are maintained
centrally in `library/vars/test_case_vars.py`.

Each result uses a concise summary plus structured key/value details. The
terminal, JSON report, and HTML report therefore expose the same test-case ID,
command or resolved path, expected result, and observed result without printing
credentials or unnecessarily dumping complete command output.

## Deploy / Verify / Cleanup Architecture

Every scenario follows a three-phase pattern:

| Phase | What it does | Marker | When it runs |
|-------|-------------|--------|--------------|
| `deploy` | **Executes** the actual omnia.sh command (setup, init, run). Changes state. | `@pytest.mark.deploy` | Step 1 |
| `verify` | **Checks results** after deploy. Read-only — inspects files, dirs, env vars. | *(no marker)* | Step 2 |
| `cleanup` | **Tears down** state (e.g. `--cleanup`). Must be explicitly requested. | `@pytest.mark.cleanup` | Explicit only |

`sanity` is reserved for positive, repeat-safe baseline checks. Negative input
and error-handling cases use `regression`; force/reinstall and extended rerun
cases use `functional` and, when they change state, `deploy`.

Aggregate execution follows the production dependency order:
`setup → init → precheck → validate → cli → omnia_cli`. Within each scenario,
`@pytest.mark.order(n)` determines the test order. Cleanup is excluded from
aggregate runs and executes only when explicitly selected.

Usage:

```bash
# Full flow: execute positive lifecycle cases once, then verify all FVTs
./run_validation.sh fvt_main test

# Verify every FVT scenario in one pytest session
./run_validation.sh fvt_main verify

# Execute and verify one scenario
./run_validation.sh fvt_main setup test

# Run cleanup explicitly (never automatic)
./run_validation.sh fvt_main cleanup exec
```

### Intelligent Skip Logic

Setup (`--setup-venv`) and cleanup (`--cleanup`) are destructive — they
modify or destroy the omnia production venv at `OMNIA_VENV_PATH`.

If the test runner is activated **from that same venv** (e.g. the user ran
`source /opt/omnia/venv/bin/activate`), these operations would destroy the
interpreter running the tests, causing a hang.

The `is_running_from_omnia_venv()` helper detects this and **automatically
skips** setup and cleanup with a clear message. When tests run with the
baremetal test installation, another active venv, or the optional test harness
venv (`test/main/.venv`), all operations execute normally.

`./setup_env.sh` installs test dependencies with `pip --user` by default. Use
`./setup_env.sh --venv` only when an isolated `test/main/.venv` is preferred.
The Omnia production venv remains owned by `omnia.sh --setup-venv`.

---

## setup (omnia.sh --setup-venv)

| TC ID | Test | Suite | Markers | Description |
|-------|------|-------|---------|-------------|
| MAIN_FVT_SETUP_E001 | `test_deploy_setup_venv` | *(root)* | deploy, sanity | Deploy omnia.sh --setup-venv --deps-only |
| MAIN_FVT_SETUP_V001 | `test_env_file_installed` | environment/ | sanity | Verify omnia.env installed at /etc/omnia/omnia.env |
| MAIN_FVT_SETUP_V002 | `test_profile_drop_in` | environment/ | sanity | Verify /etc/profile.d/omnia-env.sh exists |
| MAIN_FVT_SETUP_V003 | `test_env_vars_loaded` | environment/ | sanity | Verify environment variables are set after install |
| MAIN_FVT_SETUP_V004 | `test_env_source_validation` | environment/ | regression | Verify env source validation rejects empty SYSTEM_ADMIN_NIC_IPV4 |
| MAIN_FVT_SETUP_V005 | `test_base_dirs_created` | directories/ | sanity | Verify base directories created (.data) |
| MAIN_FVT_SETUP_V006 | `test_activate_helper` | directories/ | sanity | Verify activate-omnia.sh helper script created |
| MAIN_FVT_SETUP_V007 | `test_venv_created` | virtual_environment/ | sanity | Verify Python venv created at OMNIA_VENV_PATH |
| MAIN_FVT_SETUP_V008 | `test_ansible_available` | virtual_environment/ | sanity | Verify ansible is available in venv |
| MAIN_FVT_SETUP_V009 | `test_pip_packages_installed` | virtual_environment/ | sanity | Verify core tooling and the merged requirements from all seven domains, including version constraints |
| MAIN_FVT_SETUP_V010 | `test_galaxy_collections_installed` | virtual_environment/ | sanity | List every installed Galaxy collection with its version |
| MAIN_FVT_EXECUTION_E001 | `test_deploy_setup_deps_only` | lifecycle/ | deploy, functional | Extended dependency-only setup execution |
| MAIN_FVT_EXECUTION_V001 | `test_verify_venv_exists` | lifecycle/ | functional | Verify venv created with Ansible after extended setup |
| MAIN_FVT_EXECUTION_V002 | `test_verify_env_installed` | lifecycle/ | functional | Verify system environment files after extended setup |

---

## init (omnia.sh --init)

| TC ID | Test | Suite | Markers | Description |
|-------|------|-------|---------|-------------|
| MAIN_FVT_INIT_E001 | `test_deploy_init` | *(root)* | deploy, sanity | Deploy omnia.sh --init |
| MAIN_FVT_INIT_V001 | `test_domain_log_dirs` | domain_init/ | sanity | Verify domain log directories created (/var/log/omnia/<domain>/) |
| MAIN_FVT_INIT_V002 | `test_domain_output_dirs` | domain_init/ | sanity | Verify domain output directories created under OMNIA_DATA_PATH |
| MAIN_FVT_INIT_V003 | `test_domain_input_staged_image_build_manager` | domain_init/ | sanity | Verify input files staged for image_build_manager |
| MAIN_FVT_INIT_V004 | `test_domain_input_staged_repo_manager` | domain_init/ | sanity | Verify input files staged for repo_manager |
| MAIN_FVT_INIT_V005 | `test_domain_input_staged_orchestrator` | domain_init/ | sanity | Verify input files staged for orchestrator |
| MAIN_FVT_INIT_V006 | `test_domain_input_staged_discovery` | domain_init/ | sanity | Verify input files staged for discovery |
| MAIN_FVT_INIT_V007 | `test_init_domain_filter` | domain_init/ | deploy, functional | Verify --init with domain filter runs for single domain |
| MAIN_FVT_INIT_V008 | `test_init_force_deps` | domain_init/ | deploy, functional | Verify --init --force-deps forces reinstall |
| MAIN_FVT_EXECUTION_E002 | `test_deploy_init_domain` | lifecycle/ | deploy, functional | Extended Image Build Manager domain initialization |
| MAIN_FVT_EXECUTION_V003 | `test_verify_domain_log_dirs` | lifecycle/ | functional | Verify Image Build Manager log directory after extended init |
| MAIN_FVT_EXECUTION_V004 | `test_verify_domain_input_staged` | lifecycle/ | functional | Verify Image Build Manager inputs after extended init |

---

## cli (argument parsing and error handling)

| TC ID | Test | Suite | Markers | Description |
|-------|------|-------|---------|-------------|
| MAIN_FVT_CLI_E001 | `test_help_output` | *(root)* | deploy, sanity | Verify omnia.sh --help returns usage text |
| MAIN_FVT_CLI_V001 | `test_no_args_shows_help` | commands/ | sanity | Verify omnia.sh with no args shows help |
| MAIN_FVT_CLI_V002 | `test_run_invalid_domain` | commands/ | regression | Verify --run with invalid domain exits with error |
| MAIN_FVT_CLI_V003 | `test_run_no_domain` | commands/ | regression | Verify --run without domain exits with error |
| MAIN_FVT_CLI_V004 | `test_deps_only_in_help` | commands/ | sanity | Verify --deps-only flag appears in help output |
| MAIN_FVT_CLI_V005 | `test_unknown_option` | commands/ | regression | Verify unknown option exits with error |
| MAIN_FVT_CLI_V006 | `test_cleanup_in_help` | commands/ | sanity | Verify --cleanup flag appears in help output |
| MAIN_FVT_CLI_V007 | `test_check_deps_in_help` | commands/ | sanity | Verify --check-deps flag appears in help output |
| MAIN_FVT_CLI_V008 | `test_force_deps_in_help` | commands/ | sanity | Verify --force-deps flag appears in help output |
| MAIN_FVT_CLI_V009 | `test_skip_catalog_in_help` | commands/ | sanity | Verify --skip-catalog flag appears in help output |
| MAIN_FVT_CLI_V010 | `test_force_deps_invalid` | commands/ | regression | Verify --force-deps without -s/-i exits with error |
| MAIN_FVT_CLI_V011 | `test_check_deps_runs` | commands/ | sanity | Verify --check-deps command runs |
| MAIN_FVT_CLI_V012 | `test_skip_catalog_accepted` | commands/ | deploy, functional | Verify --setup-venv --skip-catalog --deps-only is accepted |
| MAIN_FVT_CLI_V013 | `test_skip_omnia_cli_in_help` | commands/ | sanity | Verify --skip-omnia-cli flag appears in help output |
| MAIN_FVT_CLI_V014 | `test_skip_omnia_cli_accepted` | commands/ | deploy, functional | Verify --setup-venv --skip-omnia-cli --deps-only is accepted |
| MAIN_FVT_CLI_V015 | `test_skip_in_help` | commands/ | sanity | Verify --skip flag appears in help output |
| MAIN_FVT_CLI_V016 | `test_dry_run_in_help` | commands/ | sanity | Verify --dry-run flag appears in help output |
| MAIN_FVT_CLI_V017 | `test_skip_invalid_domain` | commands/ | regression | Verify --skip with invalid domain exits with error |
| MAIN_FVT_CLI_V018 | `test_skip_with_include_error` | commands/ | regression | Verify --skip + explicit domain list is mutually exclusive |
| MAIN_FVT_CLI_V019 | `test_skip_without_init_error` | commands/ | regression | Verify --skip without -s/-i exits with error |
| MAIN_FVT_CLI_V020 | `test_skip_no_args_error` | commands/ | regression | Verify --skip without domain list exits with error |
| MAIN_FVT_CLI_V021 | `test_dry_run_output` | commands/ | sanity | Verify --dry-run shows domain list without executing |
| MAIN_FVT_CLI_V022 | `test_dry_run_with_skip` | commands/ | sanity | Verify --dry-run --skip shows filtered domain list |
| MAIN_FVT_CLI_V023 | `test_dry_run_without_init_error` | commands/ | regression | Verify --dry-run without -s/-i exits with error |

### --prepare-base tests (prepare_base/)

| TC ID | Test | Suite | Markers | Description |
|-------|------|-------|---------|-------------|
| MAIN_FVT_CLI_V024 | `test_prepare_base_in_help` | prepare_base/ | sanity | Verify --prepare-base flag appears in help output |
| MAIN_FVT_CLI_V025 | `test_prepare_base_dry_run` | prepare_base/ | sanity | Verify --prepare-base --dry-run shows domains and phases |
| MAIN_FVT_CLI_V026 | `test_prepare_base_dry_run_skip` | prepare_base/ | sanity | Verify --prepare-base --dry-run --skip filters domains |
| MAIN_FVT_CLI_V027 | `test_prepare_base_skip_invalid` | prepare_base/ | regression | Verify --prepare-base --skip with invalid domain exits with error |
| MAIN_FVT_CLI_V028 | `test_prepare_base_skip_all` | prepare_base/ | sanity | Verify --prepare-base --skip all domains shows no-op message |
| MAIN_FVT_CLI_V029 | `test_prepare_base_dry_run_phases` | prepare_base/ | sanity | Verify --prepare-base --dry-run shows all lifecycle phases (validate, credentials, prepare) |
| MAIN_FVT_CLI_V030 | `test_prepare_base_dry_run_fail_fast_note` | prepare_base/ | sanity | Verify --prepare-base --dry-run shows fail-fast note |
| MAIN_FVT_CLI_V031 | `test_prepare_base_dry_run_domain_order` | prepare_base/ | sanity | Verify --prepare-base --dry-run shows correct domain order (repo_manager -> image_build_manager -> orchestrator) |
| MAIN_FVT_CLI_V032 | `test_prepare_base_dry_run_skip_multiple` | prepare_base/ | sanity | Verify --prepare-base --dry-run --skip with 2 domains leaves only one |
| MAIN_FVT_CLI_V033 | `test_generic_tags_in_help` | tags/ | sanity | Verify omnia.sh help shows generic tags (precheck, validate, prepare, execute, cleanup) |
| MAIN_FVT_CLI_V034 | `test_execution_order_in_help` | tags/ | sanity | Verify execution order in help text |

---

## omnia_cli (omnia-cli diagnostics tool)

| TC ID | Test | Suite | Markers | Description |
|-------|------|-------|---------|-------------|
| MAIN_FVT_OMNIA_CLI_E001 | `test_cli_help_output` | *(root)* | deploy, sanity | Verify omnia-cli help returns usage text |
| MAIN_FVT_OMNIA_CLI_E002 | `test_cli_version_output` | *(root)* | deploy, sanity | Verify omnia-cli version shows release info |
| MAIN_FVT_OMNIA_CLI_V001 | `test_cli_status_runs` | diagnostics/ | sanity | Verify omnia-cli status runs successfully |
| MAIN_FVT_OMNIA_CLI_V002 | `test_cli_check_runs` | diagnostics/ | sanity | Verify omnia-cli check runs successfully |
| MAIN_FVT_OMNIA_CLI_V003 | `test_cli_status_project_flag` | diagnostics/ | sanity | Verify omnia-cli status --project flag works |
| MAIN_FVT_OMNIA_CLI_V004 | `test_cli_repo_manager` | diagnostics/ | sanity | Verify omnia-cli repo-manager runs |
| MAIN_FVT_OMNIA_CLI_V005 | `test_cli_image_build` | diagnostics/ | sanity | Verify omnia-cli image-build runs |
| MAIN_FVT_OMNIA_CLI_V006 | `test_cli_discovery_status` | diagnostics/ | sanity | Verify omnia-cli discovery runs |
| MAIN_FVT_OMNIA_CLI_V007 | `test_cli_help_repo_manager` | diagnostics/ | sanity | Verify omnia-cli help repo-manager shows domain help |
| MAIN_FVT_OMNIA_CLI_V008 | `test_cli_help_discovery` | diagnostics/ | sanity | Verify omnia-cli help discovery shows domain help |
| MAIN_FVT_OMNIA_CLI_V009 | `test_cli_orchestrator` | diagnostics/ | sanity | Verify omnia-cli orchestrator runs |
| MAIN_FVT_OMNIA_CLI_V010 | `test_cli_telemetry` | diagnostics/ | sanity | Verify omnia-cli telemetry runs |
| MAIN_FVT_OMNIA_CLI_V011 | `test_cli_build_stream` | diagnostics/ | sanity | Verify omnia-cli build-stream runs |
| MAIN_FVT_OMNIA_CLI_V012 | `test_cli_unknown_command` | errors/ | regression | Verify omnia-cli unknown command exits with error |
| MAIN_FVT_OMNIA_CLI_V013 | `test_cli_logs_help` | logs/ | sanity | Verify omnia-cli logs --help runs |
| MAIN_FVT_OMNIA_CLI_V014 | `test_cli_logs_no_opt_omnia_log` | logs/ | sanity | Verify omnia-cli logs searches /var/log/omnia only |
| MAIN_FVT_OMNIA_CLI_V015 | `test_cli_logs_limit` | logs/ | functional | Verify omnia-cli logs --limit flag works |
| MAIN_FVT_OMNIA_CLI_V016 | `test_cli_logs_limit_invalid` | logs/ | regression | Verify omnia-cli logs --limit rejects invalid values |
| MAIN_FVT_OMNIA_CLI_V017 | `test_cli_logs_limit_short` | logs/ | functional | Verify omnia-cli logs -l short form works |

---

## precheck and validate

These scenarios exercise the corresponding generic Image Build Manager tags
through the Main `omnia.sh` entry point.

| TC ID | Test | Suite | Markers | Description |
|-------|------|-------|---------|-------------|
| MAIN_FVT_EXECUTION_E003 | `test_deploy_run_precheck` | precheck/ | deploy, sanity, functional | Execute --run image_build_manager --tags precheck |
| MAIN_FVT_EXECUTION_E004 | `test_deploy_run_validate` | validate/ | deploy, sanity, functional | Execute --run image_build_manager --tags validate |

## cleanup

| TC ID | Test | Suite | Markers | Description |
|-------|------|-------|---------|-------------|
| MAIN_FVT_CLEANUP_E001 | `test_deploy_cleanup` | cleanup/ | deploy, cleanup | Explicit omnia.sh --cleanup (excluded from aggregate runs) |

---

> **NFT tests** are documented separately in [`nft/README.md`](../nft/README.md) (11 tests: performance, idempotency, permissions).
