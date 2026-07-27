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

"""Result DTO for the CleanUp Job use case."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CleanupResult:
    """Outcome of a cleanup operation.

    Attributes:
        job_id: Job identifier (string).
        image_group_id: Image Group identifier (string).
        status: Final status (always ``CLEANED`` on success).
        cleanup_type: ``manual`` for API-initiated, ``auto`` for cron.
        s3_objects_deleted: Total S3 objects removed across all images.
        nfs_files_deleted: Total NFS artifact files removed.
        cleaned_at: ISO 8601 UTC timestamp.
    """

    job_id: str
    image_group_id: str
    status: str
    cleanup_type: str
    s3_objects_deleted: int
    nfs_files_deleted: int
    cleaned_at: str
