"""Trigger and fully automate the GitLab deploy pipeline."""

import pytest

from library.functions import (
    TestLogger,
    list_pipelines,
    run_deploy_child_pipeline,
    swap_pxe_mapping_rows,
    wait_for_child_pipeline,
    wait_for_pipeline_triggered,
)
from library.vars import TEST_CASES as TC


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(0)
def test_execute_deploy_pipeline(host, deploy_pipeline_state):
    """Swap PXE rows, select the mapped image, and play deploy."""
    tc = TC["execute_deploy_pipeline"]
    tl = TestLogger(tc["title"], tc["id"])
    before = list_pipelines(host, per_page=5)
    assert before["success"], before["error"]
    initial_pipeline_id = 0
    if before["pipelines"]:
        initial_pipeline_id = int(before["pipelines"][0].get("id", 0))

    changed = swap_pxe_mapping_rows(host)
    assert changed["success"], changed["error"]
    tl.check("Swapped the first two PXE mapping data rows")
    parent = wait_for_pipeline_triggered(
        host, initial_pipeline_id, commit_id=changed["commit_id"],
    )
    assert parent["success"], parent["error"]
    deploy_pipeline_state.parent_pipeline_id = parent["pipeline_id"]
    tl.check(f"Deploy parent pipeline: {parent['pipeline_id']}")
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
