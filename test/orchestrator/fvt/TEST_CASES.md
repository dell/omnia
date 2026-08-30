# Orchestrator — Test Case Registry

> All test cases for the orchestrator domain FVT automation.

## Test Case ID Convention

| Area | Prefix | Description |
|------|--------|-------------|
| Precheck | `TC_PC_` | Read-only input validation tests |
| Validate | `TC_VL_` | Input validation tests |
| Prepare | `TC_PR_` | Prepare/deploy OpenCHAMI tests |
| Deploy | `TC_DP_` | Deploy OpenCHAMI + OpenLDAP tests |
| Provision | `TC_PV_` | Node provisioning tests |
| PXE Boot | `TC_PX_` | PXE boot on iDRAC nodes |
| Cleanup | `TC_CL_` | Cleanup verification tests |
| Upgrade | `TC_UG_` | In-place upgrade tests |
| Rollback | `TC_RB_` | Rollback to previous state tests |
| End-to-End | `TC_E2E_` | Full orchestrator tests |

---

## Precheck Scenario (`fvt/precheck/`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| TC_PC_000 | `test_deploy_precheck` | Deploy orchestrator.yml --tags precheck | deploy, sanity |

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

## Deploy Scenario (`fvt/deploy/`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| TC_DP_000 | `test_deploy_deploy` | Deploy orchestrator.yml --tags deploy | deploy, sanity |
| TC_DP_001 | `test_openchami_containers_after_deploy` | Verify OpenCHAMI containers running after deploy | sanity |
| TC_DP_002 | `test_services_active_after_deploy` | Verify systemd services active after deploy | sanity |
| TC_DP_003 | `test_openchami_api_after_deploy` | Verify OpenCHAMI API reachable after deploy | functional |

---

## Provision Scenario (`fvt/provision/`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| TC_PV_000 | `test_deploy_provision` | Deploy orchestrator.yml (full provision) | deploy, sanity |

---

## PXE Boot Scenario (`fvt/pxeboot/`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| TC_PX_000 | `test_deploy_pxeboot` | Deploy orchestrator.yml --tags pxeboot | deploy, sanity |

---

## Cleanup Scenario (`fvt/cleanup/`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| TC_CL_000 | `test_deploy_cleanup` | Deploy orchestrator.yml --tags cleanup | deploy, sanity |
| TC_CL_001 | `test_containers_removed` | Verify containers removed | sanity |
| TC_CL_002 | `test_services_removed` | Verify services stopped | sanity |
| TC_CL_003 | `test_firewall_ports_closed` | Verify firewall ports closed | functional |

---

## Upgrade Scenario (`fvt/upgrade/`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| TC_UG_000 | `test_deploy_upgrade` | Deploy orchestrator.yml --tags upgrade | deploy, sanity |

---

## Rollback Scenario (`fvt/rollback/`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| TC_RB_000 | `test_deploy_rollback` | Deploy orchestrator.yml --tags rollback | deploy, sanity |
