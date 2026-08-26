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

"""FastAPI routes for GenerateInputFiles API.

DEPRECATED (Omnia 2.3+): With domain segregation, input files are
domain-specific and placed directly by domain-init.sh or the GitLab
CI pipeline.  The generate-input-files stage has been retired.
This route is kept for backward compatibility and returns a deprecation notice.
"""

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from api.logging_utils import log_secure_info

router = APIRouter(prefix="/jobs", tags=["Input File Generation (Deprecated)"])


@router.post(
    "/{job_id}/stages/generate-input-files",
    status_code=status.HTTP_410_GONE,
    summary="[DEPRECATED] Generate input files from parsed catalog",
    description=(
        "DEPRECATED in Omnia 2.3. With domain segregation, input files are "
        "domain-specific and managed by each domain's domain-init.sh or the "
        "GitLab CI pipeline. This stage is no longer needed."
    ),
)
async def generate_input_files(
    job_id: str,
) -> JSONResponse:
    """[DEPRECATED] Generate-input-files stage — retired in Omnia 2.3.

    With domain segregation, input files are domain-specific and placed
    directly by domain-init.sh or the GitLab CI pipeline.  There is no
    longer a need for central input file generation from the catalog.

    Args:
        job_id: The job identifier (logged for traceability).

    Returns:
        JSONResponse with deprecation notice (HTTP 410).
    """
    log_secure_info(
        "warning",
        f"Deprecated generate-input-files called: job_id={job_id}, returning 410 Gone",
        job_id=job_id,
        end_section=True,
    )
    return JSONResponse(
        status_code=status.HTTP_410_GONE,
        content={
            "error_code": "STAGE_RETIRED",
            "message": (
                "The generate-input-files stage has been retired in Omnia 2.3. "
                "With domain segregation, input files are domain-specific and "
                "managed by domain-init.sh or the GitLab CI pipeline. "
                "Remove this stage from your pipeline."
            ),
            "job_id": job_id,
        },
    )
