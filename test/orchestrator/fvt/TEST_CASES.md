# Orchestrator — Test Case Registry

> All test cases for the orchestrator domain FVT automation.

## Test Case ID Convention

| Area | Prefix | Description |
|------|--------|-------------|
| Validate | `TC_VL_` | Input validation tests |
| Prepare | `TC_PR_` | Prepare/deploy OpenCHAMI tests |
| Provision | `TC_PV_` | Node provisioning tests |
| Cleanup | `TC_CL_` | Cleanup verification tests |
| End-to-End | `TC_E2E_` | Full orchestrator tests |

---

## Validate Scenario (`fvt/validate/`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| TC_VL_000 | `test_deploy_validate` | Deploy orchestrator.yml (validate) | deploy, sanity |
| TC_VL_001 | `test_input_config_exists` | Verify orchestrator_config.yml exists | sanity |
| TC_VL_002 | `test_omnia_config_exists` | Verify omnia_config.yml exists | sanity |
| TC_VL_003 | `test_network_spec_exists` | Verify network_spec.yml exists | sanity |
| TC_VL_004 | `test_credentials_present` | Verify credentials file present | sanity |
| TC_VL_005 | `test_repo_status_exists` | Verify repo_status.yml exists | sanity |

---

## Prepare Scenario (`fvt/prepare/`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| TC_PR_000 | `test_deploy_prepare` | Deploy orchestrator.yml --tags prepare | deploy, sanity |
| TC_PR_001 | `test_openchami_containers_running` | Verify all OpenCHAMI containers running | sanity |
| TC_PR_002 | `test_openchami_services_active` | Verify systemd services active | sanity |
| TC_PR_003 | `test_openchami_api_reachable` | Verify OpenCHAMI API reachable | functional |

---

## Provision Scenario (`fvt/provision/`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| TC_PV_000 | `test_deploy_provision` | Deploy orchestrator.yml (full provision) | deploy, sanity |

---

## Cleanup Scenario (`fvt/cleanup/`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| TC_CL_000 | `test_deploy_cleanup` | Deploy orchestrator.yml --tags cleanup | deploy, sanity |
| TC_CL_001 | `test_containers_removed` | Verify containers removed | sanity |
| TC_CL_002 | `test_services_removed` | Verify services stopped | sanity |
| TC_CL_003 | `test_firewall_ports_closed` | Verify firewall ports closed | functional |
