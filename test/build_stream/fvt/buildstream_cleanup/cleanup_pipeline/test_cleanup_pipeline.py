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

"""Explicit sanity coverage for the GitLab image-cleanup pipeline."""

import os

import pytest

from library.functions import (
    TestLogger,
    check_gitlab_runner_container,
    check_gitlab_url_accessible,
    get_image_groups_for_job,
    play_gitlab_job,
    trigger_pipeline_with_variables,
    verify_registry_images_absent,
    verify_s3_boot_images_absent,
    wait_for_child_pipeline,
    wait_for_pipeline_job,
)
from library.vars import TEST_CASES as TC


def _logger(name):
    case = TC[f"cleanup_{name}"]
    return TestLogger(case["title"], case["id"])


@pytest.mark.sanity
@pytest.mark.order(1)
def test_gitlab_server_running(host):
    """Verify GitLab is available before the cleanup pipeline starts."""
    tl = _logger("gitlab_server_running")
    result = check_gitlab_url_accessible(host)
    assert result["success"], result.get("error", "GitLab is not accessible")
    tl.passed(f"GitLab is accessible at {result['url']}")


@pytest.mark.sanity
@pytest.mark.order(2)
def test_gitlab_runner_running(host):
    """Verify the GitLab runner container is running."""
    tl = _logger("gitlab_runner_running")
    result = check_gitlab_runner_container(host)
    assert result["success"], result.get("error", "GitLab runner is not running")
    tl.passed(result["details"])


@pytest.mark.sanity
@pytest.mark.order(3)
def test_image_groups_for_cleanup(host, cleanup_pipeline_state):
    """Verify the selected image group is available for cleanup."""
    tl = _logger("image_groups_for_cleanup")
    groups = get_image_groups_for_job(host, cleanup_pipeline_state.job_id)
    assert groups["success"], groups["error"]
    group = next(
        (
            item for item in groups["image_groups"]
            if item["id"] == cleanup_pipeline_state.image_group_id
        ),
        None,
    )
    assert group, "No image group is available for the configured job"
    if cleanup_pipeline_state.already_cleaned:
        tl.passed(
            f"Image group {group['id']} is already CLEANED; "
            "continuing with idempotent cleanup verification"
        )
    else:
        tl.passed(f"Image group {group['id']} is cleanable")


@pytest.mark.sanity
@pytest.mark.deploy
@pytest.mark.order(4)
def test_trigger_cleanup_pipeline(host, cleanup_pipeline_state):
    """Trigger cleanup in exec mode or verify its prior completion."""
    tl = _logger("trigger_cleanup_pipeline")
    if os.environ.get("OMNIA_COMMAND_TYPE", "") == "verify":
        groups = get_image_groups_for_job(
            host, cleanup_pipeline_state.job_id,
        )
        assert groups["success"], groups["error"]
        group = next(
            (
                item for item in groups["image_groups"]
                if item["id"] == cleanup_pipeline_state.image_group_id
            ),
            None,
        )
        assert group, "The cleanup target image group was not found"
        assert group["status"] == "CLEANED", group
        tl.passed(
            "Previously triggered cleanup pipeline completed; "
            f"image group {group['id']} is CLEANED"
        )
        return

    if cleanup_pipeline_state.already_cleaned:
        tl.passed(
            "Cleanup was already completed by the prior test-created "
            "pipeline; no duplicate cleanup was triggered"
        )
        return
    parent = trigger_pipeline_with_variables(host, {"PIPELINE_TYPE": "cleanup"})
    assert parent["success"], parent["error"]
    cleanup_pipeline_state.parent_pipeline_id = parent["pipeline_id"]
    tl.check(f"Triggered cleanup pipeline {parent['pipeline_id']}")

    controller = wait_for_child_pipeline(host, parent["pipeline_id"])
    assert controller["success"], controller["error"]
    child = wait_for_child_pipeline(host, controller["child_pipeline_id"])
    assert child["success"], child["error"]
    cleanup_pipeline_state.child_pipeline_id = child["child_pipeline_id"]

    selection = wait_for_pipeline_job(
        host,
        cleanup_pipeline_state.child_pipeline_id,
        cleanup_pipeline_state.image_group_id,
        ["manual"],
    )
    assert selection["success"], selection["error"]
    played = play_gitlab_job(host, selection["job"]["id"])
    assert played["success"], played["error"]
    selected = wait_for_pipeline_job(
        host,
        cleanup_pipeline_state.child_pipeline_id,
        cleanup_pipeline_state.image_group_id,
        ["success"],
    )
    assert selected["success"], selected["error"]

    cleanup = wait_for_pipeline_job(
        host,
        cleanup_pipeline_state.child_pipeline_id,
        "cleanup",
        ["manual"],
    )
    assert cleanup["success"], cleanup["error"]
    played = play_gitlab_job(host, cleanup["job"]["id"])
    assert played["success"], played["error"]

    for job_name in ("cleanup", "summary"):
        completed = wait_for_pipeline_job(
            host,
            cleanup_pipeline_state.child_pipeline_id,
            job_name,
            ["success"],
        )
        assert completed["success"], completed["error"]
        if job_name == "summary":
            cleanup_pipeline_state.summary_job_id = completed["job"]["id"]
    tl.passed("Cleanup child pipeline completed successfully")


@pytest.mark.sanity
@pytest.mark.order(5)
def test_image_groups_cleaned(host, cleanup_pipeline_state):
    """Verify the selected image group has CLEANED database status."""
    tl = _logger("image_groups_cleaned")
    groups = get_image_groups_for_job(host, cleanup_pipeline_state.job_id)
    assert groups["success"], groups["error"]
    group = next(
        (
            item for item in groups["image_groups"]
            if item["id"] == cleanup_pipeline_state.image_group_id
        ),
        None,
    )
    assert group, "The cleaned image group was not found in the database"
    assert group["status"] == "CLEANED", group
    tl.passed(f"Image group {group['id']} is CLEANED")


@pytest.mark.sanity
@pytest.mark.order(6)
def test_s3_images_deleted(host, cleanup_pipeline_state):
    """Verify S3 boot images are absent for every recorded role."""
    tl = _logger("s3_images_deleted")
    result = verify_s3_boot_images_absent(
        host, cleanup_pipeline_state.job_id, cleanup_pipeline_state.roles,
    )
    assert result["success"], result["error"] or result["details"]
    tl.passed(result["details"])


@pytest.mark.sanity
@pytest.mark.order(7)
def test_registry_images_deleted(host, cleanup_pipeline_state):
    """Verify registry images are absent for every recorded role."""
    tl = _logger("registry_images_deleted")
    result = verify_registry_images_absent(
        host, cleanup_pipeline_state.job_id, cleanup_pipeline_state.roles,
    )
    assert result["success"], result["error"] or result["details"]
    tl.passed(result["details"])
