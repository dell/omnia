# Discovery Functional Verification Tests

This document is the authoritative test-case registry for
`test/discovery/fvt/`. It describes what each test validates and the
condition required for the test to pass.

All test-case metadata is defined in
`library/vars/test_case_vars.py`. Test files must obtain the ID and title from
that registry; IDs and titles must not be hardcoded in test implementations.

## Test-case ID standard

IDs use `DISCOVERY_FVT_<PHASE>_<TYPE><SEQ>`:

| Segment | Meaning | Values or example |
|---------|---------|-------------------|
| `DISCOVERY` | Discovery domain | Fixed domain code |
| `FVT` | Functional Verification Test level | Fixed test-level code |
| `PHASE` | Lifecycle phase | `PRECHECK`, `VALIDATE`, `CREDENTIALS`, `EXECUTE`, `DISCOVERY`, or `CLEANUP` |
| `TYPE` | Whether the case changes or inspects state | `E` runs a playbook; `V` verifies postconditions |
| `SEQ` | Stable sequence appended to the type | Three digits, starting at `001` |

For example, `DISCOVERY_FVT_PRECHECK_E001` runs the precheck playbook and
`DISCOVERY_FVT_VALIDATE_V001` verifies its first postcondition. The sequence is a
stable identifier, not a global execution position. Execution is controlled
first by lifecycle phase, then by suite, and finally by
`@pytest.mark.order(n)` inside that suite.

## Effective execution order

An untagged `verify` run excludes deploy and cleanup tests and executes the
verification suites in this order. Cleanup verification must be run explicitly
using the cleanup tag:

| Phase | Suite order |
|-------|-------------|
| precheck | (root) |
| validate | `status` |
| credentials | (root) |
| execute | `output` |
| discovery | `output` |
| cleanup | `status` |

## Precheck test cases

These cases confirm that the execution OIM is reachable and that the environment
is ready for discovery operations.

| Sequence | TC ID | Test | Markers | Validation | Pass criteria |
|----------|-------|------|---------|------------|---------------|
| 0 | DISCOVERY_FVT_PRECHECK_E001 | `test_deploy_precheck` | deploy, sanity | Runs `discovery.yml --tags precheck`. | Playbook exits successfully. |

## Validate test cases

These cases validate the input configuration and credentials before executing discovery.

| Sequence | TC ID | Test | Markers | Validation | Pass criteria |
|----------|-------|------|---------|------------|---------------|
| 0 | DISCOVERY_FVT_VALIDATE_E001 | `test_deploy_validate` | deploy, sanity | Runs `discovery.yml --tags validate`. | Playbook exits successfully. |
| 1 | DISCOVERY_FVT_VALIDATE_V001 | `test_input_config_exists` | sanity | Resolves the active project input directory on the target. | `discovery_config.yml` exists at the runtime input path. |
| 2 | DISCOVERY_FVT_VALIDATE_V002 | `test_network_spec_exists` | sanity | Resolves the network specification file on the target. | `network_spec.yml` exists at the runtime input path. |
| 3 | DISCOVERY_FVT_VALIDATE_V003 | `test_credentials_present` | sanity | Resolves the domain credential path on the execution OIM. | Credentials file exists; credential values are not printed. |

## Credentials test cases

These cases verify credential setup for OME discovery.

| Sequence | TC ID | Test | Markers | Validation | Pass criteria |
|----------|-------|------|---------|------------|---------------|
| 0 | DISCOVERY_FVT_CREDENTIALS_E001 | `test_deploy_credentials` | deploy, sanity | Runs `discovery.yml --tags credentials`. | Playbook exits successfully. |

## Execute test cases

These cases verify the OME discovery execution and output artifacts.

| Sequence | TC ID | Test | Markers | Validation | Pass criteria |
|----------|-------|------|---------|------------|---------------|
| 0 | DISCOVERY_FVT_EXECUTE_E001 | `test_deploy_execute` | deploy, sanity | Runs `discovery.yml --tags execute`. | Playbook exits successfully. |
| 1 | DISCOVERY_FVT_EXECUTE_V001 | `test_output_dir_exists` | sanity | Checks the discovery output directory on the target. | Output directory exists at the runtime path. |
| 2 | DISCOVERY_FVT_EXECUTE_V002 | `test_pxe_mapping_created` | sanity | Verifies PXE mapping CSV file creation. | `bmc_pxe_mapping_file*.csv` exists in the output directory. |
| 3 | DISCOVERY_FVT_EXECUTE_V003 | `test_pxe_mapping_columns` | functional | Validates required columns in the PXE mapping CSV. | CSV contains all required columns: FUNCTIONAL_GROUP_NAME, SERVICE_TAG, HOSTNAME, ADMIN_MAC, ADMIN_IP, BMC_IP. |
| 4 | DISCOVERY_FVT_EXECUTE_V004 | `test_pxe_mapping_has_rows` | functional | Verifies the PXE mapping CSV contains data rows. | CSV has at least one data row (excluding header). |
| 5 | DISCOVERY_FVT_EXECUTE_V005 | `test_pxe_mapping_symlink` | sanity | Checks the symlink to the latest PXE mapping file. | Symlink `bmc_pxe_mapping_file.csv` points to the latest mapping file. |
| 6 | DISCOVERY_FVT_EXECUTE_V006 | `test_discovery_report_created` | functional | Verifies discovery report CSV creation. | `bmc_discovery_report*.csv` exists in the output directory. |

## Discovery (Full Run) test cases

These cases verify the complete discovery workflow from start to finish.

| Sequence | TC ID | Test | Markers | Validation | Pass criteria |
|----------|-------|------|---------|------------|---------------|
| 0 | DISCOVERY_FVT_DISCOVERY_E001 | `test_deploy_discovery` | deploy, sanity | Runs the untagged `discovery.yml` playbook (full run). | Complete playbook exits successfully. |

The discovery full run uses the same verification tests as the execute phase
(output directory, PXE mapping, discovery report) but executes the complete
workflow in a single playbook run.

## Cleanup test cases

These cases verify the cleanup of discovery artifacts and resources.

| Sequence | TC ID | Test | Markers | Validation | Pass criteria |
|----------|-------|------|---------|------------|---------------|
| 0 | DISCOVERY_FVT_CLEANUP_E001 | `test_deploy_cleanup` | deploy, sanity | Runs `discovery.yml --tags cleanup`. | Cleanup playbook exits successfully. |
| 1 | DISCOVERY_FVT_CLEANUP_V001 | `test_output_dir_removed` | sanity | Checks the discovery output directory after cleanup. | Output directory is removed or empty. |
| 2 | DISCOVERY_FVT_CLEANUP_V002 | `test_credentials_removed` | sanity | Verifies credentials file removal after cleanup. | Credentials file is removed from input directory. |
| 3 | DISCOVERY_FVT_CLEANUP_V003 | `test_pxe_mapping_files_removed` | functional | Verifies PXE mapping CSV files removal after cleanup. | No PXE mapping files remain in output directory. |
| 4 | DISCOVERY_FVT_CLEANUP_V004 | `test_discovery_report_files_removed` | functional | Verifies discovery report CSV files removal after cleanup. | No discovery report files remain in output directory. |

## Registry summary

| Phase | Execution IDs | Verification IDs | Total | Notes |
|-------|---------------|------------------|-------|-------|
| Precheck | `DISCOVERY_FVT_PRECHECK_E001` | — | 1 | Environment precheck. |
| Validate | `DISCOVERY_FVT_VALIDATE_E001` | `DISCOVERY_FVT_VALIDATE_V001`–`003` | 4 | Input and credential validation. |
| Credentials | `DISCOVERY_FVT_CREDENTIALS_E001` | — | 1 | Credential setup. |
| Execute | `DISCOVERY_FVT_EXECUTE_E001` | `DISCOVERY_FVT_EXECUTE_V001`–`006` | 7 | OME discovery execution and output verification. |
| Discovery (Full) | `DISCOVERY_FVT_DISCOVERY_E001` | — | 1 | Complete discovery workflow. |
| Cleanup | `DISCOVERY_FVT_CLEANUP_E001` | `DISCOVERY_FVT_CLEANUP_V001`–`004` | 5 | Artifact cleanup. |
| **Total** | | | **19** | All FVT test cases. |

## Running the tests

### Run all tests for a specific phase

```bash
# Run precheck tests
./run_validation.sh discovery precheck test

# Run validate tests
./run_validation.sh discovery validate test

# Run execute tests
./run_validation.sh discovery execute test

# Run full discovery tests
./run_validation.sh discovery discovery test

# Run cleanup tests
./run_validation.sh discovery cleanup test

# Run cleanup verification only
./run_validation.sh discovery cleanup verify

# Run cleanup verification with specific suite
./run_validation.sh discovery cleanup verify --suite status
```

### Run verification only (no deploy)

```bash
# Verify execute outputs only
./run_validation.sh discovery execute verify

# Verify specific suite
./run_validation.sh discovery execute verify --suite output

# Verify cleanup outputs only
./run_validation.sh discovery cleanup verify

# Verify cleanup specific suite
./run_validation.sh discovery cleanup verify --suite status
```

### Run with specific markers

```bash
# Run sanity tests only
./run_validation.sh discovery execute verify --marker sanity

# Run functional tests only
./run_validation.sh discovery execute verify --marker functional
```

## Test data and configuration

Test datasets are located in `test/discovery/datasets/`. Each dataset contains
input files (`discovery_config.yml`, `network_spec.yml`) used for testing.

The test configuration is defined in `test/discovery/test_config.yml` and
credentials in `test/discovery/test_creds.yml` (encrypted with Ansible Vault).
