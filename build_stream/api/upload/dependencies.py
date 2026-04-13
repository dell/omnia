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

"""FastAPI dependency providers for Upload API.

This module provides upload-specific dependencies like the
upload files use case provider.
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
from common.config import load_config
from core.artifacts.interfaces import ArtifactStore
from infra.artifact_store.file_artifact_store import FileArtifactStore
from infra.db.repositories import SqlArtifactMetadataRepository
from infra.id_generator import UUIDv4Generator
from orchestrator.upload.use_cases.upload_files import UploadFilesUseCase
from pathlib import Path


# ------------------------------------------------------------------
# Upload-specific dependency providers
# ------------------------------------------------------------------
def get_upload_files_use_case(
    db_session: Session = Depends(get_db_session),
) -> UploadFilesUseCase:
    """Provide upload files use case with shared session in prod."""
    if _ENV == "prod":
        container = _get_container()
        config = load_config()
        
        # Initialize FileArtifactStore with proper arguments
        base_path = Path(config.file_store.base_path) if config.file_store else Path("/opt/omnia/build_stream_root/artifacts")
        max_size = config.artifact_store.max_file_size_bytes if config.artifact_store else 5242880  # 5MB default
        
        return UploadFilesUseCase(
            job_repository=_create_sql_job_repo(db_session),
            stage_repository=_create_sql_stage_repo(db_session),
            audit_repository=_create_sql_audit_repo(db_session),
            artifact_store=FileArtifactStore(
                base_path=base_path,
                max_artifact_size_bytes=max_size,
            ),
            artifact_metadata_repo=SqlArtifactMetadataRepository(db_session),
            uuid_generator=UUIDv4Generator(),
            config=config,
        )
    return _get_container().upload_files_use_case()
