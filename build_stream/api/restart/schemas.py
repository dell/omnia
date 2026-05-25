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

"""Pydantic schemas for Restart API responses."""

from pydantic import BaseModel, Field


class RestartLinksResponse(BaseModel):
    """HATEOAS links for restart response."""

    self_link: str = Field(..., alias="self", description="Job resource URL")
    status: str = Field(..., description="Job status URL")

    class Config:
        populate_by_name = True


class CreateRestartResponse(BaseModel):
    """Response model for restart stage acceptance (202 Accepted)."""

    job_id: str = Field(..., description="Job identifier")
    stage: str = Field(..., description="Stage identifier")
    status: str = Field(..., description="Acceptance status")
    submitted_at: str = Field(..., description="Submission timestamp (ISO 8601)")
    image_group_id: str = Field(..., description="Image group identifier")
    correlation_id: str = Field(..., description="Correlation identifier")
    links: RestartLinksResponse = Field(..., alias="_links", description="HATEOAS links")

    class Config:
        populate_by_name = True


class RestartErrorResponse(BaseModel):
    """Standard error response body for restart operations."""

    error: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    correlation_id: str = Field(..., description="Request correlation ID")
    timestamp: str = Field(..., description="Error timestamp (ISO 8601)")
