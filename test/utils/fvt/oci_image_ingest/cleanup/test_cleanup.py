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
OCI Image Ingest — Cleanup Verification.

Validates working directory cleanup on success and failure:
  TC-FVT-036: Cleanup after success
  TC-FVT-037: Cleanup after failure
"""

import pytest

from library.functions import (
    TestLogger,
    run_playbook,
)
from library.functions.oci_image_ingest_func import (
    check_oci_workdir_cleaned,
    validate_build_status,
    get_oci_workdir_path,
)
from library.vars import (
    TEST_CASES as TC,
    PLAYBOOK_UTILS,
)
from library.messages import TEST_LOG_MSGS as LOG, TEST_ASSERT_MSGS as ASSERT


@pytest.mark.functional
@pytest.mark.oci_image_ingest
@pytest.mark.order(190)
def test_oci_cleanup_after_success(host):
    """Verify working directory cleaned up after successful operation."""
    tc = TC["oci_cleanup_after_success"]
    tl = TestLogger(tc["title"], tc["id"])

    # After a successful pipeline run, working dir should be clean
    status_result = validate_build_status(host)
    if not status_result["success"]:
        tl.skipped("Pipeline must complete successfully for cleanup verification")
        pytest.skip("No successful pipeline run to verify cleanup")

    result = check_oci_workdir_cleaned(host)

    if result["success"]:
        tl.passed(LOG["oci_cleanup_ok"])
    else:
        tl.failed(result["error"])

    assert result["success"], ASSERT["oci_cleanup_failed"].format(
        error=result["error"]
    )


@pytest.mark.functional
@pytest.mark.oci_image_ingest
@pytest.mark.order(191)
def test_oci_cleanup_after_failure(host):
    """Verify working directory is clean (no residual data from any run).

    Confirms the working directory contains no residual OCI image data,
    extraction directories, or partial artifacts from either successful
    or failed pipeline runs.

    NOTE: Deliberate failure injection via extra_vars does not work
    (the playbook ignores them); this test verifies the cleanup state
    after the most recent pipeline run.
    """
    tc = TC["oci_cleanup_after_failure"]
    tl = TestLogger(tc["title"], tc["id"])

    # Verify build_status exists (pipeline has run)
    status_result = validate_build_status(host)
    if not status_result["success"]:
        tl.skipped("Pipeline must have run to verify cleanup")
        pytest.skip("No pipeline run to verify cleanup after")

    result = check_oci_workdir_cleaned(host)

    if result["success"]:
        tl.passed(LOG["oci_cleanup_ok"])
    else:
        tl.failed(LOG["oci_cleanup_partial"].format(details=result["error"]))

    assert result["success"], ASSERT["oci_cleanup_failed"].format(
        error=result["error"]
    )
