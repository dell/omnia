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
| TC_PC_000 | `test_deploy_precheck` | Deploy discovery.yml --tags precheck | deploy, sanity |

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
