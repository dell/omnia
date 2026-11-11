# Discovery — Test Case Registry

> All test cases for the discovery domain FVT automation.

## Test Case ID Convention

| Area | Prefix | Description |
|------|--------|-------------|
| Precheck | `TC_PC_` | Environment precheck tests |
| Validate | `TC_VL_` | Input validation tests |
| Credentials | `TC_CR_` | Credential management tests |
| Execute | `TC_EX_` | Execute (OME discovery) tests |
| Discovery | `TC_DS_` | End-to-end discovery tests (full run) |
| Cleanup | `TC_CL_` | Cleanup tests |

---

## Precheck Scenario (`fvt/precheck/`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| TC_PC_000 | `test_deploy_precheck` | Validate data path and conditional OME TCP/443 reachability | deploy, sanity |

---

## Validate Scenario (`fvt/validate/`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| TC_VL_000 | `test_deploy_validate` | Deploy discovery.yml --tags validate | deploy, sanity |
| TC_VL_001 | `test_input_config_exists` | Verify discovery_config.yml exists | sanity |
| TC_VL_002 | `test_network_spec_exists` | Verify network_spec.yml exists | sanity |
| TC_VL_003 | `test_credentials_present` | Verify credentials file present | sanity |

---

## Credentials Scenario (`fvt/credentials/`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| TC_CR_000 | `test_deploy_credentials` | Deploy discovery.yml --tags credentials | deploy, sanity |

---

## Execute Scenario (`fvt/execute/`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| TC_EX_000 | `test_deploy_execute` | Deploy discovery.yml --tags execute | deploy, sanity |
| TC_EX_001 | `test_output_dir_exists` | Verify output directory created | sanity |
| TC_EX_002 | `test_pxe_mapping_created` | Verify PXE mapping CSV created | sanity |
| TC_EX_003 | `test_pxe_mapping_columns` | Verify required CSV columns | functional |
| TC_EX_004 | `test_pxe_mapping_has_rows` | Verify CSV has data rows | functional |
| TC_EX_005 | `test_pxe_mapping_symlink` | Verify symlink to latest file | sanity |
| TC_EX_006 | `test_discovery_report_created` | Verify discovery report CSV | functional |

### PXE Mapping Validation (`fvt/execute/output/test_pxe_validation.py`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| DISCOVERY_FVT_EXECUTE_V007 | `test_functional_groups_supported` | Verify all functional groups are Omnia-supported | functional |
| DISCOVERY_FVT_EXECUTE_V008 | `test_ip_correlation` | Verify ADMIN_IP/IB_IP correlation with BMC_IP | functional |
| DISCOVERY_FVT_EXECUTE_V009 | `test_parent_service_tag` | Verify PARENT_SERVICE_TAG rules for slurm_node groups | functional |
| DISCOVERY_FVT_EXECUTE_V014 | `test_pxe_mapping_orchestrator_contract` | Verify PXE mapping CSV format for Orchestrator | functional, contract |

### OME Integration Validation (`fvt/execute/ome/test_ome_validation.py`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| DISCOVERY_FVT_EXECUTE_V010 | `test_ome_static_groups_match` | Verify OME static groups match PXE mapping | functional, ome |
| DISCOVERY_FVT_EXECUTE_V011 | `test_ome_unassigned_devices` | Verify OME devices without static group | functional, ome |
| DISCOVERY_FVT_EXECUTE_V012 | `test_admin_mac_validation` | Verify ADMIN_MAC matches OME first active NIC | functional, ome |
| DISCOVERY_FVT_EXECUTE_V013 | `test_ib_nic_name_validation` | Verify IB_NIC_NAME matches OME first active IB NIC | functional, ome |

> **Note:** OME integration tests require OME connectivity and credentials configured in `test_config.yml`. Tests are skipped if OME is not configured.

---

## Discovery Scenario (`fvt/discovery/`) — Full Run

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| TC_DS_000 | `test_deploy_discovery` | Deploy discovery.yml full run | deploy, sanity |
| TC_DS_001 | `test_output_dir_exists` | Verify output directory created | sanity |
| TC_DS_002 | `test_pxe_mapping_created` | Verify PXE mapping CSV created | sanity |
| TC_DS_003 | `test_pxe_mapping_columns` | Verify required CSV columns | functional |
| TC_DS_004 | `test_pxe_mapping_has_rows` | Verify CSV has data rows | functional |
| TC_DS_005 | `test_pxe_mapping_symlink` | Verify symlink to latest file | sanity |
| TC_DS_006 | `test_discovery_report_created` | Verify discovery report CSV | functional |

---

## Cleanup Scenario (`fvt/cleanup/`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| TC_CL_000 | `test_deploy_cleanup` | Deploy discovery.yml --tags cleanup | deploy, sanity |
