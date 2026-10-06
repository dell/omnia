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
Repo Manager Prepare — Pulp Infrastructure Verification.

Validates that --tags prepare created all required Pulp infrastructure:
  Pulp container running
  Pulp status healthy
  Pulp endpoint reachable
  Pulp CLI configured
  Pulp SSL certificates exist
  Pulp CLI can list RPM repositories
  Pulp API detailed health (DB, workers, content apps, storage)
  Credential collection and encryption
"""

import pytest

from library.functions import (
    TestLogger,
    check_pulp_container_running,
    check_pulp_status_healthy,
    check_pulp_endpoint_reachable,
    check_pulp_cli_configured,
    check_pulp_certificates_exist,
    check_pulp_cli_repository_list,
    check_pulp_api_detailed_status,
    check_credentials_present,
)
from library.vars import TEST_CASES as TC
from library.messages import (
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(1)
def test_pulp_container_running(host):
    """Verify Pulp container is running."""
    tc = TC["pulp_container_running"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_pulp_container_running(host)

    if result["success"]:
        tl.passed(LOG["pulp_container_running"], result["details"])
    else:
        tl.failed(LOG["pulp_container_not_running"], result["details"])

    assert result["success"], ASSERT["pulp_container_not_running"]


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(2)
def test_pulp_status_healthy(host):
    """Verify Pulp status is healthy."""
    tc = TC["pulp_status_healthy"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_pulp_status_healthy(host)

    if result["success"]:
        tl.passed(LOG["pulp_status_ok"], result["details"])
    else:
        tl.failed(LOG["pulp_status_failed"], result["details"])

    assert result["success"], ASSERT["pulp_status_failed"]


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(3)
def test_pulp_endpoint_reachable(host):
    """Verify Pulp endpoint reachable."""
    tc = TC["pulp_endpoint_reachable"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_pulp_endpoint_reachable(host)

    if result["success"]:
        tl.passed(LOG["pulp_endpoint_ok"], result["details"])
    else:
        tl.failed(LOG["pulp_endpoint_failed"], result["details"])

    assert result["success"], ASSERT["pulp_endpoint_not_reachable"]


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(4)
def test_pulp_cli_configured(host):
    """Verify Pulp CLI configured."""
    tc = TC["pulp_cli_configured"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_pulp_cli_configured(host)

    if result["success"]:
        tl.passed(LOG["pulp_cli_ok"], result["details"])
    else:
        tl.failed(LOG["pulp_cli_failed"], result["details"])

    assert result["success"], ASSERT["pulp_cli_not_configured"]


@pytest.mark.functional
@pytest.mark.positive
@pytest.mark.order(5)
def test_pulp_certificates_exist(host):
    """Verify Pulp SSL certificates exist."""
    tc = TC["pulp_certificates_exist"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_pulp_certificates_exist(host)

    if result["success"]:
        tl.passed(LOG["pulp_certs_ok"], result["details"])
    else:
        tl.failed(LOG["pulp_certs_missing"], result["details"])

    assert result["success"], ASSERT["pulp_certs_missing"]


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(6)
def test_pulp_cli_repository_list(host):
    """Verify Pulp CLI can list RPM repositories."""
    tc = TC["pulp_cli_repository_list"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_pulp_cli_repository_list(host)

    if result["success"]:
        tl.passed(LOG["pulp_cli_repo_list_ok"], result["details"])
    else:
        tl.failed(LOG["pulp_cli_repo_list_fail"], result["details"])

    assert result["success"], ASSERT["pulp_cli_repo_list_failed"]


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(7)
def test_pulp_api_detailed_status(host):
    """Verify Pulp API detailed health (DB, workers, content apps, storage)."""
    tc = TC["pulp_api_detailed_status"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_pulp_api_detailed_status(host)

    if result["success"]:
        tl.passed(LOG["pulp_api_detailed_ok"], result["details"])
    else:
        tl.failed(LOG["pulp_api_detailed_fail"], result["details"])

    assert result["success"], ASSERT["pulp_api_detailed_unhealthy"]


@pytest.mark.functional
@pytest.mark.positive
@pytest.mark.order(8)
def test_collect_credentials(host):
    """Verify collect_repo_credentials role functionality."""
    tc = TC["collect_credentials"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_credentials_present(host)

    if result["success"]:
        tl.passed("Collect repo credentials role works correctly", result["details"])
    else:
        tl.failed("Collect repo credentials role failed", result["details"])

    assert result["success"], "Collect repo credentials should manage credentials properly"


@pytest.mark.functional
@pytest.mark.positive
@pytest.mark.order(9)
def test_credential_encryption(host):
    """Verify credential encryption and vault handling."""
    tc = TC["credential_encryption"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_credentials_present(host)

    if result["success"]:
        tl.passed("Credential encryption and vault handling works", result["details"])
    else:
        tl.failed("Credential encryption failed", result["details"])

    assert result["success"], "Credentials should be properly encrypted and stored"
