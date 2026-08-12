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
Repo Manager — Pulp Verification Tests.

Validates Pulp server state after full end-to-end deployment:
  TC_RM_002: Verify Pulp container is running
  TC_RM_003: Verify Pulp is healthy
  TC_RM_004: Verify Pulp port 2225 is listening
  TC_RM_005: Verify Pulp CLI is configured
  TC_RM_006: Verify Pulp API endpoint is reachable
  TC_RM_007: Verify Pulp SSL certificates present
  TC_RM_008: Verify Pulp data directories exist
"""

import pytest

from library.functions import (
    TestLogger,
    check_pulp_container_running,
    check_pulp_healthy,
    check_pulp_port_listening,
    check_pulp_cli_configured,
    check_pulp_api_endpoint,
    check_pulp_certs,
    check_pulp_directories,
)
from library.vars import TEST_CASES as TC
from library.vars.common_vars import PULP_CONTAINER
from library.messages import (
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.sanity
@pytest.mark.order(1)
def test_pulp_container_running(host):
    """TC_RM_002: Verify Pulp container is running."""
    tc = TC["rm_pulp_container_running"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_pulp_container_running(host)

    if result["success"]:
        tl.passed(
            LOG["container_running"].format(container=PULP_CONTAINER),
            result["details"],
        )
    else:
        tl.failed(
            LOG["container_not_running"].format(container=PULP_CONTAINER),
            result.get("error", ""),
        )

    assert result["success"], ASSERT["container_not_running"].format(
        container=PULP_CONTAINER, status=result.get("status", "unknown"),
    )


@pytest.mark.sanity
@pytest.mark.order(2)
def test_pulp_healthy(host):
    """TC_RM_003: Verify Pulp is healthy."""
    tc = TC["rm_pulp_healthy"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_pulp_healthy(host)

    if result["success"]:
        tl.passed(LOG["pulp_healthy_ok"], result["details"])
    else:
        tl.failed(LOG["pulp_not_healthy"], result.get("error", ""))

    assert result["success"], result.get("error", result["details"])


@pytest.mark.sanity
@pytest.mark.order(3)
def test_pulp_port_listening(host):
    """TC_RM_004: Verify Pulp port 2225 is listening."""
    tc = TC["rm_pulp_port_listening"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_pulp_port_listening(host)

    if result["success"]:
        tl.passed(LOG["pulp_port_ok"].format(port=2225), result["details"])
    else:
        tl.failed(LOG["pulp_port_not_listening"].format(port=2225), result.get("error", ""))

    assert result["success"], result.get("error", result["details"])


@pytest.mark.sanity
@pytest.mark.order(4)
def test_pulp_cli_configured(host):
    """TC_RM_005: Verify Pulp CLI is configured."""
    tc = TC["rm_pulp_cli_configured"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_pulp_cli_configured(host)

    if result["success"]:
        tl.passed(LOG["pulp_cli_ok"], result["details"])
    else:
        tl.failed(LOG["pulp_cli_missing"], result.get("error", ""))

    assert result["success"], result.get("error", result["details"])


@pytest.mark.sanity
@pytest.mark.order(5)
def test_pulp_api_endpoint(host):
    """TC_RM_006: Verify Pulp API endpoint is reachable."""
    tc = TC["rm_pulp_api_endpoint"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_pulp_api_endpoint(host)

    if result["success"]:
        tl.passed(
            LOG["pulp_api_ok"].format(protocol=result.get("protocol", "unknown")),
            result["details"],
        )
    else:
        tl.failed(LOG["pulp_api_not_reachable"], result.get("error", ""))

    assert result["success"], ASSERT["pulp_api_failed"].format(
        error=result.get("error", ""),
    )


@pytest.mark.sanity
@pytest.mark.order(6)
def test_pulp_certs(host):
    """TC_RM_007: Verify Pulp SSL certificates present."""
    tc = TC["rm_pulp_certs"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_pulp_certs(host)

    if result["success"]:
        tl.passed(LOG["pulp_certs_ok"], result["details"])
    else:
        tl.failed(LOG["pulp_certs_missing"], result["details"])

    assert result["success"], result["details"]


@pytest.mark.sanity
@pytest.mark.order(7)
def test_pulp_directories(host):
    """TC_RM_008: Verify Pulp data directories exist."""
    tc = TC["rm_pulp_directories"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_pulp_directories(host)

    if result["success"]:
        tl.passed(LOG["pulp_dirs_ok"], result["details"])
    else:
        tl.failed(LOG["pulp_dirs_missing"], result["details"])

    assert result["success"], result["details"]
