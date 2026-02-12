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

"""Repository port interfaces (Protocols) for Local Repository domain.

These define the contracts that infrastructure implementations must satisfy.
Using Protocol instead of ABC allows for structural subtyping (duck typing).
"""

from pathlib import Path
from typing import List, Protocol

from .entities import PlaybookRequest, PlaybookResult


class PlaybookQueueRequestRepository(Protocol):
    """Repository port for writing playbook requests to the NFS queue."""

    def write_request(self, request: PlaybookRequest) -> Path:
        """Write a playbook request file to the requests directory.

        Args:
            request: Playbook request to write.

        Returns:
            Path to the written request file.

        Raises:
            QueueUnavailableError: If the queue directory is not accessible.
        """
        ...

    def is_available(self) -> bool:
        """Check if the request queue directory is accessible.

        Returns:
            True if the queue directory exists and is writable.
        """
        ...


class PlaybookQueueResultRepository(Protocol):
    """Repository port for reading playbook results from the NFS queue."""

    def get_unprocessed_results(self) -> List[Path]:
        """Return list of result files not yet processed.

        Returns:
            List of paths to unprocessed result JSON files.
        """
        ...

    def read_result(self, result_path: Path) -> PlaybookResult:
        """Read and parse a result file.

        Args:
            result_path: Path to the result JSON file.

        Returns:
            Parsed PlaybookResult entity.

        Raises:
            ValueError: If the result file is malformed.
        """
        ...

    def archive_result(self, result_path: Path) -> None:
        """Move a processed result file to the archive directory.

        Args:
            result_path: Path to the result file to archive.
        """
        ...

    def is_available(self) -> bool:
        """Check if the result queue directory is accessible.

        Returns:
            True if the queue directory exists and is readable.
        """
        ...


class InputDirectoryRepository(Protocol):
    """Repository port for managing input directory paths."""

    def get_source_input_repository_path(self, job_id: str) -> Path:
        """Get source input directory path for a job.

        Args:
            job_id: Job identifier.

        Returns:
            Path like /opt/omnia/build_stream/{job_id}/input/
        """
        ...

    def get_destination_input_repository_path(self) -> Path:
        """Get destination input directory path expected by playbook.

        Returns:
            Path like /opt/omnia/input/project_build_stream/
        """
        ...

    def validate_input_directory(self, path: Path) -> bool:
        """Validate that input directory exists and contains required files.

        Args:
            path: Path to the input directory to validate.

        Returns:
            True if directory is valid and contains required files.
        """
        ...
