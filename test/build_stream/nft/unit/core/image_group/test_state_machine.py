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

"""Unit tests for ImageGroup state machine guard functions."""

import uuid

import pytest

from build_stream.core.image_group.entities import ImageGroup
from build_stream.core.image_group.value_objects import (
    ImageGroupId,
    ImageGroupStatus,
)
from build_stream.core.image_group.state_machine import (
    ALLOWED_TRANSITIONS,
    STATUS_FLOW,
    guard_check,
)
# Import exceptions from same module path as production code to avoid
# dual-module-path issue where build_stream.core.* and core.* create
# distinct class objects.
from core.image_group.exceptions import (
    ImageGroupNotFoundError,
    ImageGroupMismatchError,
    InvalidStateTransitionError,
)
from build_stream.core.jobs.value_objects import JobId


def _make_ig(status: ImageGroupStatus, ig_id: str = "test-group") -> ImageGroup:
    """Create a test ImageGroup."""
    return ImageGroup(
        id=ImageGroupId(ig_id),
        job_id=JobId(str(uuid.uuid4())),
        status=status,
    )


class TestAllowedTransitions:
    """Tests for ALLOWED_TRANSITIONS mapping."""

    def test_deploy_accepts_all_retryable_statuses(self):
        """Deploy stage accepts BUILT and all intermediate/failed statuses for retry."""
        expected = {
            ImageGroupStatus.BUILT,
            ImageGroupStatus.DEPLOYING,
            ImageGroupStatus.DEPLOYED,
            ImageGroupStatus.RESTARTING,
            ImageGroupStatus.RESTARTED,
            ImageGroupStatus.VALIDATING,
            ImageGroupStatus.FAILED,
        }
        assert ALLOWED_TRANSITIONS["deploy"] == expected

    def test_deploy_excludes_passed_and_cleaned(self):
        """Deploy stage must NOT accept PASSED or CLEANED (require fresh build)."""
        assert ImageGroupStatus.PASSED not in ALLOWED_TRANSITIONS["deploy"]
        assert ImageGroupStatus.CLEANED not in ALLOWED_TRANSITIONS["deploy"]

    def test_restart_requires_deployed(self):
        """Restart stage should only accept DEPLOYED status."""
        assert ALLOWED_TRANSITIONS["restart"] == {ImageGroupStatus.DEPLOYED}

    def test_validate_requires_restarted(self):
        """Validate stage should only accept RESTARTED status."""
        assert ALLOWED_TRANSITIONS["validate"] == {ImageGroupStatus.RESTARTED}

    def test_cleanup_accepts_multiple_statuses(self):
        """Cleanup should accept BUILT, PASSED, and FAILED."""
        expected = {
            ImageGroupStatus.BUILT,
            ImageGroupStatus.PASSED,
            ImageGroupStatus.FAILED,
        }
        assert ALLOWED_TRANSITIONS["cleanup"] == expected


class TestStatusFlow:
    """Tests for STATUS_FLOW mapping."""

    def test_deploy_flow(self):
        """Deploy flow: DEPLOYING -> DEPLOYED -> FAILED."""
        on_start, on_success, on_failure = STATUS_FLOW["deploy"]
        assert on_start == ImageGroupStatus.DEPLOYING
        assert on_success == ImageGroupStatus.DEPLOYED
        assert on_failure == ImageGroupStatus.FAILED

    def test_restart_flow(self):
        """Restart flow: RESTARTING -> RESTARTED -> FAILED."""
        on_start, on_success, on_failure = STATUS_FLOW["restart"]
        assert on_start == ImageGroupStatus.RESTARTING
        assert on_success == ImageGroupStatus.RESTARTED
        assert on_failure == ImageGroupStatus.FAILED

    def test_validate_flow(self):
        """Validate flow: VALIDATING -> PASSED -> FAILED."""
        on_start, on_success, on_failure = STATUS_FLOW["validate"]
        assert on_start == ImageGroupStatus.VALIDATING
        assert on_success == ImageGroupStatus.PASSED
        assert on_failure == ImageGroupStatus.FAILED


class TestGuardCheck:
    """Tests for guard_check function."""

    def test_none_image_group_raises_not_found(self):
        """guard_check should raise ImageGroupNotFoundError when image_group is None."""
        with pytest.raises(ImageGroupNotFoundError):
            guard_check(None, "deploy")

    def test_deploy_with_matching_id_and_built_status(self):
        """Deploy guard should pass with matching ID and BUILT status."""
        ig = _make_ig(ImageGroupStatus.BUILT, ig_id="my-group")
        guard_check(ig, "deploy", requested_image_group_id="my-group")

    def test_deploy_with_mismatching_id_raises_mismatch(self):
        """Deploy guard should raise ImageGroupMismatchError on ID mismatch."""
        ig = _make_ig(ImageGroupStatus.BUILT, ig_id="expected-id")
        with pytest.raises(ImageGroupMismatchError) as exc_info:
            guard_check(ig, "deploy", requested_image_group_id="wrong-id")
        assert exc_info.value.supplied == "wrong-id"
        assert exc_info.value.expected == "expected-id"

    def test_deploy_with_wrong_status_raises_invalid_transition(self):
        """Deploy guard should raise InvalidStateTransitionError for PASSED status."""
        ig = _make_ig(ImageGroupStatus.PASSED)
        with pytest.raises(InvalidStateTransitionError) as exc_info:
            guard_check(ig, "deploy", requested_image_group_id=str(ig.id))
        assert exc_info.value.current == "PASSED"

    def test_deploy_with_deploying_status_passes(self):
        """Deploy guard should pass for DEPLOYING (retry interrupted deploy)."""
        ig = _make_ig(ImageGroupStatus.DEPLOYING, ig_id="my-group")
        guard_check(ig, "deploy", requested_image_group_id="my-group")

    def test_deploy_with_deployed_status_passes(self):
        """Deploy guard should pass for DEPLOYED (redeploy after successful deploy)."""
        ig = _make_ig(ImageGroupStatus.DEPLOYED, ig_id="my-group")
        guard_check(ig, "deploy", requested_image_group_id="my-group")

    def test_deploy_with_failed_status_passes(self):
        """Deploy guard should pass for FAILED (retry after failed pipeline)."""
        ig = _make_ig(ImageGroupStatus.FAILED, ig_id="my-group")
        guard_check(ig, "deploy", requested_image_group_id="my-group")

    def test_deploy_with_restarting_status_passes(self):
        """Deploy guard should pass for RESTARTING (retry interrupted restart)."""
        ig = _make_ig(ImageGroupStatus.RESTARTING, ig_id="my-group")
        guard_check(ig, "deploy", requested_image_group_id="my-group")

    def test_deploy_with_restarted_status_passes(self):
        """Deploy guard should pass for RESTARTED (full redeploy from restarted)."""
        ig = _make_ig(ImageGroupStatus.RESTARTED, ig_id="my-group")
        guard_check(ig, "deploy", requested_image_group_id="my-group")

    def test_deploy_with_validating_status_passes(self):
        """Deploy guard should pass for VALIDATING (redeploy while validating)."""
        ig = _make_ig(ImageGroupStatus.VALIDATING, ig_id="my-group")
        guard_check(ig, "deploy", requested_image_group_id="my-group")

    def test_deploy_with_cleaned_status_raises(self):
        """Deploy guard should raise for CLEANED (requires fresh build)."""
        ig = _make_ig(ImageGroupStatus.CLEANED, ig_id="my-group")
        with pytest.raises(InvalidStateTransitionError) as exc_info:
            guard_check(ig, "deploy", requested_image_group_id="my-group")
        assert exc_info.value.current == "CLEANED"

    def test_restart_with_deployed_status(self):
        """Restart guard should pass with DEPLOYED status."""
        ig = _make_ig(ImageGroupStatus.DEPLOYED)
        guard_check(ig, "restart")

    def test_restart_with_wrong_status_raises(self):
        """Restart guard should raise on wrong status."""
        ig = _make_ig(ImageGroupStatus.BUILT)
        with pytest.raises(InvalidStateTransitionError):
            guard_check(ig, "restart")

    def test_validate_with_restarted_status(self):
        """Validate guard should pass with RESTARTED status."""
        ig = _make_ig(ImageGroupStatus.RESTARTED)
        guard_check(ig, "validate")

    def test_validate_with_wrong_status_raises(self):
        """Validate guard should raise on wrong status."""
        ig = _make_ig(ImageGroupStatus.DEPLOYED)
        with pytest.raises(InvalidStateTransitionError):
            guard_check(ig, "validate")

    def test_cleanup_with_built_status(self):
        """Cleanup guard should pass with BUILT status."""
        ig = _make_ig(ImageGroupStatus.BUILT)
        guard_check(ig, "cleanup")

    def test_cleanup_with_passed_status(self):
        """Cleanup guard should pass with PASSED status."""
        ig = _make_ig(ImageGroupStatus.PASSED)
        guard_check(ig, "cleanup")

    def test_cleanup_with_failed_status(self):
        """Cleanup guard should pass with FAILED status."""
        ig = _make_ig(ImageGroupStatus.FAILED)
        guard_check(ig, "cleanup")

    def test_cleanup_with_deploying_raises(self):
        """Cleanup guard should raise on active status (DEPLOYING)."""
        ig = _make_ig(ImageGroupStatus.DEPLOYING)
        with pytest.raises(InvalidStateTransitionError):
            guard_check(ig, "cleanup")

    def test_cleanup_with_cleaned_raises(self):
        """Cleanup guard should raise on already cleaned status."""
        ig = _make_ig(ImageGroupStatus.CLEANED)
        with pytest.raises(InvalidStateTransitionError):
            guard_check(ig, "cleanup")

    def test_unknown_stage_raises(self):
        """Unknown stage name should raise due to empty required set."""
        ig = _make_ig(ImageGroupStatus.BUILT)
        with pytest.raises(InvalidStateTransitionError):
            guard_check(ig, "nonexistent-stage")
