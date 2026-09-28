"""Read-only verification for a completed deploy pipeline."""

import pytest

from library.functions import (
    TestLogger,
    get_bsm_artifact_json,
    get_bsm_job_details,
    get_gitlab_job_trace,
    get_gitlab_pipeline_jobs,
    get_pipeline_summary,
    resolve_deploy_image_group,
    verify_stage_completed,
)
from library.vars import TEST_CASES as TC
from library.vars.common_vars import (
    IMAGE_GROUP_STATUS_PASSED,
    JOB_STATE_COMPLETED,
    JOB_STATE_SUCCEEDED,
    STAGE_DEPLOY,
    STAGE_RESTART,
    STAGE_VALIDATE,
)


def _logger(case_name):
    case = TC[case_name]
    return TestLogger(case["title"], case["id"])


def _require_pipeline_ids(state):
    assert state.parent_pipeline_id > 0, (
        "Unable to discover the deploy parent pipeline from job_id"
    )
    assert state.child_pipeline_id > 0, (
        "Unable to discover the dynamic deploy child pipeline from job_id"
    )


@pytest.mark.sanity
@pytest.mark.order(1)
def test_deploy_prerequisites(host, deploy_pipeline_state):
    """The mandatory job still maps to exactly one image group."""
    tl = _logger("deploy_prerequisites")
    result = resolve_deploy_image_group(host, deploy_pipeline_state.job_id)
    assert result["success"], result["error"]
    assert result["image_group_id"] == deploy_pipeline_state.image_group_id
    tl.passed("Configured job maps to exactly one deploy image group")


@pytest.mark.sanity
@pytest.mark.order(2)
def test_deploy_gitlab_pipeline(host, deploy_pipeline_state):
    """The selected child-pipeline jobs all succeeded."""
    tl = _logger("deploy_gitlab_pipeline")
    _require_pipeline_ids(deploy_pipeline_state)
    result = get_gitlab_pipeline_jobs(host, deploy_pipeline_state.child_pipeline_id)
    assert result["success"], result["error"]
    jobs = {job["name"]: job for job in result["jobs"]}
    expected = [
        deploy_pipeline_state.image_group_id,
        "deploy", "restart", "validate", "summary",
    ]
    missing = [name for name in expected if name not in jobs]
    failed = [
        name for name in expected
        if name in jobs and jobs[name]["status"] != "success"
    ]
    assert not missing, f"Missing child-pipeline jobs: {missing}"
    assert not failed, f"Child-pipeline jobs not successful: {failed}"
    tl.passed("Deploy child pipeline completed all required jobs")


@pytest.mark.sanity
@pytest.mark.order(3)
def test_deploy_selected_image(host, deploy_pipeline_state):
    """Selection trace contains the configured job and mapped image group."""
    tl = _logger("deploy_selected_image")
    _require_pipeline_ids(deploy_pipeline_state)
    jobs = get_gitlab_pipeline_jobs(host, deploy_pipeline_state.child_pipeline_id)
    assert jobs["success"], jobs["error"]
    selected = [
        job for job in jobs["jobs"]
        if job["name"] == deploy_pipeline_state.image_group_id
    ]
    assert len(selected) == 1, "Expected exactly one selected image-group job"
    trace = get_gitlab_job_trace(host, selected[0]["id"])
    assert trace["success"], trace["error"]
    assert deploy_pipeline_state.job_id in trace["trace"]
    assert deploy_pipeline_state.image_group_id in trace["trace"]
    tl.passed("GitLab selected the image group mapped to configured job_id")


@pytest.mark.sanity
@pytest.mark.order(4)
def test_deploy_stage_completed(host, deploy_pipeline_state):
    """BuildStream deploy stage completed."""
    tl = _logger("deploy_stage_completed")
    result = verify_stage_completed(host, deploy_pipeline_state.job_id, STAGE_DEPLOY)
    assert result["success"], result["error"]
    tl.passed("Deploy stage is COMPLETED")


@pytest.mark.sanity
@pytest.mark.order(5)
def test_restart_stage_completed(host, deploy_pipeline_state):
    """BuildStream restart stage completed."""
    tl = _logger("restart_stage_completed")
    result = verify_stage_completed(host, deploy_pipeline_state.job_id, STAGE_RESTART)
    assert result["success"], result["error"]
    tl.passed("Restart stage is COMPLETED")


@pytest.mark.sanity
@pytest.mark.order(6)
def test_restart_node_results(host, deploy_pipeline_state):
    """Validate node results and treat absent failed-nodes as success."""
    tl = _logger("restart_node_results")
    nodes = get_bsm_artifact_json(host, deploy_pipeline_state.job_id, "node-results")
    assert nodes["success"] and nodes["exists"], (
        nodes["error"] or "node-results artifact is missing"
    )
    if nodes.get("source") == "filesystem-fallback":
        tl.check(nodes["api_error"] + "; validated canonical artifact file")
    node_data = nodes["data"]
    assert isinstance(node_data, dict)
    node_list = node_data.get("nodes")
    assert isinstance(node_list, list)
    assert node_data.get("job_id") == deploy_pipeline_state.job_id

    failed = get_bsm_artifact_json(host, deploy_pipeline_state.job_id, "failed-nodes")
    assert failed["success"], failed["error"]
    if failed.get("source") == "filesystem-fallback":
        tl.check(failed["api_error"] + "; validated canonical artifact file")
    if not failed["exists"]:
        tl.passed("Node results valid; no failed-nodes artifact was created")
        return
    failed_data = failed["data"]
    assert isinstance(failed_data, dict)
    failed_nodes = failed_data.get("failed_nodes", [])
    assert isinstance(failed_nodes, list)
    node_status = {
        item.get("bmc_ip"): item.get("status")
        for item in node_list if isinstance(item, dict)
    }
    inconsistent = [
        item.get("bmc_ip") if isinstance(item, dict) else "invalid-entry"
        for item in failed_nodes
        if not isinstance(item, dict)
        or node_status.get(item.get("bmc_ip")) != "failed"
    ]
    assert not inconsistent, (
        f"failed-nodes is inconsistent with node-results: {inconsistent}"
    )
    tl.passed(f"Node results valid; {len(failed_nodes)} failed nodes recorded")


@pytest.mark.sanity
@pytest.mark.order(7)
def test_validate_stage_completed(host, deploy_pipeline_state):
    """BuildStream validate stage completed."""
    tl = _logger("validate_stage_completed")
    result = verify_stage_completed(host, deploy_pipeline_state.job_id, STAGE_VALIDATE)
    assert result["success"], result["error"]
    tl.passed("Validate stage is COMPLETED")


@pytest.mark.sanity
@pytest.mark.order(8)
def test_deploy_final_state(host, deploy_pipeline_state):
    """Job and image group reached successful terminal states."""
    tl = _logger("deploy_final_state")
    job = get_bsm_job_details(host, deploy_pipeline_state.job_id)
    assert job["success"], job["error"]
    assert job["job"].get("job_state") in {
        JOB_STATE_COMPLETED, JOB_STATE_SUCCEEDED,
    }
    group = resolve_deploy_image_group(host, deploy_pipeline_state.job_id)
    assert group["success"], group["error"]
    assert group["status"] == IMAGE_GROUP_STATUS_PASSED, (
        f"Image group is {group['status']}; expected {IMAGE_GROUP_STATUS_PASSED}"
    )
    tl.passed(
        f"Job is {job['job'].get('job_state')} and image group is PASSED"
    )


@pytest.mark.sanity
@pytest.mark.order(9)
def test_deploy_pipeline_summary(host, deploy_pipeline_state):
    """Database stages and GitLab summary both report completion."""
    tl = _logger("deploy_pipeline_summary")
    summary = get_pipeline_summary(host, deploy_pipeline_state.job_id, build_only=False)
    assert summary["success"], summary["error"]
    deploy_stages = {
        item["stage_name"]: item["stage_state"]
        for item in summary["stages"]
        if item["stage_name"] in {STAGE_DEPLOY, STAGE_RESTART, STAGE_VALIDATE}
    }
    assert len(deploy_stages) == 3
    assert all(value == "COMPLETED" for value in deploy_stages.values())
    assert deploy_pipeline_state.summary_job_id > 0, (
        "Unable to discover the deploy summary job from job_id"
    )
    trace = get_gitlab_job_trace(host, deploy_pipeline_state.summary_job_id)
    assert trace["success"], trace["error"]
    assert "RESULT:  PASSED" in trace["trace"]
    tl.passed("Deploy pipeline summary reports PASSED")
