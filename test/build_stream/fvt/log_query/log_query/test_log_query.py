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

"""FVT: Pipeline log query API (ER-BSM-003 TC-FVT-013..018, TC-FVT-020).

Read-only cases query the completed build-pipeline job from ``test_config.yml``.
Cases that plant fixture logs or exhaust the shared rate-limit budget require
``nft_allow_security_mutation: true`` and use one disposable job.

Secret-looking strings planted by these tests are synthetic fixtures.
"""

import uuid

import pytest

from library.functions import TestLogger, load_test_config, nft_func
from library.functions.log_query_func import (
    delete_planted_log,
    get_job,
    plant_stage_log,
    point_stage_at,
    query_job_logs,
    read_remote_file,
)
from library.vars import TEST_CASES as TC

DEFAULT_TAIL = 50
REDACTED = "***REDACTED***"


def _logger(case_name: str) -> TestLogger:
    """Create the structured logger for a registered case."""
    case = TC[case_name]
    return TestLogger(case["title"], case["id"])


def _entry(body: dict, stage: str) -> dict:
    """Return the response entry for one stage."""
    return next(s for s in body["stages"] if s["stage_name"] == stage)


def _ok(response: dict, logger: TestLogger, what: str) -> dict:
    """Assert an HTTP 200 JSON response and return its body."""
    if response["status"] != 200 or not response["json"]:
        logger.failed(f"{what}: expected HTTP 200, got {response['status']}")
    assert response["status"] == 200, f"{what}: HTTP {response['status']}"
    return response["json"]


@pytest.mark.sanity
@pytest.mark.order(1)
def test_log_query_default_and_custom_tail(host, log_query_state):
    """TC-FVT-013: default tail (50) and tail_lines=100 per stage."""
    tl = _logger("log_query_default_and_custom_tail")
    job_id = log_query_state.job_id

    body = _ok(query_job_logs(host, job_id), tl, "GET /logs")
    assert body["tail_lines"] == DEFAULT_TAIL
    for stage in log_query_state.logged_stages:
        entry = _entry(body, stage)
        expected = min(DEFAULT_TAIL, entry["total_lines"])
        assert entry["has_log"] is True, f"{stage}: has_log is false"
        assert entry["returned_lines"] == expected, (
            f"{stage}: expected {expected} lines, got {entry['returned_lines']}"
        )
    tl.check("Default tail applied to every stage with a published log")

    custom = _ok(query_job_logs(host, job_id, {"tail_lines": 100}), tl, "GET /logs?tail_lines=100")
    for stage in log_query_state.logged_stages:
        entry = _entry(custom, stage)
        assert entry["returned_lines"] == min(100, entry["total_lines"])
    tl.passed(f"Default and custom tail verified for {len(log_query_state.logged_stages)} stages")


@pytest.mark.sanity
@pytest.mark.order(2)
def test_log_query_full_retrieval(host, log_query_state):
    """TC-FVT-014: full=true returns the complete (bounded) stage log."""
    tl = _logger("log_query_full_retrieval")
    stage = log_query_state.logged_stages[0]
    body = _ok(
        query_job_logs(host, log_query_state.job_id, {"stage": stage, "full": "true"}),
        tl, "GET /logs?full=true",
    )
    entry = body["stages"][0]
    assert body["full"] is True and body["tail_lines"] is None
    if entry["truncated"]:
        assert len(entry["log_content"].encode("utf-8")) <= 10 * 1024 * 1024
        tl.passed(f"{stage}: log exceeds 10 MiB; response bounded and truncated=true")
        return
    assert entry["returned_lines"] == entry["total_lines"], (
        f"{stage}: returned {entry['returned_lines']} of {entry['total_lines']} lines"
    )
    tl.passed(f"{stage}: complete log returned ({entry['total_lines']} lines)")


@pytest.mark.sanity
@pytest.mark.order(3)
def test_log_query_stage_filter(host, log_query_state):
    """TC-FVT-015: stage filter returns exactly one stage entry."""
    tl = _logger("log_query_stage_filter")
    stage = log_query_state.logged_stages[-1]
    body = _ok(
        query_job_logs(host, log_query_state.job_id, {"stage": stage}), tl, "GET /logs?stage="
    )
    assert [s["stage_name"] for s in body["stages"]] == [stage]
    assert body["stages"][0]["returned_lines"] == min(
        DEFAULT_TAIL, body["stages"][0]["total_lines"]
    )
    tl.passed(f"stage={stage} returned a single entry with the default tail")


@pytest.mark.sanity
@pytest.mark.order(4)
def test_log_query_error_handling(host, log_query_state):
    """TC-FVT-016: error contract for invalid requests (read-only cases)."""
    tl = _logger("log_query_error_handling")
    job_id = log_query_state.job_id
    cases = [
        ("unknown job", query_job_logs(host, str(uuid.uuid4())), 404, "Job not found"),
        ("malformed job_id", query_job_logs(host, "nonexistent"), 400, None),
        ("unknown stage", query_job_logs(host, job_id, {"stage": "nonexistent-stage"}),
         404, "Stage not found for job"),
        ("tail_lines=0", query_job_logs(host, job_id, {"tail_lines": 0}),
         400, "tail_lines must be between 1 and 10000"),
        ("tail_lines=99999", query_job_logs(host, job_id, {"tail_lines": 99999}), 400, None),
        ("full+tail_lines", query_job_logs(host, job_id, {"full": "true", "tail_lines": 50}),
         400, "full and tail_lines are mutually exclusive"),
    ]
    for label, response, status, message in cases:
        assert response["status"] == status, f"{label}: expected {status}, got {response['status']}"
        if message:
            assert response["json"]["detail"]["message"] == message, label
        tl.check(f"{label}: HTTP {status}")

    unauthenticated = nft_func.bsm_request(host, "GET", f"/jobs/{job_id}/logs", token=None)
    assert unauthenticated["status"] == 401
    assert "stages" not in (unauthenticated["body"] or "")
    tl.passed("Invalid requests rejected with the documented status codes")


@pytest.mark.sanity
@pytest.mark.order(5)
def test_job_stage_log_metadata(host, log_query_state):
    """TC-FVT-018: GET /jobs/{id} reports has_log/log_lines matching the log API."""
    tl = _logger("log_query_stage_log_metadata")
    job_id = log_query_state.job_id
    job = _ok(get_job(host, job_id), tl, "GET /jobs/{id}")
    for stage in job["stages"]:
        assert "has_log" in stage and "log_lines" in stage, stage["stage_name"]
        if not stage["has_log"]:
            assert stage["log_lines"] == 0
    logs = _ok(query_job_logs(host, job_id), tl, "GET /logs")
    for stage in log_query_state.logged_stages:
        assert _entry(logs, stage)["total_lines"] == log_query_state.stage_lines[stage], stage
    tl.passed("has_log/log_lines agree with the log query API for every stage")


@pytest.mark.security
@pytest.mark.order(6)
def test_log_query_missing_log_file(host, disposable_job):
    """TC-FVT-018: a recorded log whose file was deleted reports has_log=false."""
    tl = _logger("log_query_missing_log_file")
    planted = plant_stage_log(host, disposable_job, "deploy", "fvt_deleted.log", b"line\n")
    assert planted["success"], planted["error"]
    assert delete_planted_log(host, disposable_job, "fvt_deleted.log")
    entry = _entry(_ok(get_job(host, disposable_job), tl, "GET /jobs/{id}"), "deploy")
    assert entry["has_log"] is False and entry["log_lines"] == 0
    tl.passed("Deleted stage log reported as has_log=false, log_lines=0")


@pytest.mark.security
@pytest.mark.order(7)
def test_log_query_response_redaction(host, disposable_job):
    """TC-FVT-020: secrets in a stage log are redacted in the response; disk is unchanged."""
    tl = _logger("log_query_response_redaction")
    dirty = (
        "TASK [deploy : configure] host 10.5.0.1\n"
        "password=cleartext\n"
        '{"gitlab_api_token": "glpat-fvtfixture0001"}\n'  # gitleaks:allow - test fixture
        "Authorization: Bearer eyJhbGciOiJSUzI1.eyJzdWIiOiJmdnQ.c2lnbmF0dXJl\n"
        "-----BEGIN RSA PRIVATE KEY-----\nMIIEfvtfixturebody\n-----END RSA PRIVATE KEY-----\n"
        f"already {REDACTED}\n"
    ).encode("utf-8")
    planted = plant_stage_log(host, disposable_job, "build-image", "fvt_redaction.log", dirty)
    assert planted["success"], planted["error"]

    body = _ok(
        query_job_logs(host, disposable_job, {"stage": "build-image", "full": "true"}),
        tl, "GET /logs (fixture)",
    )
    content = body["stages"][0]["log_content"]
    for secret in ("cleartext", "glpat-fvtfixture0001", "eyJhbGciOiJSUzI1", "MIIEfvtfixturebody"):
        assert secret not in content, f"Secret fragment returned: {secret[:6]}..."
    assert "host 10.5.0.1" in content, "Operational content must be preserved"
    assert f"already {REDACTED}" in content, "Existing markers must be unchanged"
    on_disk = read_remote_file(host, planted["path"])
    assert on_disk["success"] and on_disk["content"] == dirty, "Disk file was modified"
    tl.passed("Response redacted; operational data and the file on disk unchanged")


@pytest.mark.security
@pytest.mark.order(8)
def test_log_query_path_escape_rejected(host, disposable_job):
    """TC-FVT-016: a stored path outside the log root returns 409 without content."""
    tl = _logger("log_query_path_escape_rejected")
    updated = point_stage_at(host, disposable_job, "build-image", "/etc/passwd")
    assert updated["success"], updated["error"]
    response = query_job_logs(host, disposable_job)
    assert response["status"] == 409, f"Expected 409, got {response['status']}"
    assert response["json"]["detail"]["error"] == "LOG_PATH_VIOLATION"
    assert "root:" not in response["body"] and "/etc/passwd" not in response["body"]
    tl.passed("Path outside the log root rejected with 409; no content or path echoed")


@pytest.mark.security
@pytest.mark.order(9)
def test_log_query_rate_limit(host, log_query_state):
    """TC-FVT-017: exceeding the per-client budget returns 429 with Retry-After.

    Consumes the shared per-client budget for up to one minute, so it runs only
    when ``nft_allow_security_mutation: true`` is configured.
    """
    tl = _logger("log_query_rate_limit")
    config = load_test_config()
    if not config.get("nft_allow_security_mutation", False):
        tl.skipped("Set nft_allow_security_mutation: true to exhaust the rate-limit budget")
        pytest.skip("nft_allow_security_mutation is false")
    limit = int(config.get("log_query_rate_limit", 60))
    statuses = [
        query_job_logs(host, log_query_state.job_id, {"tail_lines": 1})["status"]
        for _ in range(limit + 1)
    ]
    assert 429 in statuses, f"No 429 after {limit + 1} requests: {sorted(set(statuses))}"
    assert statuses.index(429) <= limit, "429 returned only after the budget"
    tl.passed(f"HTTP 429 returned after {statuses.index(429)} requests within one minute")
