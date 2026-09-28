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
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied
# See the License for the specific language governing permissions and
# limitations under the License.

"""Manual deploy-pipeline stage monitoring and database verification."""
# pylint: disable=duplicate-code

import os

import pytest

from library.functions import (
    TestLogger,
    poll_stage_until_complete,
    run_deploy_child_pipeline,
    trigger_pipeline_with_variables,
    verify_stage_completed,
    wait_for_child_pipeline,
)
from library.vars import TEST_CASES as TC


pytestmark = pytest.mark.usefixtures("manual_pipeline_prerequisites")


def _logger(name):
    case = TC[name]
    return TestLogger(case["title"], case["id"])


def _require_job(state, tl):
    if not state.job_id:
        tl.skipped("No configured build job is available")
        pytest.skip("Run the manual build pipeline before deploy verification")


def _monitor(host, state, stage_name, tc_name):
    tl = _logger(tc_name)
    _require_job(state, tl)
    result = poll_stage_until_complete(
        host, state.job_id, stage_name, log_callback=tl.check,
    )
    assert result["success"], result["error"]
    tl.passed(f"Stage '{stage_name}' completed")


def _verify(host, state, stage_name, tc_name):
    tl = _logger(tc_name)
    _require_job(state, tl)
    result = verify_stage_completed(host, state.job_id, stage_name)
    assert result["success"], result["error"]
    tl.passed(f"Stage '{stage_name}' is COMPLETED in the database")


@pytest.mark.manual
@pytest.mark.deploy
@pytest.mark.order(0)
def test_manual_trigger_deploy_pipeline(
    host, deploy_pipeline_state, manual_pipeline_prerequisites,
):
    """Trigger deploy with PIPELINE_TYPE=deploy and run its child pipeline."""
    tl = _logger("manual_trigger_deploy_pipeline")
    tl.check(
        "Installation prerequisites passed: "
        + ", ".join(manual_pipeline_prerequisites)
    )
    if os.environ.get("OMNIA_COMMAND_TYPE", "") == "verify":
        for stage_name in ("deploy", "restart", "validate"):
            stage = verify_stage_completed(
                host, deploy_pipeline_state.job_id, stage_name,
            )
            assert stage["success"], stage["error"]
        tl.passed(
            "Existing manual deploy pipeline recovered successfully; "
            "deploy, restart, and validate are COMPLETED"
        )
        return

    parent = trigger_pipeline_with_variables(host, {"PIPELINE_TYPE": "deploy"})
    assert parent["success"], parent["error"]
    deploy_pipeline_state.parent_pipeline_id = parent["pipeline_id"]
    tl.check(f"Triggered deploy pipeline {parent['pipeline_id']}")
    controller = wait_for_child_pipeline(host, parent["pipeline_id"])
    assert controller["success"], controller["error"]
    child = wait_for_child_pipeline(host, controller["child_pipeline_id"])
    assert child["success"], child["error"]
    deploy_pipeline_state.child_pipeline_id = child["child_pipeline_id"]
    completed = run_deploy_child_pipeline(
        host, child["child_pipeline_id"], deploy_pipeline_state.image_group_id,
        log_callback=tl.check,
    )
    assert completed["success"], completed["error"]
    deploy_pipeline_state.summary_job_id = completed["summary_job_id"]
    tl.passed("Deploy pipeline completed successfully")


@pytest.mark.manual
@pytest.mark.order(1)
def test_manual_deploy_stage_deploy_monitor(host, deploy_pipeline_state):
    """Monitor the deploy stage until it completes."""
    _monitor(host, deploy_pipeline_state, "deploy", "manual_deploy_stage_deploy_monitor")


@pytest.mark.manual
@pytest.mark.order(2)
def test_manual_deploy_stage_deploy_db_verify(host, deploy_pipeline_state):
    """Verify the deploy stage completed in the database."""
    _verify(host, deploy_pipeline_state, "deploy", "manual_deploy_stage_deploy_db_verify")


@pytest.mark.manual
@pytest.mark.order(3)
def test_manual_deploy_stage_restart_monitor(host, deploy_pipeline_state):
    """Monitor the restart stage until it completes."""
    _monitor(host, deploy_pipeline_state, "restart", "manual_deploy_stage_restart_monitor")


@pytest.mark.manual
@pytest.mark.order(4)
def test_manual_deploy_stage_restart_db_verify(host, deploy_pipeline_state):
    """Verify the restart stage completed in the database."""
    _verify(host, deploy_pipeline_state, "restart", "manual_deploy_stage_restart_db_verify")


@pytest.mark.manual
@pytest.mark.order(5)
def test_manual_deploy_stage_validate_monitor(host, deploy_pipeline_state):
    """Monitor the validate stage until it completes."""
    _monitor(host, deploy_pipeline_state, "validate", "manual_deploy_stage_validate_monitor")


@pytest.mark.manual
@pytest.mark.order(6)
def test_manual_deploy_stage_validate_db_verify(host, deploy_pipeline_state):
    """Verify the validate stage completed in the database."""
    _verify(host, deploy_pipeline_state, "validate", "manual_deploy_stage_validate_db_verify")
