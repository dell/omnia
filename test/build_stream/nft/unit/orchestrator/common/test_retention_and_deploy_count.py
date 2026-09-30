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

# pylint: disable=C0302,C0415,R0903,R0914,W0212,W0613,W0621

"""Unit tests for ER-BSM-002 Story 4: deploy_count increment and retention.

Covers:
- deploy_count increment on deploy success (_on_deploy_success)
- MockImageGroupRepo.increment_deploy_count
- Retention config loading
- Retention evaluation in cleanup_cron
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from core.image_group.entities import ImageGroup
from core.image_group.value_objects import ImageGroupId, ImageGroupStatus
from core.jobs.entities import Stage
from core.jobs.value_objects import (
    JobId,
    StageName,
    StageState,
)
from core.localrepo.entities import PlaybookResult
from orchestrator.common.result_poller import ResultPoller


# --- Mock dependencies ---

class MockResultService:
    def __init__(self):
        self.callback = None
        self.results_to_deliver = []

    def poll_results(self, callback):
        self.callback = callback
        count = 0
        for result in self.results_to_deliver:
            callback(result)
            count += 1
        self.results_to_deliver = []
        return count


class MockStageRepo:
    def __init__(self):
        self._stages = {}

    def save(self, stage):
        key = (str(stage.job_id), stage.stage_name.value)
        self._stages[key] = stage

    def find_by_job_and_name(self, job_id, stage_name):
        return self._stages.get((str(job_id), stage_name.value))


class MockAuditRepo:
    def __init__(self):
        self._events = []

    def save(self, event):
        self._events.append(event)

    def find_by_job(self, job_id):
        return [e for e in self._events if str(e.job_id) == str(job_id)]


class MockJobRepo:
    def __init__(self):
        self._jobs = {}

    def find_by_id(self, job_id):
        return self._jobs.get(str(job_id))

    def save(self, job):
        self._jobs[str(job.job_id)] = job


class MockUUIDGenerator:
    def generate(self):
        return uuid.uuid4()


class MockImageGroupRepo:
    """In-memory ImageGroup repository that supports increment_deploy_count."""

    def __init__(self):
        self._groups = {}
        self.session = type(
            "MockSession",
            (),
            {"commit": lambda self: None, "flush": lambda self: None},
        )()

    def save(self, image_group):
        self._groups[str(image_group.id)] = image_group

    def find_by_job_id(self, job_id):
        for ig in self._groups.values():
            if str(ig.job_id) == str(job_id):
                return ig
        return None

    def update_status(self, image_group_id, new_status):
        key = str(image_group_id)
        if key in self._groups:
            self._groups[key].status = new_status

    def increment_deploy_count(self, image_group_id):
        key = str(image_group_id)
        if key in self._groups:
            ig = self._groups[key]
            ig.deploy_count = (ig.deploy_count or 0) + 1
            ig.last_deployed_at = datetime.now(timezone.utc)

    def list_eligible_for_retention(self, max_age_days, min_keep_count):
        cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
        candidates = [
            ig for ig in self._groups.values()
            if not ig.is_protected
            and ig.deploy_count == 0
            and ig.created_at < cutoff
            and ig.status not in (
                ImageGroupStatus.CLEANED,
                ImageGroupStatus.CLEANING,
            )
        ]
        return candidates

    def list_by_status_all(self, status):
        return [
            ig for ig in self._groups.values()
            if ig.status == status
        ]


# --- Fixtures ---

@pytest.fixture
def mock_result_service():
    return MockResultService()


@pytest.fixture
def mock_stage_repo():
    return MockStageRepo()


@pytest.fixture
def mock_audit_repo():
    return MockAuditRepo()


@pytest.fixture
def mock_job_repo():
    return MockJobRepo()


@pytest.fixture
def mock_uuid_gen():
    return MockUUIDGenerator()


# =========================================================================
# Test Class: Deploy Count Increment on Deploy Success
# =========================================================================

class TestDeployCountIncrement:
    """ER-BSM-002 Story 4: deploy_count is incremented on deploy success."""

    def test_deploy_success_increments_deploy_count(self):
        """On deploy success, deploy_count should go from 0 to 1."""
        job_id = JobId(str(uuid.uuid4()))

        stage_repo = MockStageRepo()
        stage = Stage(
            job_id=job_id,
            stage_name=StageName("deploy"),
            stage_state=StageState.IN_PROGRESS,
            attempt=1,
        )
        stage_repo.save(stage)

        ig_repo = MockImageGroupRepo()
        ig = ImageGroup(
            id=ImageGroupId("test-cluster-v1"),
            job_id=job_id,
            status=ImageGroupStatus.DEPLOYING,
            deploy_count=0,
        )
        ig_repo.save(ig)

        poller = ResultPoller(
            result_service=MockResultService(),
            job_repo=MockJobRepo(),
            stage_repo=stage_repo,
            audit_repo=MockAuditRepo(),
            uuid_generator=MockUUIDGenerator(),
            poll_interval=1,
            image_group_repo=ig_repo,
        )

        result = PlaybookResult(
            job_id=str(job_id),
            stage_name="deploy",
            request_id=str(uuid.uuid4()),
            status="success",
            exit_code=0,
        )
        poller._on_result_received(result)

        saved_ig = ig_repo.find_by_job_id(job_id)
        assert saved_ig is not None
        assert saved_ig.deploy_count == 1, (
            f"Expected deploy_count=1, got {saved_ig.deploy_count}"
        )
        assert saved_ig.last_deployed_at is not None, (
            "last_deployed_at should be set on deploy success"
        )
        assert saved_ig.status == ImageGroupStatus.DEPLOYED

    def test_deploy_success_sets_last_deployed_at(self):
        """last_deployed_at should be a recent UTC timestamp."""
        job_id = JobId(str(uuid.uuid4()))
        before = datetime.now(timezone.utc)

        stage_repo = MockStageRepo()
        stage = Stage(
            job_id=job_id,
            stage_name=StageName("deploy"),
            stage_state=StageState.IN_PROGRESS,
            attempt=1,
        )
        stage_repo.save(stage)

        ig_repo = MockImageGroupRepo()
        ig = ImageGroup(
            id=ImageGroupId("test-cluster-v2"),
            job_id=job_id,
            status=ImageGroupStatus.DEPLOYING,
        )
        ig_repo.save(ig)

        poller = ResultPoller(
            result_service=MockResultService(),
            job_repo=MockJobRepo(),
            stage_repo=stage_repo,
            audit_repo=MockAuditRepo(),
            uuid_generator=MockUUIDGenerator(),
            poll_interval=1,
            image_group_repo=ig_repo,
        )

        result = PlaybookResult(
            job_id=str(job_id),
            stage_name="deploy",
            request_id=str(uuid.uuid4()),
            status="success",
            exit_code=0,
        )
        poller._on_result_received(result)

        after = datetime.now(timezone.utc)
        saved_ig = ig_repo.find_by_job_id(job_id)
        assert saved_ig.last_deployed_at is not None
        assert before <= saved_ig.last_deployed_at <= after

    def test_deploy_failure_does_not_increment_deploy_count(self):
        """On deploy failure, deploy_count stays at 0."""
        job_id = JobId(str(uuid.uuid4()))

        stage_repo = MockStageRepo()
        stage = Stage(
            job_id=job_id,
            stage_name=StageName("deploy"),
            stage_state=StageState.IN_PROGRESS,
            attempt=1,
        )
        stage_repo.save(stage)

        ig_repo = MockImageGroupRepo()
        ig = ImageGroup(
            id=ImageGroupId("test-cluster-v3"),
            job_id=job_id,
            status=ImageGroupStatus.DEPLOYING,
            deploy_count=0,
        )
        ig_repo.save(ig)

        poller = ResultPoller(
            result_service=MockResultService(),
            job_repo=MockJobRepo(),
            stage_repo=stage_repo,
            audit_repo=MockAuditRepo(),
            uuid_generator=MockUUIDGenerator(),
            poll_interval=1,
            image_group_repo=ig_repo,
        )

        result = PlaybookResult(
            job_id=str(job_id),
            stage_name="deploy",
            request_id=str(uuid.uuid4()),
            status="failed",
            exit_code=1,
        )
        poller._on_result_received(result)

        saved_ig = ig_repo.find_by_job_id(job_id)
        assert saved_ig.deploy_count == 0, (
            "deploy_count should NOT be incremented on failure"
        )
        assert saved_ig.last_deployed_at is None, (
            "last_deployed_at should NOT be set on failure"
        )

    def test_deploy_success_without_image_group_repo(self):
        """If no image_group_repo is wired, deploy success is a no-op."""
        job_id = JobId(str(uuid.uuid4()))

        stage_repo = MockStageRepo()
        stage = Stage(
            job_id=job_id,
            stage_name=StageName("deploy"),
            stage_state=StageState.IN_PROGRESS,
            attempt=1,
        )
        stage_repo.save(stage)

        poller = ResultPoller(
            result_service=MockResultService(),
            job_repo=MockJobRepo(),
            stage_repo=stage_repo,
            audit_repo=MockAuditRepo(),
            uuid_generator=MockUUIDGenerator(),
            poll_interval=1,
            # No image_group_repo
        )

        result = PlaybookResult(
            job_id=str(job_id),
            stage_name="deploy",
            request_id=str(uuid.uuid4()),
            status="success",
            exit_code=0,
        )
        # Should not raise
        poller._on_result_received(result)


# =========================================================================
# Test Class: Retention Eligibility Logic
# =========================================================================

class TestRetentionEligibility:
    """ER-BSM-002 Story 4: Retention evaluation criteria."""

    def test_aged_undeployed_unprotected_is_eligible(self):
        """Image > 90 days, deploy_count=0, not protected → eligible."""
        repo = MockImageGroupRepo()
        ig = ImageGroup(
            id=ImageGroupId("old-group-v1"),
            job_id=JobId(str(uuid.uuid4())),
            status=ImageGroupStatus.BUILT,
            deploy_count=0,
            is_protected=False,
            created_at=datetime.now(timezone.utc) - timedelta(days=120),
        )
        repo.save(ig)

        eligible = repo.list_eligible_for_retention(
            max_age_days=90, min_keep_count=0
        )
        assert len(eligible) == 1
        assert str(eligible[0].id) == "old-group-v1"

    def test_deployed_image_not_eligible(self):
        """Image with deploy_count > 0 → NOT eligible regardless of age."""
        repo = MockImageGroupRepo()
        ig = ImageGroup(
            id=ImageGroupId("deployed-group-v1"),
            job_id=JobId(str(uuid.uuid4())),
            status=ImageGroupStatus.DEPLOYED,
            deploy_count=1,
            is_protected=False,
            created_at=datetime.now(timezone.utc) - timedelta(days=200),
        )
        repo.save(ig)

        eligible = repo.list_eligible_for_retention(
            max_age_days=90, min_keep_count=0
        )
        assert len(eligible) == 0

    def test_protected_image_not_eligible(self):
        """Protected image → NOT eligible regardless of age or deploy_count."""
        repo = MockImageGroupRepo()
        ig = ImageGroup(
            id=ImageGroupId("protected-group-v1"),
            job_id=JobId(str(uuid.uuid4())),
            status=ImageGroupStatus.BUILT,
            deploy_count=0,
            is_protected=True,
            created_at=datetime.now(timezone.utc) - timedelta(days=365),
        )
        repo.save(ig)

        eligible = repo.list_eligible_for_retention(
            max_age_days=90, min_keep_count=0
        )
        assert len(eligible) == 0

    def test_young_image_not_eligible(self):
        """Image younger than retention threshold → NOT eligible."""
        repo = MockImageGroupRepo()
        ig = ImageGroup(
            id=ImageGroupId("young-group-v1"),
            job_id=JobId(str(uuid.uuid4())),
            status=ImageGroupStatus.BUILT,
            deploy_count=0,
            is_protected=False,
            created_at=datetime.now(timezone.utc) - timedelta(days=30),
        )
        repo.save(ig)

        eligible = repo.list_eligible_for_retention(
            max_age_days=90, min_keep_count=0
        )
        assert len(eligible) == 0

    def test_cleaned_image_not_eligible(self):
        """Already-CLEANED image → NOT eligible (already removed)."""
        repo = MockImageGroupRepo()
        ig = ImageGroup(
            id=ImageGroupId("cleaned-group-v1"),
            job_id=JobId(str(uuid.uuid4())),
            status=ImageGroupStatus.CLEANED,
            deploy_count=0,
            is_protected=False,
            created_at=datetime.now(timezone.utc) - timedelta(days=120),
        )
        repo.save(ig)

        eligible = repo.list_eligible_for_retention(
            max_age_days=90, min_keep_count=0
        )
        assert len(eligible) == 0

    def test_mixed_images_only_eligible_returned(self):
        """Multiple images with mixed criteria — only eligible ones returned."""
        repo = MockImageGroupRepo()
        old_time = datetime.now(timezone.utc) - timedelta(days=120)
        new_time = datetime.now(timezone.utc) - timedelta(days=10)

        # Eligible: old, undeployed, not protected
        ig1 = ImageGroup(
            id=ImageGroupId("eligible-v1"),
            job_id=JobId(str(uuid.uuid4())),
            status=ImageGroupStatus.BUILT,
            deploy_count=0,
            is_protected=False,
            created_at=old_time,
        )
        # NOT eligible: deployed
        ig2 = ImageGroup(
            id=ImageGroupId("deployed-v1"),
            job_id=JobId(str(uuid.uuid4())),
            status=ImageGroupStatus.DEPLOYED,
            deploy_count=1,
            is_protected=False,
            created_at=old_time,
        )
        # NOT eligible: protected
        ig3 = ImageGroup(
            id=ImageGroupId("protected-v1"),
            job_id=JobId(str(uuid.uuid4())),
            status=ImageGroupStatus.BUILT,
            deploy_count=0,
            is_protected=True,
            created_at=old_time,
        )
        # NOT eligible: too young
        ig4 = ImageGroup(
            id=ImageGroupId("young-v1"),
            job_id=JobId(str(uuid.uuid4())),
            status=ImageGroupStatus.BUILT,
            deploy_count=0,
            is_protected=False,
            created_at=new_time,
        )
        # Eligible: old, undeployed, not protected, FAILED status
        ig5 = ImageGroup(
            id=ImageGroupId("eligible-failed-v1"),
            job_id=JobId(str(uuid.uuid4())),
            status=ImageGroupStatus.FAILED,
            deploy_count=0,
            is_protected=False,
            created_at=old_time,
        )

        for ig in (ig1, ig2, ig3, ig4, ig5):
            repo.save(ig)

        eligible = repo.list_eligible_for_retention(
            max_age_days=90, min_keep_count=0
        )
        eligible_ids = {str(ig.id) for ig in eligible}
        assert eligible_ids == {"eligible-v1", "eligible-failed-v1"}


# =========================================================================
# Test Class: Retention Config Loading
# =========================================================================

class TestRetentionConfigLoading:
    """Test _load_retention_config from cleanup_cron."""

    def test_default_values_when_no_config(self):
        """When config file doesn't exist, defaults are returned."""
        from cleanup_cron import _load_retention_config, DEFAULT_RETENTION_AGE_DAYS, DEFAULT_MIN_KEEP_COUNT

        with patch("cleanup_cron.Path.exists", return_value=False):
            config = _load_retention_config()

        assert config["retention_age_days"] == DEFAULT_RETENTION_AGE_DAYS
        assert config["min_keep_count"] == DEFAULT_MIN_KEEP_COUNT

    def test_custom_values_from_config(self):
        """When config file has retention section, values are read."""
        import yaml as _yaml
        from unittest.mock import mock_open
        from cleanup_cron import _load_retention_config

        config_content = _yaml.dump({
            "retention": {
                "retention_age_days": 180,
                "min_keep_count": 10,
            }
        })
        m = mock_open(read_data=config_content)
        with patch("cleanup_cron.Path.exists", return_value=True), \
             patch("builtins.open", m):
            config = _load_retention_config()

        assert config["retention_age_days"] == 180
        assert config["min_keep_count"] == 10

    def test_missing_retention_section_uses_defaults(self):
        """When retention section is missing from config, defaults are used."""
        import yaml as _yaml
        from unittest.mock import mock_open
        from cleanup_cron import _load_retention_config, DEFAULT_RETENTION_AGE_DAYS

        config_content = _yaml.dump({"cadence": {"enabled": True}})
        m = mock_open(read_data=config_content)
        with patch("cleanup_cron.Path.exists", return_value=True), \
             patch("builtins.open", m):
            config = _load_retention_config()

        assert config["retention_age_days"] == DEFAULT_RETENTION_AGE_DAYS

    def test_corrupt_config_falls_back_to_defaults(self):
        """When config file is corrupt, defaults are returned."""
        from cleanup_cron import _load_retention_config, DEFAULT_RETENTION_AGE_DAYS

        with patch("cleanup_cron.Path.exists", return_value=True), \
             patch("builtins.open", side_effect=IOError("corrupt")):
            config = _load_retention_config()

        assert config["retention_age_days"] == DEFAULT_RETENTION_AGE_DAYS
