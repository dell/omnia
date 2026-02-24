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

"""Pydantic schemas for catalog roles API request and response models."""

from typing import List

from pydantic import BaseModel, Field


class GetRolesResponse(BaseModel):  # pylint: disable=too-few-public-methods
    """Response model for GET /jobs/{job_id}/catalog/roles."""

    job_id: str = Field(..., description="The job identifier")
    roles: List[str] = Field(..., description="List of role names from the parsed catalog")
    image_key: str = Field(..., description="Catalog identifier to use as image_key in build-image API")
    architectures: List[str] = Field(..., description="List of supported architectures (e.g., x86_64, aarch64)")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "job_id": "019bf590-1234-7890-abcd-ef1234567890",
                    "roles": [
                        "login_compiler_node_x86_64",
                        "service_kube_control_plane_x86_64",
                        "service_kube_node_x86_64",
                        "slurm_control_node_x86_64",
                        "slurm_node_x86_64",
                    ],
                    "image_key": "image-build",
                    "architectures": ["aarch64", "x86_64"],
                }
            ]
        }
    }


class ErrorResponse(BaseModel):  # pylint: disable=too-few-public-methods
    """Standard error response model."""

    error_code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    correlation_id: str = Field(..., description="Request correlation identifier")
