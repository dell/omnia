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

"""Domain services for Local Repository module."""

from pathlib import Path
from typing import Callable

from api.logging_utils import log_secure_info

from core.localrepo.entities import PlaybookRequest, PlaybookResult
from core.localrepo.exceptions import (
    InputDirectoryInvalidError,
    InputFilesMissingError,
    QueueUnavailableError,
)
from core.localrepo.repositories import (
    InputDirectoryRepository,
    PlaybookQueueRequestRepository,
    PlaybookQueueResultRepository,
)



class InputFileService:
    """Service for validating and preparing input files before playbook execution.

    Ensures that required input files exist and are properly staged
    in the destination directory expected by the playbook.
    """

    def __init__(self, input_repo: InputDirectoryRepository) -> None:
        """Initialize input file service.

        Args:
            input_repo: Input directory repository implementation.
        """
        self._input_repo = input_repo

    def prepare_playbook_input(
        self,
        job_id: str,
        correlation_id: str = "",
    ) -> bool:
        """Validate that domain-specific input files are in place.

        With domain segregation (Omnia 2.3+), input files are placed directly
        into domain-specific directories by domain-init.sh or the GitLab CI
        pipeline (e.g., /opt/omnia/repo_manager/input/project_default/).
        There is no longer a software_config.json or config/ directory to copy.

        This method validates that the destination input directory exists and
        contains the expected files for the repo_manager domain.

        Args:
            job_id: Job identifier (for logging / error context).
            correlation_id: Request correlation ID for tracing.

        Returns:
            True if input validation was successful.

        Raises:
            InputFilesMissingError: If domain input files not found.
            InputDirectoryInvalidError: If input directory is invalid.
        """
        destination_path = self._input_repo.get_destination_input_repository_path()

        if not self._input_repo.validate_input_directory(destination_path):
            log_secure_info(
                'error',
                f"Domain input files not found at {destination_path} for "
                f"job {job_id}, correlation_id={correlation_id}",
            )
            raise InputFilesMissingError(
                job_id=job_id,
                input_path=str(destination_path),
                correlation_id=correlation_id,
            )

        log_secure_info(
            "info",
            f"Domain input files validated for job {job_id} at {destination_path}",
            str(correlation_id),
        )
        return True


class PlaybookQueueRequestService:
    """Service for managing playbook request queue operations.

    Handles writing playbook requests to the NFS shared volume
    for consumption by the OIM Core watcher service.
    """

    def __init__(self, request_repo: PlaybookQueueRequestRepository) -> None:
        """Initialize request queue service.

        Args:
            request_repo: Playbook queue request repository implementation.
        """
        self._request_repo = request_repo

    def submit_request(
        self,
        request: PlaybookRequest,
        correlation_id: str = "",
    ) -> Path:
        """Submit a playbook request to the NFS queue.

        Args:
            request: Playbook request to submit.
            correlation_id: Request correlation ID for tracing.

        Returns:
            Path to the written request file.

        Raises:
            QueueUnavailableError: If the queue is not accessible.
        """
        if not self._request_repo.is_available():
            raise QueueUnavailableError(
                queue_path="requests",
                reason="Request queue directory is not accessible",
                correlation_id=correlation_id,
            )

        request_path = self._request_repo.write_request(request)
        log_secure_info(
            "info",
            f"Request submitted for job {request.job_id}",
            str(request.correlation_id),
        )
        return request_path


class PlaybookQueueResultService:
    """Service for polling and processing playbook execution results.

    Monitors the NFS result queue and invokes callbacks when
    results are available.
    """

    def __init__(self, result_repo: PlaybookQueueResultRepository) -> None:
        """Initialize result queue service.

        Args:
            result_repo: Playbook queue result repository implementation.
        """
        self._result_repo = result_repo

    def poll_results(
        self,
        callback: Callable[[PlaybookResult], None],
    ) -> int:
        """Poll for new results and invoke callback for each.

        Args:
            callback: Function to call with each new result.

        Returns:
            Number of results processed.
        """
        if not self._result_repo.is_available():
            #log_secure_info('warning', "Result queue directory is not accessible")
            return 0

        result_files = self._result_repo.get_unprocessed_results()
        processed_count = 0

        for result_path in result_files:
            try:
                result = self._result_repo.read_result(result_path)
                callback(result)
                self._result_repo.archive_result(result_path)
                processed_count += 1
                log_secure_info(
                    "info",
                    f"Processed result for job {result.job_id}",
                    str(result.request_id),
                )
            except (ValueError, KeyError) as exc:
                log_secure_info(
                    "error",
                    "Failed to parse result file",
                )
            except Exception as exc:  # pylint: disable=broad-except
                log_secure_info(
                    "error",
                    "Failed to process result file",
                )

        return processed_count


