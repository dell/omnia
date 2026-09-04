# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Image Build Manager — Test Case Registry.

Central registry mapping every test to its TC ID and title.
Test files reference ``TEST_CASES["key"]`` to get a consistent
test-case identifier and display name.

Usage in test files::

    from library.vars.test_case_vars import TEST_CASES as TC

    tc = TC["deploy_prepare"]
    tl = TestLogger(tc["title"], tc["id"])
"""

TEST_CASES = {
    # ── Deploy (one per scenario) ─────────────────────────────────────────
    "deploy_validate": {
        "id": "IBM_FVT_VALIDATE_E001",
        "title": "Deploy image_build_manager (validate)",
    },
    "deploy_prepare": {
        "id": "IBM_FVT_PREPARE_E001",
        "title": "Deploy image_build_manager (prepare)",
    },
    "deploy_build": {
        "id": "IBM_FVT_BUILD_E001",
        "title": "Deploy image_build_manager (build)",
    },
    "deploy_cleanup": {
        "id": "IBM_FVT_CLEANUP_E001",
        "title": "Deploy image_build_manager (cleanup)",
    },
    "deploy_full": {
        "id": "IBM_FVT_FULL_E001",
        "title": "Deploy image_build_manager (default: prepare + build)",
    },
    # ── Validate ──────────────────────────────────────────────────────────
    "input_config_exists": {
        "id": "IBM_FVT_VALIDATE_V001",
        "title": "Verify image_build_config.yml exists on target",
    },
    "credentials_present_vl": {
        "id": "IBM_FVT_VALIDATE_V002",
        "title": "Verify credentials file present on target",
    },
    # ── Prepare ───────────────────────────────────────────────────────────
    "storage_backend": {
        "id": "IBM_FVT_PREPARE_V001",
        "title": "Verify S3 storage backend after prepare",
    },
    "registry_container_running": {
        "id": "IBM_FVT_PREPARE_V002",
        "title": "Verify registry container is running",
    },
    "services_active": {
        "id": "IBM_FVT_PREPARE_V003",
        "title": "Verify MinIO and registry systemd services are active",
    },
    "firewall_ports_open": {
        "id": "IBM_FVT_PREPARE_V004",
        "title": "Verify service ports (9000, 9001, 5000) are listening",
    },
    "s3cmd_configured": {
        "id": "IBM_FVT_PREPARE_V005",
        "title": "Verify s3cmd is installed and configured",
    },
    "registry_reachable": {
        "id": "IBM_FVT_PREPARE_V006",
        "title": "Verify container registry is reachable",
    },
    "s3_buckets_created": {
        "id": "IBM_FVT_PREPARE_V007",
        "title": "Verify required S3 buckets exist after prepare",
    },
    # ── Build ─────────────────────────────────────────────────────────────
    "s3_images_x86_64": {
        "id": "IBM_FVT_BUILD_V006",
        "title": "Verify x86_64 images pushed to S3",
    },
    "s3_images_aarch64": {
        "id": "IBM_FVT_BUILD_V007",
        "title": "Verify aarch64 images pushed to S3",
    },
    "registry_images_x86_64": {
        "id": "IBM_FVT_BUILD_V008",
        "title": "Verify x86_64 images in registry",
    },
    "build_status_file": {
        "id": "IBM_FVT_BUILD_V010",
        "title": "Verify build_status.yml exists and reports success",
    },
    "functional_groups_x86_64": {
        "id": "IBM_FVT_BUILD_V011",
        "title": "Verify all configured x86_64 functional groups built",
    },
    "registry_images_aarch64": {
        "id": "IBM_FVT_BUILD_V009",
        "title": "Verify aarch64 images in registry",
    },
    "functional_groups_aarch64": {
        "id": "IBM_FVT_BUILD_V012",
        "title": "Verify all configured aarch64 functional groups built",
    },
    "packages_x86_64": {
        "id": "IBM_FVT_BUILD_V018",
        "title": "Verify packages installed in x86_64 S3 images",
    },
    "packages_aarch64": {
        "id": "IBM_FVT_BUILD_V019",
        "title": "Verify packages installed in aarch64 S3 images",
    },
    # ── Build — aarch64 infrastructure (IBM_FVT_BUILD_V001-005) ─────────────────────
    "aarch64_ssh_connectivity": {
        "id": "IBM_FVT_BUILD_V001",
        "title": "Verify passwordless SSH to aarch64 node",
    },
    "aarch64_work_dirs": {
        "id": "IBM_FVT_BUILD_V003",
        "title": "Verify aarch64 work directories exist",
    },
    "aarch64_builder_image": {
        "id": "IBM_FVT_BUILD_V004",
        "title": "Verify builder image on aarch64 node",
    },
    "aarch64_regctl_installed": {
        "id": "IBM_FVT_BUILD_V005",
        "title": "Verify regctl installed on aarch64 node",
    },
    "aarch64_architecture": {
        "id": "IBM_FVT_BUILD_V002",
        "title": "Verify aarch64 node is ARM architecture",
    },
    # ── Build — naming convention (IBM_FVT_BUILD_V013-017) ─────────────────────────
    "registry_naming_ib_x86_64": {
        "id": "IBM_FVT_BUILD_V013",
        "title": "Verify image-builder registry naming (-imgbld suffix, x86_64)",
    },
    "s3_naming_ib_x86_64": {
        "id": "IBM_FVT_BUILD_V014",
        "title": "Verify image-builder S3 naming (-imgbld suffix, x86_64)",
    },
    "registry_naming_th_x86_64": {
        "id": "IBM_FVT_BUILD_V015",
        "title": "Verify image-thrillhouse registry naming (-imgth suffix, x86_64)",
    },
    "s3_naming_th_x86_64": {
        "id": "IBM_FVT_BUILD_V016",
        "title": "Verify image-thrillhouse S3 naming (-imgth suffix, x86_64)",
    },
    "artifact_suffix_isolation": {
        "id": "IBM_FVT_BUILD_V017",
        "title": "Verify -imgbld and -imgth artifact paths are fully isolated",
    },
    # ── Precheck ──────────────────────────────────────────────────────────
    "deploy_precheck": {
        "id": "IBM_FVT_PRECHECK_E001",
        "title": "Deploy image_build_manager (precheck)",
    },
    "env_vars_present": {
        "id": "IBM_FVT_PRECHECK_V002",
        "title": "Verify OMNIA env vars present on target",
    },
    "target_connectivity": {
        "id": "IBM_FVT_PRECHECK_V001",
        "title": "Verify target host connectivity and SSH",
    },
    "hostname_domain": {
        "id": "IBM_FVT_PRECHECK_V003",
        "title": "Verify hostname and domain match omnia.env",
    },
    "admin_ip_assigned": {
        "id": "IBM_FVT_PRECHECK_V004",
        "title": "Verify admin IP assigned to local interface",
    },
    "omnia_setup": {
        "id": "IBM_FVT_PRECHECK_V005",
        "title": "Verify omnia.sh setup completed on target",
    },
    # ── Validate — repo_ssl_verify ──────────────────────────────────────
    "repo_ssl_verify_config": {
        "id": "IBM_FVT_VALIDATE_V003",
        "title": "Verify effective repo_ssl_verify configuration",
    },
    "repo_ssl_verify_applied": {
        "id": "IBM_FVT_VALIDATE_V004",
        "title": "Verify repo_ssl_verify is wired into build templates",
    },
    # ── Cleanup ───────────────────────────────────────────────────────────
    "deploy_cleanup_images": {
        "id": "IBM_FVT_CLEANUP_IMAGES_E001",
        "title": "Deploy image_build_manager (cleanup_images)",
    },
    "s3_images_cleaned": {
        "id": "IBM_FVT_CLEANUP_IMAGES_V001",
        "title": "Verify S3 images deleted after cleanup_images",
    },
    "registry_images_cleaned": {
        "id": "IBM_FVT_CLEANUP_IMAGES_V002",
        "title": "Verify registry images deleted after cleanup_images",
    },
    "containers_removed": {
        "id": "IBM_FVT_CLEANUP_V001",
        "title": "Verify containers removed after cleanup",
    },
    "services_removed": {
        "id": "IBM_FVT_CLEANUP_V002",
        "title": "Verify systemd services stopped after cleanup",
    },
    "firewall_ports_closed": {
        "id": "IBM_FVT_CLEANUP_V003",
        "title": "Verify firewall ports closed after cleanup",
    },
    "s3_artifacts_removed": {
        "id": "IBM_FVT_CLEANUP_V004",
        "title": "Verify managed S3 storage removed after cleanup",
    },
    "s3cfg_removed": {
        "id": "IBM_FVT_CLEANUP_V005",
        "title": "Verify s3cmd configuration removed",
    },
    "build_output_removed": {
        "id": "IBM_FVT_CLEANUP_V006",
        "title": "Verify build_status.yml removed",
    },
    "registry_cleaned": {
        "id": "IBM_FVT_CLEANUP_V007",
        "title": "Verify registry has no images",
    },
    "credentials_removed": {
        "id": "IBM_FVT_CLEANUP_V008",
        "title": "Verify credential artifacts removed after cleanup",
    },
    # ── Non-functional tests ────────────────────────────────────────────
    "prepare_performance": {
        "id": "IBM_NFT_001",
        "title": "NFT: Prepare performance",
    },
    "build_performance": {
        "id": "IBM_NFT_002",
        "title": "NFT: Build performance",
    },
    "cleanup_performance": {
        "id": "IBM_NFT_003",
        "title": "NFT: Cleanup performance",
    },
    "prepare_idempotent": {
        "id": "IBM_NFT_004",
        "title": "NFT: Prepare idempotency",
    },
}
