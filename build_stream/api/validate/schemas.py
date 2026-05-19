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

"""Pydantic schemas for Validate API requests and responses."""

from typing import List, Optional

from pydantic import BaseModel, Field


class ValidateRequestSchema(BaseModel):
    """Request model for validate stage (spec §7.2).

    Attributes:
        scenario_names: Molecule scenarios to run (e.g. ['discovery'], ['all']).
        test_suite: Optional suite filter (e.g. 'smoke', 'sanity', 'regression').
        timeout_minutes: Max execution time in minutes.
    """

    scenario_names: Optional[List[str]] = Field(
        default=["all"],
        description="Molecule scenarios to run (e.g. ['discovery'], ['slurm'], or ['all'])",
    )
    test_suite: Optional[str] = Field(
        default="",
        description="Suite filter (e.g. 'smoke', 'sanity', 'regression'). Maps to Molecule markers.",
    )
    timeout_minutes: Optional[int] = Field(
        default=120,
        ge=1,
        le=480,
        description="Max execution time in minutes (1-480, default 120)",
    )


class ValidateResponseSchema(BaseModel):
    """Response model for validate stage acceptance (202 Accepted) — spec §7.2."""

    job_id: str = Field(..., description="Job identifier")
    stage: str = Field(..., description="Stage identifier ('validate')")
    status: str = Field(..., description="Stage status ('QUEUED')")
    submitted_at: str = Field(..., description="Submission timestamp (ISO 8601)")
    correlation_id: str = Field(..., description="Correlation identifier")
    attempt: int = Field(default=1, description="Attempt number for this validate run")


class ValidateErrorResponse(BaseModel):
    """Standard error response body for validate operations."""

    error: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    correlation_id: str = Field(..., description="Request correlation ID")
    timestamp: str = Field(..., description="Error timestamp (ISO 8601)")
