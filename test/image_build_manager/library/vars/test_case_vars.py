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
        "id": "TC_VL_001",
        "title": "Deploy image_build_manager (validate)",
    },
    "deploy_prepare": {
        "id": "TC_PR_001",
        "title": "Deploy image_build_manager (prepare)",
    },
    "deploy_build": {
        "id": "TC_BD_001",
        "title": "Deploy image_build_manager (build)",
    },
    "deploy_cleanup": {
        "id": "TC_CL_001",
        "title": "Deploy image_build_manager (cleanup)",
    },
    "deploy_full": {
        "id": "TC_IB_000",
        "title": "Deploy image_build_manager (default: prepare + build)",
    },

    # ── Validate ──────────────────────────────────────────────────────────
    "input_config_exists": {
        "id": "TC_VL_002",
        "title": "Verify image_build_config.yml exists on target",
    },
    "credentials_present_vl": {
        "id": "TC_VL_003",
        "title": "Verify credentials file present on target",
    },

    # ── Prepare ───────────────────────────────────────────────────────────
    "storage_backend": {
        "id": "TC_PR_002",
        "title": "Verify S3 storage backend after prepare",
    },
    "registry_container_running": {
        "id": "TC_PR_003",
        "title": "Verify registry container is running",
    },
    "services_active": {
        "id": "TC_PR_004",
        "title": "Verify MinIO and registry systemd services are active",
    },
    "firewall_ports_open": {
        "id": "TC_PR_005",
        "title": "Verify service ports (9000, 9001, 5000) are listening",
    },
    "s3cmd_configured": {
        "id": "TC_PR_006",
        "title": "Verify s3cmd is installed and configured",
    },
    "registry_reachable": {
        "id": "TC_PR_007",
        "title": "Verify container registry is reachable",
    },
    "s3_buckets_created": {
        "id": "TC_PR_008",
        "title": "Verify required S3 buckets exist after prepare",
    },

    # ── Build ─────────────────────────────────────────────────────────────
    "s3_images_x86_64": {
        "id": "TC_BD_002",
        "title": "Verify x86_64 images pushed to S3",
    },
    "s3_images_aarch64": {
        "id": "TC_BD_003",
        "title": "Verify aarch64 images pushed to S3",
    },
    "registry_images_x86_64": {
        "id": "TC_BD_004",
        "title": "Verify x86_64 images in registry",
    },
    "build_status_file": {
        "id": "TC_BD_005",
        "title": "Verify build_status.yml exists and reports success",
    },
    "functional_groups_x86_64": {
        "id": "TC_BD_006",
        "title": "Verify all configured x86_64 functional groups built",
    },

    # ── Full (image_build_manager) ────────────────────────────────────────
    "ib_storage_backend": {
        "id": "TC_IB_001",
        "title": "Verify S3 storage backend (MinIO or PowerScale)",
    },
    "ib_registry_container": {
        "id": "TC_IB_002",
        "title": "Verify registry container is running",
    },
    "ib_s3_buckets": {
        "id": "TC_IB_003",
        "title": "Verify required S3 buckets exist",
    },
    "ib_s3_images_x86_64": {
        "id": "TC_IB_004",
        "title": "Verify x86_64 images pushed to S3",
    },
    "ib_s3_images_aarch64": {
        "id": "TC_IB_005",
        "title": "Verify aarch64 images pushed to S3",
    },
    "ib_registry_x86_64": {
        "id": "TC_IB_006",
        "title": "Verify x86_64 images in registry",
    },
    "ib_registry_aarch64": {
        "id": "TC_IB_007",
        "title": "Verify aarch64 images in registry",
    },
    "ib_build_status": {
        "id": "TC_IB_008",
        "title": "Verify build_status.yml reports success",
    },
    "ib_groups_x86_64": {
        "id": "TC_IB_009",
        "title": "Verify x86_64 functional groups built",
    },
    "ib_groups_aarch64": {
        "id": "TC_IB_010",
        "title": "Verify aarch64 functional groups built",
    },
    "ib_packages_x86_64": {
        "id": "TC_IB_011",
        "title": "Verify packages installed in x86_64 S3 images",
    },
    "ib_packages_aarch64": {
        "id": "TC_IB_012",
        "title": "Verify packages installed in aarch64 S3 images",
    },

    # ── Cleanup ───────────────────────────────────────────────────────────
    "containers_removed": {
        "id": "TC_CL_002",
        "title": "Verify containers removed after cleanup",
    },
    "services_removed": {
        "id": "TC_CL_003",
        "title": "Verify systemd services stopped after cleanup",
    },
    "firewall_ports_closed": {
        "id": "TC_CL_004",
        "title": "Verify firewall ports closed after cleanup",
    },
    "s3_artifacts_removed": {
        "id": "TC_CL_005",
        "title": "Verify S3 buckets removed after cleanup",
    },
    "s3cfg_removed": {
        "id": "TC_CL_006",
        "title": "Verify s3cmd configuration removed",
    },
    "build_output_removed": {
        "id": "TC_CL_007",
        "title": "Verify build_status.yml removed",
    },
    "registry_cleaned": {
        "id": "TC_CL_008",
        "title": "Verify registry has no images",
    },
}
