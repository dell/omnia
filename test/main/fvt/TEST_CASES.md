# Test Cases — Omnia Main FVT

All test case IDs follow the format `TC_<AREA>_<SEQ>`.

---

## setup (omnia.sh --setup-venv)

| TC ID | Test | Suite | Markers | Description |
|-------|------|-------|---------|-------------|
| TC_SU_001 | `test_deploy_setup_venv` | *(root)* | deploy, sanity | Deploy omnia.sh --setup-venv --skip-init |
| TC_SU_002 | `test_env_file_installed` | environment/ | sanity | Verify omnia.env installed at /etc/omnia/omnia.env |
| TC_SU_003 | `test_profile_drop_in` | environment/ | sanity | Verify /etc/profile.d/omnia-env.sh exists |
| TC_SU_004 | `test_env_vars_loaded` | environment/ | sanity | Verify environment variables are set after install |
| TC_SU_005 | `test_venv_created` | venv/ | sanity | Verify Python venv created at OMNIA_VENV_PATH |
| TC_SU_006 | `test_ansible_available` | venv/ | sanity | Verify ansible is available in venv |
| TC_SU_007 | `test_base_dirs_created` | directories/ | sanity | Verify base directories created (log, .data, input) |
| TC_SU_008 | `test_activate_helper` | directories/ | sanity | Verify activate-omnia.sh helper script created |

---

## init (omnia.sh --init)

| TC ID | Test | Suite | Markers | Description |
|-------|------|-------|---------|-------------|
| TC_IN_001 | `test_deploy_init` | *(root)* | deploy, sanity | Deploy omnia.sh --init |
| TC_IN_002 | `test_domain_log_dirs` | domain_init/ | sanity | Verify domain log directories created (/var/log/omnia/<domain>/) |
| TC_IN_003 | `test_domain_input_staged_image_build_manager` | domain_init/ | sanity | Verify input files staged for image_build_manager |
| TC_IN_004 | `test_domain_input_staged_repo_manager` | domain_init/ | sanity | Verify input files staged for repo_manager |

---

## cli (argument parsing and error handling)

| TC ID | Test | Suite | Markers | Description |
|-------|------|-------|---------|-------------|
| TC_CL_001 | `test_help_output` | *(root)* | deploy, sanity | Verify omnia.sh --help returns usage text |
| TC_CL_002 | `test_no_args_shows_help` | commands/ | sanity | Verify omnia.sh with no args shows help |
| TC_CL_003 | `test_run_invalid_domain` | commands/ | sanity | Verify --run with invalid domain exits with error |
| TC_CL_004 | `test_run_no_domain` | commands/ | sanity | Verify --run without domain exits with error |
| TC_CL_005 | `test_validate_no_domain` | commands/ | sanity | Verify --validate without domain exits with error |
| TC_CL_006 | `test_unknown_option` | commands/ | sanity | Verify unknown option exits with error |
