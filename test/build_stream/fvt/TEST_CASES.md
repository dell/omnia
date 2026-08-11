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

## pipeline (Auto-Trigger Build)

| TC ID | Test | Suite | Markers | Description |
|-------|------|-------|---------|-------------|
| TC_PL_001 | `test_trigger_build_pipeline` | pipeline/ | pipeline | Upload catalog to trigger build pipeline |
| TC_PL_002 | `test_core_stage_completion[upload]` | pipeline/ | pipeline | Monitor upload stage |
| TC_PL_003 | `test_core_stage_completion[parse-catalog]` | pipeline/ | pipeline | Monitor parse-catalog stage |
| TC_PL_004 | `test_core_stage_completion[generate-input]` | pipeline/ | pipeline | Monitor generate-input stage |
| TC_PL_005 | `test_core_stage_completion[create-local-repo]` | pipeline/ | pipeline | Monitor create-local-repo stage |
| TC_PL_006 | `test_build_image_x86_64` | pipeline/ | pipeline | Monitor build-image-x86_64 stage |
| TC_PL_007 | `test_build_image_aarch64` | pipeline/ | pipeline | Monitor build-image-aarch64 stage |
| TC_PL_008 | `test_verify_stages_in_db` | pipeline/ | pipeline | Verify all stages in database |
| TC_PL_009 | `test_images_created` | pipeline/ | pipeline | Verify images created for job |
| TC_PL_010 | `test_image_groups_created` | pipeline/ | pipeline | Verify image groups created |
| TC_PL_011 | `test_catalog_roles` | pipeline/ | pipeline | Verify catalog roles from API |
| TC_PL_012 | `test_verify_registry_images` | pipeline/ | pipeline | Verify container images in registry |
| TC_PL_013 | `test_verify_s3_boot_images` | pipeline/ | pipeline | Verify S3 boot images |

---

## pipeline (Manual Deploy)

| TC ID | Test | Suite | Markers | Description |
|-------|------|-------|---------|-------------|
| TC_DP_001 | `test_trigger_deploy_pipeline` | pipeline/ | pipeline, deploy | Trigger deploy pipeline via PXE commit |
| TC_DP_002 | `test_select_image_for_deploy` | pipeline/ | pipeline, deploy | Select image group for deployment |
| TC_DP_003 | `test_play_deploy_job` | pipeline/ | pipeline, deploy | Play deploy trigger job |
| TC_DP_004 | `test_deploy_stage_completion[deploy]` | pipeline/ | pipeline, deploy | Monitor deploy stage |
| TC_DP_005 | `test_deploy_stage_completion[restart]` | pipeline/ | pipeline, deploy | Monitor restart stage |
| TC_DP_006 | `test_deploy_stage_completion[validate-image]` | pipeline/ | pipeline, deploy | Monitor validate-image stage |
| TC_DP_007 | `test_verify_deploy_stages_in_db` | pipeline/ | pipeline, deploy | Verify deploy stages in database |

---

## pipeline (Cleanup)

| TC ID | Test | Suite | Markers | Description |
|-------|------|-------|---------|-------------|
| TC_CP_001 | `test_trigger_cleanup_pipeline` | pipeline/ | pipeline, cleanup | Trigger cleanup pipeline |
| TC_CP_002 | `test_select_image_for_cleanup` | pipeline/ | pipeline, cleanup | Select image group for cleanup |
| TC_CP_003 | `test_play_cleanup_job` | pipeline/ | pipeline, cleanup | Play cleanup trigger job |
| TC_CP_004 | `test_wait_for_cleanup_completion` | pipeline/ | pipeline, cleanup | Wait for image group CLEANED status |
| TC_CP_005 | `test_verify_image_group_cleaned` | pipeline/ | pipeline, cleanup | Verify CLEANED in database |
| TC_CP_006 | `test_verify_registry_images_removed` | pipeline/ | pipeline, cleanup | Verify registry images removed |
| TC_CP_007 | `test_verify_s3_images_removed` | pipeline/ | pipeline, cleanup | Verify S3 images removed |

---

## generated_input (Input Verification)

| TC ID | Test | Suite | Markers | Description |
|-------|------|-------|---------|-------------|
| TC_GI_001 | `test_clone_omnia_repo` | pipeline/ | generated_input | Clone Omnia repo for comparison |
| TC_GI_002 | `test_software_config_readable` | pipeline/ | generated_input | Read software_config.json |
| TC_GI_003 | `test_verify_generated_inputs` | pipeline/ | generated_input | Compare generated vs source configs |
| TC_GI_004 | `test_cleanup_clone` | pipeline/ | generated_input | Remove cloned repo |

---

## stress (Non-Functional Tests)

| TC ID | Test | Suite | Markers | Description |
|-------|------|-------|---------|-------------|
| TC_ST_001 | `test_stress_build_pipelines` | stress/ | stress | Repeated build pipeline executions |
| TC_ST_002 | `test_stress_cleanup_all_image_groups` | stress/ | stress, cleanup | Clean all image groups sequentially |
| TC_ST_003 | `test_cleanup_and_rebuild_cycles` | stress/ | stress | Build → cleanup → rebuild cycles |

---

## Summary

| Scenario | Prefix | Test Count |
|----------|--------|------------|
| build_stream | TC_BS_ | 6 |
| prepare | TC_PR_ | 7 |
| cleanup | TC_CL_ | 4 |
| pipeline (build) | TC_PL_ | 13 |
| pipeline (deploy) | TC_DP_ | 7 |
| pipeline (cleanup) | TC_CP_ | 7 |
| generated_input | TC_GI_ | 4 |
| stress | TC_ST_ | 3 |
| **Total** | | **51** |

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
| `test_autotrigger_pipeline` | TC_PL_001–TC_PL_013 | ✅ Covered |
| `test_manual_pipeline` | TC_DP_001–TC_DP_007 | ✅ Covered |
| `test_cleanup_pipeline` | TC_CP_001–TC_CP_007 | ✅ Covered |
| `test_generated_input` | TC_GI_001–TC_GI_004 | ✅ Covered |
| `test_stress_build_pipeline` | TC_ST_001 | ✅ Covered |
| `test_stress_cleanup_pipeline` | TC_ST_002 | ✅ Covered |
| `test_stress_cleanup_and_rebuild` | TC_ST_003 | ✅ Covered |
