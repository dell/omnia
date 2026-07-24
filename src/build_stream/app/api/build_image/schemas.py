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

"""Pydantic schemas for Build Image API requests and responses."""

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class CreateBuildImageRequest(BaseModel):
    """Request model for build image stage."""

    architecture: str = Field(
        ...,
        description="Target architecture (x86_64 or aarch64)",
        pattern="^(x86_64|aarch64)$",
    )
    image_key: str = Field(
        ...,
        description="Image identifier key",
        min_length=1,
        max_length=128,
    )
    functional_groups: List[str] = Field(
        ...,
        description="List of functional groups to build",
        min_items=1,
        max_items=50,
    )


class CreateBuildImageResponse(BaseModel):
    """Response model for build image stage acceptance (202 Accepted)."""

    job_id: str = Field(..., description="Job identifier")
    stage: str = Field(..., description="Stage identifier")
    status: str = Field(..., description="Acceptance status")
    submitted_at: str = Field(..., description="Submission timestamp (ISO 8601)")
    correlation_id: str = Field(..., description="Correlation identifier")
    architecture: str = Field(..., description="Target architecture")
    image_key: str = Field(..., description="Image identifier key")
    functional_groups: List[str] = Field(..., description="List of functional groups to build")


class BuildImageErrorResponse(BaseModel):
    """Standard error response body for build image operations."""

    error: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    correlation_id: str = Field(..., description="Request correlation ID")
    timestamp: str = Field(..., description="Error timestamp (ISO 8601)")
