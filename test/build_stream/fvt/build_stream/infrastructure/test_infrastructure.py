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
Build Stream — Infrastructure Verification Tests.

TC_BS_001: Verify build_stream is enabled
TC_BS_002: Verify build_stream API health
TC_BS_003: Verify PostgreSQL database tables
TC_BS_004: Verify GitLab server running
TC_BS_005: Verify GitLab runner running

Adapted from molecule/build_stream/tests/sanity/test_build_stream_checks.py
"""

import pytest

from library.functions import (
    TestLogger,
    is_build_stream_enabled,
    check_build_stream_health,
    verify_postgres_tables,
    verify_gitlab_server_running,
    verify_gitlab_runner_running,
)
from library.messages import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
    SKIP_MSGS,
)


# =============================================================================
# TC_BS_001: BUILD STREAM ENABLED CHECK
# =============================================================================

@pytest.mark.sanity
@pytest.mark.infrastructure
@pytest.mark.order(1)
def test_build_stream_enabled(host):
    """TC_BS_001: Verify build_stream is enabled in build_stream_config.yml."""
    tl = TestLogger(TEST_NAMES["build_stream_enabled"], "TC_BS_001")

    tl.check("Checking if build_stream is enabled in build_stream_config.yml")

    if is_build_stream_enabled(host):
        tl.passed(LOG["build_stream_enabled_ok"])
    else:
        tl.failed(
            LOG["build_stream_enabled_fail"],
            "enable_build_stream is false or not set in build_stream_config.yml"
        )
        pytest.fail(ASSERT["build_stream_not_enabled"])


# =============================================================================
# TC_BS_002: BUILD STREAM API HEALTH CHECK
# =============================================================================

@pytest.mark.sanity
@pytest.mark.infrastructure
@pytest.mark.order(2)
def test_build_stream_health(host):
    """TC_BS_002: Verify build_stream API /health endpoint returns healthy."""
    tl = TestLogger(TEST_NAMES["bsm_api_health"], "TC_BS_002")

    if not is_build_stream_enabled(host):
        tl.skipped(SKIP_MSGS["build_stream_disabled"], "Test skipped")
        pytest.skip(SKIP_MSGS["build_stream_disabled"])

    tl.check("Checking build_stream API health endpoint")

    result = check_build_stream_health(host)

    if result["success"]:
        tl.passed(LOG["health_ok"], result.get("details", ""))
    else:
        tl.failed(
            LOG["health_fail"].format(error=result["error"]),
            f"URL: {result.get('url', 'N/A')}\nStatus: {result.get('status', 'N/A')}"
        )
        pytest.fail(ASSERT["health_failed"].format(error=result["error"]))


# =============================================================================
# TC_BS_003: POSTGRESQL DATABASE TABLES CHECK
# =============================================================================

@pytest.mark.sanity
@pytest.mark.infrastructure
@pytest.mark.order(3)
def test_postgres_tables(host):
    """TC_BS_003: Verify all expected tables exist in build_stream_db."""
    tl = TestLogger(TEST_NAMES["postgres_tables"], "TC_BS_003")

    if not is_build_stream_enabled(host):
        tl.skipped(SKIP_MSGS["build_stream_disabled"], "Test skipped")
        pytest.skip(SKIP_MSGS["build_stream_disabled"])

    tl.check("Checking PostgreSQL database tables in build_stream_db")

    result = verify_postgres_tables(host)

    if result["success"]:
        tl.passed(LOG["postgres_ok"], result.get("details", ""))
    else:
        tl.failed(
            LOG["postgres_fail"].format(
                missing=", ".join(result.get("missing_tables", []))
            ),
            result.get("details", "")
        )
        pytest.fail(ASSERT["postgres_failed"].format(error=result["error"]))


# =============================================================================
# TC_BS_004: GITLAB SERVER RUNNING CHECK
# =============================================================================

@pytest.mark.sanity
@pytest.mark.infrastructure
@pytest.mark.order(4)
def test_gitlab_server_running(host):
    """TC_BS_004: Verify GitLab server is running and accessible."""
    tl = TestLogger(TEST_NAMES["gitlab_server_running"], "TC_BS_004")

    if not is_build_stream_enabled(host):
        tl.skipped(SKIP_MSGS["build_stream_disabled"], "Test skipped")
        pytest.skip(SKIP_MSGS["build_stream_disabled"])

    tl.check("Checking GitLab server accessibility")

    result = verify_gitlab_server_running(host)

    if result["success"]:
        tl.passed(LOG["gitlab_server_ok"], result.get("details", ""))
    else:
        tl.failed(
            LOG["gitlab_server_fail"].format(error=result["error"]),
            f"URL: {result.get('url', 'N/A')}\nHTTP Code: {result.get('http_code', 'N/A')}"
        )
        pytest.fail(ASSERT["gitlab_server_failed"].format(error=result["error"]))


# =============================================================================
# TC_BS_005: GITLAB RUNNER RUNNING CHECK
# =============================================================================

@pytest.mark.sanity
@pytest.mark.infrastructure
@pytest.mark.order(5)
def test_gitlab_runner_running(host):
    """TC_BS_005: Verify GitLab runner container is running."""
    tl = TestLogger(TEST_NAMES["gitlab_runner_running"], "TC_BS_005")

    if not is_build_stream_enabled(host):
        tl.skipped(SKIP_MSGS["build_stream_disabled"], "Test skipped")
        pytest.skip(SKIP_MSGS["build_stream_disabled"])

    tl.check("Checking GitLab runner container status")

    result = verify_gitlab_runner_running(host)

    if result["success"]:
        tl.passed(LOG["gitlab_runner_ok"], result.get("details", ""))
    else:
        tl.failed(
            LOG["gitlab_runner_fail"].format(error=result["error"]),
            f"Container: {result.get('container', 'N/A')}\nStatus: {result.get('status', 'N/A')}"
        )
        pytest.fail(ASSERT["gitlab_runner_failed"].format(error=result["error"]))
