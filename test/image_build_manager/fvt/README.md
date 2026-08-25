# Test Cases — Image Build Manager FVT

> Authoritative test case registry for the `fvt/` directory.

All test case IDs follow the format `TC_<AREA>_<SEQ>`.

---

## precheck

| TC ID | Test | Suite | Markers | Description |
|-------|------|-------|---------|-------------|
| TC_PC_001 | `test_deploy_precheck` | *(root)* | deploy, sanity | Deploy image_build_manager --tags precheck |
| TC_PC_002 | `test_env_vars_present` | connectivity/ | sanity | Verify all omnia.env vars present on target |
| TC_PC_003 | `test_target_connectivity` | connectivity/ | sanity | Verify target host SSH connectivity |
| TC_PC_004 | `test_hostname_domain` | connectivity/ | sanity | Verify hostname and domain match omnia.env |
| TC_PC_005 | `test_admin_ip_assigned` | connectivity/ | sanity | Verify admin IP assigned to local interface |
| TC_PC_006 | `test_omnia_setup` | connectivity/ | sanity | Verify omnia.sh setup completed |

---

## validate

| TC ID | Test | Suite | Markers | Description |
|-------|------|-------|---------|-------------|
| TC_VL_001 | `test_deploy_validate` | *(root)* | deploy, sanity | Deploy image_build_manager --tags validate |
| TC_VL_002 | `test_input_config_exists` | status/ | sanity | Verify image_build_config.yml exists on target |
| TC_VL_003 | `test_credentials_present` | status/ | sanity | Verify credentials file is synced to target |

---

## prepare

| TC ID | Test | Suite | Markers | Description |
|-------|------|-------|---------|-------------|
| TC_PR_001 | `test_deploy_prepare` | *(root)* | deploy, sanity | Deploy image_build_manager --tags prepare |
| TC_PR_002 | `test_storage_backend_after_prepare` | container/ | sanity | Verify S3 storage backend after prepare |
| TC_PR_003 | `test_registry_after_prepare` | container/ | sanity | Verify registry container running |
| TC_PR_004 | `test_services_active` | container/ | sanity | Verify systemd services active (minio, registry) |
| TC_PR_005 | `test_firewall_ports_open` | container/ | sanity | Verify firewall ports open (9000, 9001, 5000) |
| TC_PR_006 | `test_s3cmd_configured` | container/ | sanity | Verify s3cmd installed and configured |
| TC_PR_007 | `test_registry_reachable` | container/ | sanity | Verify registry is reachable via HTTP |
| TC_PR_008 | `test_s3_buckets_after_prepare` | s3/ | sanity | Verify S3 buckets created |

---

## build

| TC ID | Test | Suite | Markers | Description |
|-------|------|-------|---------|-------------|
| TC_BD_001 | `test_deploy_build` | *(root)* | deploy, sanity | Deploy image_build_manager --tags build |
| TC_BD_002 | `test_s3_images_x86_64` | s3/ | x86_64, sanity | Verify x86_64 images pushed to S3 |
| TC_BD_003 | `test_s3_images_aarch64` | s3/ | aarch64, sanity | Verify aarch64 images pushed to S3 |
| TC_BD_004 | `test_registry_images_x86_64` | registry/ | x86_64, sanity | Verify x86_64 images in registry |
| TC_BD_005 | `test_build_status` | registry/ | x86_64, aarch64, sanity | Verify build_status.yml reports success |
| TC_BD_006 | `test_functional_groups_x86_64` | registry/ | x86_64, sanity | Verify all x86_64 functional groups built |
| TC_BD_012 | `test_registry_images_aarch64` | registry/ | aarch64, sanity | Verify aarch64 images in registry |
| TC_BD_013 | `test_functional_groups_aarch64` | registry/ | aarch64, sanity | Verify all aarch64 functional groups built |
| TC_BD_014 | `test_image_packages_x86_64` | image_verification/ | x86_64, sanity | Verify packages installed in x86_64 S3 images |
| TC_BD_015 | `test_image_packages_aarch64` | image_verification/ | aarch64, sanity | Verify packages installed in aarch64 S3 images |
| TC_BD_016 | `test_repo_ssl_verify_applied` | *(validate/status)* | x86_64, functional | Verify repo_ssl_verify is applied in build templates |

### Build-type naming convention

These cases verify that the `-imgbld` / `-imgth` artifact suffix is applied correctly
so the two build engines never overwrite each other's registry images or S3 objects.

| TC ID | Test | Suite | Markers | image_build_type | Description |
|-------|------|-------|---------|-----------------|-------------|
| TC_BD_007 | `test_registry_naming_image_builder_x86_64` | naming/ | x86_64, sanity | image-builder | Registry repos carry `-imgbld` suffix; no `-imgth` contamination |
| TC_BD_008 | `test_s3_naming_image_builder_x86_64` | naming/ | x86_64, sanity | image-builder | S3 boot-images paths carry `-imgbld`; no `-imgth` contamination |
| TC_BD_009 | `test_registry_naming_image_thrillhouse_x86_64` | naming/ | x86_64, sanity | image-thrillhouse | Registry repos carry `-imgth` suffix; no `-imgbld` contamination |
| TC_BD_010 | `test_s3_naming_image_thrillhouse_x86_64` | naming/ | x86_64, sanity | image-thrillhouse | S3 boot-images paths carry `-imgth`; no `-imgbld` contamination |
| TC_BD_011 | `test_artifact_suffix_isolation` | naming/ | x86_64, functional | both | `-imgbld` and `-imgth` base names never collide in registry or S3 |

> **Skip behaviour**: TC_BD_007/008 skip automatically when `image_build_type = image-thrillhouse`
> and TC_BD_009/010 skip when `image_build_type = image-builder`.  TC_BD_011 runs in all cases.

> **Running naming tests only**:
> ```bash
> ./run_validation.sh image_build_manager build verify --suite naming
> ./run_validation.sh image_build_manager build verify --suite naming --marker x86_64+sanity
> ```

---

## cleanup

| TC ID | Test | Suite | Markers | Description |
|-------|------|-------|---------|-------------|
| TC_CL_001 | `test_deploy_cleanup` | *(root)* | deploy, sanity | Deploy image_build_manager --tags cleanup |
| TC_CL_002 | `test_containers_removed` | cleanup/ | sanity | Verify containers removed |
| TC_CL_003 | `test_services_removed` | cleanup/ | sanity | Verify systemd services stopped |
| TC_CL_004 | `test_firewall_ports_closed` | cleanup/ | sanity | Verify firewall ports closed |
| TC_CL_005 | `test_s3_artifacts_removed` | cleanup/ | sanity | Verify S3 buckets removed |
| TC_CL_006 | `test_s3cfg_removed` | cleanup/ | sanity | Verify s3cmd configuration removed |
| TC_CL_007 | `test_build_output_removed` | cleanup/ | sanity | Verify build_status.yml removed |
| TC_CL_008 | `test_registry_cleaned` | cleanup/ | sanity | Verify registry has no images |

---

## cleanup_images

| TC ID | Test | Suite | Markers | Description |
|-------|------|-------|---------|-------------|
| TC_CI_001 | `test_deploy_cleanup_images` | *(root)* | deploy, sanity | Deploy image_build_manager --tags cleanup_images |
| TC_CI_002 | `test_s3_images_cleaned` | *(root)* | sanity | Verify S3 images deleted after cleanup_images |
| TC_CI_003 | `test_registry_images_cleaned` | *(root)* | sanity | Verify registry images deleted after cleanup_images |

---

## Summary

| Tag | Prefix | Test Count | Notes |
|-----|--------|------------|-------|
| precheck | TC_PC_ | 6 (001–006) | |
| validate | TC_VL_ | 4 (001–004) | 004 = repo_ssl_verify_config |
| prepare | TC_PR_ | 8 (001–008) | |
| build | TC_BD_ | 16 (001–016) | 007–011 naming, 012–015 aarch64+packages, 016 repo_ssl_verify |
| cleanup | TC_CL_ | 8 (001–008) | |
| cleanup_images | TC_CI_ | 3 (001–003) | |
| **Total** | | **45** | Plus TC_IB_001 (full-stack deploy) |

### Naming Convention Test Matrix

| TC ID | Runs when | Skips when |
|-------|-----------|------------|
| TC_BD_007 | `image_build_type: image-builder` | `image_build_type: image-thrillhouse` |
| TC_BD_008 | `image_build_type: image-builder` | `image_build_type: image-thrillhouse` |
| TC_BD_009 | `image_build_type: image-thrillhouse` | `image_build_type: image-builder` |
| TC_BD_010 | `image_build_type: image-thrillhouse` | `image_build_type: image-builder` |
| TC_BD_011 | always | — |
