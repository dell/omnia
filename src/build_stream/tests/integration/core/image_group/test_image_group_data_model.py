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

"""Integration tests for ImageGroup/Image data model with SQLite.

Tests the full ORM model → SQL repository → domain entity round-trip
using an in-memory SQLite database.
"""

import os
import sys
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, event, JSON
from sqlalchemy.orm import sessionmaker

# Patch JSONB before model imports
if 'sqlalchemy.dialects.postgresql' not in sys.modules:
    _postgresql_module = type(sys)('postgresql')
    sys.modules['sqlalchemy.dialects.postgresql'] = _postgresql_module
sys.modules['sqlalchemy.dialects.postgresql'].JSONB = JSON

from build_stream.infra.db.models import (
    Base,
    JobModel,
    ImageGroupModel,
    ImageModel,
    StageModel,
)
from build_stream.infra.db.repositories import (
    SqlImageGroupRepository,
    SqlImageRepository,
    SqlJobRepository,
)
from build_stream.infra.db.mappers import ImageGroupMapper, ImageMapper
from build_stream.core.image_group.entities import ImageGroup, Image
from build_stream.core.image_group.value_objects import (
    ImageGroupId,
    ImageGroupStatus,
)
from build_stream.core.jobs.value_objects import JobId, JobState, ClientId
from build_stream.core.jobs.entities.job import Job


@pytest.fixture
def engine():
    """Create SQLite in-memory engine with foreign keys enabled."""
    eng = create_engine("sqlite:///:memory:", echo=False)

    @event.listens_for(eng, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(eng)
    return eng


@pytest.fixture
def session(engine):
    """Create a database session."""
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _create_job(session, job_id_str: str = None) -> str:
    """Create a prerequisite job in the database."""
    job_id_str = job_id_str or str(uuid.uuid4())
    job_model = JobModel(
        job_id=job_id_str,
        client_id="test-client",
        request_client_id="test-client",
        client_name="Test Client",
        job_state="CREATED",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        version=1,
        tombstoned=False,
    )
    session.add(job_model)
    session.flush()
    return job_id_str


class TestImageGroupModelORM:
    """Integration tests for ImageGroupModel ORM."""

    def test_create_image_group(self, session):
        """Should create an image_groups record linked to a job."""
        job_id = _create_job(session)
        ig_model = ImageGroupModel(
            id="omnia-cluster-v1",
            job_id=job_id,
            status="BUILT",
        )
        session.add(ig_model)
        session.flush()

        result = session.get(ImageGroupModel, "omnia-cluster-v1")
        assert result is not None
        assert result.job_id == job_id
        assert result.status == "BUILT"

    def test_image_group_job_relationship(self, session):
        """ImageGroupModel should have a navigable job relationship."""
        job_id = _create_job(session)
        ig_model = ImageGroupModel(
            id="test-group",
            job_id=job_id,
            status="BUILT",
        )
        session.add(ig_model)
        session.flush()
        session.expire_all()

        result = session.get(ImageGroupModel, "test-group")
        assert result.job is not None
        assert result.job.job_id == job_id

    def test_job_image_group_relationship(self, session):
        """JobModel should have a navigable image_group 1:1 relationship."""
        job_id = _create_job(session)
        ig_model = ImageGroupModel(
            id="test-group",
            job_id=job_id,
            status="BUILT",
        )
        session.add(ig_model)
        session.flush()
        session.expire_all()

        job = session.get(JobModel, job_id)
        assert job.image_group is not None
        assert job.image_group.id == "test-group"

    def test_unique_job_id_constraint(self, session):
        """Two ImageGroups with same job_id should violate UNIQUE constraint."""
        job_id = _create_job(session)
        ig1 = ImageGroupModel(id="group-1", job_id=job_id, status="BUILT")
        session.add(ig1)
        session.flush()

        ig2 = ImageGroupModel(id="group-2", job_id=job_id, status="BUILT")
        session.add(ig2)
        with pytest.raises(Exception):  # IntegrityError
            session.flush()
        session.rollback()

    def test_cascade_delete_from_job(self, session):
        """Deleting a job should cascade-delete its image_group."""
        job_id = _create_job(session)
        ig = ImageGroupModel(id="cascade-group", job_id=job_id, status="BUILT")
        session.add(ig)
        session.flush()

        job = session.get(JobModel, job_id)
        session.delete(job)
        session.flush()

        result = session.get(ImageGroupModel, "cascade-group")
        assert result is None


class TestImageModelORM:
    """Integration tests for ImageModel ORM."""

    def test_create_image(self, session):
        """Should create an images record linked to an image_group."""
        job_id = _create_job(session)
        session.add(ImageGroupModel(id="img-group", job_id=job_id, status="BUILT"))
        session.flush()

        img_id = str(uuid.uuid4())
        img = ImageModel(
            id=img_id,
            image_group_id="img-group",
            role="slurm_node",
            image_name="slurm_node.img",
        )
        session.add(img)
        session.flush()

        result = session.get(ImageModel, img_id)
        assert result is not None
        assert result.role == "slurm_node"
        assert result.image_group_id == "img-group"

    def test_image_group_images_relationship(self, session):
        """ImageGroupModel.images should contain linked images."""
        job_id = _create_job(session)
        ig = ImageGroupModel(id="group-with-imgs", job_id=job_id, status="BUILT")
        session.add(ig)
        session.flush()

        for role in ["slurm_node", "kube_node", "login_node"]:
            session.add(ImageModel(
                id=str(uuid.uuid4()),
                image_group_id="group-with-imgs",
                role=role,
                image_name=f"{role}.img",
            ))
        session.flush()
        session.expire_all()

        result = session.get(ImageGroupModel, "group-with-imgs")
        assert len(result.images) == 3
        roles = {img.role for img in result.images}
        assert roles == {"slurm_node", "kube_node", "login_node"}

    def test_unique_role_per_group_constraint(self, session):
        """Two images with same (image_group_id, role) should violate UNIQUE."""
        job_id = _create_job(session)
        session.add(ImageGroupModel(id="dup-role-group", job_id=job_id, status="BUILT"))
        session.flush()

        session.add(ImageModel(
            id=str(uuid.uuid4()),
            image_group_id="dup-role-group",
            role="slurm_node",
            image_name="slurm_node_v1.img",
        ))
        session.flush()

        session.add(ImageModel(
            id=str(uuid.uuid4()),
            image_group_id="dup-role-group",
            role="slurm_node",
            image_name="slurm_node_v2.img",
        ))
        with pytest.raises(Exception):  # IntegrityError
            session.flush()
        session.rollback()

    def test_cascade_delete_images_from_group(self, session):
        """Deleting an image_group should cascade-delete its images."""
        job_id = _create_job(session)
        ig = ImageGroupModel(id="cascade-ig", job_id=job_id, status="BUILT")
        session.add(ig)
        session.flush()

        img_id = str(uuid.uuid4())
        session.add(ImageModel(
            id=img_id,
            image_group_id="cascade-ig",
            role="node",
            image_name="node.img",
        ))
        session.flush()

        session.delete(ig)
        session.flush()
        assert session.get(ImageModel, img_id) is None


class TestSqlImageGroupRepository:
    """Integration tests for SqlImageGroupRepository."""

    def test_save_and_find_by_id(self, session):
        """Save then find by ID should return the domain entity."""
        job_id = _create_job(session)
        repo = SqlImageGroupRepository(session)

        ig = ImageGroup(
            id=ImageGroupId("repo-test-group"),
            job_id=JobId(job_id),
            status=ImageGroupStatus.BUILT,
        )
        repo.save(ig)

        found = repo.find_by_id(ImageGroupId("repo-test-group"))
        assert found is not None
        assert found.id.value == "repo-test-group"
        assert found.status == ImageGroupStatus.BUILT

    def test_find_by_job_id(self, session):
        """find_by_job_id should return the correct ImageGroup."""
        job_id = _create_job(session)
        repo = SqlImageGroupRepository(session)

        ig = ImageGroup(
            id=ImageGroupId("job-lookup-group"),
            job_id=JobId(job_id),
            status=ImageGroupStatus.BUILT,
        )
        repo.save(ig)

        found = repo.find_by_job_id(JobId(job_id))
        assert found is not None
        assert found.id.value == "job-lookup-group"

    def test_update_status(self, session):
        """update_status should change the status."""
        job_id = _create_job(session)
        repo = SqlImageGroupRepository(session)

        ig = ImageGroup(
            id=ImageGroupId("status-update-group"),
            job_id=JobId(job_id),
            status=ImageGroupStatus.BUILT,
        )
        repo.save(ig)

        repo.update_status(
            ImageGroupId("status-update-group"),
            ImageGroupStatus.DEPLOYING,
        )

        updated = repo.find_by_id(ImageGroupId("status-update-group"))
        assert updated.status == ImageGroupStatus.DEPLOYING

    def test_list_by_status(self, session):
        """list_by_status should filter and paginate."""
        repo = SqlImageGroupRepository(session)
        for i in range(3):
            job_id = _create_job(session)
            repo.save(ImageGroup(
                id=ImageGroupId(f"list-group-{i}"),
                job_id=JobId(job_id),
                status=ImageGroupStatus.BUILT,
            ))

        results, total = repo.list_by_status(ImageGroupStatus.BUILT, limit=10, offset=0)
        assert total == 3
        assert len(results) == 3

    def test_list_by_status_pagination(self, session):
        """list_by_status should respect limit and offset."""
        repo = SqlImageGroupRepository(session)
        for i in range(5):
            job_id = _create_job(session)
            repo.save(ImageGroup(
                id=ImageGroupId(f"page-group-{i}"),
                job_id=JobId(job_id),
                status=ImageGroupStatus.BUILT,
            ))

        page, total = repo.list_by_status(ImageGroupStatus.BUILT, limit=2, offset=0)
        assert total == 5
        assert len(page) == 2

    def test_exists(self, session):
        """exists() should return True for saved, False for non-existent."""
        job_id = _create_job(session)
        repo = SqlImageGroupRepository(session)

        repo.save(ImageGroup(
            id=ImageGroupId("exists-group"),
            job_id=JobId(job_id),
            status=ImageGroupStatus.BUILT,
        ))

        assert repo.exists(ImageGroupId("exists-group")) is True
        assert repo.exists(ImageGroupId("not-here")) is False

    def test_find_by_id_not_found(self, session):
        """find_by_id should return None for non-existent."""
        repo = SqlImageGroupRepository(session)
        result = repo.find_by_id(ImageGroupId("nonexistent"))
        assert result is None


class TestSqlImageRepository:
    """Integration tests for SqlImageRepository."""

    def test_save_batch_and_find(self, session):
        """save_batch and find_by_image_group_id should round-trip."""
        job_id = _create_job(session)
        session.add(ImageGroupModel(id="batch-group", job_id=job_id, status="BUILT"))
        session.flush()

        repo = SqlImageRepository(session)
        images = [
            Image(
                id=str(uuid.uuid4()),
                image_group_id="batch-group",
                role="slurm_node",
                image_name="slurm_node.img",
            ),
            Image(
                id=str(uuid.uuid4()),
                image_group_id="batch-group",
                role="kube_node",
                image_name="kube_node.img",
            ),
        ]
        repo.save_batch(images)

        found = repo.find_by_image_group_id(ImageGroupId("batch-group"))
        assert len(found) == 2
        roles = {img.role for img in found}
        assert roles == {"slurm_node", "kube_node"}

    def test_find_empty(self, session):
        """find_by_image_group_id should return empty list for no images."""
        repo = SqlImageRepository(session)
        found = repo.find_by_image_group_id(ImageGroupId("no-images"))
        assert found == []


class TestImageGroupMapper:
    """Tests for ImageGroupMapper domain↔ORM conversion."""

    def test_to_orm_and_back(self, session):
        """Round-trip through to_orm and to_domain should preserve data."""
        job_id = _create_job(session)
        ig = ImageGroup(
            id=ImageGroupId("mapper-test"),
            job_id=JobId(job_id),
            status=ImageGroupStatus.DEPLOYED,
        )
        orm_model = ImageGroupMapper.to_orm(ig)
        assert orm_model.id == "mapper-test"
        assert orm_model.job_id == job_id
        assert orm_model.status == "DEPLOYED"

        # Persist and reload to get full ORM with relationships
        session.add(orm_model)
        session.flush()
        session.expire_all()
        reloaded = session.get(ImageGroupModel, "mapper-test")

        domain_entity = ImageGroupMapper.to_domain(reloaded)
        assert domain_entity.id.value == "mapper-test"
        assert str(domain_entity.job_id) == job_id
        assert domain_entity.status == ImageGroupStatus.DEPLOYED


class TestStageModelResultDetail:
    """Tests for StageModel.result_detail column."""

    def test_result_detail_nullable(self, session):
        """result_detail should be nullable by default."""
        job_id = _create_job(session)
        stage = StageModel(
            job_id=job_id,
            stage_name="parse-catalog",
            stage_state="PENDING",
            attempt=1,
            version=1,
        )
        session.add(stage)
        session.flush()

        result = session.query(StageModel).filter_by(
            job_id=job_id, stage_name="parse-catalog"
        ).one()
        assert result.result_detail is None

    def test_result_detail_stores_json(self, session):
        """result_detail should store structured JSON data."""
        job_id = _create_job(session)
        detail = {
            "outcome": "PASSED",
            "total_tests": 10,
            "passed": 9,
            "failed": 1,
            "failure_details": [{"test": "test_x", "reason": "timeout"}],
        }
        stage = StageModel(
            job_id=job_id,
            stage_name="validate",
            stage_state="COMPLETED",
            attempt=1,
            version=1,
            result_detail=detail,
        )
        session.add(stage)
        session.flush()

        result = session.query(StageModel).filter_by(
            job_id=job_id, stage_name="validate"
        ).one()
        assert result.result_detail["outcome"] == "PASSED"
        assert result.result_detail["total_tests"] == 10


class TestJobModelPipelinePhase:
    """Tests for JobModel.pipeline_phase column."""

    def test_pipeline_phase_nullable(self, session):
        """pipeline_phase should be nullable (NULL for direct invocation)."""
        job_id = _create_job(session)
        job = session.get(JobModel, job_id)
        assert job.pipeline_phase is None

    def test_pipeline_phase_build(self, session):
        """pipeline_phase should accept BUILD value."""
        job_id = str(uuid.uuid4())
        job = JobModel(
            job_id=job_id,
            client_id="test",
            request_client_id="test",
            job_state="CREATED",
            pipeline_phase="BUILD",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            version=1,
            tombstoned=False,
        )
        session.add(job)
        session.flush()

        result = session.get(JobModel, job_id)
        assert result.pipeline_phase == "BUILD"

    def test_pipeline_phase_deploy(self, session):
        """pipeline_phase should accept DEPLOY value."""
        job_id = str(uuid.uuid4())
        job = JobModel(
            job_id=job_id,
            client_id="test",
            request_client_id="test",
            job_state="CREATED",
            pipeline_phase="DEPLOY",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            version=1,
            tombstoned=False,
        )
        session.add(job)
        session.flush()

        result = session.get(JobModel, job_id)
        assert result.pipeline_phase == "DEPLOY"
