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

"""Trigger the unified cadence pipeline through the cadence watcher."""

import re

import pytest

from library.functions import (
    TestLogger,
    check_cadence_runtime,
    check_server_credentials,
    get_cadence_catalog,
    get_gitlab_job_trace,
    list_pipelines,
    trigger_cadence_cycle,
    update_job_id_in_config,
    wait_for_cadence_catalog_update,
    wait_for_child_pipeline,
    wait_for_pipeline_job,
    wait_for_pipeline_triggered,
)
from library.vars import TEST_CASES as TC


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(0)
def test_execute_cadence_pipeline(host, cadence_pipeline_state):
    """Trigger one real cadence cycle and wait for its unified pipeline."""
    case = TC["execute_cadence_pipeline"]
    tl = TestLogger(case["title"], case["id"])

    credentials = check_server_credentials(host)
    assert credentials["success"], (
        credentials.get("error") or "BuildStream credentials are incomplete"
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
    tl.check("Cadence watcher accepted the one-shot trigger")

    catalog = wait_for_cadence_catalog_update(
        host,
        previous_commit=previous_catalog["last_commit_id"],
        previous_version=previous_catalog["version"],
        log_callback=tl.check,
    )
    assert catalog["success"], catalog["error"]
    tl.check(
        f"Cadence catalog updated by the watcher: "
        f"{previous_catalog['version']} -> {catalog['version']}"
    )

    pipeline = wait_for_pipeline_triggered(
        host,
        initial_pipeline_id,
        commit_id=catalog.get("last_commit_id", ""),
        log_callback=tl.check,
    )
    assert pipeline["success"], pipeline["error"]
    cadence_pipeline_state.parent_pipeline_id = pipeline["pipeline_id"]

    child = wait_for_child_pipeline(host, pipeline["pipeline_id"])
    assert child["success"], child["error"]
    cadence_pipeline_state.child_pipeline_id = child["child_pipeline_id"]

    initialization = wait_for_pipeline_job(
        host,
        child["child_pipeline_id"],
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
    cadence_pipeline_state.job_id = match.group(1)
    assert update_job_id_in_config(cadence_pipeline_state.job_id), (
        "Unable to persist cadence job_id in test_config.yml"
    )

    summary = wait_for_pipeline_job(
        host,
        child["child_pipeline_id"],
        "summary",
        wanted_statuses=["success"],
    )
    assert summary["success"], summary["error"]
    cadence_pipeline_state.summary_job_id = summary["job"]["id"]
    tl.passed(
        "Unified cadence pipeline completed and job_id was persisted"
    )
