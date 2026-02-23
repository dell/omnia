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

"""FastAPI dependency providers for ParseCatalog API.

This module provides parse-catalog-specific dependencies like the
parse catalog use case provider.
"""

from fastapi import Depends
from sqlalchemy.orm import Session

from api.dependencies import (
    get_db_session,
    _create_sql_job_repo,
    _create_sql_stage_repo,
    _create_sql_audit_repo,
    _get_container,
    _ENV,
)
from orchestrator.catalog.use_cases import ParseCatalogUseCase


# ------------------------------------------------------------------
# Parse-catalog-specific dependency providers
# ------------------------------------------------------------------
def get_parse_catalog_use_case(
    db_session: Session = Depends(get_db_session),
) -> ParseCatalogUseCase:
    """Provide parse-catalog use case with shared session in prod."""
    if _ENV == "prod":
        from infra.db.repositories import SqlArtifactMetadataRepository
        
        container = _get_container()
        return ParseCatalogUseCase(
            job_repo=_create_sql_job_repo(db_session),
            stage_repo=_create_sql_stage_repo(db_session),
            audit_repo=_create_sql_audit_repo(db_session),
            artifact_store=container.artifact_store(),
            artifact_metadata_repo=SqlArtifactMetadataRepository(db_session),
            uuid_generator=container.uuid_generator(),
        )
    return _get_container().parse_catalog_use_case()
