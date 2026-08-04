# Test Cases — Repo Manager FVT

All test case IDs follow the format `TC_<AREA>_<SEQ>` (3-digit zero-padded).
Deploy tests always use `TC_XX_000`.

Reference: `src/repo_manager/playbooks/repo_manager.yml`
Valid tags: `validate`, `deploy`, `download`, `status`, `cleanup_pulp`, `cleanup_repos`, `upgrade`, `rollback`

---

## repo_manager (Full End-to-End)

| TC ID | Test | Suite | Markers | Description |
|-------|------|-------|---------|-------------|
| TC_RM_000 | `test_deploy_repo_manager` | *(root)* | deploy, sanity | Deploy repo_manager.yml (no tags) |
| TC_RM_002 | `test_pulp_container_running` | pulp/ | sanity | Verify Pulp container is running |
| TC_RM_003 | `test_pulp_healthy` | pulp/ | sanity | Verify Pulp is healthy (database connected) |
| TC_RM_004 | `test_pulp_port_listening` | pulp/ | sanity | Verify Pulp port 2225 is listening |
| TC_RM_005 | `test_pulp_cli_configured` | pulp/ | sanity | Verify Pulp CLI is configured (binary + cli.toml) |
| TC_RM_006 | `test_pulp_api_endpoint` | pulp/ | sanity | Verify Pulp API endpoint is reachable |
| TC_RM_007 | `test_pulp_certs` | pulp/ | sanity | Verify Pulp SSL certificates present |
| TC_RM_008 | `test_pulp_directories` | pulp/ | sanity | Verify Pulp data directories exist |
| TC_RM_009 | `test_repo_status_file` | repo_status/ | sanity | Verify repo_status.yml exists and reports success |
| TC_RM_010 | `test_repos_synced` | repo_status/ | sanity | Verify repositories are synced in Pulp |

---

## validate

| TC ID | Test | Suite | Markers | Description |
|-------|------|-------|---------|-------------|
| TC_VL_000 | `test_deploy_validate` | *(root)* | deploy, sanity | Deploy repo_manager.yml --tags validate |
| TC_VL_002 | `test_input_config_exists` | status/ | sanity | Verify repo_manager_config.yml exists on target |
| TC_VL_003 | `test_credentials_present` | status/ | sanity | Verify credentials file is present |
| TC_VL_004 | `test_endpoint_config_exists` | status/ | sanity | Verify endpoint config exists |
| TC_VL_005 | `test_software_config_exists` | status/ | sanity | Verify software_config.json exists |

---

## deploy

| TC ID | Test | Suite | Markers | Description |
|-------|------|-------|---------|-------------|
| TC_DP_000 | `test_deploy_deploy` | *(root)* | deploy, sanity | Deploy repo_manager.yml --tags deploy |
| TC_DP_002 | `test_pulp_container_running` | pulp/ | sanity | Verify Pulp container running after deploy |
| TC_DP_003 | `test_pulp_healthy` | pulp/ | sanity | Verify Pulp healthy after deploy (database connected) |
| TC_DP_004 | `test_pulp_port_listening` | pulp/ | sanity | Verify Pulp port listening after deploy |
| TC_DP_005 | `test_pulp_cli_configured` | pulp/ | sanity | Verify Pulp CLI configured after deploy (binary + cli.toml) |
| TC_DP_006 | `test_pulp_api_endpoint` | pulp/ | sanity | Verify Pulp API endpoint reachable after deploy |
| TC_DP_007 | `test_pulp_quadlet_exists` | pulp/ | sanity | Verify Pulp quadlet/systemd unit file exists |
| TC_DP_008 | `test_pulp_certs` | pulp/ | sanity | Verify Pulp SSL certificates present (HTTPS mode) |
| TC_DP_009 | `test_pulp_directories` | pulp/ | sanity | Verify Pulp data directories exist |

---

## repo_operations

Mirrors `src/repo_manager/playbooks/repo_operations/`.

### download (--tags download)

| TC ID | Test | Suite | Markers | Description |
|-------|------|-------|---------|-------------|
| TC_DL_000 | `test_deploy_download` | download/ | deploy, sanity | Deploy repo_manager.yml --tags download |
| TC_DL_002 | `test_software_config_valid` | download/repos/ | sanity | Verify software_config.json is valid |
| TC_DL_003 | `test_repos_synced` | download/repos/ | functional | Verify repositories are synced in Pulp |
| TC_DL_004 | `test_repo_status_generated` | download/repos/ | sanity | Verify repo_status.yml generated after download |
| TC_DL_005 | `test_repo_status_success` | download/packages/ | sanity | Verify repo_status.yml reports success |

### status (--tags status)

| TC ID | Test | Suite | Markers | Description |
|-------|------|-------|---------|-------------|
| TC_ST_000 | `test_run_status` | status/ | deploy, sanity | Deploy repo_manager.yml --tags status |
| TC_ST_002 | `test_pulp_running_for_status` | status/status/ | sanity | Verify Pulp container running (prerequisite) |
| TC_ST_003 | `test_repo_status_exists` | status/status/ | sanity | Verify repo_status.yml exists |
| TC_ST_004 | `test_repo_status_content` | status/status/ | functional | Verify repo_status.yml has expected content |

---

## cleanup

| TC ID | Test | Suite | Markers | Description |
|-------|------|-------|---------|-------------|
| TC_CL_000 | `test_deploy_cleanup` | *(root)* | deploy, sanity | Deploy repo_manager.yml --tags cleanup_pulp |
| TC_CL_002 | `test_pulp_removed` / `test_pulp_container_not_running` | cleanup/ | sanity | Verify Pulp container removed |
| TC_CL_003 | `test_pulp_data_removed` / `test_containers_fully_removed` | cleanup/ | sanity | Verify Pulp data directories removed / container fully removed |
| TC_CL_004 | `test_services_removed` / `test_pulp_image_removed` | cleanup/ | sanity | Verify Pulp service removed / image removed |
| TC_CL_005 | `test_containers_removed` / `test_services_removed` | cleanup/ | sanity | Verify no containers remain / services stopped |
| TC_CL_006 | `test_pulp_image_removed` / `test_pulp_quadlet_removed` | cleanup/ | sanity | Verify Pulp container image removed / quadlet removed |
| TC_CL_007 | `test_pulp_quadlet_removed` / `test_pulp_data_removed` | cleanup/ | sanity | Verify Pulp quadlet removed / data directories removed |
| TC_CL_008 | `test_pulp_logs_cleaned` | cleanup/ | sanity | Verify Pulp log directories cleaned |

---

## Summary

| Scenario | Prefix | Test Count |
|----------|--------|------------|
| repo_manager | TC_RM_ | 10 |
| validate | TC_VL_ | 5 |
| deploy | TC_DP_ | 9 |
| repo_operations/download | TC_DL_ | 5 |
| repo_operations/status | TC_ST_ | 4 |
| cleanup | TC_CL_ | 8 |
| **Total** | | **41** |
