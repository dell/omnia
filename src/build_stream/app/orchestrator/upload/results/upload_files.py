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

"""Upload files result."""

from dataclasses import dataclass
from enum import Enum
from typing import List


class FileChangeStatus(str, Enum):
    """File change status enumeration."""
    CHANGED = "CHANGED"
    UNCHANGED = "UNCHANGED"


@dataclass(frozen=True)
class UploadSummary:
    """Summary of upload operation.
    
    Attributes:
        total_files: Total number of files uploaded.
        changed_files: Number of files that were changed.
        unchanged_files: Number of files that were unchanged.
    """
    total_files: int
    changed_files: int
    unchanged_files: int


@dataclass(frozen=True)
class UploadedFileInfo:
    """Information about an uploaded file.
    
    Attributes:
        filename: Name of the uploaded file.
        status: Change status (CHANGED or UNCHANGED).
        size_bytes: Size of the file in bytes.
    """
    filename: str
    status: FileChangeStatus
    size_bytes: int


@dataclass(frozen=True)
class UploadFilesResult:
    """Result of upload files operation.
    
    Attributes:
        job_id: Job identifier.
        upload_summary: Summary of the upload operation.
        files: List of uploaded file information.
    """
    job_id: str
    upload_summary: UploadSummary
    files: List[UploadedFileInfo]
