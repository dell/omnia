# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
Repo Manager — Deploy scenario verification tests.

TC_RM_DP_000: Deploy repo_manager --tags deploy
TC_RM_DP_001: Verify Pulp container is running
TC_RM_DP_002: Verify Pulp status is healthy
TC_RM_DP_003: Verify Pulp endpoint reachable
TC_RM_DP_004: Verify Pulp CLI configured
TC_RM_DP_005: Verify Pulp SSL certificates exist
TC_RM_DP_006: Verify Pulp CLI can list RPM repositories
TC_RM_DP_007: Verify Pulp API detailed health (DB, workers, content apps, storage)
"""

import pytest

from library.functions import (
    TestLogger,
    run_playbook,
    check_pulp_container_running,
    check_pulp_status_healthy,
    check_pulp_endpoint_reachable,
    check_pulp_cli_configured,
    check_pulp_certificates_exist,
    check_pulp_cli_repository_list,
    check_pulp_api_detailed_status,
)
from library.messages import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(0)
def test_deploy_pulp(host):
    """TC_RM_DP_000: Deploy repo_manager --tags deploy."""
    tl = TestLogger(TEST_NAMES["pulp_container_running"], "TC_RM_DP_000")
    result = run_playbook(tag="deploy")

    if result["success"]:
        tl.passed("repo_manager --tags deploy completed", result.get("details", ""))
    else:
        tl.failed("repo_manager --tags deploy failed", result.get("error", ""))

    assert result["success"], result.get("error", "Playbook failed")


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(1)
def test_pulp_container_running(host):
    """TC_RM_DP_001: Verify Pulp container is running."""
    tl = TestLogger(TEST_NAMES["pulp_container_running"], "TC_RM_DP_001")
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
    """TC_RM_DP_002: Verify Pulp status is healthy."""
    tl = TestLogger(TEST_NAMES["pulp_status_healthy"], "TC_RM_DP_002")
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
    """TC_RM_DP_003: Verify Pulp endpoint reachable."""
    tl = TestLogger(TEST_NAMES["pulp_endpoint_reachable"], "TC_RM_DP_003")
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
    """TC_RM_DP_004: Verify Pulp CLI configured."""
    tl = TestLogger(TEST_NAMES["pulp_cli_configured"], "TC_RM_DP_004")
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
    """TC_RM_DP_005: Verify Pulp SSL certificates exist."""
    tl = TestLogger(TEST_NAMES["pulp_certificates_exist"], "TC_RM_DP_005")
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
    """TC_RM_DP_006: Verify Pulp CLI can list RPM repositories."""
    tl = TestLogger(TEST_NAMES["pulp_cli_repository_list"], "TC_RM_DP_006")
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
    """TC_RM_DP_007: Verify Pulp API detailed health (DB, workers, content apps, storage)."""
    tl = TestLogger(TEST_NAMES["pulp_api_detailed_status"], "TC_RM_DP_007")
    result = check_pulp_api_detailed_status(host)

    if result["success"]:
        tl.passed(LOG["pulp_api_detailed_ok"], result["details"])
    else:
        tl.failed(LOG["pulp_api_detailed_fail"], result["details"])

    assert result["success"], ASSERT["pulp_api_detailed_unhealthy"]
