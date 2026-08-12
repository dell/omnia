# Repo Manager — Test Cases Registry

This document provides a complete registry of all test cases for the Repo Manager FVT automation, organized by scenario.

## Test Case ID Prefixes

- **TC_RM** — Repo Manager (full end-to-end)
- **TC_VL** — Validate scenario
- **TC_DP** — Deploy scenario
- **TC_DL** — Download scenario (repo operations)
- **TC_ST** — Status scenario (repo operations)
- **TC_CL** — Cleanup scenario

---

## Scenario: repo_manager (Full End-to-End)

**Playbook**: `repo_manager.yml` (no tags — default: validate + deploy + download + status)

### Deploy Test

| TC ID | Test Function | Description |
|-------|---------------|-------------|
| TC_RM_000 | test_deploy_repo_manager | Deploy repo_manager (default: validate + deploy + download + status) |

### Verification Tests

| TC ID | Test Function | Description |
|-------|---------------|-------------|
| TC_RM_002 | test_pulp_container_running | Verify Pulp container is running |
| TC_RM_003 | test_pulp_healthy | Verify Pulp service is healthy and responding |
| TC_RM_004 | test_pulp_port_listening | Verify Pulp port (2225) is listening |
| TC_RM_005 | test_pulp_cli_configured | Verify Pulp CLI is installed and configured |
| TC_RM_006 | test_pulp_api_endpoint | Verify Pulp API endpoint is reachable |
| TC_RM_007 | test_pulp_certs | Verify Pulp SSL certificates present |
| TC_RM_008 | test_pulp_directories | Verify Pulp data directories exist |
| TC_RM_009 | test_repo_status_file | Verify repo_status.yml exists and reports success |
| TC_RM_010 | test_repos_synced | Verify repositories are synced in Pulp |

---

## Scenario: validate

**Playbook**: `repo_manager.yml --tags validate`

### Deploy Test

| TC ID | Test Function | Description |
|-------|---------------|-------------|
| TC_VL_000 | test_deploy_validate | Deploy repo_manager (validate) |

### Verification Tests

| TC ID | Test Function | Description |
|-------|---------------|-------------|
| TC_VL_002 | test_input_config_exists | Verify repo_manager_config.yml exists on target |
| TC_VL_003 | test_credentials_present | Verify credentials file is present |
| TC_VL_004 | test_endpoint_config_exists | Verify repo_manager_endpoint_config.yml exists on target |
| TC_VL_005 | test_software_config_exists | Verify software_config.json exists on target |

---

## Scenario: deploy

**Playbook**: `repo_manager.yml --tags deploy`

### Deploy Test

| TC ID | Test Function | Description |
|-------|---------------|-------------|
| TC_DP_000 | test_deploy_deploy | Deploy repo_manager (deploy) |

### Verification Tests

| TC ID | Test Function | Description |
|-------|---------------|-------------|
| TC_DP_002 | test_pulp_container_running | Verify Pulp container running after deploy |
| TC_DP_003 | test_pulp_healthy | Verify Pulp healthy after deploy (database connected) |
| TC_DP_004 | test_pulp_port_listening | Verify Pulp port listening after deploy |
| TC_DP_005 | test_pulp_cli_configured | Verify Pulp CLI configured after deploy (binary + cli.toml) |
| TC_DP_006 | test_pulp_api_endpoint | Verify Pulp API endpoint reachable after deploy |
| TC_DP_007 | test_pulp_quadlet_exists | Verify Pulp quadlet/systemd unit file exists |
| TC_DP_008 | test_pulp_certs | Verify Pulp SSL certificates present (HTTPS mode) |
| TC_DP_009 | test_pulp_directories | Verify Pulp data directories exist |

---

## Scenario: repo_operations (download)

**Playbook**: `repo_manager.yml --tags download`

### Deploy Test

| TC ID | Test Function | Description |
|-------|---------------|-------------|
| TC_DL_000 | test_deploy_download | Deploy repo_manager (download) |

### Verification Tests

| TC ID | Test Function | Description |
|-------|---------------|-------------|
| TC_DL_002 | test_software_config_valid | Verify software_config.json has valid JSON with required fields |
| TC_DL_003 | test_repos_synced | Verify repos are synced in Pulp after download |
| TC_DL_004 | test_repo_status_generated | Verify repo_status.yml generated after download |
| TC_DL_005 | test_repo_status_success | Verify repo_status.yml reports success |

---

## Scenario: repo_operations (status)

**Playbook**: `repo_manager.yml --tags status`

### Deploy Test

| TC ID | Test Function | Description |
|-------|---------------|-------------|
| TC_ST_000 | test_deploy_status | Deploy repo_manager (status) |

### Verification Tests

| TC ID | Test Function | Description |
|-------|---------------|-------------|
| TC_ST_002 | test_pulp_running | Verify Pulp container running (prerequisite for status) |
| TC_ST_003 | test_repo_status_exists | Verify repo_status.yml exists |
| TC_ST_004 | test_repo_status_content | Verify repo_status.yml has expected content |

---

## Scenario: cleanup

**Playbook**: `repo_manager.yml --tags cleanup`

### Deploy Test

| TC ID | Test Function | Description |
|-------|---------------|-------------|
| TC_CL_000 | test_deploy_cleanup | Deploy repo_manager (cleanup) |

### Verification Tests

| TC ID | Test Function | Description |
|-------|---------------|-------------|
| TC_CL_002 | test_pulp_removed | Verify Pulp container removed after cleanup |
| TC_CL_003 | test_containers_removed | Verify Pulp container fully removed (not even stopped) |
| TC_CL_004 | test_pulp_image_removed | Verify Pulp container image removed after cleanup |
| TC_CL_005 | test_services_removed | Verify Pulp systemd services stopped after cleanup |
| TC_CL_006 | test_pulp_quadlet_removed | Verify Pulp quadlet/systemd file removed after cleanup |
| TC_CL_007 | test_pulp_data_removed | Verify Pulp data directories removed after cleanup |
| TC_CL_008 | test_pulp_logs_cleaned | Verify Pulp log directories cleaned after cleanup |

---

## Test Markers

All tests are categorized with the following pytest markers:

- **@pytest.mark.deploy** — Playbook deployment tests
- **@pytest.mark.sanity** — Baseline verification (must-pass)
- **@pytest.mark.functional** — Functional verification
- **@pytest.mark.regression** — Regression tests
- **@pytest.mark.order(n)** — Test execution order (lower first)

## Test Execution Order

Within each scenario, tests execute in this order:
1. **Order 0** — Deploy test (`test_playbook.py`)
2. **Order 1+** — Verification tests (suite-specific)

## Running Tests

```bash
# Run all tests for a scenario
./run_validation.sh repo_manager test

# Run only verification tests
./run_validation.sh repo_manager verify

# Run with marker filter
./run_validation.sh repo_manager verify --marker sanity

# Run specific suite
./run_validation.sh repo_manager verify --suite pulp
```

---

## Related Files

- `library/vars/test_case_vars.py` — Source of TC ID and title mappings
- `library/messages/repo_manager_msgs.py` — Test names and assertion messages
- `test_run_config.yml` — Batch execution configuration
- `docs/test_config.md` — Configuration reference