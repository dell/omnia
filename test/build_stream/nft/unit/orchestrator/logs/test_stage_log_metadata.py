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

"""TC-UT-003: StageLogMetadataService (ER-BSM-003 FR-2.2)."""

import pytest

from core.jobs.entities.stage import Stage
from core.jobs.value_objects import JobId, StageName, StageState
from infra.logs.filesystem_adapter import FileSystemLogAdapter
from orchestrator.logs.use_cases import StageLogMetadata, StageLogMetadataService

pytestmark = pytest.mark.unit

JOB = "019bf590-1234-7890-abcd-ef1234567890"


@pytest.fixture(name="log_root")
def log_root_fixture(tmp_path):
    """Container log root with published logs for two stages."""
    root = tmp_path / "opt" / "omnia" / "build_stream" / "log"
    (root / JOB).mkdir(parents=True)
    (root / JOB / "parse.log").write_text("x\n" * 245, encoding="utf-8")
    (root / JOB / "build.log").write_text("y\n" * 1830, encoding="utf-8")
    return root


@pytest.fixture(name="service")
def service_fixture(log_root) -> StageLogMetadataService:
    """Service backed by a real adapter over the temporary root."""
    return StageLogMetadataService(FileSystemLogAdapter(log_root))


def _stage(name: str, state: StageState, file_name=None) -> Stage:
    """Stage whose log path uses the host prefix, as stored by the result poller."""
    path = f"/mnt/host_share/build_stream/log/{JOB}/{file_name}" if file_name else None
    return Stage(
        job_id=JobId(JOB), stage_name=StageName(name), stage_state=state, log_file_path=path
    )


class TestStageLogMetadata:
    """Scenarios from TC-UT-003."""

    def test_stages_with_and_without_logs(self, service):
        """GIVEN 3 stages, 2 with logs on disk THEN has_log/log_lines match the files."""
        stages = [
            _stage("parse-catalog", StageState.COMPLETED, "parse.log"),
            _stage("build-image", StageState.COMPLETED, "build.log"),
            _stage("deploy", StageState.COMPLETED, "deploy.log"),
        ]
        result = [service.describe(JOB, s) for s in stages]
        assert result == [
            StageLogMetadata(True, 245),
            StageLogMetadata(True, 1830),
            StageLogMetadata(False, 0),
        ]

    def test_in_progress_stage_has_no_log(self, service):
        """GIVEN a running stage THEN has_log=false even if a path is present."""
        stage = _stage("build-image", StageState.IN_PROGRESS, "build.log")
        assert service.describe(JOB, stage) == StageLogMetadata(False, 0)

    def test_pending_stage_without_path(self, service):
        """GIVEN a pending stage with no path THEN has_log=false."""
        assert service.describe(JOB, _stage("validate", StageState.PENDING)) == StageLogMetadata(
            False, 0
        )

    def test_host_path_translated_before_reading(self, service):
        """GIVEN a host path prefix that differs from the container root THEN it still resolves."""
        stage = _stage("build-image", StageState.FAILED, "build.log")
        assert service.describe(JOB, stage).has_log is True

    def test_publish_fallback_path_has_no_log(self, service):
        """GIVEN the /var/log/omnia fallback path THEN has_log=false."""
        stage = Stage(
            job_id=JobId(JOB),
            stage_name=StageName("build-image"),
            stage_state=StageState.COMPLETED,
            log_file_path="/var/log/omnia/image_build_manager/build.log",
        )
        assert service.describe(JOB, stage) == StageLogMetadata(False, 0)

    def test_path_violation_withheld_and_never_raises(self, service):
        """GIVEN a stored path outside the root THEN metadata is withheld without an error."""
        stage = Stage(
            job_id=JobId(JOB),
            stage_name=StageName("build-image"),
            stage_state=StageState.COMPLETED,
            log_file_path="/etc/passwd",
        )
        assert service.describe(JOB, stage) == StageLogMetadata(False, 0)
