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

"""Domain exceptions for Local Repository module."""

from typing import Optional


class LocalRepoDomainError(Exception):
    """Base exception for all local repo domain errors."""

    def __init__(self, message: str, correlation_id: Optional[str] = None) -> None:
        """Initialize domain error.

        Args:
            message: Human-readable error description.
            correlation_id: Optional correlation ID for tracing.
        """
        super().__init__(message)
        self.message = message
        self.correlation_id = correlation_id




class QueueUnavailableError(LocalRepoDomainError):
    """NFS playbook queue is not accessible."""

    def __init__(
        self,
        queue_path: str,
        reason: str = "",
        correlation_id: Optional[str] = None,
    ) -> None:
        """Initialize queue unavailable error.

        Args:
            queue_path: Path to the unavailable queue directory.
            reason: Reason the queue is unavailable.
            correlation_id: Optional correlation ID for tracing.
        """
        super().__init__(
            f"Playbook queue unavailable at {queue_path}: {reason}",
            correlation_id=correlation_id,
        )
        self.queue_path = queue_path
        self.reason = reason


class InputFilesMissingError(LocalRepoDomainError):
    """Required input files not found for job."""

    def __init__(
        self,
        job_id: str,
        input_path: str,
        correlation_id: Optional[str] = None,
    ) -> None:
        """Initialize input files missing error.

        Args:
            job_id: The job ID with missing input files.
            input_path: Expected input directory path.
            correlation_id: Optional correlation ID for tracing.
        """
        super().__init__(
            f"Input files not found for job {job_id} at {input_path}. "
            f"Run GenerateInputFiles API first.",
            correlation_id=correlation_id,
        )
        self.job_id = job_id
        self.input_path = input_path


class InputDirectoryInvalidError(LocalRepoDomainError):
    """Input directory structure is invalid."""

    def __init__(
        self,
        job_id: str,
        input_path: str,
        reason: str = "",
        correlation_id: Optional[str] = None,
    ) -> None:
        """Initialize input directory invalid error.

        Args:
            job_id: The job ID with invalid input directory.
            input_path: Path to the invalid input directory.
            reason: Reason the directory is invalid.
            correlation_id: Optional correlation ID for tracing.
        """
        super().__init__(
            f"Input directory invalid for job {job_id} at {input_path}: {reason}",
            correlation_id=correlation_id,
        )
        self.job_id = job_id
        self.input_path = input_path
        self.reason = reason
