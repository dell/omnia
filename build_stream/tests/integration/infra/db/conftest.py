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

"""Fixtures for database integration tests."""

import os
from datetime import datetime, timezone

import pytest

from core.jobs.value_objects import (
    ClientId,
    CorrelationId,
    IdempotencyKey,
    JobId,
    JobState,
    RequestFingerprint,
    StageName,
    StageState,
)


@pytest.fixture
def sample_job() -> JobId:
    """Create a sample job ID for testing."""
    return JobId("12345678-1234-5678-9abc-123456789abc")


@pytest.fixture
def sample_client_id() -> ClientId:
    """Create a sample client ID for testing."""
    return ClientId("test-client")


@pytest.fixture
def sample_idempotency_key() -> IdempotencyKey:
    """Create a sample idempotency key for testing."""
    return IdempotencyKey("test-key-123")


@pytest.fixture
def sample_correlation_id() -> CorrelationId:
    """Create a sample correlation ID for testing."""
    return CorrelationId("corr-12345678-1234-5678-9abc-123456789abc")


@pytest.fixture
def sample_request_fingerprint() -> RequestFingerprint:
    """Create a sample request fingerprint for testing."""
    return RequestFingerprint("a" * 64)  # Valid SHA-256 hex


@pytest.fixture
def sample_timestamp() -> datetime:
    """Create a sample timestamp for testing."""
    return datetime(2026, 1, 26, 10, 0, tzinfo=timezone.utc)


@pytest.fixture
def sample_stage_names() -> list[StageName]:
    """Create sample stage names for testing."""
    return [
        StageName("parse-catalog"),
        StageName("generate-input-files"),
        StageName("create-local-repository"),
        StageName("update-local-repository"),
        StageName("create-image-repository"),
        StageName("build-image-x86_64"),
        StageName("build-image-aarch64"),
        StageName("validate-image"),
        StageName("validate-image-on-test"),
        StageName("promote"),
    ]


@pytest.fixture
def sample_job_states() -> list[JobState]:
    """Create sample job states for testing."""
    return list(JobState)


@pytest.fixture
def sample_stage_states() -> list[StageState]:
    """Create sample stage states for testing."""
    return list(StageState)


