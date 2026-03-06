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

"""Unit tests for Job domain value objects."""

import uuid

import pytest

from build_stream.core.jobs.value_objects import (
    ClientId,
    CorrelationId,
    IdempotencyKey,
    JobId,
    JobState,
    RequestFingerprint,
    StageName,
    StageState,
    StageType,
)


class TestJobId:
    """Tests for JobId value object."""

    @staticmethod
    def _uuid_str() -> str:
        """Generate a UUID string for tests (version-agnostic)."""
        return str(uuid.uuid4())

    def test_valid_uuid_any_version(self):
        """Any valid UUID (e.g., v4) should be accepted."""
        raw = self._uuid_str()
        job_id = JobId(raw)
        assert job_id.value == raw

    def test_uuid_is_normalized_lowercase(self):
        """Uppercase UUID strings are normalized to canonical lowercase."""
        raw = self._uuid_str()
        upper_raw = raw.upper()
        job_id = JobId(upper_raw)
        assert job_id.value == raw.lower()

    def test_invalid_uuid_format(self):
        """Malformed UUID should be rejected."""
        with pytest.raises(ValueError, match="Invalid UUID format"):
            JobId("not-a-uuid")

    def test_empty_string(self):
        """Empty string should be rejected."""
        with pytest.raises(ValueError, match="Invalid UUID format"):
            JobId("")

    def test_exceeds_maximum_length(self):
        """String longer than max length should be rejected."""
        with pytest.raises(ValueError, match="length cannot exceed"):
            JobId("018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a11-extra")

    def test_immutability(self):
        """JobId should be immutable (frozen dataclass)."""
        job_id = JobId(self._uuid_str())
        with pytest.raises(AttributeError):
            job_id.value = "018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a12"

    def test_str_representation(self):
        """String representation should return value."""
        raw = self._uuid_str()
        job_id = JobId(raw)
        assert str(job_id) == raw

    def test_equality(self):
        """Two JobIds with same value should be equal."""
        raw = self._uuid_str()
        job_id1 = JobId(raw)
        job_id2 = JobId(raw.upper())
        assert job_id1 == job_id2


class TestCorrelationId:
    """Tests for CorrelationId value object."""

    @staticmethod
    def _uuid_str() -> str:
        """Generate a UUID string for tests (version-agnostic)."""
        return str(uuid.uuid4())

    def test_valid_uuid_any_version(self):
        """Any valid UUID (e.g., v4) should be accepted."""
        raw = self._uuid_str()
        corr_id = CorrelationId(raw)
        assert corr_id.value == raw

    def test_invalid_uuid_format(self):
        """Invalid UUID format should be rejected."""
        with pytest.raises(ValueError, match="Invalid UUID format"):
            CorrelationId("invalid-correlation-id")

    def test_exceeds_maximum_length(self):
        """String longer than max length should be rejected."""
        with pytest.raises(ValueError, match="length cannot exceed"):
            CorrelationId("018f3c4b-2d9e-7d1a-8a2b-111111111111-extra")

    def test_immutability(self):
        """CorrelationId should be immutable."""
        corr_id = CorrelationId(self._uuid_str())
        with pytest.raises(AttributeError):
            corr_id.value = "018f3c4b-2d9e-7d1a-8a2b-222222222222"


class TestStageName:
    """Tests for StageName value object."""

    def test_valid_stage_names(self):
        """All canonical stage names should be accepted."""
        for stage in StageType:
            stage_name = StageName(stage.value)
            assert stage_name.value == stage.value
            assert stage_name.as_enum() == stage

    def test_invalid_stage_name(self):
        """Non-canonical stage name should be rejected."""
        with pytest.raises(ValueError, match="Invalid stage name"):
            StageName("invalid-stage")

    def test_empty_string(self):
        """Empty string should be rejected."""
        with pytest.raises(ValueError, match="Invalid stage name"):
            StageName("")

    def test_case_sensitive(self):
        """Stage names are case-sensitive."""
        with pytest.raises(ValueError, match="Invalid stage name"):
            StageName("Parse-Catalog")

    def test_exceeds_maximum_length(self):
        """String longer than max length should be rejected."""
        with pytest.raises(ValueError, match="length cannot exceed"):
            StageName("this-stage-name-is-way-too-long-for-validation")

    def test_immutability(self):
        """StageName should be immutable."""
        stage = StageName("parse-catalog")
        with pytest.raises(AttributeError):
            stage.value = "build-image"

    def test_canonical_stages_count(self):
        """Verify we have exactly 10 canonical stages."""
        assert len(StageType) == 10


class TestIdempotencyKey:
    """Tests for IdempotencyKey value object."""

    def test_valid_key(self):
        """Valid key within length bounds should be accepted."""
        key = IdempotencyKey("key-001")
        assert key.value == "key-001"

    def test_minimum_length(self):
        """Single character key should be accepted."""
        key = IdempotencyKey("a")
        assert key.value == "a"

    def test_maximum_length(self):
        """255 character key should be accepted."""
        long_key = "x" * 255
        key = IdempotencyKey(long_key)
        assert key.value == long_key

    def test_empty_string(self):
        """Empty string should be rejected."""
        with pytest.raises(ValueError, match="length must be between"):
            IdempotencyKey("")

    def test_exceeds_maximum_length(self):
        """Key longer than 255 characters should be rejected."""
        too_long = "x" * 256
        with pytest.raises(ValueError, match="length must be between"):
            IdempotencyKey(too_long)

    def test_immutability(self):
        """IdempotencyKey should be immutable."""
        key = IdempotencyKey("key-001")
        with pytest.raises(AttributeError):
            key.value = "key-002"


class TestRequestFingerprint:
    """Tests for RequestFingerprint value object."""

    def test_valid_sha256(self):
        """Valid SHA-256 hex string should be accepted."""
        fingerprint = RequestFingerprint(
            "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
        )
        assert len(fingerprint.value) == 64

    def test_valid_sha256_uppercase(self):
        """SHA-256 with uppercase hex should be accepted."""
        fingerprint = RequestFingerprint(
            "9F86D081884C7D659A2FEAA0C55AD015A3BF4F1B2B0B822CD15D6C15B0F00A08"
        )
        assert len(fingerprint.value) == 64

    def test_invalid_length(self):
        """String with wrong length should be rejected."""
        with pytest.raises(ValueError, match="Invalid SHA-256 format"):
            RequestFingerprint("abc123")

    def test_invalid_characters(self):
        """String with non-hex characters should be rejected."""
        with pytest.raises(ValueError, match="Invalid SHA-256 format"):
            RequestFingerprint("g" * 64)

    def test_empty_string(self):
        """Empty string should be rejected."""
        with pytest.raises(ValueError, match="Invalid SHA-256 format"):
            RequestFingerprint("")

    def test_immutability(self):
        """RequestFingerprint should be immutable."""
        fp = RequestFingerprint(
            "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
        )
        with pytest.raises(AttributeError):
            fp.value = "0" * 64


class TestClientId:
    """Tests for ClientId value object."""

    def test_valid_client_id(self):
        """Valid client ID should be accepted."""
        client_id = ClientId("client-1")
        assert client_id.value == "client-1"

    def test_empty_string(self):
        """Empty string should be rejected."""
        with pytest.raises(ValueError, match="cannot be empty"):
            ClientId("")

    def test_whitespace_only(self):
        """Whitespace-only string should be rejected."""
        with pytest.raises(ValueError, match="cannot be empty"):
            ClientId("   ")

    def test_exceeds_maximum_length(self):
        """String longer than max length should be rejected."""
        with pytest.raises(ValueError, match="length cannot exceed"):
            ClientId("x" * 129)

    def test_immutability(self):
        """ClientId should be immutable."""
        client_id = ClientId("client-1")
        with pytest.raises(AttributeError):
            client_id.value = "client-2"


class TestJobState:
    """Tests for JobState enum."""

    def test_all_states_exist(self):
        """All expected job states should exist."""
        assert JobState.CREATED == "CREATED"
        assert JobState.IN_PROGRESS == "IN_PROGRESS"
        assert JobState.COMPLETED == "COMPLETED"
        assert JobState.FAILED == "FAILED"
        assert JobState.CANCELLED == "CANCELLED"

    def test_terminal_states(self):
        """Terminal states should return True for is_terminal()."""
        assert JobState.COMPLETED.is_terminal() is True
        assert JobState.FAILED.is_terminal() is True
        assert JobState.CANCELLED.is_terminal() is True

    def test_non_terminal_states(self):
        """Non-terminal states should return False for is_terminal()."""
        assert JobState.CREATED.is_terminal() is False
        assert JobState.IN_PROGRESS.is_terminal() is False

    def test_state_count(self):
        """Verify we have exactly 5 job states."""
        assert len(JobState) == 5


class TestStageState:
    """Tests for StageState enum."""

    def test_all_states_exist(self):
        """All expected stage states should exist."""
        assert StageState.PENDING == "PENDING"
        assert StageState.IN_PROGRESS == "IN_PROGRESS"
        assert StageState.COMPLETED == "COMPLETED"
        assert StageState.FAILED == "FAILED"
        assert StageState.SKIPPED == "SKIPPED"
        assert StageState.CANCELLED == "CANCELLED"

    def test_terminal_states(self):
        """Terminal states should return True for is_terminal()."""
        assert StageState.COMPLETED.is_terminal() is True
        assert StageState.FAILED.is_terminal() is True
        assert StageState.SKIPPED.is_terminal() is True
        assert StageState.CANCELLED.is_terminal() is True

    def test_non_terminal_states(self):
        """Non-terminal states should return False for is_terminal()."""
        assert StageState.PENDING.is_terminal() is False
        assert StageState.IN_PROGRESS.is_terminal() is False

    def test_state_count(self):
        """Verify we have exactly 6 stage states."""
        assert len(StageState) == 6
