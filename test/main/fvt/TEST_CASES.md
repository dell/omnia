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
| TC_CL_008 | `test_catalog_in_help` | commands/ | sanity | Verify --catalog flag appears in help output |

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

---

## nft (Non-Functional Tests)

| TC ID | Test | File | Markers | Description |
|-------|------|------|---------|-------------|
| NFT_MA_001 | `test_setup_venv_performance` | nft/test_performance.py | nft | --setup-venv --deps-only completes within 300s threshold |
| NFT_MA_002 | `test_init_performance` | nft/test_performance.py | nft | --init completes within 120s threshold |
| NFT_MA_003 | `test_setup_venv_idempotent` | nft/test_idempotency.py | nft | Running --setup-venv twice produces no errors; venv and env file stable |
| NFT_MA_004 | `test_init_idempotent` | nft/test_idempotency.py | nft | Running --init twice leaves domain log dirs and input files unchanged |
