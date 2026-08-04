# Test Cases — Build Stream FVT

All test case IDs follow the format `TC_<AREA>_<SEQ>`.

---

## build_stream (Full End-to-End)

| TC ID | Test | Suite | Markers | Description |
|-------|------|-------|---------|-------------|
| TC_BS_000 | `test_deploy_build_stream` | *(root)* | deploy, sanity | Deploy build_stream.yml (no tags — prepare + build) |
| TC_BS_001 | `test_build_stream_enabled` | infrastructure/ | sanity, infrastructure | Verify build_stream is enabled in config |
| TC_BS_002 | `test_build_stream_health` | infrastructure/ | sanity, infrastructure | Verify build_stream API /health endpoint |
| TC_BS_003 | `test_postgres_tables` | infrastructure/ | sanity, infrastructure | Verify PostgreSQL database tables |
| TC_BS_004 | `test_gitlab_server_running` | infrastructure/ | sanity, infrastructure | Verify GitLab server running |
| TC_BS_005 | `test_gitlab_runner_running` | infrastructure/ | sanity, infrastructure | Verify GitLab runner running |

---

## prepare

| TC ID | Test | Suite | Markers | Description |
|-------|------|-------|---------|-------------|
| TC_PR_001 | `test_deploy_prepare` | *(root)* | deploy, sanity | Deploy build_stream.yml --tags prepare |
| TC_PR_002 | `test_bsm_container_after_prepare` | infrastructure/ | sanity, infrastructure | Verify BSM container running |
| TC_PR_003 | `test_postgres_container_after_prepare` | infrastructure/ | sanity, infrastructure | Verify PostgreSQL container running |
| TC_PR_004 | `test_api_health_after_prepare` | infrastructure/ | sanity, infrastructure | Verify API health after prepare |
| TC_PR_005 | `test_postgres_tables_after_prepare` | infrastructure/ | sanity, infrastructure | Verify PostgreSQL tables after prepare |
| TC_PR_006 | `test_ports_listening_after_prepare` | infrastructure/ | sanity, infrastructure | Verify service ports listening |
| TC_PR_007 | `test_input_config_exists` | infrastructure/ | sanity | Verify build_stream_config.yml on target |

---

## cleanup

| TC ID | Test | Suite | Markers | Description |
|-------|------|-------|---------|-------------|
| TC_CL_001 | `test_deploy_cleanup` | *(root)* | deploy, sanity | Deploy build_stream.yml --tags cleanup |
| TC_CL_002 | `test_containers_removed` | cleanup/ | sanity | Verify all containers removed |
| TC_CL_003 | `test_ports_closed` | cleanup/ | sanity | Verify service ports closed |
| TC_CL_004 | `test_gitlab_removed` | cleanup/ | sanity | Verify GitLab containers removed |

---

## Summary

| Scenario | Prefix | Test Count |
|----------|--------|------------|
| build_stream | TC_BS_ | 6 |
| prepare | TC_PR_ | 7 |
| cleanup | TC_CL_ | 4 |
| **Total** | | **17** |

---

## Molecule Test Coverage Mapping

Tests adapted from `automation_v22/molecule/build_stream/`:

| Molecule Test | New FVT TC | Status |
|---------------|-----------|--------|
| `test_build_stream_enabled` | TC_BS_001 | ✅ Covered |
| `test_build_stream_health` | TC_BS_002 | ✅ Covered |
| `test_postgres_tables` | TC_BS_003 | ✅ Covered |
| `test_gitlab_server_running` | TC_BS_004 | ✅ Covered |
| `test_gitlab_runner_running` | TC_BS_005 | ✅ Covered |
| `test_autotrigger_pipeline` | — | ⏳ Future (pipeline/ suite) |
| `test_manual_pipeline` | — | ⏳ Future (pipeline/ suite) |
| `test_cleanup_pipeline` | — | ⏳ Future (pipeline/ suite) |
| `test_generated_input` | — | ⏳ Future (input_verification/ suite) |
| `test_stress_*` | — | ⏳ Future (nft/ directory) |
