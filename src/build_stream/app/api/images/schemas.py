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

"""Pydantic schemas for Images API requests and responses."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class ImageResponse(BaseModel):
    """Single constituent image within an Image Group."""
    role: str = Field(
        ..., description="Functional role name (e.g., slurm_node)"
    )
    image_name: str = Field(
        ..., description="Generated image file name on NFS"
    )

    model_config = {"from_attributes": True}


class ImageGroupResponse(BaseModel):
    """Single Image Group with its constituent images."""
    job_id: str = Field(..., description="Associated Job ID (UUID v7)")
    image_group_id: str = Field(..., description="Image Group identifier from catalog")
    images: List[ImageResponse] = Field(
        default_factory=list,
        description="Constituent images within this Image Group",
    )
    status: str = Field(..., description="Current lifecycle status")
    created_at: datetime = Field(..., description="Image Group creation timestamp")
    updated_at: datetime = Field(..., description="Last status update timestamp")

    model_config = {"from_attributes": True}


class PaginationResponse(BaseModel):
    """Pagination metadata."""
    total_count: int = Field(..., ge=0)
    limit: int = Field(..., ge=1, le=1000)
    offset: int = Field(..., ge=0)
    has_more: bool


class ListImagesResponse(BaseModel):
    """Response for GET /api/v1/images."""
    image_groups: List[ImageGroupResponse]
    pagination: PaginationResponse


class ListImagesQueryParams(BaseModel):
    """Internal validation model for query parameters."""
    status: Optional[str] = Field(default="BUILT", description="Filter by ImageGroup status")
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


class ErrorResponse(BaseModel):
    """Standard error response model."""
    error_code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
