# Discovery — Test Case Registry

> All test cases for the discovery domain FVT automation.

## Test Case ID Convention

| Area | Prefix | Description |
|------|--------|-------------|
| Validate | `TC_VL_` | Input validation tests |
| Discovery | `TC_DS_` | End-to-end discovery tests |

---

## Validate Scenario (`fvt/validate/`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| TC_VL_000 | `test_deploy_validate` | Deploy discovery.yml (validate inputs) | deploy, sanity |
| TC_VL_001 | `test_input_config_exists` | Verify discovery_config.yml exists | sanity |
| TC_VL_002 | `test_network_spec_exists` | Verify network_spec.yml exists | sanity |
| TC_VL_003 | `test_credentials_present` | Verify credentials file present | sanity |

---

## Discovery Scenario (`fvt/discovery/`)

| TC ID | Test Function | Description | Marker |
|-------|---------------|-------------|--------|
| TC_DS_000 | `test_deploy_discovery` | Deploy discovery.yml full run | deploy, sanity |
| TC_DS_001 | `test_output_dir_exists` | Verify output directory created | sanity |
| TC_DS_002 | `test_pxe_mapping_created` | Verify PXE mapping CSV created | sanity |
| TC_DS_003 | `test_pxe_mapping_columns` | Verify required CSV columns | functional |
| TC_DS_004 | `test_pxe_mapping_has_rows` | Verify CSV has data rows | functional |
| TC_DS_005 | `test_pxe_mapping_symlink` | Verify symlink to latest file | sanity |
| TC_DS_006 | `test_discovery_report_created` | Verify discovery report CSV | functional |
