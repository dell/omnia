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

"""ParseCatalog command DTO."""

from dataclasses import dataclass
from typing import ClassVar

from core.jobs.value_objects import CorrelationId, JobId


@dataclass(frozen=True)
class ParseCatalogCommand:
    """Command to execute the parse-catalog stage.

    Attributes:
        job_id: Job identifier (validated UUID).
        correlation_id: Request correlation identifier for tracing.
        filename: Name of the uploaded catalog file.
        content: Raw bytes of the uploaded catalog file.
    """

    job_id: JobId
    correlation_id: CorrelationId
    filename: str
    content: bytes

    FILENAME_MAX_LENGTH: ClassVar[int] = 255
    MAX_CONTENT_SIZE: ClassVar[int] = 5 * 1024 * 1024  # 5 MB

    def __post_init__(self) -> None:
        """Validate command fields."""
        if not self.filename or not self.filename.strip():
            raise ValueError("filename cannot be empty")
        if len(self.filename) > self.FILENAME_MAX_LENGTH:
            raise ValueError(
                f"filename must be <= {self.FILENAME_MAX_LENGTH} chars, "
                f"got {len(self.filename)}"
            )
        if not self.content:
            raise ValueError("content cannot be empty")
        if len(self.content) > self.MAX_CONTENT_SIZE:
            raise ValueError(
                f"content size {len(self.content)} bytes exceeds maximum "
                f"{self.MAX_CONTENT_SIZE} bytes"
            )
