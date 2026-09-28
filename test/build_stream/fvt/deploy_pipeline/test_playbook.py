"""Trigger and fully automate the GitLab deploy pipeline."""

import pytest

from library.functions import (
    TestLogger,
    run_deploy_child_pipeline,
    trigger_pipeline_with_variables,
    wait_for_child_pipeline,
)
from library.vars import TEST_CASES as TC


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(0)
def test_execute_deploy_pipeline(host, deploy_pipeline_state):
    """Trigger deploy via the API, select the mapped image, and play deploy."""
    tc = TC["execute_deploy_pipeline"]
    tl = TestLogger(tc["title"], tc["id"])
    parent = trigger_pipeline_with_variables(
        host, {"PIPELINE_TYPE": "deploy"},
    )
    assert parent["success"], parent["error"]
    deploy_pipeline_state.parent_pipeline_id = parent["pipeline_id"]
    tl.check(
        f"Triggered deploy parent pipeline via API: {parent['pipeline_id']}"
    )
    controller = wait_for_child_pipeline(host, parent["pipeline_id"])
    assert controller["success"], controller["error"]
    tl.check(f"Deploy controller pipeline: {controller['child_pipeline_id']}")
    child = wait_for_child_pipeline(host, controller["child_pipeline_id"])
    assert child["success"], child["error"]
    deploy_pipeline_state.child_pipeline_id = child["child_pipeline_id"]
    tl.check(f"Dynamic deploy child pipeline: {child['child_pipeline_id']}")
    completed = run_deploy_child_pipeline(
        host,
        child["child_pipeline_id"],
        deploy_pipeline_state.image_group_id,
        log_callback=tl.check,
    )
    assert completed["success"], completed["error"]
    deploy_pipeline_state.summary_job_id = completed["summary_job_id"]
    tl.passed("Deploy pipeline completed successfully")
