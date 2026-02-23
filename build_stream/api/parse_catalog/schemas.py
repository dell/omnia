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

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ParseCatalogStatus(str, Enum):
    """Status enum for ParseCatalog API responses."""

    SUCCESS = "success"
    ERROR = "error"


class ParseCatalogResponse(BaseModel):  # pylint: disable=too-few-public-methods
    """Response model for ParseCatalog API."""

    status: ParseCatalogStatus = Field(
        ...,
        description="Status of the catalog parsing operation",
    )
    message: str = Field(
        ...,
        description="Human-readable message describing the result",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "success",
                    "message": "Catalog parsed successfully",
                },
                {
                    "status": "error",
                    "message": "Invalid file format. Only JSON files are accepted.",
                },
            ]
        }
    }


class ErrorResponse(BaseModel):  # pylint: disable=too-few-public-methods
    """Standard error response model."""

    status: ParseCatalogStatus = ParseCatalogStatus.ERROR
    message: str = Field(..., description="Error message describing what went wrong")
    detail: Optional[str] = Field(
        default=None,
        description="Additional error details (only in non-production environments)",
    )
