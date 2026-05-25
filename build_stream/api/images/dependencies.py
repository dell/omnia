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

"""FastAPI dependency providers for Images API."""

from sqlalchemy.orm import Session
from fastapi import Depends

from api.dependencies import (
    get_db_session,
    _create_sql_image_group_repo,
    _get_container,
    _ENV,
)
from orchestrator.images.use_cases.list_images_use_case import ListImagesUseCase


def get_list_images_use_case(
    db_session: Session = Depends(get_db_session),
) -> ListImagesUseCase:
    """Provide ListImagesUseCase with appropriate repository."""
    if _ENV == "prod":
        return ListImagesUseCase(
            image_group_repo=_create_sql_image_group_repo(db_session),
        )
    return _get_container().list_images_use_case()
