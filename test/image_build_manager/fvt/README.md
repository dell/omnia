# Image Build Manager Functional Verification Tests

This document is the authoritative test-case registry for
`test/image_build_manager/fvt/`. It describes what each test validates and the
condition required for the test to pass.

All test-case metadata is defined in
`library/vars/test_case_vars.py`. Test files must obtain the ID and title from
that registry; IDs and titles must not be hardcoded in test implementations.

## Test-case ID standard

IDs use `IMGBM_FVT_<PHASE>_<TYPE><SEQ>`:

| Segment | Meaning | Values or example |
|---------|---------|-------------------|
| `IMGBM` | Image Build Manager domain | Fixed domain code |
| `FVT` | Functional Verification Test level | Fixed test-level code |
| `PHASE` | Lifecycle phase | `PRECHECK`, `VALIDATE`, `PREPARE`, `BUILD`, `CLEANUP_IMAGES`, `CLEANUP`, or `FULL` |
| `TYPE` | Whether the case changes or inspects state | `E` runs a playbook; `V` verifies postconditions |
| `SEQ` | Stable sequence appended to the type | Three digits, starting at `001` |

For example, `IMGBM_FVT_PREPARE_E001` runs the prepare playbook and
`IMGBM_FVT_PREPARE_V001` verifies its first postcondition. The sequence is a
stable identifier, not a global execution position. Execution is controlled
first by lifecycle phase, then by suite, and finally by
`@pytest.mark.order(n)` inside that suite.

## Effective execution order

An untagged `verify` run excludes deploy and cleanup tests and executes the
verification suites in this order:

| Phase | Suite order |
|-------|-------------|
| precheck | `connectivity` |
| validate | `status` |
| prepare | `container` → `s3` |
| build | `aarch64` → `s3` → `registry` → `naming` → `image_verification` |

Within the AArch64 suite, checks run in dependency order: passwordless SSH,
architecture, work directories, builder image, and `regctl`.

## Precheck test cases

These cases confirm that the execution OIM is reachable and that its installed
Omnia environment matches the host. Deploy cases run only with the `test`
command; `verify` runs only the verification cases.

| Sequence | TC ID | Test | Markers | Validation | Pass criteria |
|----------|-------|------|---------|------------|---------------|
| 0 | IMGBM_FVT_PRECHECK_E001 | `test_deploy_precheck` | deploy, sanity | Runs `image_build_manager.yml --tags precheck`. | Playbook exits successfully. |
| 1 | IMGBM_FVT_PRECHECK_V001 | `test_target_connectivity` | sanity | Connects to the configured test target; remote mode verifies SSH. | Target command/SSH connection succeeds. |
| 2 | IMGBM_FVT_PRECHECK_V002 | `test_env_vars_present` | sanity | Reads required values from the target Omnia environment. | `OMNIA_DATA_PATH`, `OMNIA_PROJECT_NAME`, `SYSTEM_ADMIN_NIC_IPV4`, `SYSTEM_HOSTNAME`, and `SYSTEM_DOMAIN_NAME` are present. |
| 3 | IMGBM_FVT_PRECHECK_V003 | `test_hostname_domain` | sanity | Compares the target hostname and domain with `omnia.env`. | Short hostname and domain match the configured values. |
| 4 | IMGBM_FVT_PRECHECK_V004 | `test_admin_ip_assigned` | sanity | Compares `SYSTEM_ADMIN_NIC_IPV4` with local interface addresses. | Configured admin IP is assigned to an interface on the execution OIM. |
| 5 | IMGBM_FVT_PRECHECK_V005 | `test_omnia_setup` | sanity | Checks the system-wide environment files created by `omnia.sh`. | `/etc/omnia/omnia.env` and `/etc/profile.d/omnia-env.sh` exist. |

## Validate test cases

These cases validate the effective runtime inputs without building images.
`IMGBM_FVT_VALIDATE_V004` belongs to this phase because it checks build-template
wiring before a build begins and executes in the `validate/status` suite.
The validate tag does not require or validate `repo_status.yml`; that external
contract is consumed only by build, execute, architecture-specific, and
default build flows.

| Sequence | TC ID | Test | Markers | Validation | Pass criteria |
|----------|-------|------|---------|------------|---------------|
| 0 | IMGBM_FVT_VALIDATE_E001 | `test_deploy_validate` | deploy, sanity | Runs `image_build_manager.yml --tags validate`. | Playbook exits successfully. |
| 1 | IMGBM_FVT_VALIDATE_V001 | `test_input_config_exists` | sanity | Resolves the active project input directory on the target. | `image_build_config.yml` exists at the runtime input path. |
| 2 | IMGBM_FVT_VALIDATE_V002 | `test_credentials_present` | sanity | Resolves the separate domain-credential path on the execution OIM. | `image_build_credentials.yml` exists; credential values are not printed. |
| 3 | IMGBM_FVT_VALIDATE_V003 | `test_repo_ssl_verify_config` | sanity | Reads the explicit or default effective `repo_ssl_verify` value. | Configuration resolves to a valid Boolean value and its source is reported. |
| 4 | IMGBM_FVT_VALIDATE_V004 | `test_repo_ssl_verify_applied` | x86_64, functional | Inspects the RHEL base and compute source templates. | Both templates reference `repo_ssl_verify`, `sslverify`, and `gpgcheck`; the case skips when the effective configuration cannot be read or validated. |

## Prepare test cases

These cases verify the infrastructure created by the `prepare` flow.

| Sequence | TC ID | Test | Markers | Validation | Pass criteria |
|----------|-------|------|---------|------------|---------------|
| 0 | IMGBM_FVT_PREPARE_E001 | `test_deploy_prepare` | deploy, sanity | Runs `image_build_manager.yml --tags prepare`. | Playbook exits successfully. |
| 1 | IMGBM_FVT_PREPARE_V001 | `test_storage_backend_after_prepare` | sanity | Resolves the configured S3 provider and checks its local runtime when applicable. | MinIO container is running, or an external PowerScale backend is recognized and the local-container check is skipped. |
| 2 | IMGBM_FVT_PREPARE_V002 | `test_registry_after_prepare` | sanity | Inspects the registry container with Podman. | Registry container exists and is running. |
| 3 | IMGBM_FVT_PREPARE_V003 | `test_services_active` | sanity | Reads the MinIO and registry systemd service states. | Every applicable service reports `active`. |
| 4 | IMGBM_FVT_PREPARE_V004 | `test_firewall_ports_open` | sanity | Checks listeners used by the configured S3 backend and registry. | Registry port 5000 is listening; MinIO ports 9000 and 9001 are also required when MinIO is configured. |
| 5 | IMGBM_FVT_PREPARE_V005 | `test_s3cmd_configured` | sanity | Checks the `s3cmd` executable and client configuration. | `s3cmd` is installed and `/root/.s3cfg` exists. |
| 6 | IMGBM_FVT_PREPARE_V006 | `test_registry_reachable` | sanity | Calls the configured registry HTTP catalog endpoint. | Endpoint responds successfully and its repositories can be listed. |
| 7 | IMGBM_FVT_PREPARE_V007 | `test_s3_buckets_after_prepare` | sanity | Lists required S3 buckets through `s3cmd` and reports each bucket name. | Both `s3://boot-images` and `s3://efi` are present. |

## Build test cases

The following table is in effective execution order. The suite rank takes
precedence over the local decorator order, so AArch64 readiness is reported
before artifact verification.

| Sequence | TC ID | Test | Suite | Markers | Validation | Pass criteria |
|----------|-------|------|-------|---------|------------|---------------|
| 0 | IMGBM_FVT_BUILD_E001 | `test_deploy_image_build_manager` | root | deploy, sanity | Runs `image_build_manager.yml --tags build`; setup validates the repo-manager output contract before parsing repository URLs. | Build playbook exits successfully with a structurally valid, successful `repo_status.yml`. Internet mode may use empty repo-manager port and certificate path values. |
| 1 | IMGBM_FVT_BUILD_V001 | `test_aarch64_ssh_connectivity` | aarch64 | aarch64, sanity | Runs a non-interactive SSH command and reports the source OIM, destination, and authentication mode. | Passwordless SSH exits zero and returns `OK`; skips when no AArch64 host is configured. |
| 2 | IMGBM_FVT_BUILD_V002 | `test_aarch64_architecture` | aarch64 | aarch64, functional | Collects the architecture, kernel name, and kernel release from the configured ARM host. | Host reports `aarch64`; skips when no AArch64 host is configured. |
| 3 | IMGBM_FVT_BUILD_V003 | `test_aarch64_work_dirs` | aarch64 | aarch64, sanity | Checks and lists the Image Build Manager root, OpenCHAMI, work, and log directories on the ARM host. | All four directories exist below the execution OIM's `OMNIA_DATA_PATH`; skips when no AArch64 host is configured. |
| 4 | IMGBM_FVT_BUILD_V004 | `test_aarch64_builder_image` | aarch64 | aarch64, functional | Verifies Podman, reports its version, and lists matching builder images on the ARM host. | Podman works and an `aarch64-image-builder` or `aarch64-image-thrillhouse` image exists; skips when no AArch64 host is configured. |
| 5 | IMGBM_FVT_BUILD_V005 | `test_aarch64_regctl_installed` | aarch64 | aarch64, functional | Executes `regctl version` and reports the version tag and source revision. | `regctl` exits successfully; skips when no AArch64 host is configured. |
| 6 | IMGBM_FVT_BUILD_V006 | `test_s3_images_x86_64` | s3 | x86_64, sanity | Resolves the producing engine and exact x86_64 artifact paths from `build_status.yml`, checks S3, and reports each verified filename and object size. | Kernel, initramfs, and rootfs artifacts match the recorded engine layout and exist for every configured x86_64 functional group. |
| 7 | IMGBM_FVT_BUILD_V007 | `test_s3_images_aarch64` | s3 | aarch64, sanity | Resolves the producing engine and exact AArch64 artifact paths from `build_status.yml`, checks S3, and reports each verified filename and object size. | Kernel, initramfs, and rootfs artifacts match the recorded engine layout and exist for every configured AArch64 functional group; skips when none are configured. |
| 8 | IMGBM_FVT_BUILD_V008 | `test_registry_images_x86_64` | registry | x86_64, sanity | Compares expected x86_64 base/compute repositories with the registry catalog. | All expected x86_64 repositories are present; skips when none are configured. |
| 9 | IMGBM_FVT_BUILD_V009 | `test_registry_images_aarch64` | registry | aarch64, sanity | Compares expected AArch64 base/compute repositories with the registry catalog. | All expected AArch64 repositories are present; skips when none are configured. |
| 10 | IMGBM_FVT_BUILD_V010 | `test_build_status` | registry | sanity | Parses the active project's `build_status.yml` and resolves its producing image engine. | File exists, is valid YAML, reports `overall_status: success`, and declares a supported `image_build_type` (or is an unambiguous suffix-based legacy manifest). |
| 11 | IMGBM_FVT_BUILD_V011 | `test_functional_groups_x86_64` | registry | x86_64, sanity | Compares configured x86_64 functional groups with the build manifest. | Every configured x86_64 group appears in `build_status.yml`. |
| 12 | IMGBM_FVT_BUILD_V012 | `test_functional_groups_aarch64` | registry | aarch64, sanity | Compares configured AArch64 functional groups with the build manifest. | Every configured AArch64 group appears in `build_status.yml`; skips when none are configured. |
| 13 | IMGBM_FVT_BUILD_V013 | `test_registry_naming_image_builder_x86_64` | naming | x86_64, sanity | Inspects x86_64 registry repositories for Image Builder naming. | At least one current artifact ends in `-imgbld`; skips for Thrillhouse or when no current artifact exists. |
| 14 | IMGBM_FVT_BUILD_V014 | `test_s3_naming_image_builder_x86_64` | naming | x86_64, sanity | Inspects x86_64 S3 object paths for Image Builder naming. | At least one current artifact path contains `-imgbld`; skips for Thrillhouse or when no current artifact exists. |
| 15 | IMGBM_FVT_BUILD_V015 | `test_registry_naming_image_thrillhouse_x86_64` | naming | x86_64, sanity | Inspects x86_64 registry repositories for Thrillhouse naming. | At least one current artifact ends in `-imgth`; skips for Image Builder or when no current artifact exists. |
| 16 | IMGBM_FVT_BUILD_V016 | `test_s3_naming_image_thrillhouse_x86_64` | naming | x86_64, sanity | Inspects x86_64 S3 object paths for Thrillhouse naming. | At least one current artifact path contains `-imgth`; skips for Image Builder or when no current artifact exists. |
| 17 | IMGBM_FVT_BUILD_V017 | `test_artifact_suffix_isolation` | naming | x86_64, functional | Validates x86_64 registry repository names and S3 object paths across both image engines. | Every artifact carries exactly one of `-imgbld` or `-imgth`, complete names and paths are unique, and the engine recorded in `build_status.yml` has at least one artifact; the other engine's artifacts may coexist. |
| 18 | IMGBM_FVT_BUILD_V018 | `test_image_packages_x86_64` | image_verification | x86_64, sanity | Resolves expected RPMs and, when expectations exist, downloads and mounts each exact rootfs from `build_status.yml`. | Every expected non-driver-group, architecture-matching RPM is installed; skips when no x86_64 groups are configured. |
| 19 | IMGBM_FVT_BUILD_V019 | `test_image_packages_aarch64` | image_verification | aarch64, sanity | Resolves expected RPMs and, when expectations exist, downloads and mounts each exact rootfs from `build_status.yml`. | Every expected non-driver-group, architecture-matching RPM is installed; skips when no AArch64 groups are configured. |

### AArch64 path and tool contracts

- The ARM work root is `$OMNIA_DATA_PATH/image_build_manager`, using the value
  read from the execution OIM. The ARM host does not need to define
  `OMNIA_DATA_PATH` locally.
- `regctl` is staged on the OIM and copied to the ARM host by
  `prepare_aarch64_node`; direct download is a fallback.
- The AArch64 cases verify the postconditions of `build_image_aarch64.yml`.
  Initial password-based access is a playbook prerequisite; `IMGBM_FVT_BUILD_V001`
  verifies that passwordless access was established successfully.

### Repo-status contract boundary

The build setup validates `repo_status.yml` only when repository data is
needed. Required structural keys include status, OS metadata, repo-manager
metadata, and architecture repository mappings. Managed-repository metadata
uses a numeric port and may provide certificate paths. Internet mode preserves
the same structure but may set the port and certificate path strings to empty.
At least one usable x86_64 repository URL is required for a build.

### Naming test commands

The engine-specific naming cases use the producing engine recorded in
`build_status.yml`, not a potentially newer value in the input configuration.

```bash
./run_validation.sh fvt_image_build_manager build verify --suite naming
./run_validation.sh fvt_image_build_manager build verify \
  --suite naming --marker x86_64+sanity
```

Naming results print each artifact property on a separate line. On terminals
that support color, field names are cyan and values are bright white. The HTML
report applies theme-aware colors to the same structured fields. Set
`NO_COLOR=1` when plain terminal output is required.

## Full-stack deployment test case

The build deploy function selects its ID from the requested runner flow.

| TC ID | Test | Markers | Validation | Pass criteria |
|-------|------|---------|------------|---------------|
| IMGBM_FVT_FULL_E001 | `test_deploy_image_build_manager` | deploy, sanity | Runs the untagged Image Build Manager playbook, whose default flow prepares infrastructure and builds images. | Complete default playbook exits successfully. |

The same physical function reports `IMGBM_FVT_BUILD_E001` for a tagged `build` deployment
and `IMGBM_FVT_FULL_E001` for the untagged full-stack deployment.

## Cleanup-images test cases

Run this scenario before full cleanup because it requires the S3 and registry
services to remain available.

| Sequence | TC ID | Test | Markers | Validation | Pass criteria |
|----------|-------|------|---------|------------|---------------|
| 0 | IMGBM_FVT_CLEANUP_IMAGES_E001 | `test_deploy_cleanup_images` | deploy, sanity | Runs `image_build_manager.yml --tags cleanup_images` with the runner's approved automation settings. | Playbook exits successfully. |
| 1 | IMGBM_FVT_CLEANUP_IMAGES_V001 | `test_s3_images_cleaned` | sanity | Lists objects remaining in `s3://boot-images`. | No built image objects remain; the bucket itself may remain. |
| 2 | IMGBM_FVT_CLEANUP_IMAGES_V002 | `test_registry_images_cleaned` | sanity | Queries every repository's tags in the local registry. | Registry infrastructure remains available, every tag query succeeds, and no tagged build images remain. |

## Full-cleanup test cases

These cases verify the state after the opt-in `cleanup` flow. A verify-only run
checks postconditions and does not execute cleanup first. The MinIO storage and
`s3cmd` cases skip automatically for PowerScale because cleanup intentionally
retains those external resources.

| Sequence | TC ID | Test | Markers | Validation | Pass criteria |
|----------|-------|------|---------|------------|---------------|
| 0 | IMGBM_FVT_CLEANUP_E001 | `test_deploy_cleanup` | deploy, sanity | Runs `image_build_manager.yml --tags cleanup`. | Cleanup playbook exits successfully. |
| 1 | IMGBM_FVT_CLEANUP_V001 | `test_containers_removed` | sanity | Searches Podman for the MinIO and registry containers. | Neither container remains. |
| 2 | IMGBM_FVT_CLEANUP_V002 | `test_services_removed` | sanity | Reads MinIO and registry systemd states. | No applicable service is active. |
| 3 | IMGBM_FVT_CLEANUP_V003 | `test_firewall_ports_closed` | sanity | Checks the MinIO, console, and registry listeners. | TCP ports 9000, 9001, and 5000 are not listening. |
| 4 | IMGBM_FVT_CLEANUP_V004 | `test_s3_artifacts_removed` | sanity | Checks the managed MinIO storage directory and reports any reachable remaining buckets. | Managed MinIO storage is absent; skips for PowerScale. |
| 5 | IMGBM_FVT_CLEANUP_V005 | `test_s3cfg_removed` | sanity | Checks the local S3 client configuration. | `/root/.s3cfg` is absent; skips for PowerScale. |
| 6 | IMGBM_FVT_CLEANUP_V006 | `test_build_output_removed` | sanity | Checks the active project's build-status path. | `build_status.yml` is absent. |
| 7 | IMGBM_FVT_CLEANUP_V007 | `test_registry_cleaned` | sanity | Inspects remaining registry tags when the registry is reachable. | The registry is unavailable after cleanup, or every repository tag query succeeds and no tagged build images remain. |
| 8 | IMGBM_FVT_CLEANUP_V008 | `test_credentials_removed` | sanity | Checks the domain credential file and vault-key paths without reading their contents. | Both credential artifacts are absent. |

## Registry summary

| Phase | Execution IDs | Verification IDs | Total | Notes |
|-------|---------------|------------------|-------|-------|
| Precheck | `IMGBM_FVT_PRECHECK_E001` | `IMGBM_FVT_PRECHECK_V001`–`005` | 6 | Execution-host prerequisites. |
| Validate | `IMGBM_FVT_VALIDATE_E001` | `IMGBM_FVT_VALIDATE_V001`–`004` | 5 | Input and template validation. |
| Prepare | `IMGBM_FVT_PREPARE_E001` | `IMGBM_FVT_PREPARE_V001`–`007` | 8 | Infrastructure preparation. |
| Build | `IMGBM_FVT_BUILD_E001` | `IMGBM_FVT_BUILD_V001`–`019` | 20 | AArch64, artifacts, naming, and package contracts. |
| Cleanup images | `IMGBM_FVT_CLEANUP_IMAGES_E001` | `IMGBM_FVT_CLEANUP_IMAGES_V001`–`002` | 3 | Selective image deletion. |
| Cleanup | `IMGBM_FVT_CLEANUP_E001` | `IMGBM_FVT_CLEANUP_V001`–`008` | 9 | Full local infrastructure cleanup. |
| Tagged FVT IDs | | | 51 | IDs emitted by tagged flows. |
| Full-stack alternate | `IMGBM_FVT_FULL_E001` | — | 1 | Alternate ID for the build deploy function. |

There are 51 physical FVT functions. The registry contains 52 reportable IDs
because the build deploy function can emit either `IMGBM_FVT_BUILD_E001` or `IMGBM_FVT_FULL_E001`.

## Legacy ID migration

Historical reports may contain the former phase-abbreviation IDs. Use this
complete mapping when comparing those reports with current output.

Reports created during the earlier long-form design convert directly:

| Earlier long-form ID | Current ID |
|----------------------|------------|
| `TC_IB_<PHASE>_EXEC_<SEQ>` | `IMGBM_FVT_<PHASE>_E<SEQ>` |
| `TC_IB_<PHASE>_VERIFY_<SEQ>` | `IMGBM_FVT_<PHASE>_V<SEQ>` |

For example, `TC_IB_CLEANUP_VERIFY_002` is now
`IMGBM_FVT_CLEANUP_V002`.

| Legacy IDs | Current IDs |
|------------|-------------|
| `TC_PC_001` | `IMGBM_FVT_PRECHECK_E001` |
| `TC_PC_003`, `TC_PC_002`, `TC_PC_004`–`006` | `IMGBM_FVT_PRECHECK_V001`–`005`, respectively |
| `TC_VL_001` | `IMGBM_FVT_VALIDATE_E001` |
| `TC_VL_002`–`004` | `IMGBM_FVT_VALIDATE_V001`–`003`, respectively |
| `TC_BD_016` | `IMGBM_FVT_VALIDATE_V004` |
| `TC_PR_001` | `IMGBM_FVT_PREPARE_E001` |
| `TC_PR_002`–`008` | `IMGBM_FVT_PREPARE_V001`–`007`, respectively |
| `TC_BD_001` | `IMGBM_FVT_BUILD_E001` |
| `TC_BD_017`, `TC_BD_021`, `TC_BD_018`–`020` | `IMGBM_FVT_BUILD_V001`–`005`, respectively |
| `TC_BD_002`–`004` | `IMGBM_FVT_BUILD_V006`–`008`, respectively |
| `TC_BD_012` | `IMGBM_FVT_BUILD_V009` |
| `TC_BD_005`–`011` | `IMGBM_FVT_BUILD_V010`–`016`, respectively |
| `TC_BD_013` | `IMGBM_FVT_BUILD_V017` |
| `TC_BD_014`, `TC_BD_015` | `IMGBM_FVT_BUILD_V018`, `IMGBM_FVT_BUILD_V019`, respectively |
| `TC_CI_001` | `IMGBM_FVT_CLEANUP_IMAGES_E001` |
| `TC_CI_002`–`003` | `IMGBM_FVT_CLEANUP_IMAGES_V001`–`002`, respectively |
| `TC_CL_001` | `IMGBM_FVT_CLEANUP_E001` |
| `TC_CL_002`–`008` | `IMGBM_FVT_CLEANUP_V001`–`007`, respectively |
| No legacy ID | `IMGBM_FVT_CLEANUP_V008` |
| `TC_IB_001` | `IMGBM_FVT_FULL_E001` |

## Execution commands

Run from `test/image_build_manager/`:

```bash
# Deploy and verify one lifecycle phase
./run_validation.sh fvt_image_build_manager precheck test
./run_validation.sh fvt_image_build_manager validate test
./run_validation.sh fvt_image_build_manager prepare test
./run_validation.sh fvt_image_build_manager build test

# Verify the existing non-cleanup deployment without running a playbook
./run_validation.sh fvt_image_build_manager verify

# Focused build verification
./run_validation.sh fvt_image_build_manager build verify --suite aarch64
./run_validation.sh fvt_image_build_manager build verify --suite registry
./run_validation.sh fvt_image_build_manager build verify --marker x86_64+sanity

# Destructive flows; run in this order
./run_validation.sh fvt_image_build_manager cleanup_images test
./run_validation.sh fvt_image_build_manager cleanup test
```

`verify` never executes a playbook. The untagged form excludes cleanup and
deploy cases. Cleanup scenarios run only when explicitly selected.
