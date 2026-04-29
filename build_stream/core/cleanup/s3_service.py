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

"""Abstract S3 cleanup service interface.

Implementations of this interface delete S3 image objects/prefixes for
the CleanUp API. The concrete implementation (`S3CmdCleanupService`)
shells out to the `s3cmd` CLI which is available in the BuildStream
container.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class S3CleanupResult:
    """Result of a single S3 cleanup operation."""

    image_path: str
    objects_deleted: int
    exit_code: int
    success: bool


class S3CleanupService(ABC):
    """Abstract interface for deleting images from S3 storage."""

    @abstractmethod
    def delete_image_path(self, image_path: str) -> S3CleanupResult:
        """Delete all S3 objects under the given S3 path/prefix.

        Args:
            image_path: Complete S3 path/prefix as stored in
                ``images.image_name`` (for example
                ``s3://boot-images/<role>/rhel-<role>_<job_id>-<image_key>/``).

        Returns:
            S3CleanupResult with details of the deletion.

        Raises:
            CleanupS3FailedError: If the underlying s3cmd invocation fails.
        """
        ...
