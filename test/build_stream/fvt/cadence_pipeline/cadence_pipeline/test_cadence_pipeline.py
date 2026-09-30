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

"""Read-only verification for one completed unified cadence pipeline."""

import pytest

from library.functions import (
    TestLogger,
    check_build_status,
    check_cadence_local_repo_status,
    check_repo_resync_status,
    get_bsm_artifact_json,
    get_catalog_identity_for_job,
    get_bsm_job_details,
    get_gitlab_job_trace,
    get_gitlab_pipeline_jobs,
    get_images_for_job,
    get_pipeline_summary,
    resolve_deploy_image_group,
    verify_initialization_health,
    verify_registry_images,
    verify_s3_boot_images,
    verify_stage_completed,
)
from library.vars import TEST_CASES as TC
from library.vars.common_vars import (
    GITLAB_CI_CADENCE_JOBS,
    IMAGE_GROUP_STATUS_PASSED,
    JOB_STATE_COMPLETED,
    JOB_STATE_SUCCEEDED,
    STAGE_BUILD_IMAGE,
    STAGE_CREATE_LOCAL_REPO,
    STAGE_DEPLOY,
    STAGE_PARSE_CATALOG,
    STAGE_RESTART,
    STAGE_VALIDATE,
)


def _logger(case_name):
    case = TC[case_name]
    return TestLogger(case["title"], case["id"])


def _job_roles(host, state):
    images = get_images_for_job(host, state.job_id)
    assert images["success"], images["error"]
    roles = sorted({
        image["role"] for image in images["images"] if image.get("role")
    })
    assert roles, f"No image roles recorded for cadence job {state.job_id}"
    return roles


@pytest.mark.sanity
@pytest.mark.order(17)
def test_cadence_gitlab_jobs(host, cadence_pipeline_state):
    """V017: All eight GitLab cadence jobs completed successfully."""
    tl = _logger("cadence_gitlab_jobs")
    result = get_gitlab_pipeline_jobs(
        host, cadence_pipeline_state.child_pipeline_id,
    )
    assert result["success"], result["error"]
    jobs = {job["name"]: job for job in result["jobs"]}
    missing = [name for name in GITLAB_CI_CADENCE_JOBS if name not in jobs]
    failed = [
        name for name in GITLAB_CI_CADENCE_JOBS
        if name in jobs and jobs[name]["status"] != "success"
    ]
    assert not missing, f"Missing cadence GitLab jobs: {missing}"
    assert not failed, f"Cadence GitLab jobs not successful: {failed}"
    tl.passed("All eight cadence GitLab jobs succeeded")


@pytest.mark.sanity
@pytest.mark.order(18)
def test_cadence_catalog_identity(host, cadence_pipeline_state):
    """V018: Job and ImageGroup identities match the pipeline catalog."""
    tl = _logger("cadence_catalog_identity")
    expected = (
        f"{cadence_pipeline_state.catalog_identifier}"
        f"-v{cadence_pipeline_state.catalog_version}"
    )
    assert cadence_pipeline_state.image_group_id == expected

    job = get_bsm_job_details(host, cadence_pipeline_state.job_id)
    assert job["success"], job["error"]
    assert job["job"].get("job_id") == cadence_pipeline_state.job_id
    identity = get_catalog_identity_for_job(
        host, cadence_pipeline_state.job_id,
    )
    assert identity["success"], identity["error"]
    # The ImageGroup ID is the canonical composite catalog identity. Older
    # migrated Job rows may not duplicate that value in
    # composite_image_group_id, so validate it when present without rejecting
    # an otherwise consistent Job/ImageGroup relationship.
    if identity["job_composite_id"]:
        assert identity["job_composite_id"] == expected
    assert identity["image_group_id"] == expected
    if identity["job_catalog_identifier"]:
        assert identity["job_catalog_identifier"] == (
            cadence_pipeline_state.catalog_identifier
        )
    assert identity["group_catalog_identifier"] == (
        cadence_pipeline_state.catalog_identifier
    )
    if identity["job_catalog_version"]:
        assert identity["job_catalog_version"] == (
            cadence_pipeline_state.catalog_version
        )
    assert identity["group_catalog_version"] == (
        cadence_pipeline_state.catalog_version
    )

    jobs = get_gitlab_pipeline_jobs(
        host, cadence_pipeline_state.child_pipeline_id,
    )
    assert jobs["success"], jobs["error"]
    by_name = {item["name"]: item for item in jobs["jobs"]}
    initialization = get_gitlab_job_trace(
        host, by_name["initialization"]["id"],
    )
    parsed = get_gitlab_job_trace(host, by_name["parse-catalog"]["id"])
    assert initialization["success"], initialization["error"]
    assert parsed["success"], parsed["error"]
    assert cadence_pipeline_state.job_id in initialization["trace"]
    assert expected in parsed["trace"]
    # Deployment is linked to the same BSM job through its completed DB
    # stage.  The deploy console output is not an identity contract and may
    # omit the composite ImageGroup ID, so do not depend on incidental log
    # text here.
    deploy_stage = verify_stage_completed(
        host, cadence_pipeline_state.job_id, STAGE_DEPLOY,
    )
    assert deploy_stage["success"], deploy_stage["error"]
    tl.passed(f"Cadence pipeline consistently used {expected}")


@pytest.mark.sanity
@pytest.mark.order(19)
def test_cadence_build_stages(host, cadence_pipeline_state):
    """V019: Parse, local-repository, and image-build DB stages completed."""
    tl = _logger("cadence_build_stages")
    stages = (
        STAGE_PARSE_CATALOG,
        STAGE_CREATE_LOCAL_REPO,
        STAGE_BUILD_IMAGE,
    )
    failures = []
    for stage in stages:
        result = verify_stage_completed(
            host, cadence_pipeline_state.job_id, stage,
        )
        if not result["success"]:
            failures.append(result["error"])
    assert not failures, "\n".join(failures)
    tl.passed("All mandatory cadence build stages are COMPLETED")


@pytest.mark.sanity
@pytest.mark.order(20)
def test_cadence_registry_artifacts(host, cadence_pipeline_state):
    """V020: Every requested role has a registry artifact."""
    tl = _logger("cadence_registry_artifacts")
    roles = _job_roles(host, cadence_pipeline_state)
    registry = verify_registry_images(
        host, cadence_pipeline_state.job_id, roles,
    )
    assert registry["success"], (
        registry.get("error")
        or f"Missing registry images: {registry.get('missing', [])}"
    )
    tl.passed(f"Registry artifacts verified for {len(roles)} roles")


@pytest.mark.sanity
@pytest.mark.order(21)
def test_cadence_job_accessible(host, cadence_pipeline_state):
    """V021: BSM is healthy and the cadence job is API-accessible."""
    tl = _logger("cadence_job_accessible")
    health = verify_initialization_health(
        host, cadence_pipeline_state.job_id,
    )
    assert health["success"], health["error"]
    job = get_bsm_job_details(host, cadence_pipeline_state.job_id)
    assert job["success"], job["error"]
    assert job["job"].get("job_id") == cadence_pipeline_state.job_id
    tl.passed("BSM API is healthy and cadence job is accessible")


@pytest.mark.sanity
@pytest.mark.order(22)
def test_cadence_repo_resync_status(host, cadence_pipeline_state):
    """V022: Exact-mirror Repo Manager output contract is successful."""
    tl = _logger("cadence_repo_resync_status")
    result = check_repo_resync_status(
        host, catalog_ref=cadence_pipeline_state.pipeline_sha,
    )
    assert result["success"], result["error"]
    tl.passed(result["details"])


@pytest.mark.sanity
@pytest.mark.order(23)
def test_cadence_deploy_stage(host, cadence_pipeline_state):
    """V023: Deploy DB stage completed."""
    tl = _logger("cadence_deploy_stage")
    result = verify_stage_completed(
        host, cadence_pipeline_state.job_id, STAGE_DEPLOY,
    )
    assert result["success"], result["error"]
    tl.passed("Cadence deploy stage is COMPLETED")


@pytest.mark.sanity
@pytest.mark.order(24)
def test_cadence_restart_stage(host, cadence_pipeline_state):
    """V024: Restart DB stage completed."""
    tl = _logger("cadence_restart_stage")
    result = verify_stage_completed(
        host, cadence_pipeline_state.job_id, STAGE_RESTART,
    )
    assert result["success"], result["error"]
    tl.passed("Cadence restart stage is COMPLETED")


@pytest.mark.sanity
@pytest.mark.order(25)
def test_cadence_validate_stage(host, cadence_pipeline_state):
    """V025: Validate DB stage completed."""
    tl = _logger("cadence_validate_stage")
    result = verify_stage_completed(
        host, cadence_pipeline_state.job_id, STAGE_VALIDATE,
    )
    assert result["success"], result["error"]
    tl.passed("Cadence validate stage is COMPLETED")


@pytest.mark.sanity
@pytest.mark.order(26)
def test_cadence_restart_results(host, cadence_pipeline_state):
    """V026: Restart produced consistent node-result artifacts."""
    tl = _logger("cadence_restart_results")
    nodes = get_bsm_artifact_json(
        host, cadence_pipeline_state.job_id, "node-results",
    )
    assert nodes["success"] and nodes["exists"], (
        nodes["error"] or "node-results artifact is missing"
    )
    node_data = nodes["data"]
    assert isinstance(node_data, dict)
    assert node_data.get("job_id") == cadence_pipeline_state.job_id
    node_list = node_data.get("nodes")
    assert isinstance(node_list, list)

    failed = get_bsm_artifact_json(
        host, cadence_pipeline_state.job_id, "failed-nodes",
    )
    assert failed["success"], failed["error"]
    if failed["exists"]:
        failed_nodes = failed["data"].get("failed_nodes", [])
        assert isinstance(failed_nodes, list)
        statuses = {
            item.get("bmc_ip"): item.get("status")
            for item in node_list if isinstance(item, dict)
        }
        inconsistent = [
            item.get("bmc_ip") if isinstance(item, dict) else "invalid-entry"
            for item in failed_nodes
            if not isinstance(item, dict)
            or statuses.get(item.get("bmc_ip")) != "failed"
        ]
        assert not inconsistent, (
            f"failed-nodes conflicts with node-results: {inconsistent}"
        )
    tl.passed("Cadence restart node-result artifacts are consistent")


@pytest.mark.sanity
@pytest.mark.order(27)
def test_cadence_final_state(host, cadence_pipeline_state):
    """V027: The cadence job and image group reached success states."""
    tl = _logger("cadence_final_state")
    job = get_bsm_job_details(host, cadence_pipeline_state.job_id)
    assert job["success"], job["error"]
    assert job["job"].get("job_state") in {
        JOB_STATE_COMPLETED, JOB_STATE_SUCCEEDED,
    }
    image_group = resolve_deploy_image_group(
        host, cadence_pipeline_state.job_id,
    )
    assert image_group["success"], image_group["error"]
    assert image_group["status"] == IMAGE_GROUP_STATUS_PASSED, (
        f"Image group is {image_group['status']}; "
        f"expected {IMAGE_GROUP_STATUS_PASSED}"
    )
    tl.passed(
        f"Job is {job['job'].get('job_state')} and image group is PASSED"
    )


@pytest.mark.sanity
@pytest.mark.order(28)
def test_cadence_summary(host, cadence_pipeline_state):
    """V028: Database stages and GitLab summary report completion."""
    tl = _logger("cadence_summary")
    summary = get_pipeline_summary(
        host, cadence_pipeline_state.job_id, build_only=False,
    )
    assert summary["success"], summary["error"]
    required = {
        STAGE_PARSE_CATALOG,
        STAGE_CREATE_LOCAL_REPO,
        STAGE_BUILD_IMAGE,
        STAGE_DEPLOY,
        STAGE_RESTART,
        STAGE_VALIDATE,
    }
    actual = {
        item["stage_name"]: item["stage_state"]
        for item in summary["stages"]
        if item["stage_name"] in required
    }
    assert set(actual) == required, (
        f"Missing cadence DB stages: {sorted(required - set(actual))}"
    )
    assert all(state == "COMPLETED" for state in actual.values())

    trace = get_gitlab_job_trace(
        host, cadence_pipeline_state.summary_job_id,
    )
    assert trace["success"], trace["error"]
    assert "Status:           COMPLETED" in trace["trace"]
    tl.passed("Cadence database stages and GitLab summary completed")


@pytest.mark.sanity
@pytest.mark.order(29)
def test_cadence_local_repo_status(host, cadence_pipeline_state):
    """V029: Pipeline Repo Manager output matches the cadence catalog."""
    tl = _logger("cadence_local_repo_status")
    result = check_cadence_local_repo_status(
        host, catalog_ref=cadence_pipeline_state.pipeline_sha,
    )
    assert result["success"], result["error"]
    tl.passed(result["details"])


@pytest.mark.sanity
@pytest.mark.order(30)
def test_cadence_build_status(host, cadence_pipeline_state):
    """V030: Image Build Manager output is complete for this cadence job."""
    tl = _logger("cadence_build_status")
    roles = _job_roles(host, cadence_pipeline_state)
    result = check_build_status(
        host, cadence_pipeline_state.job_id, roles,
    )
    assert result["success"], result["error"]
    tl.passed(result["details"])


@pytest.mark.sanity
@pytest.mark.order(31)
def test_cadence_s3_artifacts(host, cadence_pipeline_state):
    """V031: Every requested role has all three S3 boot artifacts."""
    tl = _logger("cadence_s3_artifacts")
    roles = _job_roles(host, cadence_pipeline_state)
    result = verify_s3_boot_images(
        host, cadence_pipeline_state.job_id, roles,
    )
    assert result["success"], (
        result.get("error")
        or f"Missing S3 roles: {result.get('missing_roles', [])}"
    )
    tl.passed(f"S3 boot artifacts verified for {len(roles)} roles")
