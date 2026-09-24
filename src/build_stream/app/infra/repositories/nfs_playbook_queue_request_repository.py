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

"""Authenticated NFS implementation of PlaybookQueueRequestRepository."""

import os
from pathlib import Path
from typing import Optional

from api.logging_utils import log_secure_info
from common.queue_auth import load_auth_key, write_signed_payload
from common.queue_state import PendingRequestStore
from core.localrepo.entities import PlaybookRequest
from core.localrepo.exceptions import QueueUnavailableError


DEFAULT_QUEUE_BASE = os.getenv(
    "PLAYBOOK_QUEUE_BASE",
    str(Path(os.getenv("OMNIA_DATA_PATH", "/opt/omnia")) / "playbook_queue"),
)
REQUEST_DIR_NAME = "requests"


class NfsPlaybookQueueRequestRepository:
    """NFS shared volume implementation for playbook request queue.

    Writes playbook request JSON files to the NFS requests directory
    for consumption by the OIM Core watcher service.
    """

    def __init__(
        self,
        queue_base_path: str = DEFAULT_QUEUE_BASE,
        auth_key: Optional[bytes] = None,
        pending_state_path: Optional[str] = None,
    ) -> None:
        """Initialize repository with queue base path.

        Args:
            queue_base_path: Base path for the playbook queue on NFS.
        """
        self._queue_base = Path(queue_base_path)
        self._requests_dir = self._queue_base / REQUEST_DIR_NAME
        self._auth_key = auth_key
        self._pending_state_path = pending_state_path
        self._pending_store = None

    def _get_auth_key(self) -> bytes:
        """Load the host-managed queue key only when the queue is used."""
        if self._auth_key is None:
            self._auth_key = load_auth_key()
        return self._auth_key

    def _get_pending_store(self) -> PendingRequestStore:
        """Return the trusted host-local active-request registry."""
        if self._pending_store is None:
            self._pending_store = PendingRequestStore(
                self._get_auth_key(), self._pending_state_path
            )
        return self._pending_store

    def write_request(self, request: PlaybookRequest) -> Path:
        """Write a playbook request file to the requests directory.

        Args:
            request: Playbook request to write.

        Returns:
            Path to the written request file.

        Raises:
            QueueUnavailableError: If the queue directory is not accessible.
        """
        if not self.is_available():
            raise QueueUnavailableError(
                queue_path=str(self._requests_dir),
                reason="Request queue directory does not exist or is not writable",
            )

        filename = request.generate_filename()
        file_path = self._requests_dir / filename

        try:
            request_data = request.to_dict()
            request_data.setdefault("command_type", "ansible-playbook")
            self._get_pending_store().register_request(request_data)
            write_signed_payload(
                file_path,
                request_data,
                self._get_auth_key(),
                purpose="request",
            )

            log_secure_info(
                "info",
                f"Request file written for job {request.job_id}",
                str(request.correlation_id),
            )
            return file_path

        except (OSError, ValueError) as exc:
            log_secure_info(
                "error",
                "Failed to write request file",
            )
            raise QueueUnavailableError(
                queue_path=str(self._requests_dir),
                reason=f"Failed to write request file: {exc}",
            ) from exc

    def is_available(self) -> bool:
        """Check if the request queue directory is accessible.

        Returns:
            True if the queue directory exists and is writable.
        """
        return self._requests_dir.is_dir() and os.access(
            self._requests_dir, os.W_OK
        )

    def ensure_directories(self) -> None:
        """Create queue directories if they do not exist."""
        self._requests_dir.mkdir(parents=True, exist_ok=True)
        log_secure_info('info', f"Request queue directory ensured: {self._requests_dir}")
