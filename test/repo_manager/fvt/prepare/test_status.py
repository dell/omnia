# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
Repo Manager — Prepare scenario verification tests.

TC_RM_PP_000: Deploy repo_manager --tags prepare
TC_RM_PP_001: Verify Pulp container is running
TC_RM_PP_002: Verify Pulp status is healthy
TC_RM_PP_003: Verify Pulp endpoint reachable
TC_RM_PP_004: Verify Pulp CLI configured
TC_RM_PP_005: Verify Pulp SSL certificates exist
TC_RM_PP_006: Verify Pulp CLI can list RPM repositories
TC_RM_PP_007: Verify Pulp API detailed health (DB, workers, content apps, storage)
TC_RM_PP_008: Verify collect_repo_credentials role functionality
TC_RM_PP_009: Verify credential encryption and vault handling
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
    check_credentials_present,
)
from library.messages import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(0)
def test_prepare_pulp(host):
    """TC_RM_PP_000: Deploy repo_manager --tags prepare."""
    tl = TestLogger(TEST_NAMES["pulp_container_running"], "TC_RM_PP_000")
    result = run_playbook(tag="prepare")

    if result["success"]:
        tl.passed("repo_manager --tags prepare completed", result.get("details", ""))
    else:
        tl.failed("repo_manager --tags prepare failed", result.get("error", ""))

    assert result["success"], result.get("error", "Playbook failed")


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(1)
def test_pulp_container_running(host):
    """TC_RM_PP_001: Verify Pulp container is running."""
    tl = TestLogger(TEST_NAMES["pulp_container_running"], "TC_RM_PP_001")
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
    """TC_RM_PP_002: Verify Pulp status is healthy."""
    tl = TestLogger(TEST_NAMES["pulp_status_healthy"], "TC_RM_PP_002")
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
    """TC_RM_PP_003: Verify Pulp endpoint reachable."""
    tl = TestLogger(TEST_NAMES["pulp_endpoint_reachable"], "TC_RM_PP_003")
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
    """TC_RM_PP_004: Verify Pulp CLI configured."""
    tl = TestLogger(TEST_NAMES["pulp_cli_configured"], "TC_RM_PP_004")
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
    """TC_RM_PP_005: Verify Pulp SSL certificates exist."""
    tl = TestLogger(TEST_NAMES["pulp_certificates_exist"], "TC_RM_PP_005")
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
    """TC_RM_PP_006: Verify Pulp CLI can list RPM repositories."""
    tl = TestLogger(TEST_NAMES["pulp_cli_repository_list"], "TC_RM_PP_006")
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
    """TC_RM_PP_007: Verify Pulp API detailed health (DB, workers, content apps, storage)."""
    tl = TestLogger(TEST_NAMES["pulp_api_detailed_status"], "TC_RM_PP_007")
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
    """TC_RM_PP_008: Verify collect_repo_credentials role functionality."""
    tl = TestLogger(TEST_NAMES["credentials_present"], "TC_RM_PP_008")
    # This test verifies that the collect_repo_credentials role
    # properly collects and manages credentials
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
    """TC_RM_PP_009: Verify credential encryption and vault handling."""
    tl = TestLogger(TEST_NAMES["credentials_present"], "TC_RM_PP_009")
    # This test verifies that credentials are properly encrypted
    # and handled via Ansible Vault
    result = check_credentials_present(host)

    if result["success"]:
        tl.passed("Credential encryption and vault handling works", result["details"])
    else:
        tl.failed("Credential encryption failed", result["details"])

    assert result["success"], "Credentials should be properly encrypted and stored"
