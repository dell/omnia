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

"""FastAPI dependency providers for Local Repository API."""

from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from api.dependencies import (
    get_db_session,
    _create_sql_job_repo,
    _create_sql_stage_repo,
    _create_sql_audit_repo,
    _get_container,
    _ENV,
    verify_token,
)
from core.jobs.value_objects import ClientId, CorrelationId
from orchestrator.local_repo.use_cases import CreateLocalRepoUseCase


def _get_container():
    """Lazy import of container to avoid circular imports."""
    from container import container  # pylint: disable=import-outside-toplevel
    return container


def get_create_local_repo_use_case(
    db_session: Session = Depends(get_db_session),
) -> CreateLocalRepoUseCase:
    """Provide create local repo use case with shared session in prod."""
    if _ENV == "prod":
        container = _get_container()
        return CreateLocalRepoUseCase(
            job_repo=_create_sql_job_repo(db_session),
            stage_repo=_create_sql_stage_repo(db_session),
            audit_repo=_create_sql_audit_repo(db_session),
            input_file_service=container.input_file_service(),
            playbook_queue_service=container.playbook_queue_request_service(),
            uuid_generator=container.uuid_generator(),
        )
    return _get_container().create_local_repo_use_case()


def get_local_repo_correlation_id(
    x_correlation_id: Optional[str] = Header(
        default=None,
        alias="X-Correlation-Id",
        description="Request tracing ID",
    ),
) -> CorrelationId:
    """Return provided correlation ID or generate one."""
    generator = _get_container().uuid_generator()
    if x_correlation_id:
        try:
            return CorrelationId(x_correlation_id)
        except ValueError:
            pass

    generated_id = generator.generate()
    return CorrelationId(str(generated_id))
