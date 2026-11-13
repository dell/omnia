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

"""GET /api/v1/jobs/{job_id} stage log metadata: has_log / log_lines (ER-BSM-003 FR-2.2)."""

import pytest

from core.jobs.value_objects import StageState

pytestmark = pytest.mark.unit


def _stage(body: dict, name: str) -> dict:
    """Pick one stage entry from a job response."""
    return next(s for s in body["stages"] if s["stage_name"] == name)


class TestJobStageLogMetadata:
    """FR-2.2 scenarios against the existing job detail endpoint."""

    def test_has_log_and_line_counts(self, client, headers, create_job, publish_log):
        """GIVEN published logs for two stages THEN has_log and log_lines are reported."""
        job_id = create_job()
        publish_log(job_id, "parse-catalog", "x\n" * 245)
        publish_log(job_id, "build-image", "y\n" * 1830)

        body = client.get(f"/api/v1/jobs/{job_id}", headers=headers).json()

        assert _stage(body, "parse-catalog")["has_log"] is True
        assert _stage(body, "parse-catalog")["log_lines"] == 245
        assert _stage(body, "build-image")["log_lines"] == 1830
        assert _stage(body, "deploy")["has_log"] is False
        assert _stage(body, "deploy")["log_lines"] == 0

    def test_deleted_log_file_reports_no_log(self, client, headers, create_job, publish_log):
        """GIVEN a recorded log path whose file was deleted THEN has_log=false, log_lines=0."""
        job_id = create_job()
        publish_log(job_id, "deploy")

        entry = _stage(client.get(f"/api/v1/jobs/{job_id}", headers=headers).json(), "deploy")

        assert entry["has_log"] is False
        assert entry["log_lines"] == 0

    def test_running_stage_reports_no_log(self, client, headers, create_job, publish_log):
        """GIVEN a stage still in progress THEN has_log=false."""
        job_id = create_job()
        publish_log(job_id, "build-image", "partial\n", state=StageState.IN_PROGRESS)

        entry = _stage(
            client.get(f"/api/v1/jobs/{job_id}", headers=headers).json(), "build-image"
        )

        assert entry["has_log"] is False

    def test_existing_fields_preserved(self, client, headers, create_job, publish_log):
        """Backward compatibility: log_file_path and other fields are still returned."""
        job_id = create_job()
        name = publish_log(job_id, "build-image", "ok\n")

        entry = _stage(
            client.get(f"/api/v1/jobs/{job_id}", headers=headers).json(), "build-image"
        )

        assert entry["log_file_path"].endswith(name)
        assert entry["stage_state"] == "COMPLETED"
