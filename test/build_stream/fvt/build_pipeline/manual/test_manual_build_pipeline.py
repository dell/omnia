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

"""Manual BuildStream build-pipeline coverage.

These tests intentionally use the ``manual`` marker.  They are opt-in because
they create a new build job and validate the resulting artifacts in the live
registry and S3 store.
"""
# pylint: disable=duplicate-code,too-many-arguments,too-many-positional-arguments

import os

import pytest

from library.functions import (
    TestLogger,
    get_image_groups_for_job,
    get_images_for_job,
    get_latest_job,
    get_pipeline_summary,
    get_stage_state,
    poll_stage_until_complete,
    push_catalog_from_examples,
    trigger_pipeline_with_variables,
    update_job_id_in_config,
    verify_registry_images,
    verify_s3_boot_images,
    verify_stage_completed,
    wait_for_new_job,
)
from library.vars import TEST_CASES as TC


pytestmark = pytest.mark.usefixtures("manual_pipeline_prerequisites")


def _logger(name):
    case = TC[name]
    return TestLogger(case["title"], case["id"])


def _require_job(state, tl):
    if not state.job_id:
        tl.skipped("No job_id is available; run the manual trigger first")
        pytest.skip("No manual build job is available")


def _require_architecture(state, tl, architecture, optional=False):
    """Require an architecture, or skip when the catalog makes it optional."""
    if architecture in state.architectures:
        return
    message = f"Architecture '{architecture}' is not present in the catalog"
    if optional:
        tl.skipped(message)
        pytest.skip(message)
    pytest.fail(message)


def _monitor(
    host, state, stage_name, tc_name, allow_absent=False,
    architecture="", optional_architecture=False,
):
    tl = _logger(tc_name)
    _require_job(state, tl)
    if architecture:
        _require_architecture(
            state, tl, architecture, optional=optional_architecture,
        )
    if allow_absent:
        current = get_stage_state(host, state.job_id, stage_name)
        if not current["success"] and "not found" in current["error"].lower():
            tl.skipped(f"Stage '{stage_name}' is not present in this catalog")
            pytest.skip(f"Optional stage '{stage_name}' is not present")
    result = poll_stage_until_complete(
        host, state.job_id, stage_name, log_callback=tl.check,
    )
    assert result["success"], result["error"]
    tl.passed(f"Stage '{stage_name}' completed")


def _verify_stage(
    host, state, stage_name, tc_name, allow_absent=False,
    architecture="", optional_architecture=False,
):
    tl = _logger(tc_name)
    _require_job(state, tl)
    if architecture:
        _require_architecture(
            state, tl, architecture, optional=optional_architecture,
        )
    result = verify_stage_completed(host, state.job_id, stage_name)
    if allow_absent and not result["success"] and "not found" in result["error"].lower():
        tl.skipped(f"Stage '{stage_name}' is not present in this catalog")
        pytest.skip(f"Optional stage '{stage_name}' is not present")
    assert result["success"], result["error"]
    tl.passed(f"Stage '{stage_name}' is COMPLETED in the database")


@pytest.mark.manual
@pytest.mark.deploy
@pytest.mark.order(0)
def test_manual_trigger_build_pipeline(
    host, pipeline_state, manual_pipeline_prerequisites,
):
    """Trigger a build pipeline with PIPELINE_TYPE=build."""
    tl = _logger("manual_trigger_build_pipeline")
    tl.check(
        "Installation prerequisites passed: "
        + ", ".join(manual_pipeline_prerequisites)
    )
    catalog_path = pipeline_state.catalog_path
    tl.check(f"Catalog: {catalog_path}")

    if os.environ.get("OMNIA_COMMAND_TYPE", "") == "verify":
        _require_job(pipeline_state, tl)
        result = get_pipeline_summary(
            host, pipeline_state.job_id, build_only=True,
        )
        assert result["success"], result["error"]
        assert result["stages"], "No stages were recorded for the build job"
        incomplete = [
            stage for stage in result["stages"]
            if stage["stage_state"] != "COMPLETED"
        ]
        assert not incomplete, f"Build pipeline has incomplete stages: {incomplete}"
        tl.passed(
            f"Existing manual build job {pipeline_state.job_id} verified; "
            "no new pipeline was triggered"
        )
        return

    staged = push_catalog_from_examples(
        host, catalog_path, log_callback=tl.check, skip_ci=True,
    )
    assert staged["success"], staged["error"]
    tl.check("Catalog staged in GitLab without an automatic CI pipeline")
    previous = get_latest_job(host)
    old_job_id = previous.get("job_id", "") if previous["success"] else ""
    result = trigger_pipeline_with_variables(host, {"PIPELINE_TYPE": "build"})
    assert result["success"], result["error"]
    tl.check(f"Triggered build pipeline {result['pipeline_id']}")

    job = wait_for_new_job(host, old_job_id, log_callback=tl.check)
    assert job["success"], job["error"]
    pipeline_state.pipeline_id = result["pipeline_id"]
    pipeline_state.job_id = job["job_id"]
    assert update_job_id_in_config(job["job_id"]), (
        "Unable to persist the manual build job_id to test_config.yml"
    )
    tl.passed(f"Build job {job['job_id']} was created")


@pytest.mark.manual
@pytest.mark.order(1)
def test_manual_build_stage_upload_monitor(host, pipeline_state):
    """Monitor the upload stage until it completes."""
    _monitor(host, pipeline_state, "upload", "manual_build_stage_upload_monitor")


@pytest.mark.manual
@pytest.mark.order(2)
def test_manual_build_stage_upload_db_verify(host, pipeline_state):
    """Verify the upload stage completed in the database."""
    _verify_stage(host, pipeline_state, "upload", "manual_build_stage_upload_db_verify")


@pytest.mark.manual
@pytest.mark.order(3)
def test_manual_build_stage_parse_catalog_monitor(host, pipeline_state):
    """Monitor the parse-catalog stage until it completes."""
    _monitor(
        host, pipeline_state, "parse-catalog",
        "manual_build_stage_parse_catalog_monitor",
    )


@pytest.mark.manual
@pytest.mark.order(4)
def test_manual_build_stage_parse_catalog_db_verify(host, pipeline_state):
    """Verify the parse-catalog stage completed in the database."""
    _verify_stage(
        host, pipeline_state, "parse-catalog",
        "manual_build_stage_parse_catalog_db_verify",
    )


@pytest.mark.manual
@pytest.mark.order(7)
def test_manual_build_stage_create_local_repository_monitor(host, pipeline_state):
    """Monitor create-local-repository until it completes."""
    _monitor(
        host, pipeline_state, "create-local-repository",
        "manual_build_stage_create_local_repository_monitor",
    )


@pytest.mark.manual
@pytest.mark.order(8)
def test_manual_build_stage_create_local_repository_db_verify(host, pipeline_state):
    """Verify create-local-repository completed in the database."""
    _verify_stage(
        host, pipeline_state, "create-local-repository",
        "manual_build_stage_create_local_repository_db_verify",
    )


@pytest.mark.manual
@pytest.mark.order(9)
def test_manual_build_stage_build_image_x86_64_monitor(host, pipeline_state):
    """Monitor the x86_64 image-build stage until it completes."""
    _monitor(
        host, pipeline_state, "build-image",
        "manual_build_stage_build_image_x86_64_monitor",
        architecture="x86_64",
    )


@pytest.mark.manual
@pytest.mark.order(10)
def test_manual_build_stage_build_image_x86_64_db_verify(host, pipeline_state):
    """Verify the x86_64 image-build database state."""
    _verify_stage(
        host, pipeline_state, "build-image",
        "manual_build_stage_build_image_x86_64_db_verify",
        architecture="x86_64",
    )


@pytest.mark.manual
@pytest.mark.order(11)
def test_manual_build_stage_build_image_aarch64_monitor(host, pipeline_state):
    """Monitor the optional aarch64 image-build stage."""
    _monitor(
        host, pipeline_state, "build-image",
        "manual_build_stage_build_image_aarch64_monitor",
        architecture="aarch64", optional_architecture=True,
    )


@pytest.mark.manual
@pytest.mark.order(12)
def test_manual_build_stage_build_image_aarch64_db_verify(host, pipeline_state):
    """Verify the optional aarch64 image-build database state."""
    _verify_stage(
        host, pipeline_state, "build-image",
        "manual_build_stage_build_image_aarch64_db_verify",
        architecture="aarch64", optional_architecture=True,
    )


@pytest.mark.manual
@pytest.mark.order(13)
def test_manual_build_image_groups_created(host, pipeline_state):
    """Verify the manual build created image-group records."""
    tl = _logger("manual_build_image_groups_created")
    _require_job(pipeline_state, tl)
    result = get_image_groups_for_job(host, pipeline_state.job_id)
    assert result["success"], result["error"]
    assert result["image_groups"], "No image groups were created for the job"
    tl.passed(f"Created {len(result['image_groups'])} image group(s)")


@pytest.mark.manual
@pytest.mark.order(14)
def test_manual_build_images_created(host, pipeline_state):
    """Verify the manual build created image records."""
    tl = _logger("manual_build_images_created")
    _require_job(pipeline_state, tl)
    result = get_images_for_job(host, pipeline_state.job_id)
    assert result["success"], result["error"]
    assert result["images"], "No images were created for the job"
    tl.passed(f"Created {len(result['images'])} image(s)")


@pytest.mark.manual
@pytest.mark.order(15)
def test_manual_build_registry_images(host, pipeline_state):
    """Verify each built role has a registry image."""
    tl = _logger("manual_build_registry_images")
    _require_job(pipeline_state, tl)
    images = get_images_for_job(host, pipeline_state.job_id)
    assert images["success"], images["error"]
    roles = sorted({image["role"] for image in images["images"]})
    assert roles, "No image roles were recorded for the job"
    result = verify_registry_images(host, pipeline_state.job_id, roles)
    assert result["success"], result["error"] or result["details"]
    tl.passed(result["details"])


@pytest.mark.manual
@pytest.mark.order(16)
def test_manual_build_s3_boot_images(host, pipeline_state):
    """Verify each built role has boot artifacts in S3."""
    tl = _logger("manual_build_s3_boot_images")
    _require_job(pipeline_state, tl)
    images = get_images_for_job(host, pipeline_state.job_id)
    assert images["success"], images["error"]
    roles = sorted({image["role"] for image in images["images"]})
    assert roles, "No image roles were recorded for the job"
    result = verify_s3_boot_images(host, pipeline_state.job_id, roles)
    assert result["success"], result["error"] or result["details"]
    tl.passed(result["details"])


@pytest.mark.manual
@pytest.mark.order(17)
def test_manual_build_pipeline_result(host, pipeline_state):
    """Verify every build-only stage reached COMPLETED."""
    tl = _logger("manual_build_pipeline_result")
    _require_job(pipeline_state, tl)
    result = get_pipeline_summary(host, pipeline_state.job_id, build_only=True)
    assert result["success"], result["error"]
    assert result["stages"], "No stages were recorded for the build job"
    failed = [
        stage for stage in result["stages"]
        if stage["stage_state"] != "COMPLETED"
    ]
    assert not failed, f"Build pipeline has incomplete stages: {failed}"
    tl.passed("All recorded build pipeline stages are COMPLETED")
