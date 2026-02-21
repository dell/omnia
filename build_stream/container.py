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

"""Dependency Injector containers for the Build Stream API."""
# pylint: disable=c-extension-no-member

import os
from pathlib import Path

from dependency_injector import containers, providers

from infra.artifact_store.in_memory_artifact_store import InMemoryArtifactStore
from infra.artifact_store.in_memory_artifact_metadata import (
    InMemoryArtifactMetadataRepository,
)
from infra.artifact_store.file_artifact_store import FileArtifactStore
from infra.id_generator import JobUUIDGenerator, UUIDv4Generator
from infra.repositories import (
    InMemoryJobRepository,
    InMemoryStageRepository,
    InMemoryIdempotencyRepository,
    InMemoryAuditEventRepository,
    NfsInputRepository,
    NfsPlaybookQueueRequestRepository,
    NfsPlaybookQueueResultRepository,
)
from orchestrator.catalog.use_cases.generate_input_files import GenerateInputFilesUseCase
from orchestrator.catalog.use_cases.parse_catalog import ParseCatalogUseCase
from orchestrator.jobs.use_cases import CreateJobUseCase
from orchestrator.local_repo.use_cases import CreateLocalRepoUseCase
from orchestrator.local_repo.result_poller import LocalRepoResultPoller
from orchestrator.build_image.use_cases import CreateBuildImageUseCase

from core.localrepo.services import (
    InputFileService,
    PlaybookQueueRequestService,
    PlaybookQueueResultService,
)
from core.build_image.services import (
    BuildImageConfigService,
)
from core.catalog.adapter_policy import _DEFAULT_POLICY_PATH, _DEFAULT_SCHEMA_PATH
from core.artifacts.value_objects import SafePath
from common.config import load_config


def _create_artifact_store():
    """Factory function to create artifact store based on configuration.

    Returns:
        InMemoryArtifactStore or FileArtifactStore based on config.
    """
    try:
        config = load_config()

        # Check backend setting
        if config.artifact_store.backend == "file_store" and config.file_store is not None:
            base_path = Path(config.file_store.base_path)
            return FileArtifactStore(
                base_path=base_path,
                max_artifact_size_bytes=config.artifact_store.max_file_size_bytes,
            )

        if config.artifact_store.backend == "memory_store":
            return InMemoryArtifactStore(
                max_artifact_size_bytes=config.artifact_store.max_file_size_bytes,
            )

        # Fall back to file store with default path
        return FileArtifactStore(
            base_path=Path("/opt/omnia/build_stream/artifacts"),
            max_artifact_size_bytes=config.artifact_store.max_file_size_bytes,
        )
    except (FileNotFoundError, ValueError):
        # If config not found or invalid, use file store with defaults as fallback
        return FileArtifactStore(
            base_path=Path("/opt/omnia/build_stream/artifacts"),
            max_artifact_size_bytes=5242880,  # 5MB default
        )

_RESOURCES_DIR = Path(__file__).resolve().parent / "core" / "catalog" / "resources"
_DEFAULT_POLICY_PATH = _RESOURCES_DIR / "adapter_policy_default.json"
_DEFAULT_SCHEMA_PATH = _RESOURCES_DIR / "AdapterPolicySchema.json"


class DevContainer(containers.DeclarativeContainer):  # pylint: disable=R0903
    """Development profile container.

    Uses in-memory mock repositories for fast development and testing.
    No external dependencies (database, S3, etc.) required.

    Activated when ENV=dev (default).
    """

    wiring_config = containers.WiringConfiguration(
        modules=[
            "api.jobs.routes",
            "api.jobs.dependencies",
            "api.local_repo.routes",
            "api.local_repo.dependencies",
            "api.build_image.routes",
            "api.build_image.dependencies",
        ]
    )

    job_id_generator = providers.Singleton(JobUUIDGenerator)
    uuid_generator = providers.Singleton(UUIDv4Generator)


    default_policy_path = providers.Singleton(
        SafePath,
        value=_DEFAULT_POLICY_PATH,
    )

    policy_schema_path = providers.Singleton(
        SafePath,
        value=_DEFAULT_SCHEMA_PATH,
    )

    # --- Jobs repositories ---
    job_repository = providers.Singleton(InMemoryJobRepository)
    stage_repository = providers.Singleton(InMemoryStageRepository)
    idempotency_repository = providers.Singleton(InMemoryIdempotencyRepository)
    audit_repository = providers.Singleton(InMemoryAuditEventRepository)

    # --- input repository ---
    input_repository = providers.Singleton(
        NfsInputRepository,
    )

    # --- Queue repositories ---
    playbook_queue_request_repository = providers.Singleton(
        NfsPlaybookQueueRequestRepository,
    )

    playbook_queue_result_repository = providers.Singleton(
        NfsPlaybookQueueResultRepository,
    )

    # --- Local repo services ---
    input_file_service = providers.Factory(
        InputFileService,
        input_repo=input_repository,
    )

    # --- Build image services ---
    build_image_config_service = providers.Factory(
        BuildImageConfigService,
        config_repo=input_repository,
    )

    playbook_queue_request_service = providers.Factory(
        PlaybookQueueRequestService,
        request_repo=playbook_queue_request_repository,
    )

    playbook_queue_result_service = providers.Factory(
        PlaybookQueueResultService,
        result_repo=playbook_queue_result_repository,
    )

    # --- Result poller ---
    result_poller = providers.Singleton(
        LocalRepoResultPoller,
        result_service=playbook_queue_result_service,
        stage_repo=stage_repository,
        audit_repo=audit_repository,
        uuid_generator=uuid_generator,
        poll_interval=int(os.getenv("RESULT_POLL_INTERVAL", "5")),
    )

    # --- Use cases ---
    artifact_store = providers.Singleton(_create_artifact_store)

    artifact_metadata_repository = providers.Singleton(
        InMemoryArtifactMetadataRepository,
    )

    create_job_use_case = providers.Factory(
        CreateJobUseCase,
        job_repo=job_repository,
        stage_repo=stage_repository,
        idempotency_repo=idempotency_repository,
        audit_repo=audit_repository,
        job_id_generator=job_id_generator,
        uuid_generator=uuid_generator,
    )

    create_local_repo_use_case = providers.Factory(
        CreateLocalRepoUseCase,
        job_repo=job_repository,
        stage_repo=stage_repository,
        audit_repo=audit_repository,
        input_file_service=input_file_service,
        playbook_queue_service=playbook_queue_request_service,
        uuid_generator=uuid_generator,
    )

    parse_catalog_use_case = providers.Factory(
        ParseCatalogUseCase,
        job_repo=job_repository,
        stage_repo=stage_repository,
        audit_repo=audit_repository,
        artifact_store=artifact_store,
        artifact_metadata_repo=artifact_metadata_repository,
        uuid_generator=uuid_generator,
    )

    generate_input_files_use_case = providers.Factory(
        GenerateInputFilesUseCase,
        job_repo=job_repository,
        stage_repo=stage_repository,
        audit_repo=audit_repository,
        artifact_store=artifact_store,
        artifact_metadata_repo=artifact_metadata_repository,
        uuid_generator=uuid_generator,
        default_policy_path=default_policy_path,
        policy_schema_path=policy_schema_path,
    )
    
    create_build_image_use_case = providers.Factory(
        CreateBuildImageUseCase,
        job_repo=job_repository,
        stage_repo=stage_repository,
        audit_repo=audit_repository,
        config_service=build_image_config_service,
        queue_service=playbook_queue_request_service,
        inventory_repo=input_repository,
        uuid_generator=uuid_generator,
    )


class ProdContainer(containers.DeclarativeContainer):  # pylint: disable=R0903
    """Production profile container.

    Currently uses mock repositories (same as dev).
    TODO: Replace with PostgreSQL repositories when SQL implementation is ready.

    Activated when ENV=prod.
    """

    wiring_config = containers.WiringConfiguration(
        modules=[
            "api.jobs.routes",
            "api.jobs.dependencies",
            "api.local_repo.routes",
            "api.local_repo.dependencies",
            "api.build_image.routes",
            "api.build_image.dependencies",
        ]
    )

    job_id_generator = providers.Singleton(JobUUIDGenerator)
    uuid_generator = providers.Singleton(UUIDv4Generator)


    default_policy_path = providers.Singleton(
        SafePath,
        value=_DEFAULT_POLICY_PATH,
    )

    policy_schema_path = providers.Singleton(
        SafePath,
        value=_DEFAULT_SCHEMA_PATH,
    )

    # --- Jobs repositories ---
    job_repository = providers.Singleton(InMemoryJobRepository)
    stage_repository = providers.Singleton(InMemoryStageRepository)
    idempotency_repository = providers.Singleton(InMemoryIdempotencyRepository)
    audit_repository = providers.Singleton(InMemoryAuditEventRepository)

    # --- Consolidated input repository ---
    input_repository = providers.Singleton(
        NfsInputRepository,
    )

    # --- Queue repositories ---
    playbook_queue_request_repository = providers.Singleton(
        NfsPlaybookQueueRequestRepository,
    )

    playbook_queue_result_repository = providers.Singleton(
        NfsPlaybookQueueResultRepository,
    )

    # --- Local repo services ---
    input_file_service = providers.Factory(
        InputFileService,
        input_repo=input_repository,
    )

    playbook_queue_request_service = providers.Factory(
        PlaybookQueueRequestService,
        request_repo=playbook_queue_request_repository,
    )

    playbook_queue_result_service = providers.Factory(
        PlaybookQueueResultService,
        result_repo=playbook_queue_result_repository,
    )
    # --- Build image services ---
    build_image_config_service = providers.Factory(
        BuildImageConfigService,
        config_repo=input_repository,
    )


    # --- Result poller ---
    result_poller = providers.Singleton(
        LocalRepoResultPoller,
        result_service=playbook_queue_result_service,
        stage_repo=stage_repository,
        audit_repo=audit_repository,
        uuid_generator=uuid_generator,
        poll_interval=int(os.getenv("RESULT_POLL_INTERVAL", "5")),
    )

    # --- Use cases ---
    artifact_store = providers.Singleton(_create_artifact_store)

    artifact_metadata_repository = providers.Singleton(
        InMemoryArtifactMetadataRepository,
    )

    create_job_use_case = providers.Factory(
        CreateJobUseCase,
        job_repo=job_repository,
        stage_repo=stage_repository,
        idempotency_repo=idempotency_repository,
        audit_repo=audit_repository,
        job_id_generator=job_id_generator,
        uuid_generator=uuid_generator,
    )

    create_local_repo_use_case = providers.Factory(
        CreateLocalRepoUseCase,
        job_repo=job_repository,
        stage_repo=stage_repository,
        audit_repo=audit_repository,
        input_file_service=input_file_service,
        playbook_queue_service=playbook_queue_request_service,
        uuid_generator=uuid_generator,
    )

    parse_catalog_use_case = providers.Factory(
        ParseCatalogUseCase,
        job_repo=job_repository,
        stage_repo=stage_repository,
        audit_repo=audit_repository,
        artifact_store=artifact_store,
        artifact_metadata_repo=artifact_metadata_repository,
        uuid_generator=uuid_generator,
    )
    create_build_image_use_case = providers.Factory(
        CreateBuildImageUseCase,
        job_repo=job_repository,
        stage_repo=stage_repository,
        audit_repo=audit_repository,
        config_service=build_image_config_service,
        queue_service=playbook_queue_request_service,
        inventory_repo=input_repository,
        uuid_generator=uuid_generator,
    )


    generate_input_files_use_case = providers.Factory(
        GenerateInputFilesUseCase,
        job_repo=job_repository,
        stage_repo=stage_repository,
        audit_repo=audit_repository,
        artifact_store=artifact_store,
        artifact_metadata_repo=artifact_metadata_repository,
        uuid_generator=uuid_generator,
        default_policy_path=default_policy_path,
        policy_schema_path=policy_schema_path,
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
