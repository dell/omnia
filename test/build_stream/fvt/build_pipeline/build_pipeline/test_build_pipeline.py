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

"""
Build Pipeline -- Post-Execution Verification Tests (--verify mode).

Validates that a completed build pipeline created expected artifacts
and updated the database correctly.  These tests only check state --
no triggering, catalog push, or monitoring.

BSM stage names match the StageType enum in
``src/build_stream/app/core/jobs/value_objects.py``:

  create-local-repository   Build pipeline stage
  build-image               Build pipeline stage
  upload                    Build pipeline stage
  validate                  Deploy pipeline stage (excluded)
  restart                   Deploy pipeline stage (excluded)
  deploy                    Deploy pipeline stage (excluded)

Checks performed:
  Server credentials pre-check
  BSM health, OAuth auth, job creation, BSM API access
  create-local-repository stage completed in DB
  build-image stage completed in DB
  repo_status.yml overall_status success
  Container images in registry
  Boot images in S3
  Build pipeline final result (build stages only COMPLETED)

These tests run in both ``verify`` and ``test`` modes.
"""

import pytest

from library.functions import (
    TestLogger,
    verify_initialization_health,
    verify_initialization_auth,
    verify_initialization_job,
    verify_initialization_upload,
    verify_stage_completed,
    get_pipeline_summary,
    check_repo_status,
    check_server_credentials,
    check_registry_images_exist,
    check_s3_boot_images_exist,
)
from library.vars import TEST_CASES as TC
from library.vars.common_vars import (
    STAGE_BUILD_IMAGE,
    STAGE_CREATE_LOCAL_REPO,
    STAGE_STATE_COMPLETED,
)
from library.messages import (
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


# Session flag: set to False if credentials check fails
_creds_ok = True


def _skip_if_no_job(pipeline_state, tl):
    """Skip test if no job_id is available in pipeline state."""
    if not pipeline_state.job_id:
        tl.skipped("No job_id -- trigger may have failed or no prior run")
        pytest.skip("No job_id available")


def _skip_if_no_creds(tl):
    """Skip test if credentials check failed."""
    if not _creds_ok:
        tl.skipped("Credentials not configured -- skipping")
        pytest.skip("build_stream_credentials.yml not configured")


# =============================================================================
# CREDENTIALS PRE-CHECK (TC_BP_PRE)
# =============================================================================

@pytest.mark.sanity
@pytest.mark.order(0)
def test_build_credentials_configured(host, pipeline_state):
    """TC_BP_PRE: Verify build_stream_credentials.yml has required fields."""
    global _creds_ok
    tc = TC["build_credentials_configured"]
    tl = TestLogger(tc["title"], tc["id"])

    result = check_server_credentials(host)
    if result["success"]:
        tl.passed(
            f"Credentials configured: {', '.join(result['found'])}"
        )
    else:
        _creds_ok = False
        tl.failed(
            f"Credentials missing: {', '.join(result.get('missing', []))}"
        )

    assert result["success"], (
        ASSERT["credentials_not_configured"].format(
            path=result["path"],
            missing=", ".join(result.get("missing", [])),
        )
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


# =============================================================================
# PRE-BUILD CHECKS (TC_BP_002 -- TC_BP_005)
# =============================================================================

@pytest.mark.sanity
@pytest.mark.order(1)
def test_build_bsm_health_check(host, pipeline_state):
    """TC_BP_002: Verify BSM API /health returns 200."""
    tc = TC["build_bsm_health_check"]
    tl = TestLogger(tc["title"], tc["id"])
    _skip_if_no_creds(tl)
    _skip_if_no_job(pipeline_state, tl)

    result = verify_initialization_health(host, pipeline_state.job_id)
    if result["success"]:
        tl.passed(LOG["init_health_ok"])
    else:
        tl.failed(LOG["init_health_fail"])

    assert result["success"], (
        ASSERT.get("bsm_health_fail", "BSM health check failed").format(
            url=result.get("details", ""),
        )
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(2)
def test_build_oauth_auth(host, pipeline_state):
    """TC_BP_003: Verify BSM_CLIENT_ID / BSM_CLIENT_SECRET in GitLab CI vars."""
    tc = TC["build_oauth_auth"]
    tl = TestLogger(tc["title"], tc["id"])
    _skip_if_no_creds(tl)
    _skip_if_no_job(pipeline_state, tl)

    result = verify_initialization_auth(host)
    if result["success"]:
        tl.passed(LOG["init_auth_ok"])
    else:
        tl.failed(LOG["init_auth_fail"].format(error=result["error"]))

    assert result["success"], (
        f"OAuth auth verification failed: {result['error']}"
    )


@pytest.mark.sanity
@pytest.mark.order(3)
def test_build_job_created(host, pipeline_state):
    """TC_BP_004: Verify BSM job row exists in jobs table."""
    tc = TC["build_job_created"]
    tl = TestLogger(tc["title"], tc["id"])
    _skip_if_no_creds(tl)
    _skip_if_no_job(pipeline_state, tl)

    result = verify_initialization_job(host, pipeline_state.job_id)
    if result["success"]:
        tl.passed(LOG["init_job_ok"].format(job_id=result["job_id"][:8]))
    else:
        tl.failed(LOG["init_job_fail"])

    assert result["success"], (
        ASSERT["job_not_created"]
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(4)
def test_build_job_accessible_via_api(host, pipeline_state):
    """TC_BP_005: Verify job retrievable via GET /api/v1/jobs/{job_id}."""
    tc = TC["build_job_accessible_via_api"]
    tl = TestLogger(tc["title"], tc["id"])
    _skip_if_no_creds(tl)
    _skip_if_no_job(pipeline_state, tl)

    result = verify_initialization_upload(host, pipeline_state.job_id)
    if result["success"]:
        tl.passed(LOG["init_upload_ok"])
    else:
        tl.failed(LOG["init_upload_fail"])

    assert result["success"], (
        f"Job not accessible via BSM API: {result['error']}"
    )


# =============================================================================
# DB STAGE VERIFICATION (TC_BP_006 -- TC_BP_007)
# =============================================================================

@pytest.mark.sanity
@pytest.mark.order(5)
def test_build_stage_create_local_repository(host, pipeline_state):
    """TC_BP_006: Verify create-local-repository stage COMPLETED in job_stages."""
    tc = TC["build_stage_create_local_repository"]
    tl = TestLogger(tc["title"], tc["id"])
    _skip_if_no_creds(tl)
    _skip_if_no_job(pipeline_state, tl)

    result = verify_stage_completed(
        host, pipeline_state.job_id, STAGE_CREATE_LOCAL_REPO,
    )
    if result["success"]:
        tl.passed(LOG["stage_db_ok"].format(
            stage=STAGE_CREATE_LOCAL_REPO, state=STAGE_STATE_COMPLETED,
        ))
    elif "not found" in result.get("error", "").lower():
        tl.skipped(LOG["stage_skipped"].format(stage=STAGE_CREATE_LOCAL_REPO))
        pytest.skip(f"{STAGE_CREATE_LOCAL_REPO} not found for this job")
    else:
        tl.failed(LOG["stage_db_fail"].format(
            stage=STAGE_CREATE_LOCAL_REPO,
            state=result.get("stage_state", "unknown"),
        ))

    assert result["success"], (
        ASSERT["stage_not_completed"].format(
            stage=STAGE_CREATE_LOCAL_REPO,
            state=result.get("stage_state", "unknown"),
        )
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(6)
def test_build_stage_build_image(host, pipeline_state):
    """TC_BP_007: Verify build-image stage COMPLETED in job_stages."""
    tc = TC["build_stage_build_image"]
    tl = TestLogger(tc["title"], tc["id"])
    _skip_if_no_creds(tl)
    _skip_if_no_job(pipeline_state, tl)

    result = verify_stage_completed(
        host, pipeline_state.job_id, STAGE_BUILD_IMAGE,
    )
    if result["success"]:
        tl.passed(LOG["stage_db_ok"].format(
            stage=STAGE_BUILD_IMAGE, state=STAGE_STATE_COMPLETED,
        ))
    elif "not found" in result.get("error", "").lower():
        tl.skipped(LOG["stage_skipped"].format(stage=STAGE_BUILD_IMAGE))
        pytest.skip(f"{STAGE_BUILD_IMAGE} not found for this job")
    else:
        tl.failed(LOG["stage_db_fail"].format(
            stage=STAGE_BUILD_IMAGE,
            state=result.get("stage_state", "unknown"),
        ))

    assert result["success"], (
        ASSERT["stage_not_completed"].format(
            stage=STAGE_BUILD_IMAGE,
            state=result.get("stage_state", "unknown"),
        )
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


# =============================================================================
# REPO MANAGER VERIFICATION (TC_BP_008)
# =============================================================================

@pytest.mark.sanity
@pytest.mark.order(7)
def test_build_repo_status(host, pipeline_state):
    """TC_BP_008: Verify repo_status.yml overall_status is success."""
    tc = TC["build_repo_status"]
    tl = TestLogger(tc["title"], tc["id"])
    _skip_if_no_creds(tl)
    _skip_if_no_job(pipeline_state, tl)

    result = check_repo_status(host)
    if result["success"]:
        tl.passed(LOG["repo_status_ok"])
    else:
        tl.failed(LOG["repo_status_fail"].format(
            status=result.get("overall_status", "unknown"),
        ))

    assert result["success"], (
        ASSERT["repo_status_failed"].format(
            path=result["path"],
            status=result.get("overall_status", "unknown"),
        )
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


# =============================================================================
# ARTIFACT VERIFICATION (TC_BP_010 -- TC_BP_011)
# =============================================================================

@pytest.mark.sanity
@pytest.mark.order(8)
def test_build_registry_images(host, pipeline_state):
    """TC_BP_010: Verify container images exist in local registry."""
    tc = TC["build_registry_images"]
    tl = TestLogger(tc["title"], tc["id"])
    _skip_if_no_creds(tl)
    _skip_if_no_job(pipeline_state, tl)

    result = check_registry_images_exist(host)
    if result["success"]:
        tl.passed(LOG["registry_ok"].format(
            count=len(result["found_images"]),
        ))
    else:
        tl.failed(LOG["registry_fail"].format(
            count=0, missing="none found",
        ))

    assert result["success"], (
        ASSERT["registry_images_missing"].format(
            missing=result.get("error", "No images in registry"),
        )
    )


@pytest.mark.sanity
@pytest.mark.order(9)
def test_build_s3_boot_images(host, pipeline_state):
    """TC_BP_011: Verify boot images exist in S3 bucket."""
    tc = TC["build_s3_boot_images"]
    tl = TestLogger(tc["title"], tc["id"])
    _skip_if_no_creds(tl)
    _skip_if_no_job(pipeline_state, tl)

    result = check_s3_boot_images_exist(host)
    if result["success"]:
        tl.passed(LOG["s3_ok"].format(
            count=len(result["found_images"]),
        ))
    else:
        tl.failed(LOG["s3_fail"].format(
            count=0, missing="none found",
        ))

    assert result["success"], (
        ASSERT["s3_images_missing"].format(
            missing=result.get("error", "No boot images in S3"),
        )
    )


# =============================================================================
# PIPELINE SUMMARY (TC_BP_012)
# =============================================================================

@pytest.mark.sanity
@pytest.mark.order(10)
def test_build_pipeline_result(host, pipeline_state):
    """TC_BP_012: Verify build pipeline stages reached COMPLETED.

    Only checks build-pipeline stages (upload, create-local-repository,
    build-image). Deploy-pipeline stages (deploy, restart, validate)
    are excluded.
    """
    tc = TC["build_pipeline_result"]
    tl = TestLogger(tc["title"], tc["id"])
    _skip_if_no_creds(tl)
    _skip_if_no_job(pipeline_state, tl)

    result = get_pipeline_summary(host, pipeline_state.job_id, build_only=True)
    if not result["success"]:
        tl.failed(f"Failed to get summary: {result['error']}")
        assert False, f"Pipeline summary query failed: {result['error']}"

    if result["all_completed"]:
        tl.passed(LOG["pipeline_result_ok"])
    else:
        tl.failed(LOG["pipeline_result_fail"])

    if result["details"]:
        tl.check(f"Stage summary:\n{result['details']}")

    assert result["all_completed"], (
        ASSERT["pipeline_result_failed"]
        + f"\n{result['details']}"
    )
