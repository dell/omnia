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

"""Pydantic schemas for ParseCatalog API request and response models."""

from pydantic import BaseModel, Field


class ParseCatalogResponse(BaseModel):
    """Response model for the parse-catalog stage (200 OK).

    Kept minimal (Omnia 2.3+ reintroduction): the stage's only job today
    is the image_group_id uniqueness check, so the response only reports
    that outcome.
    """

    job_id: str = Field(..., description="Job identifier")
    stage: str = Field(..., description="Stage identifier")
    status: str = Field(..., description="Stage completion status")
    image_group_id: str = Field(..., description="Image group identifier extracted from the catalog")
    message: str = Field(..., description="Human-readable result message")
    correlation_id: str = Field(..., description="Correlation identifier")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "job_id": "019bf590-1234-7890-abcd-ef1234567890",
                    "stage": "parse-catalog",
                    "status": "COMPLETED",
                    "image_group_id": "omnia-services-rhel-10-0-slurm-test",
                    "message": "Catalog parsed successfully; image_group_id is unique",
                    "correlation_id": "corr-123456",
                },
            ]
        }
    }


class ParseCatalogErrorResponse(BaseModel):
    """Standard error response body for parse-catalog operations."""

    error: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    correlation_id: str = Field(..., description="Request correlation ID")
    timestamp: str = Field(..., description="Error timestamp (ISO 8601)")
