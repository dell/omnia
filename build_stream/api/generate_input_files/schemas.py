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

"""Pydantic schemas for GenerateInputFiles API."""

from typing import List, Optional, Tuple

from pydantic import BaseModel, Field


class GenerateInputFilesRequest(BaseModel):
    """Request model for GenerateInputFiles API."""

    adapter_policy_path: Optional[str] = Field(
        default=None,
        max_length=4096,
        description="Optional custom adapter policy path. Uses default if omitted.",
    )


class ArtifactRefResponse(BaseModel):
    """Artifact reference in API responses."""

    key: str = Field(..., description="Artifact key")
    digest: str = Field(..., description="SHA-256 content digest")
    size_bytes: int = Field(..., description="Content size in bytes")
    uri: str = Field(..., description="Storage URI")


class GenerateInputFilesResponse(BaseModel):
    """Response model for GenerateInputFiles API."""

    job_id: str = Field(..., description="Job identifier")
    stage_state: str = Field(..., description="Stage state after execution")
    message: str = Field(..., description="Human-readable result message")


class ErrorResponse(BaseModel):
    """Standard error response model."""

    error: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    correlation_id: Optional[str] = Field(
        default=None, description="Correlation ID for tracing"
    )
