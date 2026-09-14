# Utils Domain Functional Verification Tests

This document is the authoritative test-case registry for
`test/utils/fvt/`. It describes what each test validates and the
condition required for the test to pass.

All test-case metadata is defined in
`library/vars/test_case_vars.py`. Test files must obtain the ID and title from
that registry; IDs and titles must not be hardcoded in test implementations.

## Test-case ID Standard

IDs use `UTILS_FVT_<PHASE>_<TYPE><SEQ>`:

| Segment | Meaning | Values or example |
|---------|---------|-------------------|
| `UTILS` | Utils domain | Fixed domain code |
| `FVT` | Functional Verification Test level | Fixed test-level code |
| `PHASE` | Lifecycle phase | `PRECHECK`, `SETUP`, `COLLECT`, `INSTALL_OS`, `CLEANUP_LOGS`, `CLEANUP_INSTALL_OS`, `CLEANUP` |
| `TYPE` | Whether the case changes or inspects state | `E` runs a playbook; `V` verifies postconditions |
| `SEQ` | Stable sequence appended to the type | Three digits, starting at `001` |

For example, `UTILS_FVT_COLLECT_E001` runs the collect playbook and
`UTILS_FVT_COLLECT_V001` verifies its first postcondition.

## Effective Execution Order

An untagged `verify` run excludes deploy and cleanup tests and executes the
verification suites in this order:

| Phase | Suite order |
|-------|-------------|
| precheck | `connectivity` |
| setup | `setup` |
| collect | `log_collector` |
| install_os | `install_os` |
| cleanup_logs | `cleanup_logs` |
| cleanup_install_os | `cleanup_install_os` |
| cleanup | `cleanup` |

---

## Precheck Test Cases

These cases confirm that the execution OIM is reachable and that its installed
Omnia environment matches the host.

| Sequence | TC ID | Test | Markers | Validation | Pass criteria |
|----------|-------|------|---------|------------|---------------|
| 0 | UTILS_FVT_PRECHECK_E001 | `test_deploy_precheck` | deploy, sanity | Runs `utils.yml --tags precheck`. | Playbook exits successfully. |
| 1 | UTILS_FVT_PRECHECK_V001 | `test_target_connectivity` | sanity | Connects to the configured test target; remote mode verifies SSH. | Target command/SSH connection succeeds. |
| 2 | UTILS_FVT_PRECHECK_V002 | `test_env_vars_present` | sanity | Reads required values from the target Omnia environment. | `OMNIA_DATA_PATH`, `OMNIA_PROJECT_NAME`, `SYSTEM_ADMIN_NIC_IPV4`, `SYSTEM_HOSTNAME` are present. |
| 3 | UTILS_FVT_PRECHECK_V003 | `test_hostname_domain` | sanity | Compares the target hostname and domain with `omnia.env`. | Short hostname and domain match the configured values. |
| 4 | UTILS_FVT_PRECHECK_V004 | `test_admin_ip_assigned` | sanity | Compares `SYSTEM_ADMIN_NIC_IPV4` with local interface addresses. | Configured admin IP is assigned to an interface on the execution OIM. |
| 5 | UTILS_FVT_PRECHECK_V005 | `test_omnia_setup` | sanity | Checks the system-wide environment files created by `omnia.sh`. | `/etc/omnia/omnia.env` exists. |

---

## Setup Test Cases

These cases verify the utils domain setup functionality.

| Sequence | TC ID | Test | Markers | Validation | Pass criteria |
|----------|-------|------|---------|------------|---------------|
| 0 | UTILS_FVT_SETUP_E001 | `test_deploy_setup` | deploy, sanity | Runs `utils.yml --tags setup`. | Playbook exits successfully. |
| 1 | UTILS_FVT_SETUP_V001 | `test_setup_omnia_data_path_set` | sanity | Verifies OMNIA_DATA_PATH is set. | Environment variable is present and non-empty. |
| 2 | UTILS_FVT_SETUP_V002 | `test_setup_project_paths_set` | sanity | Verifies project input/output paths. | At least output path exists. |
| 3 | UTILS_FVT_SETUP_V003 | `test_setup_output_dir_created` | sanity | Checks output directory exists. | Directory exists at expected path. |
| 4 | UTILS_FVT_SETUP_V004 | `test_setup_domain_ready_fact` | sanity | Verifies domain is ready. | Output directory structure is in place. |

---

## Collect Test Cases

These cases verify log collection functionality.

| Sequence | TC ID | Test | Markers | Validation | Pass criteria |
|----------|-------|------|---------|------------|---------------|
| 0 | UTILS_FVT_COLLECT_E001 | `test_deploy_collect_setup` | deploy, sanity | Runs `collect.yml --tags setup`. | Playbook exits successfully. |
| 1 | UTILS_FVT_COLLECT_E002 | `test_deploy_collect_prepare` | deploy, sanity | Runs `collect.yml --tags prepare`. | Playbook exits successfully. |
| 2 | UTILS_FVT_COLLECT_E003 | `test_deploy_collect_bundle` | deploy, sanity | Runs `collect.yml --tags bundle`. | Playbook exits successfully. |
| 3 | UTILS_FVT_COLLECT_E004 | `test_deploy_collect_full` | deploy, functional | Runs `collect.yml` (all tags). | Playbook exits successfully. |
| 10 | UTILS_FVT_COLLECT_V001 | `test_collect_input_file_exists` | sanity | Checks `collect_pxe.yml` exists. | File exists at input path. |
| 11 | UTILS_FVT_COLLECT_V002 | `test_collect_input_file_valid` | sanity | Validates YAML structure. | File is valid YAML. |
| 12 | UTILS_FVT_COLLECT_V003 | `test_collect_functional_groups_valid` | sanity | Validates functional groups. | Only valid group names present. |
| 20 | UTILS_FVT_COLLECT_V004 | `test_collect_output_dir_exists` | sanity | Checks output directory. | Directory exists. |
| 21 | UTILS_FVT_COLLECT_V005 | `test_collect_bundle_created` | functional | Checks log bundle created. | tar.gz file exists. |
| 22 | UTILS_FVT_COLLECT_V006 | `test_collect_metadata_exists` | functional | Checks metadata.json exists. | File exists. |
| 23 | UTILS_FVT_COLLECT_V007 | `test_collect_metadata_valid` | functional | Validates metadata structure. | Valid JSON with required fields. |
| 24 | UTILS_FVT_COLLECT_V008 | `test_collect_metadata_sha256` | functional | Checks SHA256 in metadata. | Checksum field present. |
| 25 | UTILS_FVT_COLLECT_V009 | `test_collect_bundle_contents` | functional | Validates bundle directories. | Expected directories present. |
| 30 | UTILS_FVT_COLLECT_V010 | `test_collect_env_vars_loaded` | sanity | Checks OMNIA_DATA_PATH loaded. | Variable is set. |
| 31 | UTILS_FVT_COLLECT_V011 | `test_collect_project_name_loaded` | sanity | Checks OMNIA_PROJECT_NAME loaded. | Variable is set. |
| 32 | UTILS_FVT_COLLECT_V012 | `test_collect_bundle_log_files_content` | functional | Validates log files in bundle. | Log files have content. |

---

## Install OS Test Cases

These cases verify OS installation functionality via iDRAC.

| Sequence | TC ID | Test | Markers | Validation | Pass criteria |
|----------|-------|------|---------|------------|---------------|
| 0 | UTILS_FVT_INSTALL_OS_E001 | `test_deploy_install_os_credentials` | deploy, sanity | Runs `install_os.yml --tags credentials`. | Playbook exits successfully. |
| 1 | UTILS_FVT_INSTALL_OS_E002 | `test_deploy_install_os_build_iso` | deploy, sanity | Runs `install_os.yml --tags build_iso`. | Playbook exits successfully. |
| 2 | UTILS_FVT_INSTALL_OS_E003 | `test_deploy_install_os_deploy` | deploy, functional | Runs `install_os.yml --tags deploy`. | Playbook exits successfully. |
| 3 | UTILS_FVT_INSTALL_OS_E004 | `test_deploy_install_os_generate_ks` | deploy, sanity | Runs `install_os.yml --tags generate_ks`. | Playbook exits successfully. |
| 4 | UTILS_FVT_INSTALL_OS_E005 | `test_deploy_install_os_full` | deploy, functional | Runs `install_os.yml` (all tags). | Playbook exits successfully. |
| 10 | UTILS_FVT_INSTALL_OS_V001 | `test_install_os_config_file_exists` | sanity | Checks config file exists. | File exists at input path. |
| 11 | UTILS_FVT_INSTALL_OS_V002 | `test_install_os_config_valid` | sanity | Validates config structure. | Valid YAML with required fields. |
| 12 | UTILS_FVT_INSTALL_OS_V003 | `test_install_os_credentials_file_exists` | sanity | Checks credentials file exists. | File exists. |
| 20 | UTILS_FVT_INSTALL_OS_V004 | `test_install_os_output_dir_exists` | sanity | Checks output directory. | Directory exists. |
| 21 | UTILS_FVT_INSTALL_OS_V005 | `test_install_os_status_file_exists` | functional | Checks status file created. | File exists. |
| 22 | UTILS_FVT_INSTALL_OS_V006 | `test_install_os_status_valid` | functional | Validates status structure. | Valid YAML with status fields. |
| 30 | UTILS_FVT_INSTALL_OS_V007 | `test_install_os_custom_iso_created` | functional | Checks custom ISO created. | ISO file exists. |
| 31 | UTILS_FVT_INSTALL_OS_V008 | `test_install_os_kickstart_generated` | functional | Checks kickstart file. | kickstart.ks exists. |

---

## Cleanup Logs Test Cases

These cases verify log collection cleanup functionality.

| Sequence | TC ID | Test | Markers | Validation | Pass criteria |
|----------|-------|------|---------|------------|---------------|
| 0 | UTILS_FVT_CLEANUP_LOGS_E001 | `test_deploy_cleanup_logs` | deploy, sanity | Runs `utils.yml --tags cleanup_logs`. | Playbook exits successfully. |
| 1 | UTILS_FVT_CLEANUP_LOGS_V001 | `test_cleanup_logs_old_bundles_removed` | sanity | Checks old bundles removed. | No bundles older than retention period. |
| 2 | UTILS_FVT_CLEANUP_LOGS_V002 | `test_cleanup_logs_empty_dirs_removed` | sanity | Checks empty directories removed. | No empty omnia_logs_* directories. |
| 3 | UTILS_FVT_CLEANUP_LOGS_V003 | `test_cleanup_logs_temp_dirs_cleaned` | sanity | Checks temp directories cleaned. | k8s, slurm directories empty or removed. |

---

## Cleanup Install OS Test Cases

These cases verify OS installation cleanup functionality.

| Sequence | TC ID | Test | Markers | Validation | Pass criteria |
|----------|-------|------|---------|------------|---------------|
| 0 | UTILS_FVT_CLEANUP_INSTALL_OS_E001 | `test_deploy_cleanup_install_os` | deploy, sanity | Runs `utils.yml --tags cleanup_install_os`. | Playbook exits successfully. |
| 1 | UTILS_FVT_CLEANUP_INSTALL_OS_V001 | `test_cleanup_install_os_temp_iso_removed` | sanity | Checks /tmp/install_os removed. | Directory does not exist. |
| 2 | UTILS_FVT_CLEANUP_INSTALL_OS_V002 | `test_cleanup_install_os_nfs_unmounted` | sanity | Checks NFS unmounted and removed. | Not mounted, directory removed. |
| 3 | UTILS_FVT_CLEANUP_INSTALL_OS_V003 | `test_cleanup_install_os_credentials_removed` | functional | Checks credential files status. | Reports credential file state (informational). |

---

## Cleanup (Combined) Test Cases

These cases verify combined cleanup functionality.

| Sequence | TC ID | Test | Markers | Validation | Pass criteria |
|----------|-------|------|---------|------------|---------------|
| 0 | UTILS_FVT_CLEANUP_E001 | `test_deploy_cleanup` | deploy, sanity | Runs `utils.yml --tags cleanup`. | Playbook exits successfully. |
| 1 | UTILS_FVT_CLEANUP_V001 | `test_cleanup_all_logs_cleaned` | sanity | Verifies all log artifacts cleaned. | All log cleanup checks pass. |
| 2 | UTILS_FVT_CLEANUP_V002 | `test_cleanup_all_install_os_cleaned` | sanity | Verifies all install_os artifacts cleaned. | Temp dir and NFS cleaned. |

---

## Negative Test Cases

### Collect Negative Tests

| TC ID | Test | Markers | Validation | Pass criteria |
|-------|------|---------|------------|---------------|
| UTILS_FVT_COLLECT_NEG001 | `test_collect_missing_input_fails` | negative | Runs collect without input file. | Playbook fails gracefully. |
| UTILS_FVT_COLLECT_NEG002 | `test_collect_invalid_yaml_fails` | negative | Runs collect with invalid YAML. | Playbook fails with error. |
| UTILS_FVT_COLLECT_NEG003 | `test_collect_empty_groups_succeeds` | negative | Runs collect with empty groups. | Playbook succeeds (no logs collected). |

### Install OS Negative Tests

| TC ID | Test | Markers | Validation | Pass criteria |
|-------|------|---------|------------|---------------|
| UTILS_FVT_INSTALL_OS_NEG001 | `test_install_os_missing_config_fails` | negative | Runs without config file. | Playbook fails gracefully. |
| UTILS_FVT_INSTALL_OS_NEG002 | `test_install_os_invalid_config_params_fails` | negative | Runs with invalid config. | Playbook fails with validation error. |
| UTILS_FVT_INSTALL_OS_NEG003 | `test_install_os_missing_iso_path_fails` | negative | Runs without ISO path. | Playbook fails with error. |
| UTILS_FVT_INSTALL_OS_NEG004 | `test_install_os_missing_bmc_ip_fails` | negative | Runs deploy without BMC IP. | Playbook fails with error. |

---

## Registry Summary

| Phase | Execution IDs | Verification IDs | Total |
|-------|---------------|------------------|-------|
| Precheck | 1 | 5 | 6 |
| Setup | 1 | 4 | 5 |
| Collect | 4 | 12 | 16 |
| Install OS | 5 | 8 | 13 |
| Cleanup Logs | 1 | 3 | 4 |
| Cleanup Install OS | 1 | 3 | 4 |
| Cleanup (combined) | 1 | 2 | 3 |
| Negative (Collect) | 0 | 3 | 3 |
| Negative (Install OS) | 0 | 4 | 4 |
| **Total** | **14** | **44** | **58** |

---

## Legacy ID Migration

Historical reports may contain the former phase-abbreviation IDs. Use this
mapping when comparing those reports with current output:

| Earlier ID | Current ID |
|------------|------------|
| `TC_PC_*` | `UTILS_FVT_PRECHECK_V*` |
| `TC_CL_001-004` | `UTILS_FVT_COLLECT_E*` |
| `TC_CL_010-032` | `UTILS_FVT_COLLECT_V*` |
| `TC_IO_001-005` | `UTILS_FVT_INSTALL_OS_E*` |
| `TC_IO_010-031` | `UTILS_FVT_INSTALL_OS_V*` |
| `TC_NEG_001-003` | `UTILS_FVT_COLLECT_NEG*` |
| `TC_NEG_020-023` | `UTILS_FVT_INSTALL_OS_NEG*` |

The complete mapping is available in `library/vars/test_case_vars.py` as `LEGACY_ID_MAP`.
