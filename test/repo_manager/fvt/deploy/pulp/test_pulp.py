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
Repo Manager Deploy — Pulp Verification Tests.

Validates Pulp server state after ``--tags deploy``.
References: src/repo_manager/roles/deploy_pulp/tasks/verify_status.yml
            src/repo_manager/roles/deploy_pulp/tasks/preflight_checks.yml

  TC_DP_002: Verify Pulp container running after deploy
  TC_DP_003: Verify Pulp healthy after deploy (database connected)
  TC_DP_004: Verify Pulp port 2225 listening after deploy
  TC_DP_005: Verify Pulp CLI configured after deploy (binary + cli.toml)
  TC_DP_006: Verify Pulp API endpoint reachable after deploy
  TC_DP_007: Verify Pulp quadlet/systemd unit file exists
  TC_DP_008: Verify Pulp SSL certificates present (HTTPS mode)
  TC_DP_009: Verify Pulp data directories exist
"""

import pytest

from library.functions import (
    TestLogger,
    check_pulp_container_running,
    check_pulp_healthy,
    check_pulp_port_listening,
    check_pulp_cli_configured,
    check_pulp_api_endpoint,
    check_pulp_quadlet_exists,
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
    """TC_DP_002: Verify Pulp container running after deploy."""
    tc = TC["dp_pulp_container_running"]
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
    """TC_DP_003: Verify Pulp healthy after deploy."""
    tc = TC["dp_pulp_healthy"]
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
    """TC_DP_004: Verify Pulp port listening after deploy."""
    tc = TC["dp_pulp_port_listening"]
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
    """TC_DP_005: Verify Pulp CLI configured after deploy."""
    tc = TC["dp_pulp_cli_configured"]
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
    """TC_DP_006: Verify Pulp API endpoint reachable after deploy."""
    tc = TC["dp_pulp_api_endpoint"]
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
def test_pulp_quadlet_exists(host):
    """TC_DP_007: Verify Pulp quadlet/systemd unit file exists."""
    tc = TC["dp_pulp_quadlet_exists"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_pulp_quadlet_exists(host)

    if result["success"]:
        tl.passed(LOG["pulp_quadlet_ok"], result["details"])
    else:
        tl.failed(LOG["pulp_quadlet_missing"], result["details"])

    assert result["success"], result["details"]


@pytest.mark.sanity
@pytest.mark.order(7)
def test_pulp_certs(host):
    """TC_DP_008: Verify Pulp SSL certificates present (HTTPS mode)."""
    tc = TC["dp_pulp_certs"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_pulp_certs(host)

    if result["success"]:
        tl.passed(LOG["pulp_certs_ok"], result["details"])
    else:
        tl.failed(LOG["pulp_certs_missing"], result["details"])

    assert result["success"], result["details"]


@pytest.mark.sanity
@pytest.mark.order(8)
def test_pulp_directories(host):
    """TC_DP_009: Verify Pulp data directories exist."""
    tc = TC["dp_pulp_directories"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_pulp_directories(host)

    if result["success"]:
        tl.passed(LOG["pulp_dirs_ok"], result["details"])
    else:
        tl.failed(LOG["pulp_dirs_missing"], result["details"])

    assert result["success"], result["details"]
