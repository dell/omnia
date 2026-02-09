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

"""Shared fixtures and utilities for entity tests."""

import pytest
from datetime import datetime, timezone

from build_stream.core.jobs.value_objects import JobId, ClientId, CorrelationId


@pytest.fixture
def sample_job_id():
    """Sample job ID for testing."""
    return JobId("018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a11")


@pytest.fixture
def sample_client_id():
    """Sample client ID for testing."""
    return ClientId("client-1")


@pytest.fixture
def sample_correlation_id():
    """Sample correlation ID for testing."""
    return CorrelationId("018f3c4b-2d9e-7d1a-8a2b-111111111111")


@pytest.fixture
def sample_timestamp():
    """Sample timestamp for testing."""
    return datetime.now(timezone.utc)
