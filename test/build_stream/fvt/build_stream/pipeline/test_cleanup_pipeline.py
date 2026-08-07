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
Build Stream — Cleanup Pipeline FVT Tests.

Tests the cleanup pipeline lifecycle:
1. Trigger cleanup pipeline (PIPELINE_TYPE=cleanup)
2. Select image group for cleanup
3. Play cleanup trigger job
4. Wait for image group status → CLEANED
5. Verify registry images removed
6. Verify S3 boot images removed

Adapted from automation_v22/molecule/build_stream/test_cleanup_pipeline.py.
"""

import pytest

from library.functions import (
    TestLogger,
    trigger_cleanup_pipeline,
    select_image_for_cleanup,
    play_cleanup_stage_job,
    wait_for_cleanup_completion,
    get_all_image_groups,
    verify_registry_images,
    verify_s3_boot_images,
    get_catalog_roles,
    is_build_stream_enabled,
)
from library.vars.common_vars import CLEANUP_WAIT_TIMEOUT
from library.messages.build_stream_msgs import TEST_NAMES, TEST_LOG_MSGS, SKIP_MSGS


# =============================================================================
# MODULE-LEVEL STATE
# =============================================================================

_cleanup_state = {
    "pipeline_id": 0,
    "job_id": "",
    "image_group_id": "",
    "cleanup_success": False,
}


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(scope="module")
def cleanup_state():
    """Provide shared cleanup state across tests in this module."""
    return _cleanup_state


# =============================================================================
# TESTS
# =============================================================================

@pytest.mark.build_stream
@pytest.mark.pipeline
@pytest.mark.cleanup
@pytest.mark.order(400)
class TestCleanupPipeline:
    """Cleanup pipeline: trigger → select image → cleanup → verify."""

    def test_trigger_cleanup_pipeline(self, host, cleanup_state):
        """Trigger cleanup pipeline with PIPELINE_TYPE=cleanup."""
        log = TestLogger(TEST_NAMES.get(
            "cleanup_pipeline_trigger", "Cleanup Pipeline Trigger"
        ))

        if not is_build_stream_enabled(host):
            log.skipped(SKIP_MSGS["build_stream_disabled"])
            pytest.skip(SKIP_MSGS["build_stream_disabled"])

        result = trigger_cleanup_pipeline(host, log_callback=log.info)

        assert result["success"], (
            f"Failed to trigger cleanup pipeline: {result['error']}"
        )

        cleanup_state["pipeline_id"] = result["pipeline_id"]

        log.passed(f"Cleanup pipeline #{result['pipeline_id']} triggered")

    def test_select_image_for_cleanup(self, host, cleanup_state):
        """Select image group for cleanup."""
        log = TestLogger(TEST_NAMES.get(
            "cleanup_image_select", "Cleanup Image Selection"
        ))

        if not cleanup_state["pipeline_id"]:
            log.skipped(SKIP_MSGS["pipeline_not_triggered"])
            pytest.skip(SKIP_MSGS["pipeline_not_triggered"])

        result = select_image_for_cleanup(
            host, cleanup_state["pipeline_id"], log_callback=log.info
        )

        assert result["success"], (
            f"Failed to select image for cleanup: {result['error']}"
        )

        cleanup_state["image_group_id"] = result["image_group_id"]
        cleanup_state["job_id"] = result.get("job_id", "")

        log.passed(f"Image group selected for cleanup: {result['image_group_id']}")

    def test_play_cleanup_job(self, host, cleanup_state):
        """Play the cleanup trigger job to start cleanup stages."""
        log = TestLogger("Play Cleanup Trigger Job")

        if not cleanup_state["pipeline_id"]:
            log.skipped(SKIP_MSGS["pipeline_not_triggered"])
            pytest.skip(SKIP_MSGS["pipeline_not_triggered"])

        result = play_cleanup_stage_job(
            host, cleanup_state["pipeline_id"], log_callback=log.info
        )

        assert result["success"], (
            f"Failed to play cleanup job: {result['error']}"
        )

        log.passed(f"Cleanup job played (GitLab job ID: {result['job_id']})")

    def test_wait_for_cleanup_completion(self, host, cleanup_state):
        """Wait for image group status to become CLEANED."""
        log = TestLogger(TEST_NAMES.get("cleanup_verify", "Cleanup Verification"))

        if not cleanup_state["image_group_id"]:
            log.skipped("No image group selected for cleanup")
            pytest.skip("No image group selected for cleanup")

        result = wait_for_cleanup_completion(
            host,
            cleanup_state["image_group_id"],
            timeout=CLEANUP_WAIT_TIMEOUT,
            log_callback=log.info,
        )

        assert result["success"], (
            f"Cleanup did not complete: {result['error']}"
        )

        cleanup_state["cleanup_success"] = True

        log.passed(
            f"Image group {cleanup_state['image_group_id']} "
            f"cleaned successfully (status: {result['status']})"
        )

    def test_verify_image_group_cleaned(self, host, cleanup_state):
        """Verify image group status is CLEANED in database."""
        log = TestLogger("Verify Image Group CLEANED Status")

        if not cleanup_state["image_group_id"]:
            log.skipped("No image group to verify")
            pytest.skip("No image group to verify")

        result = get_all_image_groups(host)

        assert result["success"], (
            f"Failed to get image groups: {result['error']}"
        )

        target_group = None
        for ig in result["image_groups"]:
            if ig.get("id") == cleanup_state["image_group_id"]:
                target_group = ig
                break

        assert target_group is not None, (
            f"Image group {cleanup_state['image_group_id']} not found in database"
        )

        assert target_group["status"] == "CLEANED", (
            f"Image group status is '{target_group['status']}', expected 'CLEANED'"
        )

        log.passed(
            f"Image group {cleanup_state['image_group_id']} "
            f"verified as CLEANED in database"
        )

    def test_verify_registry_images_removed(self, host, cleanup_state):
        """Verify container images removed from registry after cleanup."""
        log = TestLogger("Verify Registry Images Removed After Cleanup")

        if not cleanup_state["job_id"]:
            log.skipped(SKIP_MSGS["no_job_id"])
            pytest.skip(SKIP_MSGS["no_job_id"])

        if not cleanup_state["cleanup_success"]:
            log.skipped("Cleanup did not complete successfully")
            pytest.skip("Cleanup did not complete successfully")

        roles_result = get_catalog_roles(host, cleanup_state["job_id"])
        if not roles_result["success"] or not roles_result["roles"]:
            log.skipped("Cannot determine roles for verification")
            pytest.skip("Cannot determine roles for verification")

        result = verify_registry_images(
            host, cleanup_state["job_id"],
            roles_result["roles"],
            roles_result.get("image_key", ""),
        )

        # After cleanup, images should NOT be found
        assert not result["success"] or len(result["found"]) == 0, (
            f"Registry images still present after cleanup: "
            f"{[r['role'] for r in result['found']]}"
        )

        log.passed("Registry images verified as removed after cleanup")

    def test_verify_s3_images_removed(self, host, cleanup_state):
        """Verify S3 boot images removed after cleanup."""
        log = TestLogger("Verify S3 Boot Images Removed After Cleanup")

        if not cleanup_state["job_id"]:
            log.skipped(SKIP_MSGS["no_job_id"])
            pytest.skip(SKIP_MSGS["no_job_id"])

        if not cleanup_state["cleanup_success"]:
            log.skipped("Cleanup did not complete successfully")
            pytest.skip("Cleanup did not complete successfully")

        roles_result = get_catalog_roles(host, cleanup_state["job_id"])
        if not roles_result["success"] or not roles_result["roles"]:
            log.skipped("Cannot determine roles for verification")
            pytest.skip("Cannot determine roles for verification")

        result = verify_s3_boot_images(
            host, cleanup_state["job_id"],
            roles_result["roles"],
            roles_result.get("image_key", ""),
        )

        # After cleanup, boot images should NOT be found
        assert not result["success"] or len(result["found_roles"]) == 0, (
            f"S3 boot images still present after cleanup: "
            f"{[r['role'] for r in result['found_roles']]}"
        )

        log.passed("S3 boot images verified as removed after cleanup")
