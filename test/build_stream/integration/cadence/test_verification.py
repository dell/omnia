# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

"""Read-only integration verification for installation and cadence."""

import pytest

from library.functions import (
    TestLogger,
    check_build_stream_enabled,
    check_build_stream_health,
    check_cadence_input_snapshot,
    check_cadence_local_repo_status,
    check_gitlab_runner_container,
    check_gitlab_url_accessible,
    check_postgres_tables,
    check_repo_resync_status,
    get_bsm_job_details,
    get_gitlab_pipeline_jobs,
    get_images_for_job,
    get_pipeline_summary,
    resolve_deploy_image_group,
    verify_registry_images,
    verify_s3_boot_images,
    verify_stage_completed,
)
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


def _logger(identifier, title):
    return TestLogger(title, identifier)


def _roles(host, state):
    images = get_images_for_job(host, state.job_id)
    assert images["success"], images["error"]
    roles = sorted({item["role"] for item in images["images"] if item.get("role")})
    assert roles, f"No roles recorded for cadence job {state.job_id}"
    return roles


@pytest.mark.sanity
@pytest.mark.order(10)
def test_buildstream_installation_operational(host):
    """Verify the services required by the integration flow are operational."""
    logger = _logger("BSM_INT_CADENCE_V001", "Verify BuildStream installation")
    checks = (
        ("BuildStream enabled", check_build_stream_enabled(host)),
        ("BuildStream healthy", check_build_stream_health(host)),
        ("PostgreSQL schema", check_postgres_tables(host)),
        ("GitLab accessible", check_gitlab_url_accessible(host)),
        ("GitLab runner", check_gitlab_runner_container(host)),
    )
    failures = [
        f"{name}: {result.get('error') or result.get('details')}"
        for name, result in checks if not result.get("success")
    ]
    assert not failures, "\n".join(failures)
    logger.passed("BuildStream, PostgreSQL, GitLab, and runner are operational")


@pytest.mark.sanity
@pytest.mark.order(11)
def test_cadence_gitlab_jobs(host, integration_state):
    """Verify every job in the unified cadence child pipeline succeeded."""
    logger = _logger("BSM_INT_CADENCE_V002", "Verify cadence GitLab jobs")
    result = get_gitlab_pipeline_jobs(host, integration_state.child_pipeline_id)
    assert result["success"], result["error"]
    jobs = {job["name"]: job for job in result["jobs"]}
    missing = [name for name in GITLAB_CI_CADENCE_JOBS if name not in jobs]
    failed = [
        name for name in GITLAB_CI_CADENCE_JOBS
        if name in jobs and jobs[name]["status"] != "success"
    ]
    assert not missing, f"Missing cadence jobs: {missing}"
    assert not failed, f"Unsuccessful cadence jobs: {failed}"
    logger.passed("All cadence GitLab jobs succeeded")


@pytest.mark.sanity
@pytest.mark.order(12)
def test_cadence_repository_sync(host, integration_state):
    """Verify repo_sync.yml and pipeline repository output contracts."""
    logger = _logger("BSM_INT_CADENCE_V003", "Verify cadence repository sync")
    resync = check_repo_resync_status(
        host, catalog_ref=integration_state.pipeline_sha,
    )
    assert resync["success"], resync["error"]
    local = check_cadence_local_repo_status(
        host, catalog_ref=integration_state.pipeline_sha,
    )
    assert local["success"], local["error"]
    logger.passed("Repository synchronization and local repository output passed")


@pytest.mark.sanity
@pytest.mark.order(13)
def test_cadence_database_stages(host, integration_state):
    """Verify all unified cadence database stages completed."""
    logger = _logger("BSM_INT_CADENCE_V004", "Verify cadence database stages")
    stages = (
        STAGE_PARSE_CATALOG,
        STAGE_CREATE_LOCAL_REPO,
        STAGE_BUILD_IMAGE,
        STAGE_DEPLOY,
        STAGE_RESTART,
        STAGE_VALIDATE,
    )
    failures = []
    for stage_name in stages:
        result = verify_stage_completed(host, integration_state.job_id, stage_name)
        if not result["success"]:
            failures.append(result["error"])
    assert not failures, "\n".join(failures)
    logger.passed("All unified cadence database stages completed")


@pytest.mark.sanity
@pytest.mark.order(14)
def test_cadence_artifacts(host, integration_state):
    """Verify registry, S3, and uploaded-input artifacts for the cadence job."""
    logger = _logger("BSM_INT_CADENCE_V005", "Verify cadence artifacts")
    roles = _roles(host, integration_state)
    registry = verify_registry_images(host, integration_state.job_id, roles)
    assert registry["success"], registry.get("error") or registry.get("details")
    s3_result = verify_s3_boot_images(host, integration_state.job_id, roles)
    assert s3_result["success"], s3_result.get("error") or s3_result.get("details")
    snapshot = check_cadence_input_snapshot(
        host,
        integration_state.job_id,
        integration_state.pipeline_sha,
    )
    assert snapshot["success"], snapshot["error"]
    logger.passed("Cadence registry, S3, and input snapshot artifacts passed")


@pytest.mark.sanity
@pytest.mark.order(15)
def test_cadence_final_state(host, integration_state):
    """Verify the cadence Job and ImageGroup reached final success states."""
    logger = _logger("BSM_INT_CADENCE_V006", "Verify cadence final state")
    job = get_bsm_job_details(host, integration_state.job_id)
    assert job["success"], job["error"]
    assert job["job"].get("job_state") in {JOB_STATE_COMPLETED, JOB_STATE_SUCCEEDED}
    image_group = resolve_deploy_image_group(host, integration_state.job_id)
    assert image_group["success"], image_group["error"]
    assert image_group["status"] == IMAGE_GROUP_STATUS_PASSED
    summary = get_pipeline_summary(host, integration_state.job_id, build_only=False)
    assert summary["success"], summary["error"]
    logger.passed("Cadence Job completed and ImageGroup passed")
