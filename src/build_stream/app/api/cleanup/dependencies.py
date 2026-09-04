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

"""FastAPI dependency providers for the CleanUp (hard delete) operation."""

from fastapi import Depends
from sqlalchemy.orm import Session

from api.dependencies import (
    _ENV,
    _create_sql_audit_repo,
    _create_sql_image_group_repo,
    _create_sql_image_repo,
    _create_sql_job_repo,
    _create_sql_stage_repo,
    _get_container,
    get_db_session,
)
from orchestrator.cleanup.use_cases.cleanup_job import CleanupJobUseCase


def get_cleanup_job_use_case(
    db_session: Session = Depends(get_db_session),
) -> CleanupJobUseCase:
    """Provide the CleanupJobUseCase wired to the appropriate repos.

    In ``prod`` mode (default) the use case operates on the SQL-backed
    repositories sharing the request-scoped session. In ``dev`` mode it
    falls back to the in-memory container singletons.

    Image cleanup is handled by submitting ``image_build_manager.yml
    --tags cleanup_images`` to the NFS playbook queue (replacing the
    earlier direct s3cmd subprocess approach).
    """
    container = _get_container()
    queue_service = container.playbook_queue_request_service()

    if _ENV == "prod":
        return CleanupJobUseCase(
            job_repo=_create_sql_job_repo(db_session),
            stage_repo=_create_sql_stage_repo(db_session),
            audit_repo=_create_sql_audit_repo(db_session),
            image_group_repo=_create_sql_image_group_repo(db_session),
            image_repo=_create_sql_image_repo(db_session),
            uuid_generator=container.uuid_generator(),
            queue_service=queue_service,
        )

    return CleanupJobUseCase(
        job_repo=container.job_repository(),
        stage_repo=container.stage_repository(),
        audit_repo=container.audit_repository(),
        image_group_repo=container.image_group_repository(),
        image_repo=container.image_repository(),
        uuid_generator=container.uuid_generator(),
        queue_service=queue_service,
    )
