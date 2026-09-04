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

"""Unit tests for AuditEvent entity."""

from datetime import datetime, timezone

import pytest

from build_stream.core.jobs.entities.audit import AuditEvent
from build_stream.core.jobs.value_objects import ClientId, CorrelationId, JobId


class TestAuditEvent:
    """Tests for AuditEvent entity."""

    def test_create_event(self):
        """AuditEvent should be immutable."""
        event = AuditEvent(
            event_id="evt-123",
            job_id=JobId("018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a11"),
            event_type="JOB_CREATED",
            correlation_id=CorrelationId("018f3c4b-2d9e-7d1a-8a2b-111111111111"),
            client_id=ClientId("client-1"),
            timestamp=datetime.now(timezone.utc),
        )
        assert event.event_type == "JOB_CREATED"
        assert event.details == {}

    def test_event_with_details(self):
        """AuditEvent should support additional details."""
        event = AuditEvent(
            event_id="evt-123",
            job_id=JobId("018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a11"),
            event_type="STAGE_COMPLETED",
            correlation_id=CorrelationId("018f3c4b-2d9e-7d1a-8a2b-111111111111"),
            client_id=ClientId("client-1"),
            timestamp=datetime.now(timezone.utc),
            details={"stage_name": "parse-catalog", "duration_ms": 1500},
        )
        assert event.details["stage_name"] == "parse-catalog"
        assert event.details["duration_ms"] == 1500

    def test_event_immutability(self):
        """AuditEvent should be frozen."""
        event = AuditEvent(
            event_id="evt-123",
            job_id=JobId("018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a11"),
            event_type="JOB_CREATED",
            correlation_id=CorrelationId("018f3c4b-2d9e-7d1a-8a2b-111111111111"),
            client_id=ClientId("client-1"),
            timestamp=datetime.now(timezone.utc),
        )
        with pytest.raises(AttributeError):
            event.event_type = "JOB_UPDATED"
