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
Build Stream — Prepare Infrastructure Verification Tests.

TC_PR_002: Verify omnia_build_stream container running after prepare
TC_PR_003: Verify omnia_postgres container running after prepare
TC_PR_004: Verify build_stream API health after prepare
TC_PR_005: Verify PostgreSQL tables after prepare
TC_PR_006: Verify service ports listening after prepare
TC_PR_007: Verify build_stream_config.yml exists on target
"""

import pytest

from library.functions import (
    TestLogger,
    check_bsm_container,
    check_postgres_container,
    check_build_stream_health,
    verify_postgres_tables,
    check_ports_listening,
    check_input_config_exists,
)
from library.vars.common_vars import BSM_CONTAINER, POSTGRES_CONTAINER
from library.messages import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


# =============================================================================
# TC_PR_002: BSM CONTAINER RUNNING
# =============================================================================

@pytest.mark.sanity
@pytest.mark.infrastructure
@pytest.mark.order(1)
def test_bsm_container_after_prepare(host):
    """TC_PR_002: Verify omnia_build_stream container running after prepare."""
    tl = TestLogger(TEST_NAMES["bsm_container_running"], "TC_PR_002")
    result = check_bsm_container(host)

    if result["success"]:
        tl.passed(
            LOG["container_running"].format(container=BSM_CONTAINER),
            result["status"],
        )
    else:
        tl.failed(
            LOG["container_not_running"].format(container=BSM_CONTAINER),
            result.get("error", ""),
        )

    assert result["success"], ASSERT["container_not_running"].format(
        container=BSM_CONTAINER, status=result["status"],
    )


# =============================================================================
# TC_PR_003: POSTGRES CONTAINER RUNNING
# =============================================================================

@pytest.mark.sanity
@pytest.mark.infrastructure
@pytest.mark.order(2)
def test_postgres_container_after_prepare(host):
    """TC_PR_003: Verify omnia_postgres container running after prepare."""
    tl = TestLogger(TEST_NAMES["postgres_container_running"], "TC_PR_003")
    result = check_postgres_container(host)

    if result["success"]:
        tl.passed(
            LOG["container_running"].format(container=POSTGRES_CONTAINER),
            result["status"],
        )
    else:
        tl.failed(
            LOG["container_not_running"].format(container=POSTGRES_CONTAINER),
            result.get("error", ""),
        )

    assert result["success"], ASSERT["container_not_running"].format(
        container=POSTGRES_CONTAINER, status=result["status"],
    )


# =============================================================================
# TC_PR_004: API HEALTH AFTER PREPARE
# =============================================================================

@pytest.mark.sanity
@pytest.mark.infrastructure
@pytest.mark.order(3)
def test_api_health_after_prepare(host):
    """TC_PR_004: Verify build_stream API health after prepare."""
    tl = TestLogger(TEST_NAMES["bsm_api_health"], "TC_PR_004")
    result = check_build_stream_health(host)

    if result["success"]:
        tl.passed(LOG["health_ok"], result.get("details", ""))
    else:
        tl.failed(
            LOG["health_fail"].format(error=result["error"]),
            f"URL: {result.get('url', 'N/A')}",
        )

    assert result["success"], ASSERT["health_failed"].format(
        error=result["error"],
    )


# =============================================================================
# TC_PR_005: POSTGRES TABLES AFTER PREPARE
# =============================================================================

@pytest.mark.sanity
@pytest.mark.infrastructure
@pytest.mark.order(4)
def test_postgres_tables_after_prepare(host):
    """TC_PR_005: Verify PostgreSQL tables after prepare."""
    tl = TestLogger(TEST_NAMES["postgres_tables"], "TC_PR_005")
    result = verify_postgres_tables(host)

    if result["success"]:
        tl.passed(LOG["postgres_ok"], result.get("details", ""))
    else:
        tl.failed(
            LOG["postgres_fail"].format(
                missing=", ".join(result.get("missing_tables", []))
            ),
            result.get("details", ""),
        )

    assert result["success"], ASSERT["postgres_failed"].format(
        error=result["error"],
    )


# =============================================================================
# TC_PR_006: SERVICE PORTS LISTENING
# =============================================================================

@pytest.mark.sanity
@pytest.mark.infrastructure
@pytest.mark.order(5)
def test_ports_listening_after_prepare(host):
    """TC_PR_006: Verify service ports listening after prepare."""
    tl = TestLogger(TEST_NAMES["ports_listening"], "TC_PR_006")
    result = check_ports_listening(host)

    if result["success"]:
        tl.passed(LOG["ports_listening_ok"], result.get("details", ""))
    else:
        tl.failed(
            LOG["ports_not_listening"].format(
                count=len(result.get("closed_ports", []))
            ),
            f"Closed ports: {result.get('closed_ports', [])}",
        )

    assert result["success"], (
        f"Ports not listening: {result.get('closed_ports', [])}"
    )


# =============================================================================
# TC_PR_007: INPUT CONFIG EXISTS
# =============================================================================

@pytest.mark.sanity
@pytest.mark.order(6)
def test_input_config_exists(host):
    """TC_PR_007: Verify build_stream_config.yml exists on target."""
    tl = TestLogger(TEST_NAMES["input_config_exists"], "TC_PR_007")
    result = check_input_config_exists(host)

    if result["success"]:
        tl.passed(LOG["input_config_ok"], result.get("details", ""))
    else:
        tl.failed(LOG["input_config_missing"], result.get("error", ""))

    assert result["success"], result["error"]
