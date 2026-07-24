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

"""Upload API schemas."""

from typing import List
from pydantic import BaseModel, Field

from orchestrator.upload.results.upload_files import (
    UploadFilesResult,
    FileChangeStatus,
)


class UploadSummarySchema(BaseModel):
    """Upload summary schema."""

    total_files: int = Field(..., description="Total number of files uploaded")
    changed_files: int = Field(..., description="Number of files that were changed")
    unchanged_files: int = Field(..., description="Number of files that were unchanged")


class UploadedFileSchema(BaseModel):
    """Uploaded file information schema."""

    filename: str = Field(..., description="Name of the uploaded file")
    status: FileChangeStatus = Field(..., description="Change status (CHANGED or UNCHANGED)")
    size_bytes: int = Field(..., description="Size of the file in bytes")


class UploadFilesResponse(BaseModel):
    """Upload files response schema."""

    job_id: str = Field(..., description="Job identifier")
    upload_summary: UploadSummarySchema = Field(..., description="Summary of the upload operation")
    files: List[UploadedFileSchema] = Field(..., description="List of uploaded file information")

    @classmethod
    def from_result(cls, result: UploadFilesResult) -> "UploadFilesResponse":
        """Convert use case result to API response.

        Args:
            result: Upload files result from use case.

        Returns:
            API response schema.
        """
        return cls(
            job_id=result.job_id,
            upload_summary=UploadSummarySchema(
                total_files=result.upload_summary.total_files,
                changed_files=result.upload_summary.changed_files,
                unchanged_files=result.upload_summary.unchanged_files,
            ),
            files=[
                UploadedFileSchema(
                    filename=f.filename,
                    status=f.status,
                    size_bytes=f.size_bytes,
                )
                for f in result.files
            ],
        )

    class Config:
        """Pydantic config."""
        schema_extra = {
            "example": {
                "job_id": "018f3c4b-7b5b-7a9d-b6c4-9f3b4f9b2c10",
                "upload_summary": {
                    "total_files": 2,
                    "changed_files": 1,
                    "unchanged_files": 1,
                },
                "files": [
                    {
                        "filename": "pxe_mapping_file.csv",
                        "status": "CHANGED",
                        "size_bytes": 512,
                    },
                    {
                        "filename": "network_spec.yml",
                        "status": "UNCHANGED",
                        "size_bytes": 1024,
                    },
                ],
            }
        }
