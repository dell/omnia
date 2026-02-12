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

"""NFS-based implementation of PlaybookQueueRequestRepository."""

import json
import logging
import os
import stat
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Final

from api.logging_utils import log_secure_info
from core.localrepo.entities import PlaybookRequest
from core.localrepo.exceptions import QueueUnavailableError

logger = logging.getLogger(__name__)

DEFAULT_QUEUE_BASE = "/opt/omnia/build_stream/playbook_queue"
REQUEST_DIR_NAME = "requests"
FILE_PERMISSIONS = stat.S_IRUSR | stat.S_IWUSR  # 600


class NfsPlaybookQueueRequestRepository:
    """NFS shared volume implementation for playbook request queue.

    Writes playbook request JSON files to the NFS requests directory
    for consumption by the OIM Core watcher service.
    """

    def __init__(self, queue_base_path: str = DEFAULT_QUEUE_BASE) -> None:
        """Initialize repository with queue base path.

        Args:
            queue_base_path: Base path for the playbook queue on NFS.
        """
        self._queue_base = Path(queue_base_path)
        self._requests_dir = self._queue_base / REQUEST_DIR_NAME

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
            with open(file_path, "w", encoding="utf-8") as request_file:
                json.dump(request_data, request_file, indent=2)

            os.chmod(file_path, FILE_PERMISSIONS)

            log_secure_info(
                "info",
                f"Request file written for job {request.job_id}",
                str(request.correlation_id),
            )
            return file_path

        except OSError as exc:
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
        logger.info("Request queue directory ensured: %s", self._requests_dir)
