# Utils Domain Test Automation - Gap Analysis Report

**Date**: 2026-09-09  
**Domain**: utils  
**Reference Implementation**: image_build_manager  
**Compliance Document**: /root/utils_test_domain_compliance.md

---

## Executive Summary

This report provides a comprehensive gap analysis of the utils domain test automation against the utils.yml playbook functionality and compliance standards. The analysis identifies missing test coverage, naming convention issues, and structural gaps that need to be addressed.

**Current Compliance Score**: 87.75/100 (IN_PROGRESS)

---

## 1. utils.yml Tag Coverage Analysis

### 1.1 Tag-to-Test Mapping

| Tag | Description | Playbook Flow | Test Coverage | Status |
|-----|-------------|---------------|---------------|--------|
| `precheck` | Environment validation | `precheck/precheck_environment.yml` | TC_PC_001 to TC_PC_005 | **COVERED** |
| `setup` | Setup and configuration | `utils_setup` role (always runs) | No dedicated tests | **MISSING** |
| `collect` | Log collection utility | `collect.yml` | TC_CL_001 to TC_CL_032 | **COVERED** |
| `install_os` | OS installation via iDRAC | `install_os.yml` | TC_IO_001 to TC_IO_031 | **COVERED** |
| `cleanup` | Cleanup all utilities | `cleanup_logs.yml` + `cleanup_install_os.yml` | No tests | **MISSING** |
| `cleanup_logs` | Cleanup log collection only | `cleanup/cleanup_logs.yml` | No tests | **MISSING** |
| `cleanup_install_os` | Cleanup OS installation only | `cleanup/cleanup_install_os.yml` | No tests | **MISSING** |
| `upgrade` | Upgrade flow (placeholder) | Not implemented | N/A | **N/A** |
| `rollback` | Rollback flow (placeholder) | Not implemented | N/A | **N/A** |

### 1.2 Dry-Run Analysis Results

**Tag: precheck**
- Executes: `utils_setup` role (always) + `precheck_environment` role
- Validates: omnia.env, SYSTEM_ADMIN_NIC_IPV4, hostname, domain, OMNIA_DATA_PATH
- Output: Precheck summary with PASS/FAIL status

**Tag: setup**
- Executes: `utils_setup` role only (tagged as `always`)
- Sets: OMNIA_DATA_PATH, project paths, output directory
- Note: Runs implicitly with every tag but has no dedicated test

**Tag: collect**
- Executes: `log_collector` role with setup, prepare, bundle stages
- Requires: `collect_pxe.yml` input file
- Output: Log bundles in `output/project_default/collect/`

**Tag: install_os**
- Executes: validate_install_os_config, collect_install_os_credentials, iso_creation, iso_delivery
- Requires: `install_os_config.yml`, credentials
- Output: Custom ISO, kickstart file, installation status

**Tag: cleanup_logs**
- Executes: `cleanup/cleanup_logs.yml`
- Actions: Delete old log bundles (retention-based), remove empty directories, clean temp dirs
- Output: Cleanup summary

**Tag: cleanup_install_os**
- Executes: `cleanup/cleanup_install_os.yml`
- Actions: Remove temp ISO dir, unmount NFS, optionally delete credentials
- Output: Cleanup summary with credential deletion status

**Tag: cleanup**
- Executes: Both `cleanup_logs` and `cleanup_install_os`
- Combined cleanup of all utils artifacts

---

## 2. Test Case ID Compliance Analysis

### 2.1 Current ID Format (Non-Compliant)

Current format: `TC_<SCENARIO>_<SEQ>`
- Examples: `TC_PC_001`, `TC_CL_001`, `TC_IO_001`, `TC_NEG_001`

### 2.2 Required ID Format (Compliant)

Following image_build_manager pattern: `UTILS_FVT_<PHASE>_<TYPE><SEQ>`

| Segment | Meaning | Values |
|---------|---------|--------|
| `UTILS` | Domain code | Fixed |
| `FVT` | Test level | Functional Verification Test |
| `PHASE` | Lifecycle phase | `PRECHECK`, `SETUP`, `COLLECT`, `INSTALL_OS`, `CLEANUP_LOGS`, `CLEANUP_INSTALL_OS`, `CLEANUP` |
| `TYPE` | Test type | `E` (execution/deploy), `V` (verification) |
| `SEQ` | Sequence number | Three digits (001, 002, etc.) |

### 2.3 ID Migration Mapping

| Current ID | New ID | Test Function |
|------------|--------|---------------|
| TC_PC_001 | UTILS_FVT_PRECHECK_V001 | test_target_connectivity |
| TC_PC_002 | UTILS_FVT_PRECHECK_V002 | test_env_vars_present |
| TC_PC_003 | UTILS_FVT_PRECHECK_V003 | test_hostname_domain |
| TC_PC_004 | UTILS_FVT_PRECHECK_V004 | test_admin_ip_assigned |
| TC_PC_005 | UTILS_FVT_PRECHECK_V005 | test_omnia_setup |
| TC_CL_001 | UTILS_FVT_COLLECT_E001 | test_deploy_collect_setup |
| TC_CL_002 | UTILS_FVT_COLLECT_E002 | test_deploy_collect_prepare |
| TC_CL_003 | UTILS_FVT_COLLECT_E003 | test_deploy_collect_bundle |
| TC_CL_004 | UTILS_FVT_COLLECT_E004 | test_deploy_collect_full |
| TC_CL_010 | UTILS_FVT_COLLECT_V001 | test_collect_input_file_exists |
| TC_CL_011 | UTILS_FVT_COLLECT_V002 | test_collect_input_file_valid |
| TC_CL_012 | UTILS_FVT_COLLECT_V003 | test_collect_functional_groups_valid |
| TC_CL_020 | UTILS_FVT_COLLECT_V004 | test_collect_output_dir_exists |
| TC_CL_021 | UTILS_FVT_COLLECT_V005 | test_collect_bundle_created |
| TC_CL_022 | UTILS_FVT_COLLECT_V006 | test_collect_metadata_exists |
| TC_CL_023 | UTILS_FVT_COLLECT_V007 | test_collect_metadata_valid |
| TC_CL_024 | UTILS_FVT_COLLECT_V008 | test_collect_metadata_sha256 |
| TC_CL_025 | UTILS_FVT_COLLECT_V009 | test_collect_bundle_contents |
| TC_CL_030 | UTILS_FVT_COLLECT_V010 | test_collect_env_vars_loaded |
| TC_CL_031 | UTILS_FVT_COLLECT_V011 | test_collect_project_name_loaded |
| TC_CL_032 | UTILS_FVT_COLLECT_V012 | test_collect_bundle_log_files_content |
| TC_IO_001 | UTILS_FVT_INSTALL_OS_E001 | test_deploy_install_os_credentials |
| TC_IO_002 | UTILS_FVT_INSTALL_OS_E002 | test_deploy_install_os_build_iso |
| TC_IO_003 | UTILS_FVT_INSTALL_OS_E003 | test_deploy_install_os_deploy |
| TC_IO_004 | UTILS_FVT_INSTALL_OS_E004 | test_deploy_install_os_generate_ks |
| TC_IO_005 | UTILS_FVT_INSTALL_OS_E005 | test_deploy_install_os_full |
| TC_IO_010 | UTILS_FVT_INSTALL_OS_V001 | test_install_os_config_file_exists |
| TC_IO_011 | UTILS_FVT_INSTALL_OS_V002 | test_install_os_config_valid |
| TC_IO_012 | UTILS_FVT_INSTALL_OS_V003 | test_install_os_credentials_file_exists |
| TC_IO_020 | UTILS_FVT_INSTALL_OS_V004 | test_install_os_output_dir_exists |
| TC_IO_021 | UTILS_FVT_INSTALL_OS_V005 | test_install_os_status_file_exists |
| TC_IO_022 | UTILS_FVT_INSTALL_OS_V006 | test_install_os_status_valid |
| TC_IO_030 | UTILS_FVT_INSTALL_OS_V007 | test_install_os_custom_iso_created |
| TC_IO_031 | UTILS_FVT_INSTALL_OS_V008 | test_install_os_kickstart_generated |
| TC_NEG_001 | UTILS_FVT_COLLECT_NEG001 | test_collect_missing_input_fails |
| TC_NEG_002 | UTILS_FVT_COLLECT_NEG002 | test_collect_invalid_yaml_fails |
| TC_NEG_003 | UTILS_FVT_COLLECT_NEG003 | test_collect_empty_groups_succeeds |
| TC_NEG_020 | UTILS_FVT_INSTALL_OS_NEG001 | test_install_os_missing_config_fails |
| TC_NEG_021 | UTILS_FVT_INSTALL_OS_NEG002 | test_install_os_invalid_config_params_fails |
| TC_NEG_022 | UTILS_FVT_INSTALL_OS_NEG003 | test_install_os_missing_iso_path_fails |
| TC_NEG_023 | UTILS_FVT_INSTALL_OS_NEG004 | test_install_os_missing_bmc_ip_fails |

---

## 3. Missing Test Cases

### 3.1 Setup Tag Tests (NEW)

| ID | Test Function | Description | Markers |
|----|---------------|-------------|---------|
| UTILS_FVT_SETUP_E001 | test_deploy_setup | Deploy utils.yml --tags setup | deploy, sanity |
| UTILS_FVT_SETUP_V001 | test_setup_omnia_data_path_set | Verify OMNIA_DATA_PATH fact is set | sanity |
| UTILS_FVT_SETUP_V002 | test_setup_project_paths_set | Verify project input/output paths set | sanity |
| UTILS_FVT_SETUP_V003 | test_setup_output_dir_created | Verify output directory created | sanity |
| UTILS_FVT_SETUP_V004 | test_setup_domain_ready_fact | Verify utils_domain_ready fact is true | sanity |

### 3.2 Cleanup Logs Tag Tests (NEW)

| ID | Test Function | Description | Markers |
|----|---------------|-------------|---------|
| UTILS_FVT_CLEANUP_LOGS_E001 | test_deploy_cleanup_logs | Deploy utils.yml --tags cleanup_logs | deploy, sanity |
| UTILS_FVT_CLEANUP_LOGS_V001 | test_cleanup_logs_old_bundles_removed | Verify old log bundles removed (retention-based) | sanity |
| UTILS_FVT_CLEANUP_LOGS_V002 | test_cleanup_logs_empty_dirs_removed | Verify empty log directories removed | sanity |
| UTILS_FVT_CLEANUP_LOGS_V003 | test_cleanup_logs_temp_dirs_cleaned | Verify temp directories (k8s, slurm) cleaned | sanity |

### 3.3 Cleanup Install OS Tag Tests (NEW)

| ID | Test Function | Description | Markers |
|----|---------------|-------------|---------|
| UTILS_FVT_CLEANUP_INSTALL_OS_E001 | test_deploy_cleanup_install_os | Deploy utils.yml --tags cleanup_install_os | deploy, sanity |
| UTILS_FVT_CLEANUP_INSTALL_OS_V001 | test_cleanup_install_os_temp_iso_removed | Verify /tmp/install_os removed | sanity |
| UTILS_FVT_CLEANUP_INSTALL_OS_V002 | test_cleanup_install_os_nfs_unmounted | Verify /tmp/install_os_nfs unmounted | sanity |
| UTILS_FVT_CLEANUP_INSTALL_OS_V003 | test_cleanup_install_os_credentials_prompt | Verify credential cleanup prompt behavior | functional |

### 3.4 Combined Cleanup Tag Tests (NEW)

| ID | Test Function | Description | Markers |
|----|---------------|-------------|---------|
| UTILS_FVT_CLEANUP_E001 | test_deploy_cleanup | Deploy utils.yml --tags cleanup | deploy, sanity |
| UTILS_FVT_CLEANUP_V001 | test_cleanup_all_logs_cleaned | Verify all log artifacts cleaned | sanity |
| UTILS_FVT_CLEANUP_V002 | test_cleanup_all_install_os_cleaned | Verify all install_os artifacts cleaned | sanity |

### 3.5 Precheck Deploy Test (NEW)

| ID | Test Function | Description | Markers |
|----|---------------|-------------|---------|
| UTILS_FVT_PRECHECK_E001 | test_deploy_precheck | Deploy utils.yml --tags precheck | deploy, sanity |

---

## 4. Structural Gaps

### 4.1 Missing Files (from compliance doc)

| File | Status | Action Required |
|------|--------|-----------------|
| `test/utils/_run.py` | Missing | Create entry point script |
| `test/utils/docs/test_config.md` | Missing | Create configuration documentation |
| `test/utils/docs/test_run_config.md` | Missing | Create run config documentation |
| `test/utils/library/vars/domain_vars.py` | Missing | Create domain-specific variables |
| `test/utils/fvt/setup/` | Missing | Create setup test directory |
| `test/utils/fvt/cleanup/` | Missing | Create cleanup test directory |
| `test/utils/fvt/cleanup_logs/` | Missing | Create cleanup_logs test directory |
| `test/utils/fvt/cleanup_install_os/` | Missing | Create cleanup_install_os test directory |

### 4.2 Code Quality Issues

| File | Issue | Current Score | Required |
|------|-------|---------------|----------|
| `library/functions/host_func.py` | Pylint score | 6.22 | >= 8.0 |

### 4.3 Inline Commands in Tests

Tests with inline shell commands that should be moved to library functions:

- `fvt/collect/log_collector/test_log_collector.py`: lines 176, 205, 234
- `fvt/install_os/test_playbook.py`: lines 296, 314, 345, 364, 395, 414
- `fvt/precheck/connectivity/test_connectivity.py`: line 174

---

## 5. Test Registry Summary

### 5.1 Current State

| Phase | Execution IDs | Verification IDs | Total |
|-------|---------------|------------------|-------|
| Precheck | 0 | 5 | 5 |
| Collect | 4 | 12 | 16 |
| Install OS | 5 | 8 | 13 |
| Negative | 0 | 7 | 7 |
| **Current Total** | **9** | **32** | **41** |

### 5.2 After Implementation

| Phase | Execution IDs | Verification IDs | Total |
|-------|---------------|------------------|-------|
| Precheck | 1 | 5 | 6 |
| Setup | 1 | 4 | 5 |
| Collect | 4 | 12 | 16 |
| Install OS | 5 | 8 | 13 |
| Cleanup Logs | 1 | 3 | 4 |
| Cleanup Install OS | 1 | 3 | 4 |
| Cleanup (combined) | 1 | 2 | 3 |
| Negative | 0 | 7 | 7 |
| **New Total** | **14** | **44** | **58** |

---

## 6. Implementation Priority

### Priority 1 (Critical)
1. Create cleanup test directories and test files
2. Implement cleanup_logs tests
3. Implement cleanup_install_os tests
4. Implement combined cleanup tests

### Priority 2 (High)
1. Create setup test directory and tests
2. Add precheck deploy test
3. Update test case IDs to compliant format

### Priority 3 (Medium)
1. Create missing documentation files
2. Create domain_vars.py
3. Create _run.py entry point

### Priority 4 (Low)
1. Fix pylint score in host_func.py
2. Refactor inline commands to library functions

---

## 7. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Cleanup tests may affect production data | High | Use test datasets, add safeguards |
| ID renaming may break existing reports | Medium | Provide legacy ID mapping |
| Credential cleanup tests require user input | Medium | Use non-interactive mode with `-e cleanup_credentials=true` |

---

## 8. Deliverables Checklist

- [x] Gap analysis report (this document)
- [ ] Updated test_case_vars.py with compliant IDs
- [ ] New test files for setup, cleanup_logs, cleanup_install_os, cleanup
- [ ] Updated fvt/README.md with new test cases
- [ ] New library functions for cleanup verification
- [ ] Documentation files (test_config.md, test_run_config.md)
- [ ] domain_vars.py
- [ ] _run.py entry point

---

**Report Generated**: 2026-09-09  
**Author**: Test Automation Analysis
