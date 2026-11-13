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

# pylint: disable=C0413,C0411,W0621,C0415,W0105,R0913,R0917
# JSONB shim for SQLite compatibility - must precede app imports.
import sqlalchemy.dialects.sqlite.base as sqlite_base
from sqlalchemy import JSON
if not hasattr(sqlite_base, "JSONB"):
    sqlite_base.JSONB = JSON

# PyJWT compatibility shim, mirroring the Jobs API test fixtures.
import jwt.exceptions
for _name in ("ExpiredSignatureError", "InvalidAudienceError", "InvalidIssuerError",
              "InvalidSignatureError"):
    if not hasattr(jwt.exceptions, _name):
        setattr(jwt.exceptions, _name, type(_name, (jwt.exceptions.JWTException,), {}))
if not hasattr(jwt.exceptions, "DecodeError"):
    jwt.exceptions.DecodeError = jwt.exceptions.JWTDecodeError

"""Shared fixtures for the pipeline log query API tests (ER-BSM-003)."""

import os
import uuid
from pathlib import Path
from typing import Callable, Dict, Optional

import pytest
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.testclient import TestClient

os.environ.setdefault("ENV", "dev")

from main import app
from api.dependencies import get_audit_repo, get_job_repo, get_stage_repo, verify_token
from api.logs.dependencies import (
    get_concurrency_limiter,
    get_log_file_service,
    get_rate_limiter,
)
from api.logs.limiter import ConcurrencyLimiter, SlidingWindowRateLimiter
from core.jobs.entities.job import Job
from core.jobs.entities.stage import Stage
from core.jobs.value_objects import ClientId, JobId, StageName, StageState, StageType
from infra.logs.filesystem_adapter import FileSystemLogAdapter
from infra.repositories.in_memory import (
    InMemoryAuditEventRepository,
    InMemoryJobRepository,
    InMemoryStageRepository,
)

HOST_LOG_PREFIX = "/mnt/host_share/build_stream/log"

_bearer = HTTPBearer(auto_error=False)


def _mock_verify_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> dict:
    """Use the bearer value as the client_id."""
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "missing_token",
                "error_description": "Authorization header is required",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {
        "client_id": credentials.credentials,
        "client_name": credentials.credentials,
        "scopes": ["job:write", "job:read"],
        "token_id": "test-token-id",
    }


@pytest.fixture
def log_root(tmp_path) -> Path:
    """Container-side log root for the test."""
    root = tmp_path / "opt" / "omnia" / "build_stream" / "log"
    root.mkdir(parents=True)
    return root


@pytest.fixture
def rate_limit() -> Dict[str, int]:
    """Mutable rate limit used by the client fixture (tests may lower it)."""
    return {"per_minute": 60, "concurrent": 5}


@pytest.fixture
def job_repo() -> InMemoryJobRepository:
    """Per-test job repository (isolated from the shared container)."""
    return InMemoryJobRepository()


@pytest.fixture
def stage_repo() -> InMemoryStageRepository:
    """Per-test stage repository (isolated from the shared container)."""
    return InMemoryStageRepository()


@pytest.fixture
def client(log_root, rate_limit, job_repo, stage_repo):
    """TestClient with mocked auth, isolated repositories, a log root, and fresh limiters."""
    adapter = FileSystemLogAdapter(log_root)
    limiter = SlidingWindowRateLimiter(rate_limit["per_minute"])
    concurrency = ConcurrencyLimiter(rate_limit["concurrent"])
    audit_repo = InMemoryAuditEventRepository()
    app.dependency_overrides[verify_token] = _mock_verify_token
    app.dependency_overrides[get_job_repo] = lambda: job_repo
    app.dependency_overrides[get_stage_repo] = lambda: stage_repo
    app.dependency_overrides[get_audit_repo] = lambda: audit_repo
    app.dependency_overrides[get_log_file_service] = lambda: adapter
    app.dependency_overrides[get_rate_limiter] = lambda: limiter
    app.dependency_overrides[get_concurrency_limiter] = lambda: concurrency
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def unauth_client():
    """TestClient using the real JWT dependency."""
    return TestClient(app)


@pytest.fixture
def owner() -> str:
    """Unique client identifier that owns the test job."""
    return f"client-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def headers(owner) -> Dict[str, str]:
    """Authorization headers for the owning client."""
    return {"Authorization": f"Bearer {owner}"}


@pytest.fixture
def create_job(owner, job_repo, stage_repo) -> Callable[[], str]:
    """Create a job owned by ``owner`` with every stage PENDING and return its ID."""
    def _create() -> str:
        job_id = JobId(str(uuid.uuid4()))
        job_repo.save(Job(job_id=job_id, client_id=ClientId(owner), request_client_id=owner))
        stage_repo.save_all([
            Stage(job_id=job_id, stage_name=StageName(stage_type.value))
            for stage_type in StageType
        ])
        return str(job_id)
    return _create


@pytest.fixture
def publish_log(log_root, stage_repo) -> Callable[..., str]:
    """Write a stage log under the log root and mark the stage as completed with it."""
    def _publish(
        job_id: str,
        stage_name: str,
        content: Optional[str] = None,
        raw: Optional[bytes] = None,
        state: StageState = StageState.COMPLETED,
        stored_path: Optional[str] = None,
    ) -> str:
        file_name = f"{stage_name}_playbook.yml_20261113_101500_attempt1.log"
        if content is not None or raw is not None:
            job_dir = log_root / job_id
            job_dir.mkdir(exist_ok=True)
            target = job_dir / file_name
            if raw is not None:
                target.write_bytes(raw)
            else:
                target.write_text(content, encoding="utf-8")
        stage = stage_repo.find_by_job_and_name(JobId(job_id), StageName(stage_name))
        stage.stage_state = state
        stage.log_file_path = stored_path or f"{HOST_LOG_PREFIX}/{job_id}/{file_name}"
        stage_repo.save(stage)
        return file_name

    return _publish
