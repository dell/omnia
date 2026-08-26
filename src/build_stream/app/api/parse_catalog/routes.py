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

"""FastAPI routes for ParseCatalog API.

DEPRECATED (Omnia 2.3+): With domain segregation, the catalog is consumed
directly by each domain.  The parse-catalog stage has been retired.
This route is kept for backward compatibility and returns a deprecation notice.
"""

from fastapi import APIRouter, File, UploadFile, status
from fastapi.responses import JSONResponse

from api.logging_utils import log_secure_info

router = APIRouter(prefix="/jobs", tags=["Catalog Parsing (Deprecated)"])


@router.post(
    "/{job_id}/stages/parse-catalog",
    status_code=status.HTTP_410_GONE,
    summary="[DEPRECATED] Parse a catalog file",
    description=(
        "DEPRECATED in Omnia 2.3. With domain segregation, the catalog "
        "is consumed directly by each domain. This stage is no longer needed."
    ),
)
async def parse_catalog(
    job_id: str,
    file: UploadFile = File(None, description="Ignored — stage is deprecated"),
) -> JSONResponse:
    """[DEPRECATED] Parse-catalog stage — retired in Omnia 2.3.

    With domain segregation, the catalog is consumed directly by each domain
    (repo_manager, image_build_manager).  This endpoint is no longer functional
    and returns HTTP 410 Gone.

    Args:
        job_id: The job identifier (logged for traceability).
        file: Ignored.

    Returns:
        JSONResponse with deprecation notice (HTTP 410).
    """
    log_secure_info(
        "warning",
        f"Deprecated parse-catalog called: job_id={job_id}, returning 410 Gone",
        job_id=job_id,
        end_section=True,
    )
    return JSONResponse(
        status_code=status.HTTP_410_GONE,
        content={
            "error_code": "STAGE_RETIRED",
            "message": (
                "The parse-catalog stage has been retired in Omnia 2.3. "
                "With domain segregation, the catalog is consumed directly "
                "by each domain. Remove this stage from your pipeline."
            ),
            "job_id": job_id,
        },
    )
