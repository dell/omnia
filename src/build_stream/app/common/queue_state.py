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

"""Host-local state binding queue results to active API requests."""

import hashlib
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from common.queue_auth import (
    DEFAULT_TTL_SECONDS,
    MAX_CLOCK_SKEW_SECONDS,
    QueueAuthenticationError,
    read_signed_payload,
    write_signed_payload,
)

API_STATE_ENV = "PLAYBOOK_QUEUE_API_STATE_DIR"
DEFAULT_API_STATE_DIR = "/var/lib/omnia/build_stream/playbook_queue/api"


class QueueStateError(ValueError):
    """Raised when a result does not match trusted pending-request state."""


def _identity(payload: Dict[str, Any]) -> Tuple[str, str, str]:
    """Extract the stable identity shared by a request and its result."""
    job_id = payload.get("job_id")
    stage_name = payload.get("stage_name", payload.get("stage_type"))
    request_id = payload.get("request_id")
    if not all(
        isinstance(value, str) and value
        for value in (job_id, stage_name, request_id)
    ):
        raise QueueStateError(
            "Queue message lacks job, stage, or request identity"
        )
    return job_id, stage_name, request_id


def _stage_marker_name(job_id: str, stage_name: str) -> str:
    identity = f"{job_id}\0{stage_name}".encode("utf-8")
    return hashlib.sha256(identity).hexdigest()


def _request_marker_name(request_id: str) -> str:
    return hashlib.sha256(request_id.encode("utf-8")).hexdigest()


class PendingRequestStore:
    """Persist the one result identity currently expected for each stage."""

    def __init__(
        self,
        key: bytes,
        base_path: Optional[str] = None,
    ) -> None:
        configured_path = base_path or os.environ.get(
            API_STATE_ENV, DEFAULT_API_STATE_DIR
        )
        self._base_path = Path(configured_path)
        self._pending_dir = self._base_path / "pending"
        self._consumed_dir = self._base_path / "consumed"
        self._key = key
        self._initialized = False

    def ensure_directories(self) -> None:
        """Create private state directories when deployment has not yet done so."""
        if self._initialized:
            return
        for directory in (self._base_path, self._pending_dir, self._consumed_dir):
            directory.mkdir(parents=True, exist_ok=True)
            os.chmod(directory, 0o700)
        cutoff = (
            time.time() - DEFAULT_TTL_SECONDS - MAX_CLOCK_SKEW_SECONDS
        )
        for marker in self._consumed_dir.iterdir():
            try:
                if marker.lstat().st_mtime < cutoff:
                    marker.unlink()
            except OSError:
                continue
        self._initialized = True

    def register_request(self, payload: Dict[str, Any]) -> Path:
        """Atomically replace the expected result identity for a job stage."""
        job_id, stage_name, request_id = _identity(payload)
        self.ensure_directories()
        marker_path = self._pending_dir / _stage_marker_name(
            job_id, stage_name
        )
        write_signed_payload(
            marker_path,
            {
                "job_id": job_id,
                "stage_name": stage_name,
                "request_id": request_id,
            },
            self._key,
            purpose="pending",
        )
        return marker_path

    def validate_result(self, payload: Dict[str, Any]) -> Dict[str, str]:
        """Require a result to match the current, unconsumed stage request."""
        job_id, stage_name, request_id = _identity(payload)
        consumed_path = self._consumed_dir / _request_marker_name(request_id)
        if consumed_path.exists():
            raise QueueStateError("Queue result request ID was already consumed")

        marker_path = self._pending_dir / _stage_marker_name(
            job_id, stage_name
        )
        try:
            pending = read_signed_payload(
                marker_path,
                self._key,
                purpose="pending",
            )
        except QueueAuthenticationError as exc:
            raise QueueStateError(
                "Queue result has no authenticated pending request"
            ) from exc

        expected = {
            "job_id": job_id,
            "stage_name": stage_name,
            "request_id": request_id,
        }
        if pending != expected:
            raise QueueStateError(
                "Queue result does not match the active stage request"
            )
        return expected

    def consume_result(self, identity: Dict[str, str]) -> None:
        """Atomically record consumption, then remove the matching pending state."""
        job_id, stage_name, request_id = _identity(identity)
        self.ensure_directories()
        consumed_path = self._consumed_dir / _request_marker_name(request_id)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        try:
            descriptor = os.open(consumed_path, flags, 0o600)
        except FileExistsError as exc:
            raise QueueStateError(
                "Queue result request ID was already consumed"
            ) from exc
        try:
            os.write(descriptor, request_id.encode("utf-8"))
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

        pending_path = self._pending_dir / _stage_marker_name(
            job_id, stage_name
        )
        try:
            pending = read_signed_payload(
                pending_path,
                self._key,
                purpose="pending",
            )
            if pending == identity:
                pending_path.unlink()
        except (OSError, QueueAuthenticationError):
            # Consumption is already persistent. A newer pending request must
            # never be removed merely because cleanup of the old marker failed.
            pass
