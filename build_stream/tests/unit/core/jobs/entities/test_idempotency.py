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

"""Unit tests for IdempotencyRecord entity."""

from datetime import datetime, timedelta

import pytest

from build_stream.core.jobs.entities.idempotency import IdempotencyRecord
from build_stream.core.jobs.value_objects import ClientId, IdempotencyKey, JobId, RequestFingerprint


class TestIdempotencyRecord:
    """Tests for IdempotencyRecord entity."""

    def test_create_record(self):
        """IdempotencyRecord should be immutable."""
        now = datetime.now()
        record = IdempotencyRecord(
            idempotency_key=IdempotencyKey("key-123"),
            job_id=JobId("018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a11"),
            request_fingerprint=RequestFingerprint("a" * 64),
            client_id=ClientId("client-1"),
            created_at=now,
            expires_at=now + timedelta(hours=1),
        )
        assert record.idempotency_key.value == "key-123"
        assert record.job_id.value == "018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a11"

    def test_record_immutability(self):
        """IdempotencyRecord should be frozen."""
        now = datetime.now()
        record = IdempotencyRecord(
            idempotency_key=IdempotencyKey("key-123"),
            job_id=JobId("018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a11"),
            request_fingerprint=RequestFingerprint("a" * 64),
            client_id=ClientId("client-1"),
            created_at=now,
            expires_at=now + timedelta(hours=1),
        )
        with pytest.raises(AttributeError):
            record.job_id = JobId("018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a12")

    def test_is_expired(self):
        """Record should correctly detect expiration."""
        now = datetime.now()
        record = IdempotencyRecord(
            idempotency_key=IdempotencyKey("key-123"),
            job_id=JobId("018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a11"),
            request_fingerprint=RequestFingerprint("a" * 64),
            client_id=ClientId("client-1"),
            created_at=now,
            expires_at=now + timedelta(hours=1),
        )
        assert record.is_expired(now) is False
        assert record.is_expired(now + timedelta(hours=2)) is True

    def test_matches_fingerprint(self):
        """Record should correctly match fingerprints."""
        now = datetime.now()
        fingerprint = RequestFingerprint("a" * 64)
        record = IdempotencyRecord(
            idempotency_key=IdempotencyKey("key-123"),
            job_id=JobId("018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a11"),
            request_fingerprint=fingerprint,
            client_id=ClientId("client-1"),
            created_at=now,
            expires_at=now + timedelta(hours=1),
        )
        assert record.matches_fingerprint(fingerprint) is True
        assert record.matches_fingerprint(RequestFingerprint("b" * 64)) is False
