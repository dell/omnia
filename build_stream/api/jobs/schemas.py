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

"""Pydantic schemas for Jobs API requests and responses."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class CreateJobRequest(BaseModel):
    """Request payload for creating a job."""

    client_id: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Client identifier",
    )
    client_name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Optional client name",
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional metadata describing the job",
    )
    parameters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional parameters for job execution",
    )

    model_config = {"populate_by_name": True}

    @field_validator("client_id")
    @classmethod
    def validate_client_id(cls, v: str) -> str:
        """Validate client_id."""
        if not v.strip():
            raise ValueError("client_id cannot be empty")
        return v.strip()

    @field_validator("client_name")
    @classmethod
    def validate_client_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate client name when provided."""
        if v is None:
            return None
        if not v.strip():
            raise ValueError("client_name cannot be empty")
        return v.strip()


class StageResponse(BaseModel):
    """Response model for a stage entry."""
    stage_name: str = Field(..., description="Stage identifier")
    stage_state: str = Field(..., description="Stage state")
    started_at: Optional[str] = Field(default=None, description="Start timestamp (ISO 8601)")
    ended_at: Optional[str] = Field(default=None, description="End timestamp (ISO 8601)")
    error_code: Optional[str] = Field(default=None, description="Error code if failed")
    error_summary: Optional[str] = Field(default=None, description="Error summary if failed")


class CreateJobResponse(BaseModel):
    """Response model for job creation."""
    job_id: str = Field(..., description="Job identifier")
    correlation_id: str = Field(..., description="Correlation identifier")
    job_state: str = Field(..., description="Job state")
    created_at: str = Field(..., description="Creation timestamp (ISO 8601)")
    stages: List[StageResponse] = Field(..., description="Job stages")


class GetJobResponse(BaseModel):
    """Response model for retrieving a job."""
    job_id: str = Field(..., description="Job identifier")
    correlation_id: str = Field(..., description="Correlation identifier")
    job_state: str = Field(..., description="Job state")
    created_at: str = Field(..., description="Creation timestamp (ISO 8601)")
    updated_at: Optional[str] = Field(
        default=None, description="Update timestamp (ISO 8601)"
    )
    tombstone: Optional[bool] = Field(default=None, description="Tombstone flag")
    stages: List[StageResponse] = Field(..., description="Job stages")


class ErrorResponse(BaseModel):
    """Standard error response body."""
    error: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    correlation_id: str = Field(..., description="Request correlation ID")
    timestamp: str = Field(..., description="Error timestamp (ISO 8601)")

    @classmethod
    def create(cls, error: str, message: str, correlation_id: str) -> "ErrorResponse":
        """Convenience constructor with current UTC timestamp."""
        return cls(
            error=error,
            message=message,
            correlation_id=correlation_id,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )
