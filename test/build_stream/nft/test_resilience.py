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
"""Live operational-recovery tests for BuildStream and its GitLab pipeline."""

import pytest

from library.functions import (
    TestLogger,
    cancel_pipeline,
    get_bsm_job_details,
    get_child_pipeline_id,
    load_test_config,
    restart_service,
    stop_service,
    trigger_catalog_job,
    update_job_id_in_config,
    wait_for_pipeline_status,
    wait_for_queue_claimed,
    wait_for_queue_entry,
)
from library.vars import TEST_CASES as TC


def _case(name):
    details = TC[name]
    return TestLogger(details["title"], details["id"])


def _enabled(config, key, logger):
    if not config.get(key, False):
        logger.skipped(f"Set {key}: true to authorize this disruptive NFT")
        pytest.skip(f"{key} is false")


def _job_id(config, nft_state):
    return nft_state.get("active_job_id") or str(config.get("job_id", "") or "")


@pytest.mark.nft
@pytest.mark.resilience
@pytest.mark.disruptive
@pytest.mark.order(1)
def test_gitlab_cancel_then_create_new_job(host, nft_state):
    """Cancel only the test-created GitLab pipeline, then require a new BSM job."""
    # pylint: disable=too-many-locals
    logger = _case("gitlab_cancel_then_create_new_job")
    config = load_test_config()
    _enabled(config, "nft_allow_pipeline_cancel", logger)
    catalog_path = str(config.get("catalog_path", "") or "")
    pipeline_timeout = int(config.get("nft_pipeline_timeout_seconds", 300))
    assert catalog_path, "catalog_path is required for the cancellation NFT"

    first = trigger_catalog_job(host, catalog_path, pipeline_timeout)
    first_pipeline = int(first.get("pipeline_id", 0))
    first_job = str(first.get("job_id", ""))
    if first_pipeline:
        nft_state.update({
            "active_pipeline_id": first_pipeline,
            "active_job_id": first_job,
        })
    assert first.get("success"), first.get("error", "First job was not created")
    assert first_pipeline > 0 and first_job
    logger.check(f"Created pipeline #{first_pipeline} for job {first_job[:8]}...")

    cancelled = cancel_pipeline(host, first_pipeline)
    assert cancelled["success"], cancelled["error"]
    timeout = int(config.get("nft_recovery_timeout_seconds", 120))
    terminal = wait_for_pipeline_status(
        host, first_pipeline, {"canceled", "cancelled"}, timeout,
    )
    assert terminal["success"], terminal["error"]
    child = get_child_pipeline_id(host, first_pipeline)
    if child.get("success") and child.get("child_pipeline_id"):
        child_terminal = wait_for_pipeline_status(
            host, int(child["child_pipeline_id"]),
            {"canceled", "cancelled"}, timeout,
        )
        assert child_terminal["success"], child_terminal["error"]
    nft_state.update({"active_pipeline_id": 0, "active_job_id": ""})

    second = trigger_catalog_job(host, catalog_path, pipeline_timeout)
    second_pipeline = int(second.get("pipeline_id", 0))
    second_job = str(second.get("job_id", ""))
    if second_pipeline:
        nft_state.update({
            "active_pipeline_id": second_pipeline,
            "active_job_id": second_job,
        })
    assert second.get("success"), second.get("error", "Replacement job was not created")
    assert second_pipeline > first_pipeline
    assert second_job and second_job != first_job
    assert update_job_id_in_config(second_job), "Could not persist replacement job_id"

    nft_state.update({
        "cancelled_pipeline_id": first_pipeline,
        "cancelled_job_id": first_job,
        "active_pipeline_id": second_pipeline,
        "active_job_id": second_job,
    })
    logger.passed(
        f"Canceled pipeline #{first_pipeline}; pipeline #{second_pipeline} "
        f"created independent job {second_job[:8]}..."
    )


@pytest.mark.nft
@pytest.mark.resilience
@pytest.mark.disruptive
@pytest.mark.order(3)
def test_bsm_container_restart_recovery(host, nft_state):
    """Restart the BSM service and preserve an existing job across recovery."""
    logger = _case("bsm_container_restart_recovery")
    config = load_test_config()
    _enabled(config, "nft_allow_service_restart", logger)
    job_id = _job_id(config, nft_state)
    assert job_id, "job_id is required before restarting the BSM container"
    before = get_bsm_job_details(host, job_id)
    assert before["success"], before["error"]

    recovered = restart_service(
        host, "omnia_build_stream.service",
        int(config.get("nft_recovery_timeout_seconds", 120)),
        require_health=True,
    )
    assert recovered["success"], recovered["error"]
    after = get_bsm_job_details(host, job_id)
    assert after["success"], after["error"]
    assert after["job"].get("job_id") == before["job"].get("job_id")
    logger.passed("BSM service recovered and the persisted job remained accessible")


@pytest.mark.nft
@pytest.mark.resilience
@pytest.mark.disruptive
@pytest.mark.order(4)
def test_bsm_restart_during_active_stage(host, nft_state):
    """Restart BSM while a test-created job is non-terminal and retain its identity."""
    logger = _case("bsm_restart_during_active_stage")
    config = load_test_config()
    _enabled(config, "nft_allow_active_stage_restart", logger)
    job_id = _job_id(config, nft_state)
    assert job_id, "Run the cancellation/new-job NFT first or configure an active job_id"
    before = get_bsm_job_details(host, job_id)
    assert before["success"], before["error"]
    assert before["job"].get("job_state") in {"PENDING", "RUNNING", "IN_PROGRESS"}, (
        "The selected job is terminal; this test requires an active job"
    )

    recovered = restart_service(
        host, "omnia_build_stream.service",
        int(config.get("nft_recovery_timeout_seconds", 120)),
        require_health=True,
    )
    assert recovered["success"], recovered["error"]
    after = get_bsm_job_details(host, job_id)
    assert after["success"], after["error"]
    assert after["job"].get("job_id") == job_id
    assert len(after["job"].get("stages", [])) == len(before["job"].get("stages", []))
    logger.passed("Active job survived BSM restart without duplicated stage records")


@pytest.mark.nft
@pytest.mark.resilience
@pytest.mark.disruptive
@pytest.mark.order(2)
def test_watcher_restart_during_queued_request(host, nft_state):
    """Recover the watcher with an exact NFT-created pipeline request queued."""
    logger = _case("watcher_restart_during_queued_request")
    config = load_test_config()
    _enabled(config, "nft_allow_watcher_restart", logger)
    job_id = _job_id(config, nft_state)
    assert job_id, "A test-created active job is required for watcher recovery"
    timeout = int(config.get("nft_recovery_timeout_seconds", 120))
    stopped = stop_service(host, "playbook-watcher.service")
    assert stopped["success"], stopped["error"]
    queued = {"success": False, "entry": "", "error": "Queue wait not executed"}
    try:
        queued = wait_for_queue_entry(host, job_id, timeout)
    finally:
        # Always restore the watcher, including when the expected request never
        # appears or the assertion below fails.
        recovered = restart_service(host, "playbook-watcher.service", timeout)

    assert queued["success"], queued["error"]
    assert recovered["success"], recovered["error"]
    claimed = wait_for_queue_claimed(host, queued["entry"], timeout)
    assert claimed["success"], claimed["error"]
    job = get_bsm_job_details(host, job_id)
    assert job["success"], job["error"]
    assert job["job"].get("job_id") == job_id
    logger.passed(
        f"Watcher recovered and claimed {queued['entry']} for the exact NFT job"
    )
