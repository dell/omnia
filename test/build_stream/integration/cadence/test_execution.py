# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

"""Execute installation, build prerequisite, and unified cadence pipeline."""

import json
import re

import pytest

from library.functions import (
    TestLogger,
    check_cadence_runtime,
    check_server_credentials,
    get_cadence_catalog,
    get_gitlab_job_trace,
    get_latest_job,
    list_pipelines,
    poll_gitlab_ci_stages,
    poll_stage_until_complete,
    run_playbook,
    upload_catalog_file,
    trigger_build_pipeline_auto,
    trigger_cadence_cycle,
    update_job_id_in_config,
    wait_for_cadence_catalog_update,
    wait_for_child_pipeline,
    wait_for_pipeline_job,
    wait_for_pipeline_triggered,
)
from library.vars.common_vars import BUILD_PIPELINE_STAGES
from integration.support import deployment_catalog_path, selected_catalog


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(0)
def test_deploy_buildstream_with_selected_cadence_catalog(host):
    """Deploy GitLab with the selected source stored as cadence_catalog_rhel.json."""
    relative, source = selected_catalog()
    logger = TestLogger(
        "Deploy BuildStream with selected cadence catalog",
        "BSM_INT_CADENCE_E001",
    )
    logger.check(f"Selected cadence catalog: {relative}")
    result = run_playbook(
        timeout=3600,
        extra_vars={
            "standalone_mode": True,
            "gitlab_cadence_catalog_json_source": deployment_catalog_path(),
        },
    )
    assert result["success"], result.get("error") or (
        f"BuildStream deployment failed with rc={result['rc']}"
    )
    deployed = get_cadence_catalog(host)
    assert deployed["success"], deployed["error"]
    assert deployed["catalog"] == json.loads(source.read_text(encoding="utf-8")), (
        "GitLab cadence_catalog_rhel.json does not match cadence_catalog_path; "
        "a pre-existing GitLab project must be cleaned before integration install"
    )
    logger.passed(
        "BuildStream deployed with the selected source uploaded as "
        "cadence_catalog_rhel.json"
    )


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(1)
def test_run_full_build_prerequisite(host, integration_state):
    """Run the selected catalog through the full build before repo_sync.yml."""
    logger = TestLogger(
        "Run full build prerequisite for cadence repository sync",
        "BSM_INT_CADENCE_E002",
    )
    credentials = check_server_credentials(host)
    assert credentials["success"], credentials.get("error")

    pipelines = list_pipelines(host, per_page=5)
    assert pipelines["success"], pipelines["error"]
    initial_pipeline_id = (
        int(pipelines["pipelines"][0].get("id", 0))
        if pipelines["pipelines"] else 0
    )
    latest_job = get_latest_job(host)
    assert latest_job.get("success") or latest_job.get("error") == (
        "No jobs found in database"
    ), latest_job.get("error")
    initial_job_id = latest_job.get("job_id", "") if latest_job.get("success") else ""

    relative, source = selected_catalog()
    logger.check(
        f"Uploading the same selected catalog as catalog_rhel.json: {relative}"
    )
    pushed = upload_catalog_file(host, source.read_text(encoding="utf-8"))
    assert pushed["success"], pushed["error"]
    result = trigger_build_pipeline_auto(
        host,
        initial_pipeline_id=initial_pipeline_id,
        initial_job_id=initial_job_id,
    )
    assert result["success"], result["error"]
    integration_state.build_pipeline_id = result["pipeline_id"]
    integration_state.build_job_id = result.get("job_id", "")
    assert integration_state.build_job_id, "Build prerequisite did not create a job"

    ci_result = poll_gitlab_ci_stages(
        host,
        pipeline_id=integration_state.build_pipeline_id,
        log_callback=logger.check,
    )
    assert ci_result["success"], ci_result.get("error")
    for stage_name in BUILD_PIPELINE_STAGES:
        stage = poll_stage_until_complete(
            host, integration_state.build_job_id, stage_name,
        )
        assert stage["success"], stage.get("error")
    logger.passed(
        "Full build completed; repositories required by repo_sync.yml are ready"
    )


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(2)
def test_execute_cadence_pipeline(host, integration_state):
    """Trigger the watcher only after the full build prerequisite succeeds."""
    logger = TestLogger(
        "Execute unified cadence pipeline",
        "BSM_INT_CADENCE_E003",
    )
    runtime = check_cadence_runtime(host)
    assert runtime["success"], runtime["error"]
    previous_catalog = get_cadence_catalog(host)
    assert previous_catalog["success"], previous_catalog["error"]

    pipelines = list_pipelines(host, per_page=5)
    assert pipelines["success"], pipelines["error"]
    initial_pipeline_id = (
        int(pipelines["pipelines"][0].get("id", 0))
        if pipelines["pipelines"] else 0
    )
    trigger = trigger_cadence_cycle(host)
    assert trigger["success"], trigger["error"]
    catalog = wait_for_cadence_catalog_update(
        host,
        previous_commit=previous_catalog["last_commit_id"],
        previous_version=previous_catalog["version"],
        log_callback=logger.check,
    )
    assert catalog["success"], catalog["error"]
    pipeline = wait_for_pipeline_triggered(
        host,
        initial_pipeline_id,
        commit_id=catalog.get("last_commit_id", ""),
        log_callback=logger.check,
    )
    assert pipeline["success"], pipeline["error"]
    integration_state.parent_pipeline_id = pipeline["pipeline_id"]

    child = wait_for_child_pipeline(host, pipeline["pipeline_id"])
    assert child["success"], child["error"]
    integration_state.child_pipeline_id = child["child_pipeline_id"]
    initialization = wait_for_pipeline_job(
        host,
        integration_state.child_pipeline_id,
        "initialization",
        wanted_statuses=["success"],
    )
    assert initialization["success"], initialization["error"]
    trace = get_gitlab_job_trace(host, initialization["job"]["id"])
    assert trace["success"], trace["error"]
    match = re.search(
        r"Job created:\s*"
        r"([0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12})",
        trace["trace"],
    )
    assert match, "Initialization trace did not contain the cadence job_id"
    integration_state.job_id = match.group(1)
    assert update_job_id_in_config(integration_state.job_id), (
        "Unable to persist cadence job_id in integration/test_config.yml"
    )

    summary = wait_for_pipeline_job(
        host,
        integration_state.child_pipeline_id,
        "summary",
        wanted_statuses=["success"],
    )
    assert summary["success"], summary["error"]
    integration_state.summary_job_id = summary["job"]["id"]
    logger.passed(
        f"Unified cadence pipeline completed for job {integration_state.job_id}"
    )
