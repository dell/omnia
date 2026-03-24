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

"""FastAPI dependency providers for Catalog Roles API.

This module provides catalog-roles-specific dependencies like the
catalog roles service provider.
"""

from fastapi import Depends
from sqlalchemy.orm import Session

from api.dependencies import (
    get_db_session,
    _create_sql_stage_repo,
    _create_sql_job_repo,
    _get_container,
    _ENV,
)
from api.catalog_roles.service import CatalogRolesService


# ------------------------------------------------------------------
# Catalog-roles-specific dependency providers
# ------------------------------------------------------------------
def get_catalog_roles_service(
    db_session: Session = Depends(get_db_session),
) -> CatalogRolesService:
    """Provide catalog roles service with shared session in prod."""
    if _ENV == "prod":
        from infra.db.repositories import SqlArtifactMetadataRepository
        
        container = _get_container()
        return CatalogRolesService(
            artifact_store=container.artifact_store(),
            artifact_metadata_repo=SqlArtifactMetadataRepository(db_session),
            stage_repo=_create_sql_stage_repo(db_session),
            job_repo=_create_sql_job_repo(db_session),
        )
    return _get_container().catalog_roles_service() if hasattr(_get_container(), 'catalog_roles_service') else CatalogRolesService(
        artifact_store=_get_container().artifact_store(),
        artifact_metadata_repo=_get_container().artifact_metadata_repository(),
        stage_repo=_get_container().stage_repository(),
        job_repo=_get_container().job_repository(),
    )
