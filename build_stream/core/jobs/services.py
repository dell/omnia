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

"""Domain services for Jobs domain."""

import hashlib
import json
from typing import Any, Dict

from .value_objects import RequestFingerprint


class FingerprintService:
    """Domain service for computing request fingerprints.

    Computes deterministic SHA-256 hash of request payload for idempotency.
    """

    @staticmethod
    def compute(request_body: Dict[str, Any]) -> RequestFingerprint:
        """Compute SHA-256 fingerprint of request payload.

        Creates a deterministic hash by:
        1. Sorting keys alphabetically
        2. JSON serializing with no whitespace
        3. UTF-8 encoding
        4. SHA-256 hashing

        Args:
            request_body: Dictionary of request fields.

        Returns:
            RequestFingerprint value object.

        Example:
            >>> body = {"job_id": "123", "client_id": "abc"}
            >>> fp = FingerprintService.compute(body)
            >>> len(fp.value)
            64
        """
        normalized = json.dumps(request_body, sort_keys=True, separators=(',', ':'))
        digest = hashlib.sha256(normalized.encode('utf-8')).hexdigest()
        return RequestFingerprint(digest)
