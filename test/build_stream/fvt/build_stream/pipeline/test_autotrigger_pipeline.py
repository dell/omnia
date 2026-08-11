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
Build Stream — Auto-Trigger Build Pipeline FVT Tests.

Tests the complete build pipeline lifecycle:
1. Upload catalog → auto-trigger pipeline
2. Monitor core stages (upload, parse-catalog, generate-input, create-local-repo)
3. Monitor build-image stages (x86_64, aarch64)
4. Verify database state (jobs, stages, images, image_groups)
5. Verify artifacts (registry images, S3 boot images)

Adapted from automation_v22/molecule/build_stream/test_autotrigger_pipeline.py.
"""

import pytest

from library.functions import (
    TestLogger,
    trigger_build_pipeline,
    wait_for_stage_completion,
    verify_stage_completed,
    get_images_for_job,
    get_image_groups_for_job,
    get_catalog_roles,
    verify_registry_images,
    verify_s3_boot_images,
    is_build_stream_enabled,
)
from library.vars.common_vars import (
    BUILD_PIPELINE_CORE_STAGES,
    STAGE_BUILD_IMAGE_X86_64,
    STAGE_BUILD_IMAGE_AARCH64,
    STAGE_POLL_INTERVAL,
    STAGE_POLL_TIMEOUT,
)
from library.messages.build_stream_msgs import TEST_NAMES, TEST_LOG_MSGS, SKIP_MSGS


# =============================================================================
# MODULE-LEVEL STATE
# =============================================================================
# Shared across tests in this module to pass pipeline/job context.

_pipeline_state = {
    "pipeline_id": 0,
    "job_id": "",
    "build_success": False,
    "roles": [],
    "architectures": [],
    "image_key": "",
}


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(scope="module")
def pipeline_state():
    """Provide shared pipeline state across tests in this module."""
    return _pipeline_state


# =============================================================================
# TESTS
# =============================================================================

@pytest.mark.build_stream
@pytest.mark.pipeline
@pytest.mark.order(200)
class TestAutotriggerBuildPipeline:
    """Auto-triggered build pipeline: catalog upload → stages → artifacts."""

    def test_trigger_build_pipeline(self, host, pipeline_state):
        """Upload catalog to trigger build pipeline and wait for job creation."""
        log = TestLogger(TEST_NAMES.get("catalog_upload", "Catalog Upload and Pipeline Trigger"))
        
        if not is_build_stream_enabled(host):
            log.skipped(SKIP_MSGS["build_stream_disabled"])
            pytest.skip(SKIP_MSGS["build_stream_disabled"])

        result = trigger_build_pipeline(host, log_callback=log.info)

        assert result["success"], (
            f"Failed to trigger build pipeline: {result['error']}"
        )

        pipeline_state["pipeline_id"] = result["pipeline_id"]
        pipeline_state["job_id"] = result.get("job_id", "")

        log.passed(f"Pipeline #{result['pipeline_id']} triggered, "
                   f"Job: {result.get('job_id', 'N/A')[:8]}...")

    @pytest.mark.parametrize("stage_name", BUILD_PIPELINE_CORE_STAGES)
    def test_core_stage_completion(self, host, pipeline_state, stage_name):
        """Monitor each core build stage until completion."""
        log = TestLogger(TEST_NAMES.get("stage_monitor", "Stage Monitor").format(stage=stage_name))

        if not pipeline_state["job_id"]:
            log.skipped(SKIP_MSGS["no_job_id"])
            pytest.skip(SKIP_MSGS["no_job_id"])

        result = wait_for_stage_completion(
            host,
            pipeline_state["job_id"],
            stage_name,
            timeout=STAGE_POLL_TIMEOUT,
            poll_interval=STAGE_POLL_INTERVAL,
            log_callback=log.info,
        )

        assert result["success"], (
            f"Stage '{stage_name}' failed: {result['error']}"
        )

        log.passed(TEST_LOG_MSGS["stage_completed"].format(
            stage=stage_name, elapsed=result["elapsed"]
        ))

    def test_build_image_x86_64(self, host, pipeline_state):
        """Monitor build-image-x86_64 stage."""
        log = TestLogger(TEST_NAMES.get("stage_monitor", "Stage Monitor").format(
            stage=STAGE_BUILD_IMAGE_X86_64
        ))

        if not pipeline_state["job_id"]:
            log.skipped(SKIP_MSGS["no_job_id"])
            pytest.skip(SKIP_MSGS["no_job_id"])

        result = wait_for_stage_completion(
            host,
            pipeline_state["job_id"],
            STAGE_BUILD_IMAGE_X86_64,
            timeout=STAGE_POLL_TIMEOUT,
            poll_interval=STAGE_POLL_INTERVAL,
            log_callback=log.info,
        )

        assert result["success"], (
            f"Stage '{STAGE_BUILD_IMAGE_X86_64}' failed: {result['error']}"
        )

        log.passed(TEST_LOG_MSGS["stage_completed"].format(
            stage=STAGE_BUILD_IMAGE_X86_64, elapsed=result["elapsed"]
        ))

    def test_build_image_aarch64(self, host, pipeline_state):
        """Monitor build-image-aarch64 stage."""
        log = TestLogger(TEST_NAMES.get("stage_monitor", "Stage Monitor").format(
            stage=STAGE_BUILD_IMAGE_AARCH64
        ))

        if not pipeline_state["job_id"]:
            log.skipped(SKIP_MSGS["no_job_id"])
            pytest.skip(SKIP_MSGS["no_job_id"])

        result = wait_for_stage_completion(
            host,
            pipeline_state["job_id"],
            STAGE_BUILD_IMAGE_AARCH64,
            timeout=STAGE_POLL_TIMEOUT,
            poll_interval=STAGE_POLL_INTERVAL,
            log_callback=log.info,
        )

        assert result["success"], (
            f"Stage '{STAGE_BUILD_IMAGE_AARCH64}' failed: {result['error']}"
        )

        pipeline_state["build_success"] = True
        log.passed(TEST_LOG_MSGS["stage_completed"].format(
            stage=STAGE_BUILD_IMAGE_AARCH64, elapsed=result["elapsed"]
        ))

    def test_verify_stages_in_db(self, host, pipeline_state):
        """Verify all build stages completed in database."""
        log = TestLogger("Verify All Build Stages in Database")

        if not pipeline_state["job_id"]:
            log.skipped(SKIP_MSGS["no_job_id"])
            pytest.skip(SKIP_MSGS["no_job_id"])

        all_stages = BUILD_PIPELINE_CORE_STAGES + [
            STAGE_BUILD_IMAGE_X86_64,
            STAGE_BUILD_IMAGE_AARCH64,
        ]

        failed_stages = []
        for stage in all_stages:
            result = verify_stage_completed(host, pipeline_state["job_id"], stage)
            if not result["success"]:
                failed_stages.append(f"{stage}: {result['error']}")
            else:
                log.info(TEST_LOG_MSGS["stage_db_ok"].format(
                    stage=stage, state=result["stage_state"]
                ))

        assert not failed_stages, (
            f"Stage verification failed:\n" + "\n".join(failed_stages)
        )

        log.passed("All build stages verified in database")

    def test_images_created(self, host, pipeline_state):
        """Verify images were created for the build job."""
        log = TestLogger(TEST_NAMES.get("images_created", "Images Created Check"))

        if not pipeline_state["job_id"]:
            log.skipped(SKIP_MSGS["no_job_id"])
            pytest.skip(SKIP_MSGS["no_job_id"])

        result = get_images_for_job(host, pipeline_state["job_id"])

        assert result["success"], f"Failed to query images: {result['error']}"
        assert len(result["images"]) > 0, (
            TEST_LOG_MSGS["images_fail"].format(job_id=pipeline_state["job_id"])
        )

        log.passed(TEST_LOG_MSGS["images_ok"].format(
            count=len(result["images"]), job_id=pipeline_state["job_id"][:8]
        ))

    def test_image_groups_created(self, host, pipeline_state):
        """Verify image groups were created for the build job."""
        log = TestLogger(TEST_NAMES.get("image_groups_created", "Image Groups Created Check"))

        if not pipeline_state["job_id"]:
            log.skipped(SKIP_MSGS["no_job_id"])
            pytest.skip(SKIP_MSGS["no_job_id"])

        result = get_image_groups_for_job(host, pipeline_state["job_id"])

        assert result["success"], f"Failed to query image groups: {result['error']}"
        assert len(result["image_groups"]) > 0, (
            TEST_LOG_MSGS["image_groups_fail"].format(job_id=pipeline_state["job_id"])
        )

        log.passed(TEST_LOG_MSGS["image_groups_ok"].format(
            count=len(result["image_groups"]), job_id=pipeline_state["job_id"][:8]
        ))

    def test_catalog_roles(self, host, pipeline_state):
        """Verify catalog roles and architectures from API."""
        log = TestLogger(TEST_NAMES.get("catalog_roles", "Catalog Roles Check"))

        if not pipeline_state["job_id"]:
            log.skipped(SKIP_MSGS["no_job_id"])
            pytest.skip(SKIP_MSGS["no_job_id"])

        result = get_catalog_roles(host, pipeline_state["job_id"])

        assert result["success"], (
            TEST_LOG_MSGS["catalog_roles_fail"].format(error=result["error"])
        )
        assert len(result["roles"]) > 0, "No roles found in catalog"

        pipeline_state["roles"] = result["roles"]
        pipeline_state["architectures"] = result["architectures"]
        pipeline_state["image_key"] = result["image_key"]

        log.passed(TEST_LOG_MSGS["catalog_roles_ok"].format(
            roles=result["roles"], archs=result["architectures"]
        ))

    def test_verify_registry_images(self, host, pipeline_state):
        """Verify container images exist in registry for each role."""
        log = TestLogger(TEST_NAMES.get("registry_images", "Registry Images Verification"))

        if not pipeline_state["job_id"]:
            log.skipped(SKIP_MSGS["no_job_id"])
            pytest.skip(SKIP_MSGS["no_job_id"])

        roles = pipeline_state.get("roles", [])
        if not roles:
            log.skipped("No roles available - catalog_roles test may have been skipped")
            pytest.skip("No roles available")

        result = verify_registry_images(
            host, pipeline_state["job_id"], roles, pipeline_state.get("image_key", "")
        )

        assert result["success"], (
            TEST_LOG_MSGS["registry_fail"].format(
                count=len(result["missing"]), missing=result["missing"]
            )
        )

        log.passed(TEST_LOG_MSGS["registry_ok"].format(count=len(result["found"])))

    def test_verify_s3_boot_images(self, host, pipeline_state):
        """Verify S3 boot images exist for each role."""
        log = TestLogger(TEST_NAMES.get("s3_boot_images", "S3 Boot Images Verification"))

        if not pipeline_state["job_id"]:
            log.skipped(SKIP_MSGS["no_job_id"])
            pytest.skip(SKIP_MSGS["no_job_id"])

        roles = pipeline_state.get("roles", [])
        if not roles:
            log.skipped("No roles available - catalog_roles test may have been skipped")
            pytest.skip("No roles available")

        result = verify_s3_boot_images(
            host, pipeline_state["job_id"], roles, pipeline_state.get("image_key", "")
        )

        assert result["success"], (
            TEST_LOG_MSGS["s3_fail"].format(
                count=len(result["missing_roles"]),
                missing=[r["role"] for r in result["missing_roles"]]
            )
        )

        log.passed(TEST_LOG_MSGS["s3_ok"].format(count=len(result["found_roles"])))
