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

"""Authenticated NFS implementation of PlaybookQueueResultRepository."""

import os
import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional, Set

from api.logging_utils import log_secure_info
from common.queue_auth import (
    QueueAuthenticationError,
    load_auth_key,
    read_signed_payload,
)
from common.queue_state import PendingRequestStore, QueueStateError

from core.localrepo.entities import PlaybookResult


DEFAULT_QUEUE_BASE = os.getenv(
    "PLAYBOOK_QUEUE_BASE",
    str(Path(os.getenv("OMNIA_DATA_PATH", "/opt/omnia")) / "playbook_queue"),
)
RESULTS_DIR_NAME = "results"
ARCHIVE_DIR_NAME = "archive/results"
QUARANTINE_DIR_NAME = "archive/rejected-results"
MAX_QUARANTINED_RESULTS = 100


class NfsPlaybookQueueResultRepository:  # pylint: disable=too-many-instance-attributes
    """NFS shared volume implementation for playbook result queue.

    Reads playbook result JSON files from the NFS results directory
    written by the OIM Core watcher service.
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
        self._results_dir = self._queue_base / RESULTS_DIR_NAME
        self._archive_dir = self._queue_base / ARCHIVE_DIR_NAME
        self._quarantine_dir = self._queue_base / QUARANTINE_DIR_NAME
        self._auth_key = auth_key
        self._pending_state_path = pending_state_path
        self._pending_store = None
        self._validated_results: Dict[Path, Dict[str, str]] = {}
        self._processed_files: Set[str] = set()
        # Clear cache on startup to ensure we don't miss any files
        self.clear_processed_cache()
        log_secure_info('info', "Initialized NfsPlaybookQueueResultRepository with cleared cache")

    def _get_auth_key(self) -> bytes:
        """Load the host-managed queue key only when results are read."""
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

    def get_unprocessed_results(self) -> List[Path]:
        """Return list of result files not yet processed.

        Returns:
            List of paths to unprocessed result JSON files.
        """
        result_files = []

        # Check results directory
        if self._results_dir.is_dir():
            for file_path in sorted(self._results_dir.glob("*.json")):
                if file_path.name not in self._processed_files:
                    result_files.append(file_path)

        return result_files

    def read_result(self, result_path: Path) -> PlaybookResult:
        """Read and parse a result file.

        Args:
            result_path: Path to the result JSON file.

        Returns:
            Parsed PlaybookResult entity.

        Raises:
            ValueError: If the result file is malformed.
            FileNotFoundError: If the result file does not exist.
        """
        try:
            data = read_signed_payload(
                result_path,
                self._get_auth_key(),
                purpose="result",
            )

            required_fields = {
                "job_id",
                "stage_name",
                "request_id",
                "status",
            }
            missing = required_fields - set(data.keys())
            if missing:
                raise ValueError(
                    f"Result file {result_path} missing required fields: {missing}"
                )

            identity = self._get_pending_store().validate_result(data)
            self._validated_results[result_path] = identity
            return PlaybookResult.from_dict(data)

        except (QueueAuthenticationError, QueueStateError) as exc:
            raise ValueError(
                f"Untrusted result file {result_path}: {exc}"
            ) from exc

    def archive_result(self, result_path: Path) -> None:
        """Move a processed result file to the archive directory.

        Args:
            result_path: Path to the result file to archive.
        """
        self._archive_dir.mkdir(parents=True, exist_ok=True)
        archive_path = self._archive_dir / result_path.name

        try:
            identity = self._validated_results.pop(result_path, None)
            if identity is None:
                raise ValueError("Result was not validated before archival")
            self._get_pending_store().consume_result(identity)

            # Only move if not already in archive
            if result_path.parent != self._archive_dir:
                shutil.move(str(result_path), str(archive_path))
                log_secure_info(
                    "info",
                    "Result file moved to archive",
                )
            else:
                log_secure_info(
                    "info",
                    "Result file already in archive",
                )
            self._processed_files.add(result_path.name)
        except (OSError, ValueError):  # pylint: disable=unused-variable
            log_secure_info(
                "error",
                "Failed to archive result file",
            )

    def quarantine_result(self, result_path: Path) -> None:
        """Move an invalid or unauthenticated result out of the live poll set."""
        self._quarantine_dir.mkdir(parents=True, exist_ok=True)
        quarantine_path = self._quarantine_dir / (
            f"{result_path.stem}.{time.time_ns()}{result_path.suffix}"
        )
        try:
            shutil.move(str(result_path), str(quarantine_path))
            self._processed_files.add(result_path.name)
            quarantined = sorted(
                self._quarantine_dir.glob("*.json"),
                key=lambda path: path.lstat().st_mtime_ns,
                reverse=True,
            )
            for expired_path in quarantined[MAX_QUARANTINED_RESULTS:]:
                expired_path.unlink()
            log_secure_info("warning", "Rejected result moved to quarantine")
        except OSError:
            log_secure_info("error", "Failed to quarantine rejected result")

    def is_available(self) -> bool:
        """Check if the result queue directory is accessible.

        Returns:
            True if the queue directory exists and is readable.
        """
        return self._results_dir.is_dir() and os.access(
            self._results_dir, os.R_OK
        )

    def ensure_directories(self) -> None:
        """Create queue directories if they do not exist."""
        self._results_dir.mkdir(parents=True, exist_ok=True)
        self._archive_dir.mkdir(parents=True, exist_ok=True)
        self._quarantine_dir.mkdir(parents=True, exist_ok=True)
        self._get_pending_store().ensure_directories()
        log_secure_info('info', f"Result queue directories ensured: {self._results_dir}")

    def clear_processed_cache(self) -> None:
        """Clear the in-memory set of processed file names."""
        self._processed_files.clear()
