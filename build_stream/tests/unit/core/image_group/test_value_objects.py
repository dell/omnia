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

"""Unit tests for ImageGroup domain value objects."""

import pytest

from build_stream.core.image_group.value_objects import (
    ImageGroupId,
    ImageGroupStatus,
    PipelinePhase,
)


class TestImageGroupId:
    """Tests for ImageGroupId value object."""

    def test_valid_id(self):
        """Valid identifier string should be accepted."""
        ig_id = ImageGroupId("omnia-cluster-v1.2")
        assert ig_id.value == "omnia-cluster-v1.2"

    def test_str_representation(self):
        """String representation should return value."""
        ig_id = ImageGroupId("test-group")
        assert str(ig_id) == "test-group"

    def test_empty_string_rejected(self):
        """Empty string should be rejected."""
        with pytest.raises(ValueError, match="cannot be empty"):
            ImageGroupId("")

    def test_whitespace_only_rejected(self):
        """Whitespace-only string should be rejected."""
        with pytest.raises(ValueError, match="cannot be empty"):
            ImageGroupId("   ")

    def test_exceeds_maximum_length(self):
        """String exceeding 128 characters should be rejected."""
        long_id = "a" * 129
        with pytest.raises(ValueError, match="cannot exceed 128"):
            ImageGroupId(long_id)

    def test_maximum_length_accepted(self):
        """String at exactly 128 characters should be accepted."""
        exact_id = "a" * 128
        ig_id = ImageGroupId(exact_id)
        assert ig_id.value == exact_id

    def test_immutability(self):
        """ImageGroupId should be immutable (frozen dataclass)."""
        ig_id = ImageGroupId("test")
        with pytest.raises(AttributeError):
            ig_id.value = "other"

    def test_equality(self):
        """Two ImageGroupIds with the same value should be equal."""
        id1 = ImageGroupId("same-id")
        id2 = ImageGroupId("same-id")
        assert id1 == id2

    def test_inequality(self):
        """Two ImageGroupIds with different values should not be equal."""
        id1 = ImageGroupId("id-one")
        id2 = ImageGroupId("id-two")
        assert id1 != id2

    def test_special_characters_accepted(self):
        """Identifiers with hyphens, underscores, dots should be accepted."""
        ig_id = ImageGroupId("omnia_cluster-v1.2.3-rc1")
        assert ig_id.value == "omnia_cluster-v1.2.3-rc1"


class TestImageGroupStatus:
    """Tests for ImageGroupStatus enum."""

    def test_all_values_exist(self):
        """All expected status values should be present."""
        expected = {
            "BUILT", "DEPLOYING", "DEPLOYED", "RESTARTING",
            "RESTARTED", "VALIDATING", "PASSED", "FAILED", "CLEANED",
        }
        actual = {s.value for s in ImageGroupStatus}
        assert actual == expected

    def test_terminal_states(self):
        """PASSED, FAILED, and CLEANED should be terminal."""
        assert ImageGroupStatus.PASSED.is_terminal()
        assert ImageGroupStatus.FAILED.is_terminal()
        assert ImageGroupStatus.CLEANED.is_terminal()

    def test_non_terminal_states(self):
        """Non-terminal states should return False for is_terminal."""
        non_terminal = [
            ImageGroupStatus.BUILT,
            ImageGroupStatus.DEPLOYING,
            ImageGroupStatus.DEPLOYED,
            ImageGroupStatus.RESTARTING,
            ImageGroupStatus.RESTARTED,
            ImageGroupStatus.VALIDATING,
        ]
        for status in non_terminal:
            assert not status.is_terminal(), f"{status} should not be terminal"

    def test_string_enum_values(self):
        """Status values should be usable as strings."""
        assert ImageGroupStatus.BUILT == "BUILT"
        assert ImageGroupStatus.DEPLOYED == "DEPLOYED"

    def test_from_string(self):
        """Status should be constructible from string."""
        status = ImageGroupStatus("BUILT")
        assert status == ImageGroupStatus.BUILT

    def test_invalid_string_raises(self):
        """Invalid string should raise ValueError."""
        with pytest.raises(ValueError):
            ImageGroupStatus("INVALID")


class TestPipelinePhase:
    """Tests for PipelinePhase enum."""

    def test_build_phase(self):
        """BUILD phase should exist."""
        assert PipelinePhase.BUILD.value == "BUILD"

    def test_deploy_phase(self):
        """DEPLOY phase should exist."""
        assert PipelinePhase.DEPLOY.value == "DEPLOY"

    def test_only_two_phases(self):
        """Only BUILD and DEPLOY phases should exist."""
        assert len(PipelinePhase) == 2

    def test_string_enum(self):
        """PipelinePhase values should be usable as strings."""
        assert PipelinePhase.BUILD == "BUILD"
        assert PipelinePhase.DEPLOY == "DEPLOY"

    def test_from_string(self):
        """Phase should be constructible from string."""
        phase = PipelinePhase("BUILD")
        assert phase == PipelinePhase.BUILD
