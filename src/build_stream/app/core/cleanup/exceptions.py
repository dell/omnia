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

"""Domain exceptions for the CleanUp module."""


class CleanupDomainError(Exception):
    """Base class for cleanup domain exceptions."""


class CleanupStateInvalidError(CleanupDomainError):
    """Raised when ImageGroup is in an active state that disallows cleanup."""

    def __init__(self, image_group_id: str, current_status: str) -> None:
        self.image_group_id = image_group_id
        self.current_status = current_status
        self.message = (
            f"Image Group '{image_group_id}' is in state '{current_status}' "
            f"which does not allow cleanup. Cleanup is only permitted for "
            f"BUILT, DEPLOYED, RESTARTED, PASSED, or FAILED states."
        )
        super().__init__(self.message)


class AlreadyCleanedError(CleanupDomainError):
    """Raised when the Job has already been cleaned."""

    def __init__(self, job_id: str) -> None:
        self.job_id = job_id
        self.message = f"Job '{job_id}' has already been cleaned."
        super().__init__(self.message)


class CleanupS3FailedError(CleanupDomainError):
    """Raised when S3 image deletion fails."""

    def __init__(
        self, image_group_id: str, exit_code: int, stderr: str
    ) -> None:
        self.image_group_id = image_group_id
        self.exit_code = exit_code
        self.message = (
            f"S3 cleanup failed for Image Group '{image_group_id}': "
            f"s3cmd exit code {exit_code}. Error: {stderr[:500]}"
        )
        super().__init__(self.message)


class CleanupNfsFailedError(CleanupDomainError):
    """Raised when NFS artifact removal fails."""

    def __init__(self, job_id: str, path: str, error: str) -> None:
        self.job_id = job_id
        self.path = path
        self.message = (
            f"NFS cleanup failed for Job '{job_id}': "
            f"could not remove '{path}'. Error: {error[:500]}"
        )
        super().__init__(self.message)


class RetentionLimitExceededError(CleanupDomainError):
    """Raised when image retention limit is reached during build-image."""

    def __init__(self, current_count: int, limit: int) -> None:
        self.current_count = current_count
        self.limit = limit
        self.message = (
            f"Image retention limit reached ({current_count}/{limit}). "
            f"Please clean up existing jobs using the CleanUp Pipeline "
            f"before building new images."
        )
        super().__init__(self.message)
