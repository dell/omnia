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
Build Stream — Manual Deploy Pipeline FVT Tests.

Tests the deploy pipeline lifecycle:
1. Trigger deploy pipeline (PXE commit or manual variable)
2. Select image group for deployment
3. Play deploy trigger job
4. Monitor deploy stages (deploy, restart, validate-image)
5. Verify database state

Adapted from automation_v22/molecule/build_stream/test_manual_pipeline.py.
"""

import pytest

from library.functions import (
    TestLogger,
    trigger_deploy_pipeline,
    select_image_for_deploy,
    play_deploy_stage_job,
    wait_for_stage_completion,
    verify_stage_completed,
    is_build_stream_enabled,
)
from library.vars.common_vars import (
    DEPLOY_PIPELINE_STAGES,
    STAGE_POLL_INTERVAL,
    STAGE_POLL_TIMEOUT,
    STAGE_VALIDATE_IMAGE,
)
from library.messages.build_stream_msgs import TEST_NAMES, TEST_LOG_MSGS, SKIP_MSGS


# =============================================================================
# MODULE-LEVEL STATE
# =============================================================================

_deploy_state = {
    "pipeline_id": 0,
    "job_id": "",
    "image_group_id": "",
    "deploy_success": False,
}


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(scope="module")
def deploy_state():
    """Provide shared deploy state across tests in this module."""
    return _deploy_state


# =============================================================================
# TESTS
# =============================================================================

@pytest.mark.build_stream
@pytest.mark.pipeline
@pytest.mark.deploy
@pytest.mark.order(300)
class TestManualDeployPipeline:
    """Manual deploy pipeline: trigger → select image → deploy → validate."""

    def test_trigger_deploy_pipeline(self, host, deploy_state):
        """Trigger deploy pipeline via PXE mapping file commit."""
        log = TestLogger(TEST_NAMES.get("deploy_pipeline_trigger", "Deploy Pipeline Trigger"))

        if not is_build_stream_enabled(host):
            log.skipped(SKIP_MSGS["build_stream_disabled"])
            pytest.skip(SKIP_MSGS["build_stream_disabled"])

        result = trigger_deploy_pipeline(
            host, log_callback=log.info, use_pxe_commit=True
        )

        assert result["success"], (
            f"Failed to trigger deploy pipeline: {result['error']}"
        )

        deploy_state["pipeline_id"] = result["pipeline_id"]
        deploy_state["job_id"] = result.get("job_id", "")

        log.passed(f"Deploy pipeline #{result['pipeline_id']} triggered")

    def test_select_image_for_deploy(self, host, deploy_state):
        """Select image group for deployment."""
        log = TestLogger(TEST_NAMES.get("deploy_image_select", "Deploy Image Selection"))

        if not deploy_state["pipeline_id"]:
            log.skipped(SKIP_MSGS["pipeline_not_triggered"])
            pytest.skip(SKIP_MSGS["pipeline_not_triggered"])

        result = select_image_for_deploy(
            host, deploy_state["pipeline_id"], log_callback=log.info
        )

        assert result["success"], (
            f"Failed to select image for deploy: {result['error']}"
        )

        deploy_state["image_group_id"] = result["image_group_id"]
        if result.get("job_id"):
            deploy_state["job_id"] = result["job_id"]

        log.passed(f"Image group selected: {result['image_group_id']}")

    def test_play_deploy_job(self, host, deploy_state):
        """Play the deploy trigger job to start deployment stages."""
        log = TestLogger("Play Deploy Trigger Job")

        if not deploy_state["pipeline_id"]:
            log.skipped(SKIP_MSGS["pipeline_not_triggered"])
            pytest.skip(SKIP_MSGS["pipeline_not_triggered"])

        result = play_deploy_stage_job(
            host, deploy_state["pipeline_id"], log_callback=log.info
        )

        assert result["success"], (
            f"Failed to play deploy job: {result['error']}"
        )

        log.passed(f"Deploy job played (GitLab job ID: {result['job_id']})")

    @pytest.mark.parametrize("stage_name", DEPLOY_PIPELINE_STAGES)
    def test_deploy_stage_completion(self, host, deploy_state, stage_name):
        """Monitor each deploy stage until completion."""
        log = TestLogger(TEST_NAMES.get("stage_monitor", "Stage Monitor").format(
            stage=stage_name
        ))

        if not deploy_state["job_id"]:
            log.skipped(SKIP_MSGS["no_job_id"])
            pytest.skip(SKIP_MSGS["no_job_id"])

        result = wait_for_stage_completion(
            host,
            deploy_state["job_id"],
            stage_name,
            timeout=STAGE_POLL_TIMEOUT,
            poll_interval=STAGE_POLL_INTERVAL,
            log_callback=log.info,
        )

        assert result["success"], (
            f"Deploy stage '{stage_name}' failed: {result['error']}"
        )

        if stage_name == STAGE_VALIDATE_IMAGE:
            deploy_state["deploy_success"] = True

        log.passed(TEST_LOG_MSGS["stage_completed"].format(
            stage=stage_name, elapsed=result["elapsed"]
        ))

    def test_verify_deploy_stages_in_db(self, host, deploy_state):
        """Verify all deploy stages completed in database."""
        log = TestLogger("Verify All Deploy Stages in Database")

        if not deploy_state["job_id"]:
            log.skipped(SKIP_MSGS["no_job_id"])
            pytest.skip(SKIP_MSGS["no_job_id"])

        failed_stages = []
        for stage in DEPLOY_PIPELINE_STAGES:
            result = verify_stage_completed(host, deploy_state["job_id"], stage)
            if not result["success"]:
                failed_stages.append(f"{stage}: {result['error']}")
            else:
                log.info(TEST_LOG_MSGS["stage_db_ok"].format(
                    stage=stage, state=result["stage_state"]
                ))

        assert not failed_stages, (
            f"Deploy stage verification failed:\n" + "\n".join(failed_stages)
        )

        log.passed("All deploy stages verified in database")
