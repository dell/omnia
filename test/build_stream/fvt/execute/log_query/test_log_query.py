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

"""
Execute — Pipeline log observability (ER-BSM-003; one test case per check).

target    the job under test: pipeline.build_job_id (verify-only), else the
          job of deploy_automatic / deploy_manual / build_automatic /
          build_manual run in this session (a deploy job holds all five
          playbook stage logs). No job: every read-only test is skipped
          with the command to run.
read-only GET /api/v1/jobs/{id}/logs tail, full, stage filter, error contract,
          scope enforcement and GET /jobs has_log/log_lines
          (TC-FVT-013..016, 018); the stage logs on disk (TC-FVT-019) and
          the GitLab CI job traces of the job (TC-FVT-021, 022).
fixtures  with nft_allow_security_mutation: true only: one disposable job
          (client_name omnia-fvt-log-query) gets synthetic fvt_*.log files
          and job_stages rows for the missing-file, unavailable-reason,
          redaction, truncation, path-violation, ownership, concurrency and
          rate-limit checks (TC-FVT-014, 016, 017, 018, 020); they are
          removed and the rows reset when the module ends. The rate-limit
          test is skipped while a GitLab pipeline runs.
Markers: log_observability; sanity (read-only) or security (fixtures).
"""

import pytest

from library.functions import (
    release_log_fixture_job,
    resolve_log_target,
    run_step,
    verify_ci_log_preview,
    verify_ci_log_templates,
    verify_log_concurrency_limit,
    verify_log_errors,
    verify_log_full,
    verify_log_full_truncation,
    verify_log_job_metadata,
    verify_log_job_ownership,
    verify_log_missing_file,
    verify_log_path_violation,
    verify_log_rate_limit,
    verify_log_response_redaction,
    verify_log_scopes,
    verify_log_stage_filter,
    verify_log_tail,
    verify_log_unavailable_reasons,
    verify_write_time_redaction,
)
from library.vars import TEST_CASES as TC


@pytest.fixture(scope="module", autouse=True)
def _release_fixture_job(host):
    """Remove the fixture logs and reset the disposable job after the suite."""
    yield
    release_log_fixture_job(host)


# =============================================================================
# Read-only checks on the job under test
# =============================================================================

@pytest.mark.log_observability
@pytest.mark.sanity
@pytest.mark.order(41101)
def test_log_query_target(host):
    """Resolve the job under test and the stages with a published log."""
    run_step(TC["log_query_target"], "Log query target", resolve_log_target, host)


@pytest.mark.log_observability
@pytest.mark.sanity
@pytest.mark.order(41102)
def test_log_query_default_and_custom_tail(host):
    """TC-FVT-013: default, custom, 1 and max tail_lines per logged stage."""
    run_step(TC["log_query_default_and_custom_tail"], "Log query tail", verify_log_tail, host)


@pytest.mark.log_observability
@pytest.mark.sanity
@pytest.mark.order(41103)
def test_log_query_full_retrieval(host):
    """TC-FVT-014: full=true returns each complete log within the byte limit."""
    run_step(TC["log_query_full_retrieval"], "Log query full", verify_log_full, host)


@pytest.mark.log_observability
@pytest.mark.sanity
@pytest.mark.order(41104)
def test_log_query_stage_filter(host):
    """TC-FVT-015: ?stage= returns exactly that stage."""
    run_step(TC["log_query_stage_filter"], "Log query stage filter", verify_log_stage_filter,
             host)


@pytest.mark.log_observability
@pytest.mark.sanity
@pytest.mark.order(41106)
def test_log_query_error_handling(host):
    """TC-FVT-016: invalid job, stage, tail_lines, full, query and token."""
    run_step(TC["log_query_error_handling"], "Log query errors", verify_log_errors, host)


@pytest.mark.log_observability
@pytest.mark.sanity
@pytest.mark.order(41107)
def test_log_query_scope_enforced(host):
    """A catalog-only token gets 403; a job:write token gets 200."""
    run_step(TC["log_query_scope_enforced"], "Log query scopes", verify_log_scopes, host)


@pytest.mark.log_observability
@pytest.mark.sanity
@pytest.mark.order(41108)
def test_log_query_stage_log_metadata(host):
    """TC-FVT-018: GET /jobs has_log/log_lines agree with the log query API."""
    run_step(TC["log_query_stage_log_metadata"], "Stage log metadata", verify_log_job_metadata,
             host)


@pytest.mark.log_observability
@pytest.mark.sanity
@pytest.mark.order(41109)
def test_log_query_write_time_redaction(host):
    """TC-FVT-019: published and domain stage logs hold only sanitized output."""
    run_step(TC["log_query_write_time_redaction"], "Write-time redaction",
             verify_write_time_redaction, host)


@pytest.mark.log_observability
@pytest.mark.sanity
@pytest.mark.order(41110)
def test_log_query_ci_console_preview(host):
    """TC-FVT-021: playbook-stage CI jobs preview the last N log lines."""
    run_step(TC["log_query_ci_console_preview"], "CI log preview", verify_ci_log_preview, host)


@pytest.mark.log_observability
@pytest.mark.sanity
@pytest.mark.order(41111)
def test_log_query_ci_cli_templates(host):
    """TC-FVT-022: CI jobs print curl templates with placeholders and no credential."""
    run_step(TC["log_query_ci_cli_templates"], "CI log templates", verify_ci_log_templates,
             host)


# =============================================================================
# Fixture logs on a disposable job (nft_allow_security_mutation: true)
# =============================================================================

@pytest.mark.log_observability
@pytest.mark.security
@pytest.mark.order(41112)
def test_log_query_missing_log_file(host):
    """TC-FVT-018: a deleted log reports has_log=false and its stage query 404."""
    run_step(TC["log_query_missing_log_file"], "Missing stage log", verify_log_missing_file,
             host)


@pytest.mark.log_observability
@pytest.mark.security
@pytest.mark.order(41113)
def test_log_query_unavailable_reasons(host):
    """Pending, legacy (no path, no discovery), unpublished and binary logs."""
    run_step(TC["log_query_unavailable_reasons"], "Unavailable stage logs",
             verify_log_unavailable_reasons, host)


@pytest.mark.log_observability
@pytest.mark.security
@pytest.mark.order(41114)
def test_log_query_response_redaction(host):
    """TC-FVT-020: response-time redaction; markers kept; disk file unchanged."""
    run_step(TC["log_query_response_redaction"], "Response-time redaction",
             verify_log_response_redaction, host)


@pytest.mark.log_observability
@pytest.mark.security
@pytest.mark.order(41115)
def test_log_query_full_truncation(host):
    """TC-FVT-014: full=true above max_log_response_bytes is truncated."""
    run_step(TC["log_query_full_truncation"], "Full log truncation", verify_log_full_truncation,
             host)


@pytest.mark.log_observability
@pytest.mark.security
@pytest.mark.order(41116)
def test_log_query_path_escape_rejected(host):
    """TC-FVT-016: stored paths outside the job directory return 409 and are audited."""
    run_step(TC["log_query_path_escape_rejected"], "Log path violation",
             verify_log_path_violation, host)


@pytest.mark.log_observability
@pytest.mark.security
@pytest.mark.order(41117)
def test_log_query_non_owned_job(host):
    """TC-FVT-016: another client's job returns 404 Job not found (same body as unknown)."""
    run_step(TC["log_query_non_owned_job"], "Job ownership", verify_log_job_ownership, host)


@pytest.mark.log_observability
@pytest.mark.security
@pytest.mark.order(41118)
def test_log_query_concurrency_limit(host):
    """Parallel queries above log_query_max_concurrent return 503 with Retry-After."""
    run_step(TC["log_query_concurrency_limit"], "Log query concurrency",
             verify_log_concurrency_limit, host)


@pytest.mark.log_observability
@pytest.mark.security
@pytest.mark.order(41119)
def test_log_query_rate_limit(host):
    """TC-FVT-017: request log_query_rate_limit + 1 returns 429, then recovers."""
    run_step(TC["log_query_rate_limit"], "Log query rate limit", verify_log_rate_limit, host)
