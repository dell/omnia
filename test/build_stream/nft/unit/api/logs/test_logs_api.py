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

"""API contract tests for GET /api/v1/jobs/{job_id}/logs (ER-BSM-003 FR-2.1, FR-3.2).

Secret-looking values are synthetic fixtures, not real credentials.
"""

# pylint: disable=too-few-public-methods,too-many-arguments,too-many-positional-arguments

import uuid

import pytest

from core.jobs.value_objects import JobId, StageName, StageState
from core.logs.redaction_patterns import REDACTED

pytestmark = pytest.mark.unit


def _lines(count: int) -> str:
    """Numbered log lines with trailing newline."""
    return "".join(f"line {i}\n" for i in range(1, count + 1))


def _stage(body: dict, name: str) -> dict:
    """Pick one stage entry from a response body."""
    return next(s for s in body["stages"] if s["stage_name"] == name)


class TestLogQuerySuccess:
    """Default tail, custom tail, full, and stage filter."""

    def test_default_tail_applied_to_each_stage(self, client, headers, create_job, publish_log):
        """GIVEN two published stage logs WHEN GET /logs THEN 50 lines per stage are returned."""
        job_id = create_job()
        publish_log(job_id, "parse-catalog", _lines(245))
        publish_log(job_id, "build-image", _lines(1830))

        response = client.get(f"/api/v1/jobs/{job_id}/logs", headers=headers)

        assert response.status_code == 200
        body = response.json()
        assert body["tail_lines"] == 50
        build = _stage(body, "build-image")
        assert build["has_log"] is True
        assert build["returned_lines"] == 50
        assert build["total_lines"] == 1830
        assert build["truncated"] is True
        assert build["log_content"].splitlines()[-1] == "line 1830"
        assert _stage(body, "parse-catalog")["total_lines"] == 245
        pending = _stage(body, "deploy")
        assert pending["has_log"] is False
        assert pending["unavailable_reason"] == "NOT_YET_AVAILABLE"

    def test_custom_tail_lines(self, client, headers, create_job, publish_log):
        """GIVEN tail_lines=100 THEN the last 100 lines are returned, or all when shorter."""
        job_id = create_job()
        publish_log(job_id, "build-image", _lines(1830))
        publish_log(job_id, "parse-catalog", _lines(30))

        body = client.get(
            f"/api/v1/jobs/{job_id}/logs?tail_lines=100", headers=headers
        ).json()

        assert _stage(body, "build-image")["returned_lines"] == 100
        short = _stage(body, "parse-catalog")
        assert short["returned_lines"] == 30
        assert short["truncated"] is False

    def test_full_log_for_stage(self, client, headers, create_job, publish_log):
        """GIVEN full=true and stage THEN the whole stage log is returned untruncated."""
        job_id = create_job()
        publish_log(job_id, "build-image", _lines(1830))

        response = client.get(
            f"/api/v1/jobs/{job_id}/logs?stage=build-image&full=true", headers=headers
        )

        body = response.json()
        assert response.status_code == 200
        assert body["full"] is True
        assert body["tail_lines"] is None
        entry = body["stages"][0]
        assert entry["returned_lines"] == entry["total_lines"] == 1830
        assert entry["truncated"] is False

    def test_stage_filter_returns_one_entry(self, client, headers, create_job, publish_log):
        """GIVEN stage=build-image THEN only that stage is returned."""
        job_id = create_job()
        publish_log(job_id, "build-image", _lines(80))
        publish_log(job_id, "parse-catalog", _lines(10))

        body = client.get(
            f"/api/v1/jobs/{job_id}/logs?stage=build-image", headers=headers
        ).json()

        assert [s["stage_name"] for s in body["stages"]] == ["build-image"]
        assert body["stages"][0]["returned_lines"] == 50


class TestLogQueryRedaction:
    """Response-time redaction through the real stack (FR-3.2)."""

    def test_secrets_redacted_and_disk_unchanged(
        self, client, headers, create_job, publish_log, log_root
    ):
        """GIVEN a log with secrets THEN the response is redacted and the file is untouched."""
        job_id = create_job()
        dirty = (
            "TASK [deploy : configure] host 10.5.0.1\n"
            "password=cleartext\n"
            '{"gitlab_api_token": "glpat-abc123secret"}\n'  # gitleaks:allow - test fixture
            "Authorization: Bearer eyJhbGciOiJSUzI1.eyJzdWIiOiJ4eXo.c2lnbmF0dXJl\n"
            "-----BEGIN RSA PRIVATE KEY-----\nMIIEsecretbody\n-----END RSA PRIVATE KEY-----\n"
            f"already {REDACTED}\n"
        )
        name = publish_log(job_id, "build-image", dirty)

        body = client.get(
            f"/api/v1/jobs/{job_id}/logs?stage=build-image&full=true", headers=headers
        ).json()

        content = body["stages"][0]["log_content"]
        for secret in ("cleartext", "glpat-abc123secret", "eyJhbGciOiJSUzI1", "MIIEsecretbody"):  # gitleaks:allow - test fixture
            assert secret not in content
        assert "password=" + REDACTED in content
        assert "host 10.5.0.1" in content
        assert f"already {REDACTED}" in content
        assert (log_root / job_id / name).read_text(encoding="utf-8") == dirty


class TestLogQueryErrors:
    """Error contract from ER-BSM-003 FR-2.1 / HLD 4.3."""

    def test_non_owned_job_returns_404(self, client, create_job, publish_log):
        """GIVEN a job owned by another client THEN 404 Job not found."""
        job_id = create_job()
        publish_log(job_id, "build-image", _lines(5))
        response = client.get(
            f"/api/v1/jobs/{job_id}/logs", headers={"Authorization": "Bearer someone-else"}
        )
        assert response.status_code == 404
        assert response.json()["detail"]["message"] == "Job not found"

    def test_unknown_job_returns_404(self, client, headers):
        """GIVEN a well-formed but unknown job ID THEN 404."""
        response = client.get(f"/api/v1/jobs/{uuid.uuid4()}/logs", headers=headers)
        assert response.status_code == 404
        assert response.json()["detail"]["error"] == "JOB_NOT_FOUND"

    def test_malformed_job_id_returns_400(self, client, headers):
        """GIVEN a non-UUID job ID THEN 400 INVALID_JOB_ID (existing job API behaviour)."""
        response = client.get("/api/v1/jobs/nonexistent/logs", headers=headers)
        assert response.status_code == 400
        assert response.json()["detail"]["error"] == "INVALID_JOB_ID"

    def test_unknown_stage_returns_404(self, client, headers, create_job):
        """GIVEN stage=nonexistent-stage THEN 404 Stage not found for job."""
        job_id = create_job()
        response = client.get(
            f"/api/v1/jobs/{job_id}/logs?stage=nonexistent-stage", headers=headers
        )
        assert response.status_code == 404
        assert response.json()["detail"]["message"] == "Stage not found for job"

    def test_running_stage_returns_404_not_yet_available(self, client, headers, create_job):
        """GIVEN a stage without a published log THEN 404 Stage log not yet available."""
        job_id = create_job()
        response = client.get(f"/api/v1/jobs/{job_id}/logs?stage=deploy", headers=headers)
        assert response.status_code == 404
        assert response.json()["detail"]["message"] == "Stage log not yet available"

    def test_unauthenticated_returns_401(self, unauth_client):
        """GIVEN no JWT THEN 401 and no content."""
        response = unauth_client.get(f"/api/v1/jobs/{uuid.uuid4()}/logs")
        assert response.status_code == 401
        assert "stages" not in response.json()

    @pytest.mark.parametrize("tail_lines", [0, 10001])
    def test_tail_lines_out_of_range_returns_400(self, client, headers, create_job, tail_lines):
        """GIVEN tail_lines outside 1..10000 THEN 400 with the contract message."""
        job_id = create_job()
        response = client.get(
            f"/api/v1/jobs/{job_id}/logs?tail_lines={tail_lines}", headers=headers
        )
        assert response.status_code == 400
        assert response.json()["detail"]["message"] == "tail_lines must be between 1 and 10000"

    def test_full_and_tail_lines_returns_400(self, client, headers, create_job):
        """GIVEN full=true and tail_lines THEN 400 mutually exclusive."""
        job_id = create_job()
        response = client.get(
            f"/api/v1/jobs/{job_id}/logs?full=true&tail_lines=50", headers=headers
        )
        assert response.status_code == 400
        assert response.json()["detail"]["message"] == "full and tail_lines are mutually exclusive"

    def test_path_escape_returns_409_without_path(self, client, headers, create_job, publish_log):
        """GIVEN a stored path outside the log root THEN 409 and the path is not echoed."""
        job_id = create_job()
        publish_log(job_id, "build-image", stored_path="/etc/passwd")
        response = client.get(f"/api/v1/jobs/{job_id}/logs", headers=headers)
        assert response.status_code == 409
        assert response.json()["detail"]["error"] == "LOG_PATH_VIOLATION"
        assert "/etc/passwd" not in response.text
        assert "root:" not in response.text

    def test_binary_log_returns_422(self, client, headers, create_job, publish_log):
        """GIVEN a binary stage log THEN 422 LOG_CONTENT_UNREADABLE."""
        job_id = create_job()
        publish_log(job_id, "build-image", raw=b"\x00\x01binary")
        response = client.get(
            f"/api/v1/jobs/{job_id}/logs?stage=build-image", headers=headers
        )
        assert response.status_code == 422
        assert response.json()["detail"]["error"] == "LOG_CONTENT_UNREADABLE"

    def test_legacy_stage_without_path_returns_404(
        self, client, headers, create_job, stage_repo
    ):
        """GIVEN a completed pre-ER-BSM-003 stage with no log path THEN 404 (no discovery)."""
        job_id = create_job()
        stage = stage_repo.find_by_job_and_name(JobId(job_id), StageName("build-image"))
        stage.stage_state = StageState.COMPLETED
        stage_repo.save(stage)
        response = client.get(
            f"/api/v1/jobs/{job_id}/logs?stage=build-image", headers=headers
        )
        assert response.status_code == 404
        assert response.json()["detail"]["message"] == "Log file not available for this stage"


class TestLogQueryLimits:
    """Rate limit (429) and concurrency limit (503)."""

    @pytest.fixture
    def rate_limit(self):
        """Lower limits so the test stays fast."""
        return {"per_minute": 3, "concurrent": 5}

    def test_rate_limit_returns_429(self, client, headers, create_job):
        """GIVEN the per-client budget is used THEN 429 with Retry-After."""
        job_id = create_job()
        for _ in range(3):
            assert client.get(f"/api/v1/jobs/{job_id}/logs", headers=headers).status_code == 200
        response = client.get(f"/api/v1/jobs/{job_id}/logs", headers=headers)
        assert response.status_code == 429
        assert response.json()["detail"]["message"] == "Rate limit exceeded"
        assert int(response.headers["Retry-After"]) >= 1


class TestConcurrencyLimit:
    """503 when no concurrency slot is free."""

    @pytest.fixture
    def rate_limit(self):
        """Allow a single concurrent request."""
        return {"per_minute": 60, "concurrent": 1}

    def test_concurrency_limit_returns_503(self, client, headers, create_job):
        """GIVEN every slot is held THEN 503 with Retry-After."""
        from api.logs.dependencies import get_concurrency_limiter  # pylint: disable=import-outside-toplevel
        from main import app  # pylint: disable=import-outside-toplevel

        job_id = create_job()
        limiter = app.dependency_overrides[get_concurrency_limiter]()
        with limiter.slot():
            response = client.get(f"/api/v1/jobs/{job_id}/logs", headers=headers)
        assert response.status_code == 503
        assert response.headers["Retry-After"] == "1"
        assert client.get(f"/api/v1/jobs/{job_id}/logs", headers=headers).status_code == 200
