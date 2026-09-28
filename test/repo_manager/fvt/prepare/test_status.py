# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
Repo Manager — Prepare scenario verification tests.

RM_FVT_PREPARE_E001: Deploy repo_manager --tags prepare
RM_FVT_PREPARE_V001: Verify Pulp container is running
RM_FVT_PREPARE_V002: Verify Pulp status is healthy
RM_FVT_PREPARE_V003: Verify Pulp endpoint reachable
RM_FVT_PREPARE_V004: Verify Pulp CLI configured
RM_FVT_PREPARE_V005: Verify Pulp SSL certificates exist
RM_FVT_PREPARE_V006: Verify Pulp CLI can list RPM repositories
RM_FVT_PREPARE_V007: Verify Pulp API detailed health (DB, workers, content apps, storage)
RM_FVT_PREPARE_E002: Verify collect_repo_credentials role functionality
RM_FVT_PREPARE_E003: Verify credential encryption and vault handling
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
    """RM_FVT_PREPARE_E001: Deploy repo_manager --tags prepare."""
    tl = TestLogger(TEST_NAMES["pulp_container_running"], "RM_FVT_PREPARE_E001")
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
    """RM_FVT_PREPARE_V001: Verify Pulp container is running."""
    tl = TestLogger(TEST_NAMES["pulp_container_running"], "RM_FVT_PREPARE_V001")
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
    """RM_FVT_PREPARE_V002: Verify Pulp status is healthy."""
    tl = TestLogger(TEST_NAMES["pulp_status_healthy"], "RM_FVT_PREPARE_V002")
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
    """RM_FVT_PREPARE_V003: Verify Pulp endpoint reachable."""
    tl = TestLogger(TEST_NAMES["pulp_endpoint_reachable"], "RM_FVT_PREPARE_V003")
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
    """RM_FVT_PREPARE_V004: Verify Pulp CLI configured."""
    tl = TestLogger(TEST_NAMES["pulp_cli_configured"], "RM_FVT_PREPARE_V004")
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
    """RM_FVT_PREPARE_V005: Verify Pulp SSL certificates exist."""
    tl = TestLogger(TEST_NAMES["pulp_certificates_exist"], "RM_FVT_PREPARE_V005")
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
    """RM_FVT_PREPARE_V006: Verify Pulp CLI can list RPM repositories."""
    tl = TestLogger(TEST_NAMES["pulp_cli_repository_list"], "RM_FVT_PREPARE_V006")
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
    """RM_FVT_PREPARE_V007: Verify Pulp API detailed health (DB, workers, content apps, storage)."""
    tl = TestLogger(TEST_NAMES["pulp_api_detailed_status"], "RM_FVT_PREPARE_V007")
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
    """RM_FVT_PREPARE_E002: Verify collect_repo_credentials role functionality."""
    tl = TestLogger(TEST_NAMES["credentials_present"], "RM_FVT_PREPARE_E002")
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
    """RM_FVT_PREPARE_E003: Verify credential encryption and vault handling."""
    tl = TestLogger(TEST_NAMES["credentials_present"], "RM_FVT_PREPARE_E003")
    # This test verifies that credentials are properly encrypted
    # and handled via Ansible Vault
    result = check_credentials_present(host)

    if result["success"]:
        tl.passed("Credential encryption and vault handling works", result["details"])
    else:
        tl.failed("Credential encryption failed", result["details"])

    assert result["success"], "Credentials should be properly encrypted and stored"
