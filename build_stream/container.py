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

"""Dependency Injector containers for the Jobs API."""
# pylint: disable=c-extension-no-member

import os

from dependency_injector import containers, providers

from infra.id_generator import JobUUIDGenerator, UUIDv4Generator
from infra.repositories import (
    InMemoryJobRepository,
    InMemoryStageRepository,
    InMemoryIdempotencyRepository,
    InMemoryAuditEventRepository,
)
from orchestrator.jobs.use_cases import CreateJobUseCase


class DevContainer(containers.DeclarativeContainer):  # pylint: disable=R0903
    """Development profile container.
    
    Uses in-memory mock repositories for fast development and testing.
    No external dependencies (database, S3, etc.) required.
    
    Activated when ENV=dev (default).
    """

    # Don't wire at module level to avoid circular imports
    # wiring_config will be set later in main.py

    job_id_generator = providers.Singleton(JobUUIDGenerator)
    uuid_generator = providers.Singleton(UUIDv4Generator)

    job_repository = providers.Singleton(InMemoryJobRepository)

    stage_repository = providers.Singleton(InMemoryStageRepository)

    idempotency_repository = providers.Singleton(InMemoryIdempotencyRepository)

    audit_repository = providers.Singleton(InMemoryAuditEventRepository)

    create_job_use_case = providers.Factory(
        CreateJobUseCase,
        job_repo=job_repository,
        stage_repo=stage_repository,
        idempotency_repo=idempotency_repository,
        audit_repo=audit_repository,
        job_id_generator=job_id_generator,
        uuid_generator=uuid_generator,
    )


class ProdContainer(containers.DeclarativeContainer):  # pylint: disable=R0903
    """Production profile container.
    
    Currently uses mock repositories (same as dev).
    TODO: Replace with PostgreSQL repositories when SQL implementation is ready.

    Activated when ENV=prod.
    """

    # Don't wire at module level to avoid circular imports
    # wiring_config will be set later in main.py

    job_id_generator = providers.Singleton(JobUUIDGenerator)
    uuid_generator = providers.Singleton(UUIDv4Generator)

    job_repository = providers.Singleton(InMemoryJobRepository)

    stage_repository = providers.Singleton(InMemoryStageRepository)

    idempotency_repository = providers.Singleton(InMemoryIdempotencyRepository)

    audit_repository = providers.Singleton(InMemoryAuditEventRepository)

    create_job_use_case = providers.Factory(
        CreateJobUseCase,
        job_repo=job_repository,
        stage_repo=stage_repository,
        idempotency_repo=idempotency_repository,
        audit_repo=audit_repository,
        job_id_generator=job_id_generator,
        uuid_generator=uuid_generator,
    )


def get_container_class():
    """Select container class based on ENV environment variable.
    
    Returns:
        DevContainer if ENV=dev (default)
        ProdContainer if ENV=prod
    
    Usage:
        # Set environment variable before running
        ENV=prod python main.py
        
        # Or set in code before importing
        os.environ['ENV'] = 'prod'
        
        # Or set in shell
        export ENV=prod
        python main.py
        
        # Windows PowerShell
        $env:ENV = "prod"
        python main.py
        
        # Windows Command Prompt
        set ENV=prod
        python main.py
    """
    env = os.getenv("ENV", "dev").lower()

    if env == "prod":
        return ProdContainer

    return DevContainer


Container = get_container_class()

# Singleton container instance shared across app and dependencies
container = Container()

__all__ = ["Container", "container", "get_container_class"]
