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

"""FastAPI routes for Images API (GET /api/v1/images)."""

from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException, status

from api.dependencies import verify_token, require_catalog_read
from api.images.dependencies import get_list_images_use_case
from api.images.schemas import ListImagesResponse, ErrorResponse
from api.logging_utils import log_secure_info
from core.image_group.value_objects import ImageGroupStatus

router = APIRouter(prefix="/images", tags=["Images"])


@router.get(
    "",
    response_model=ListImagesResponse,
    status_code=status.HTTP_200_OK,
    summary="List available Image Groups",
    description="Returns paginated Image Groups with constituent images.",
    responses={
        200: {"description": "Image groups listed", "model": ListImagesResponse},
        400: {"description": "Invalid query parameters", "model": ErrorResponse},
        401: {"description": "Unauthorized", "model": ErrorResponse},
        403: {"description": "Forbidden", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
def list_images(
    status_filter: Optional[str] = Query(
        default=None,
        alias="status",
        description="Filter by ImageGroup status. Use 'BUILT' for exact match or leave empty for all post-BUILT states (BUILT+).",
    ),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    token_data: dict = Depends(verify_token),
    _: dict = Depends(require_catalog_read),
    use_case=Depends(get_list_images_use_case),
) -> ListImagesResponse:
    """List available Image Groups with constituent images."""
    log_secure_info("info", "ListImages request received", token_data.get("client_id", ""))

    # Parse status filter - None means all post-BUILT states (cumulative)
    # If status_filter is "BUILT", treat it as cumulative query (BUILT+)
    parsed_status = None
    if status_filter:
        try:
            parsed_status = ImageGroupStatus(status_filter)
            # If querying for BUILT specifically, treat as cumulative query
            if parsed_status == ImageGroupStatus.BUILT:
                parsed_status = None
        except ValueError as exc:
            allowed = [s.value for s in ImageGroupStatus]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "INVALID_STATUS",
                    "message": (
                        f"Invalid status filter value '{status_filter}'. "
                        f"Allowed values: {', '.join(allowed)}"
                    ),
                },
            ) from exc

    try:
        result = use_case.execute(
            status=parsed_status,
            limit=limit,
            offset=offset,
        )
        return result
    except Exception as exc:
        log_secure_info("error", f"ListImages failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "INTERNAL_ERROR", "message": "Internal server error"},
        ) from exc
