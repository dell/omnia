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

"""Idempotency tracking record entity."""

from dataclasses import dataclass
from datetime import datetime

from ..value_objects import ClientId, IdempotencyKey, JobId, RequestFingerprint


@dataclass(frozen=True)
class IdempotencyRecord:
    """Idempotency tracking record.

    Immutable record linking idempotency key to job and request fingerprint.
    Used for request deduplication and retry safety.

    Attributes:
        idempotency_key: Client-provided deduplication token.
        job_id: Associated job identifier.
        request_fingerprint: SHA-256 hash of normalized request.
        client_id: Client who created the request.
        created_at: Record creation timestamp.
        expires_at: Record expiration timestamp.
    """

    idempotency_key: IdempotencyKey
    job_id: JobId
    request_fingerprint: RequestFingerprint
    client_id: ClientId
    created_at: datetime
    expires_at: datetime

    def is_expired(self, current_time: datetime) -> bool:
        """Check if record has expired.

        Args:
            current_time: Current timestamp for comparison.

        Returns:
            True if record is expired.
        """
        return current_time >= self.expires_at

    def matches_fingerprint(self, fingerprint: RequestFingerprint) -> bool:
        """Check if fingerprint matches this record.

        Args:
            fingerprint: Request fingerprint to compare.

        Returns:
            True if fingerprints match.
        """
        return self.request_fingerprint == fingerprint
