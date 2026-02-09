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

"""Shared fixtures for Jobs API integration tests."""

import os
from typing import Dict

import pytest
from fastapi.testclient import TestClient

from main import app
from infra.id_generator import UUIDv4Generator


@pytest.fixture(scope="function")
def client():
    """Create test client with fresh container for each test."""
    os.environ["ENV"] = "dev"
    return TestClient(app)


@pytest.fixture(name="uuid_generator")
def uuid_generator_fixture():
    """UUID generator for test fixtures."""
    return UUIDv4Generator()


@pytest.fixture
def auth_headers(uuid_generator) -> Dict[str, str]:
    """Standard authentication headers for testing."""
    return {
        "Authorization": "Bearer test-client-123",
        "X-Correlation-Id": str(uuid_generator.generate()),
        "Idempotency-Key": f"test-key-{uuid_generator.generate()}",
    }


@pytest.fixture
def unique_idempotency_key(uuid_generator) -> str:
    """Generate unique idempotency key for each test."""
    return f"test-key-{uuid_generator.generate()}"


@pytest.fixture
def unique_correlation_id(uuid_generator) -> str:
    """Generate unique correlation ID for each test."""
    return str(uuid_generator.generate())
