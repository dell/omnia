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

# ****
# Secure code generated utilizing Code Guardian.
# Applicable rules used: CG-OUTPUT-001.2
# ****

"""Pydantic schemas for the pipeline log query API."""

from typing import List, Optional

from pydantic import BaseModel, Field


class StageLogEntry(BaseModel):
    """Redacted log content for one stage."""

    stage_name: str = Field(..., description="BSM stage name, e.g. build-image")
    stage_state: str = Field(..., description="Stage state")
    has_log: bool = Field(..., description="True when log content is returned")
    log_content: Optional[str] = Field(
        default=None, description="Redacted log lines joined by newlines"
    )
    total_lines: int = Field(..., description="Lines in the whole stage log")
    returned_lines: int = Field(..., description="Lines returned in log_content")
    truncated: bool = Field(..., description="True when log_content is not the whole log")
    unavailable_reason: Optional[str] = Field(
        default=None,
        description=(
            "Why no content is returned: NOT_YET_AVAILABLE, NOT_RECORDED, "
            "NOT_PUBLISHED, MISSING, or NOT_TEXT"
        ),
    )


class JobLogsResponse(BaseModel):
    """Response for GET /api/v1/jobs/{job_id}/logs."""

    job_id: str = Field(..., description="Job identifier")
    correlation_id: str = Field(..., description="Request correlation ID")
    tail_lines: Optional[int] = Field(
        default=None, description="Tail lines applied per stage; null when full=true"
    )
    full: bool = Field(..., description="True when the complete (bounded) log was requested")
    stages: List[StageLogEntry] = Field(..., description="Per-stage log entries")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "job_id": "019bf590-1234-7890-abcd-ef1234567890",
                    "correlation_id": "0b8e3c0e-6f3c-4d8a-9a43-6f0b6a3cfa10",
                    "tail_lines": 50,
                    "full": False,
                    "stages": [
                        {
                            "stage_name": "build-image",
                            "stage_state": "COMPLETED",
                            "has_log": True,
                            "log_content": "TASK [image_build : Build image] ****\nok: [oim]",
                            "total_lines": 1830,
                            "returned_lines": 50,
                            "truncated": True,
                            "unavailable_reason": None,
                        }
                    ],
                }
            ]
        }
    }
