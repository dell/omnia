# Test Cases — Omnia Main FVT

All test case IDs follow the format `TC_<AREA>_<SEQ>`.

---

## setup (omnia.sh --setup-venv)

| TC ID | Test | Suite | Markers | Description |
|-------|------|-------|---------|-------------|
| TC_SU_001 | `test_deploy_setup_venv` | *(root)* | deploy, sanity | Deploy omnia.sh --setup-venv --deps-only |
| TC_SU_002 | `test_env_file_installed` | environment/ | sanity | Verify omnia.env installed at /etc/omnia/omnia.env |
| TC_SU_003 | `test_profile_drop_in` | environment/ | sanity | Verify /etc/profile.d/omnia-env.sh exists |
| TC_SU_004 | `test_env_vars_loaded` | environment/ | sanity | Verify environment variables are set after install |
| TC_SU_005 | `test_venv_created` | venv/ | sanity | Verify Python venv created at OMNIA_VENV_PATH |
| TC_SU_006 | `test_ansible_available` | venv/ | sanity | Verify ansible is available in venv |
| TC_SU_007 | `test_base_dirs_created` | directories/ | sanity | Verify base directories created (log, .data, input) |
| TC_SU_008 | `test_activate_helper` | directories/ | sanity | Verify activate-omnia.sh helper script created |
| TC_SU_009 | `test_pip_packages_installed` | venv/ | sanity | Verify pip packages installed in venv (ansible-core) |
| TC_SU_010 | `test_galaxy_collections_installed` | venv/ | sanity | Verify Galaxy collections installed in venv |

---

## init (omnia.sh --init)

| TC ID | Test | Suite | Markers | Description |
|-------|------|-------|---------|-------------|
| TC_IN_001 | `test_deploy_init` | *(root)* | deploy, sanity | Deploy omnia.sh --init |
| TC_IN_002 | `test_domain_log_dirs` | domain_init/ | sanity | Verify domain log directories created (/var/log/omnia/<domain>/) |
| TC_IN_003 | `test_domain_input_staged_image_build_manager` | domain_init/ | sanity | Verify input files staged for image_build_manager |
| TC_IN_004 | `test_domain_input_staged_repo_manager` | domain_init/ | sanity | Verify input files staged for repo_manager |
| TC_IN_005 | `test_domain_input_staged_orchestrator` | domain_init/ | sanity | Verify input files staged for orchestrator |
| TC_IN_006 | `test_domain_input_staged_discovery` | domain_init/ | sanity | Verify input files staged for discovery |
| TC_IN_007 | `test_init_domain_filter` | domain_init/ | sanity | Verify --init with domain filter runs for single domain |
| TC_IN_008 | `test_init_force_deps` | domain_init/ | sanity | Verify --init --force-deps forces reinstall |

---

## cli (argument parsing and error handling)

| TC ID | Test | Suite | Markers | Description |
|-------|------|-------|---------|-------------|
| TC_CL_001 | `test_help_output` | *(root)* | deploy, sanity | Verify omnia.sh --help returns usage text |
| TC_CL_002 | `test_no_args_shows_help` | commands/ | sanity | Verify omnia.sh with no args shows help |
| TC_CL_003 | `test_run_invalid_domain` | commands/ | sanity | Verify --run with invalid domain exits with error |
| TC_CL_004 | `test_run_no_domain` | commands/ | sanity | Verify --run without domain exits with error |
| TC_CL_005 | `test_deps_only_in_help` | commands/ | sanity | Verify --deps-only flag appears in help output |
| TC_CL_006 | `test_unknown_option` | commands/ | sanity | Verify unknown option exits with error |
| TC_CL_007 | `test_cleanup_in_help` | commands/ | sanity | Verify --cleanup flag appears in help output |
| TC_CL_008 | `test_check_deps_in_help` | commands/ | sanity | Verify --check-deps flag appears in help output |
| TC_CL_009 | `test_force_deps_in_help` | commands/ | sanity | Verify --force-deps flag appears in help output |
| TC_CL_010 | `test_skip_catalog_in_help` | commands/ | sanity | Verify --skip-catalog flag appears in help output |
| TC_CL_011 | `test_force_deps_invalid` | commands/ | sanity | Verify --force-deps without -s/-i exits with error |
| TC_CL_012 | `test_check_deps_runs` | commands/ | sanity | Verify --check-deps command runs |
| TC_CL_013 | `test_generic_tags_in_help` | tags/ | sanity | Verify omnia.sh help shows generic tags (precheck, validate, prepare, execute, cleanup) |
| TC_CL_014 | `test_execution_order_in_help` | tags/ | sanity | Verify execution order in help text |
| TC_CL_015 | `test_skip_catalog_accepted` | commands/ | sanity | Verify --setup-venv --skip-catalog --deps-only is accepted |
| TC_CL_016 | `test_skip_omnia_cli_in_help` | commands/ | sanity | Verify --skip-omnia-cli flag appears in help output |
| TC_CL_017 | `test_skip_omnia_cli_accepted` | commands/ | sanity | Verify --setup-venv --skip-omnia-cli --deps-only is accepted |

---

## setup — environment

| TC ID | Test | Suite | Markers | Description |
|-------|------|-------|---------|-------------|
| TC_SU_011 | `test_env_source_validation` | environment/ | sanity | Verify env source validation rejects empty SYSTEM_ADMIN_NIC_IPV4 |

---

## omnia_cli (omnia-cli diagnostics tool)

| TC ID | Test | Suite | Markers | Description |
|-------|------|-------|---------|-------------|
| TC_OC_001 | `test_cli_help_output` | *(root)* | deploy, sanity | Verify omnia-cli help returns usage text |
| TC_OC_002 | `test_cli_version_output` | *(root)* | deploy, sanity | Verify omnia-cli version shows release info |
| TC_OC_003 | `test_cli_status_runs` | diagnostics/ | sanity | Verify omnia-cli status runs successfully |
| TC_OC_004 | `test_cli_check_runs` | diagnostics/ | sanity | Verify omnia-cli check runs successfully |
| TC_OC_005 | `test_cli_status_project_flag` | diagnostics/ | sanity | Verify omnia-cli status --project flag works |
| TC_OC_006 | `test_cli_repo_manager` | diagnostics/ | sanity | Verify omnia-cli repo-manager runs |
| TC_OC_007 | `test_cli_image_build` | diagnostics/ | sanity | Verify omnia-cli image-build runs |
| TC_OC_008 | `test_cli_discovery_status` | diagnostics/ | sanity | Verify omnia-cli discovery runs |
| TC_OC_009 | `test_cli_help_repo_manager` | diagnostics/ | sanity | Verify omnia-cli help repo-manager shows domain help |
| TC_OC_010 | `test_cli_help_discovery` | diagnostics/ | sanity | Verify omnia-cli help discovery shows domain help |
| TC_OC_011 | `test_cli_unknown_command` | errors/ | sanity | Verify omnia-cli unknown command exits with error |
| TC_OC_012 | `test_cli_logs_help` | logs/ | sanity | Verify omnia-cli logs --help runs |
| TC_OC_013 | `test_cli_logs_no_opt_omnia_log` | logs/ | sanity | Verify omnia-cli logs searches /var/log/omnia only |
| TC_OC_014 | `test_cli_orchestrator` | diagnostics/ | sanity | Verify omnia-cli orchestrator runs |
| TC_OC_015 | `test_cli_telemetry` | diagnostics/ | sanity | Verify omnia-cli telemetry runs |
| TC_OC_016 | `test_cli_build_stream` | diagnostics/ | sanity | Verify omnia-cli build-stream runs |

---

## execution (actual omnia.sh operations)

Tests actual execution of omnia.sh commands — not just help output or flag parsing.
Covers the full lifecycle: setup -> init -> run --tags -> cleanup -> re-setup.

### setup_exec — Full setup and init execution

| TC ID | Test | Suite | Markers | Description |
|-------|------|-------|---------|-------------|
| TC_EX_001 | `test_deploy_full_setup` | *(root)* | deploy, sanity | Deploy omnia.sh --setup-venv (full setup, not deps-only) |
| TC_EX_002 | `test_full_setup_venv_exists` | setup_exec/ | sanity | Verify full setup created venv with ansible |
| TC_EX_003 | `test_full_setup_env_installed` | setup_exec/ | sanity | Verify full setup installed system env files |
| TC_EX_004 | `test_init_domain_exec` | setup_exec/ | sanity | Execute omnia.sh --init for image_build_manager |
| TC_EX_005 | `test_init_domain_log_dirs` | setup_exec/ | sanity | Verify domain init created log directories |
| TC_EX_006 | `test_init_domain_input_staged` | setup_exec/ | sanity | Verify domain init staged input files |

### run_exec — Run domain with tags

| TC ID | Test | Suite | Markers | Description |
|-------|------|-------|---------|-------------|
| TC_EX_007 | `test_run_precheck` | run_exec/ | sanity, functional | Execute --run image_build_manager --tags precheck |
| TC_EX_008 | `test_run_validate` | run_exec/ | sanity, functional | Execute --run image_build_manager --tags validate |
| TC_EX_009 | `test_run_prepare` | run_exec/ | sanity, functional | Execute --run image_build_manager --tags prepare |
| TC_EX_010 | `test_run_execute` | run_exec/ | sanity, functional | Execute --run image_build_manager --tags execute |
| TC_EX_011 | `test_run_cleanup` | run_exec/ | sanity, functional | Execute --run image_build_manager --tags cleanup |

### cleanup_exec — Cleanup lifecycle

| TC ID | Test | Suite | Markers | Description |
|-------|------|-------|---------|-------------|
| TC_EX_012 | `test_cleanup_cancel` | cleanup_exec/ | sanity | Execute --cleanup with 'no' — verify cancel |
| TC_EX_013 | `test_cleanup_exec` | cleanup_exec/ | sanity | Execute --cleanup with 'yes' — verify success |
| TC_EX_014 | `test_cleanup_verify_removed` | cleanup_exec/ | sanity | Verify cleanup removed venv, env files, omnia-cli |
| TC_EX_015 | `test_cleanup_verify_data_preserved` | cleanup_exec/ | sanity | Verify cleanup preserved runtime data (/opt/omnia/) |
| TC_EX_016 | `test_re_setup_after_cleanup` | cleanup_exec/ | sanity | Re-deploy --setup-venv --deps-only after cleanup |
| TC_EX_017 | `test_cleanup_all_exec` | cleanup_exec/ | sanity | Execute --cleanup --all with 'yes' — full reset |
| TC_EX_018 | `test_cleanup_all_verify_removed` | cleanup_exec/ | sanity | Verify --cleanup --all removed data directory |
| TC_EX_019 | `test_re_setup_after_full_cleanup` | cleanup_exec/ | sanity | Re-deploy --setup-venv --deps-only after full cleanup |

---

> **NFT tests** are documented separately in [`nft/README.md`](../nft/README.md) (11 tests: performance, idempotency, permissions).
