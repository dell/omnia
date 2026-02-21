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

"""NFS-based implementation of PlaybookQueueResultRepository."""

import json
import logging
import os
import shutil
from pathlib import Path
from typing import List, Set

from api.logging_utils import log_secure_info

from core.localrepo.entities import PlaybookResult

logger = logging.getLogger(__name__)

DEFAULT_QUEUE_BASE = "/opt/omnia/playbook_queue"
RESULTS_DIR_NAME = "results"
ARCHIVE_DIR_NAME = "archive/results"


class NfsPlaybookQueueResultRepository:
    """NFS shared volume implementation for playbook result queue.

    Reads playbook result JSON files from the NFS results directory
    written by the OIM Core watcher service.
    """

    def __init__(self, queue_base_path: str = DEFAULT_QUEUE_BASE) -> None:
        """Initialize repository with queue base path.

        Args:
            queue_base_path: Base path for the playbook queue on NFS.
        """
        self._queue_base = Path(queue_base_path)
        self._results_dir = self._queue_base / RESULTS_DIR_NAME
        self._archive_dir = self._queue_base / ARCHIVE_DIR_NAME
        self._processed_files: Set[str] = set()

    def get_unprocessed_results(self) -> List[Path]:
        """Return list of result files not yet processed.

        Returns:
            List of paths to unprocessed result JSON files.
        """
        if not self._results_dir.is_dir():
            return []

        result_files = []
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
            with open(result_path, "r", encoding="utf-8") as result_file:
                data = json.load(result_file)

            required_fields = {"job_id", "stage_name", "status"}
            missing = required_fields - set(data.keys())
            if missing:
                raise ValueError(
                    f"Result file {result_path} missing required fields: {missing}"
                )

            return PlaybookResult.from_dict(data)

        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Invalid JSON in result file {result_path}: {exc}"
            ) from exc

    def archive_result(self, result_path: Path) -> None:
        """Move a processed result file to the archive directory.

        Args:
            result_path: Path to the result file to archive.
        """
        self._archive_dir.mkdir(parents=True, exist_ok=True)
        archive_path = self._archive_dir / result_path.name

        try:
            shutil.move(str(result_path), str(archive_path))
            self._processed_files.add(result_path.name)
            log_secure_info(
                "info",
                "Result file archived",
            )
        except OSError:  # pylint: disable=unused-variable
            log_secure_info(
                "error",
                "Failed to archive result file",
            )

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
        logger.info("Result queue directories ensured: %s", self._results_dir)

    def clear_processed_cache(self) -> None:
        """Clear the in-memory set of processed file names."""
        self._processed_files.clear()
