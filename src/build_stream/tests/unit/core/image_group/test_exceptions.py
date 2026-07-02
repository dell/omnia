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

"""Unit tests for ImageGroup domain exceptions."""

import pytest

from build_stream.core.image_group.exceptions import (
    DuplicateImageGroupError,
    ImageGroupNotFoundError,
    ImageGroupMismatchError,
    InvalidStateTransitionError,
)


class TestDuplicateImageGroupError:
    """Tests for DuplicateImageGroupError."""

    def test_message_includes_id(self):
        """Error message should include the image group ID."""
        err = DuplicateImageGroupError("omnia-v1")
        assert "omnia-v1" in str(err)
        assert err.image_group_id == "omnia-v1"

    def test_message_content(self):
        """Error message should indicate duplication."""
        err = DuplicateImageGroupError("test-id")
        assert "already exists" in str(err)


class TestImageGroupNotFoundError:
    """Tests for ImageGroupNotFoundError."""

    def test_message_includes_job_id(self):
        """Error message should include the job ID."""
        err = ImageGroupNotFoundError("job-123")
        assert "job-123" in str(err)
        assert err.job_id == "job-123"

    def test_message_content(self):
        """Error message should indicate not found."""
        err = ImageGroupNotFoundError("job-123")
        assert "No Image Group" in str(err)


class TestImageGroupMismatchError:
    """Tests for ImageGroupMismatchError."""

    def test_message_includes_both_ids(self):
        """Error message should include both supplied and expected IDs."""
        err = ImageGroupMismatchError(supplied="wrong-id", expected="right-id")
        assert "wrong-id" in str(err)
        assert "right-id" in str(err)
        assert err.supplied == "wrong-id"
        assert err.expected == "right-id"

    def test_message_content(self):
        """Error message should indicate mismatch."""
        err = ImageGroupMismatchError(supplied="a", expected="b")
        assert "does not match" in str(err)


class TestInvalidStateTransitionError:
    """Tests for InvalidStateTransitionError."""

    def test_message_includes_current_and_required(self):
        """Error message should include current status and required statuses."""
        err = InvalidStateTransitionError(
            current="DEPLOYING",
            required={"BUILT"},
        )
        assert "DEPLOYING" in str(err)
        assert err.current == "DEPLOYING"
        assert err.required == {"BUILT"}

    def test_message_content(self):
        """Error message should indicate state requirement."""
        err = InvalidStateTransitionError(current="X", required={"A", "B"})
        assert "required" in str(err)

    def test_sorted_required_in_message(self):
        """Required statuses in message should be sorted for determinism."""
        err = InvalidStateTransitionError(
            current="X",
            required={"FAILED", "BUILT", "PASSED"},
        )
        msg = str(err)
        assert "['BUILT', 'FAILED', 'PASSED']" in msg
